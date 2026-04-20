"""Celery tasks for async document generation.

The task receives a DocumentoGenerato.id and dispatches to the right
generator based on tipo_documento. Updates status through
pending -> in_progress -> completed, or rolls back to 'bozza' on failure
per US-2.8 AC3 (partial file discarded, user-friendly error recorded).
"""

import asyncio
import logging
import os
import traceback
import uuid
from datetime import datetime, timezone

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import async_session_factory
from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.dispatcher import get_generator_for
from app.services.survey_snapshot import compute_survey_snapshot_hash

logger = logging.getLogger(__name__)


def _friendly_error_for(exc: Exception) -> str:
    """Translate a raw exception into a short Italian line for the operator.

    The full traceback stays in the worker log; only this line ends up in
    the DB and the UI. Kept deliberately terse so it fits in a tooltip.
    """
    name = type(exc).__name__
    if isinstance(exc, FileNotFoundError):
        return "Template mancante o file di supporto non trovato. Contatta l'amministratore."
    if isinstance(exc, PermissionError):
        return "Permessi insufficienti sul disco di output. Contatta l'amministratore."
    if isinstance(exc, (TimeoutError, SoftTimeLimitExceeded)):
        return "Timeout durante la generazione (oltre 10 minuti). Riprova tra qualche minuto."
    # Generic fallback: expose just the exception class — never the message,
    # which can leak stack traces or SQL fragments.
    return f"Generazione non riuscita ({name}). Riprova o contatta l'amministratore."


async def _run_generation(document_id: uuid.UUID) -> None:
    """Async inner: load the doc record, run the generator, update status."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(DocumentoGenerato).where(DocumentoGenerato.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            logger.error("Document record not found: %s", document_id)
            return

        output_path: str | None = None
        try:
            doc.status = "in_progress"
            doc.generation_started_at = datetime.utcnow()
            doc.error_message = None  # clear any prior rollback note
            # US-5.2 AC2 — snapshot the survey state we're generating
            # against so we can detect drift on completion. Compute it
            # before any generator runs so the worker is comparing apples
            # to apples even if the generator takes minutes.
            try:
                doc.survey_snapshot_hash = await compute_survey_snapshot_hash(
                    doc.azienda_id, db
                )
                doc.stale_snapshot = False
            except Exception:  # pragma: no cover — defensive: never block gen on snapshot failures
                logger.exception("Snapshot hash compute failed for %s", doc.id)
                doc.survey_snapshot_hash = None
            await db.commit()

            # Dispatch to the right generator class. Forward the per-row
            # options dict (US-4.4) so generators like haccp_forms can pick
            # up subset selections that were posted with the request.
            generator = get_generator_for(
                doc.tipo_documento,
                doc.azienda_id,
                db,
                options=doc.options,
            )
            output_path = await generator.generate()

            doc.status = "completed"
            doc.file_path = output_path
            doc.file_name = os.path.basename(output_path)
            # Store bytes in Postgres so the API service can serve downloads
            # without needing access to the worker's filesystem (on Render
            # they run on separate disks).
            try:
                with open(output_path, "rb") as f:
                    doc.file_content = f.read()
            except OSError as read_err:
                logger.warning("Could not read generated file into DB: %s", read_err)
            doc.generation_completed_at = datetime.utcnow()
            # US-5.2 AC2 — re-hash and flag drift. If the survey changed
            # while the generator was running, the documents page will
            # render the "rigenera" banner so the operator can refresh.
            if doc.survey_snapshot_hash:
                try:
                    completion_hash = await compute_survey_snapshot_hash(
                        doc.azienda_id, db
                    )
                    if completion_hash != doc.survey_snapshot_hash:
                        doc.stale_snapshot = True
                        logger.info(
                            "Stale snapshot detected for %s (start=%s, end=%s)",
                            doc.id,
                            doc.survey_snapshot_hash[:12],
                            completion_hash[:12],
                        )
                except Exception:  # pragma: no cover — same defensive guard
                    logger.exception("Completion-hash compute failed for %s", doc.id)
            await db.commit()
            logger.info("Generated %s v%s -> %s", doc.tipo_documento, doc.versione, output_path)

            # Attempt Google Drive upload (best-effort)
            try:
                from app.services.gdrive_service import upload_generated_document
                gdrive_id = await upload_generated_document(doc, output_path)
                if gdrive_id:
                    doc.gdrive_file_id = gdrive_id
                    await db.commit()
            except Exception as drive_err:
                logger.warning("Google Drive upload failed (non-fatal): %s", drive_err)

        except Exception as e:
            # US-2.8 AC3: discard the partial file, roll status back to
            # "bozza", and log a user-friendly error message. The full
            # traceback stays in the worker log only.
            logger.error("Generation failed for %s: %s\n%s", document_id, e, traceback.format_exc())

            # Best-effort: remove a partially-written file if the generator
            # managed to open one before throwing. Swallow OSErrors because
            # the exact path may never have been created.
            if output_path and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError as rm_err:
                    logger.warning("Failed to remove partial %s: %s", output_path, rm_err)

            doc.status = "bozza"
            doc.file_path = None
            doc.file_content = None
            doc.file_name = None
            doc.error_message = _friendly_error_for(e)
            doc.generation_completed_at = datetime.utcnow()
            await db.commit()


# B2 fix: large docs (POS ~110 pages, HACCP ~90 pages) can take a while.
# `soft_time_limit` raises SoftTimeLimitExceeded inside the task so the
# generic except in _run_generation can still roll the row back to "bozza"
# with a "timeout" error_message instead of leaving it in_progress forever.
# `time_limit` is the hard ceiling — the worker is killed past that.
@celery_app.task(
    name="app.tasks.document_tasks.generate_document_task",
    soft_time_limit=600,  # 10 min — triggers a catchable exception
    time_limit=660,       # 11 min — hard kill (worker process terminated)
)
def generate_document_task(document_id: str) -> str:
    """Entry point from the API layer. Runs the async workflow in a new loop.

    Each call disposes the SQLAlchemy async engine first because asyncpg
    connections become bound to the event loop that opened them. Reusing the
    same engine across `asyncio.run()` calls (which create fresh loops)
    triggers `cannot perform operation: another operation is in progress`.
    """
    logger.info("generate_document_task started for %s", document_id)
    doc_uuid = uuid.UUID(document_id)

    async def _runner():
        from app.db.session import engine
        try:
            await engine.dispose()
        except Exception:
            pass
        await _run_generation(doc_uuid)
        try:
            await engine.dispose()
        except Exception:
            pass

    asyncio.run(_runner())
    return document_id
