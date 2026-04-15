"""Celery tasks for async document generation.

The task receives a DocumentoGenerato.id and dispatches to the right
generator based on tipo_documento. Updates status through
pending -> in_progress -> completed / failed.
"""

import asyncio
import logging
import traceback
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import async_session_factory
from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.dispatcher import get_generator_for

logger = logging.getLogger(__name__)


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

        try:
            doc.status = "in_progress"
            doc.generation_started_at = datetime.now(timezone.utc)
            await db.commit()

            # Dispatch to the right generator class
            generator = get_generator_for(doc.tipo_documento, doc.azienda_id, db)
            output_path = await generator.generate()

            doc.status = "completed"
            doc.file_path = output_path
            doc.generation_completed_at = datetime.now(timezone.utc)
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
            logger.error("Generation failed for %s: %s\n%s", document_id, e, traceback.format_exc())
            doc.status = "failed"
            doc.file_path = f"ERROR: {type(e).__name__}: {str(e)[:500]}"
            doc.generation_completed_at = datetime.now(timezone.utc)
            await db.commit()


@celery_app.task(name="app.tasks.document_tasks.generate_document_task")
def generate_document_task(document_id: str) -> str:
    """Entry point from the API layer. Runs the async workflow in a new loop."""
    logger.info("generate_document_task started for %s", document_id)
    doc_uuid = uuid.UUID(document_id)
    asyncio.run(_run_generation(doc_uuid))
    return document_id
