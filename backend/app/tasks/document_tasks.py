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

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import async_session_factory
from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.dispatcher import get_generator_for

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
    if isinstance(exc, TimeoutError):
        return "Timeout durante la generazione. Riprova tra qualche minuto."
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
            await db.commit()

            # Dispatch to the right generator class
            generator = get_generator_for(doc.tipo_documento, doc.azienda_id, db)
            output_path = await generator.generate()

            doc.status = "completed"
            doc.file_path = output_path
            doc.generation_completed_at = datetime.utcnow()
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
            doc.error_message = _friendly_error_for(e)
            doc.generation_completed_at = datetime.utcnow()
            await db.commit()


@celery_app.task(name="app.tasks.document_tasks.generate_document_task")
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
