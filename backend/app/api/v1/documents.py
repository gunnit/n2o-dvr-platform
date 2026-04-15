import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org, get_current_user
from app.models.azienda import Azienda
from app.models.documento_generato import DocumentoGenerato
from app.models.user import User
from app.schemas.document import DocumentBatchRequest, DocumentGenerateRequest, DocumentResponse

router = APIRouter(prefix="/aziende/{azienda_id}/documents", tags=["documents"])

# Global (non-nested) router for download-by-id endpoint
download_router = APIRouter(prefix="/documenti", tags=["documents"])


@download_router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Stream back the generated file (.docx or .zip)."""
    result = await db.execute(
        select(DocumentoGenerato)
        .join(Azienda, Azienda.id == DocumentoGenerato.azienda_id)
        .where(DocumentoGenerato.id == document_id, Azienda.organization_id == org_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document not found")
    if doc.status != "completed" or not doc.file_path:
        raise NotFoundError("Document not ready yet")
    if not os.path.exists(doc.file_path):
        raise NotFoundError("File missing on disk")

    media_type = "application/zip" if doc.file_path.endswith(".zip") else (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    filename = os.path.basename(doc.file_path)
    return FileResponse(doc.file_path, media_type=media_type, filename=filename)


async def _get_azienda(azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Azienda:
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


@router.post("/generate", response_model=DocumentResponse, status_code=202)
async def generate_document(
    azienda_id: uuid.UUID,
    body: DocumentGenerateRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger async document generation for a single document type.

    Creates a DocumentoGenerato record with status='pending' and returns
    immediately. The actual generation will be handled by a Celery worker.
    """
    await _get_azienda(azienda_id, org_id, db)

    # Determine the next version number for this document type
    result = await db.execute(
        select(DocumentoGenerato)
        .where(
            DocumentoGenerato.azienda_id == azienda_id,
            DocumentoGenerato.tipo_documento == body.tipo_documento,
        )
        .order_by(DocumentoGenerato.versione.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    next_version = (latest.versione + 1) if latest else 1

    doc = DocumentoGenerato(
        azienda_id=azienda_id,
        tipo_documento=body.tipo_documento,
        versione=next_version,
        status="pending",
        generated_by=user.id,
        generation_started_at=datetime.utcnow(),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Dispatch Celery task for async generation
    try:
        from app.tasks.document_tasks import generate_document_task
        generate_document_task.delay(str(doc.id))
    except Exception:
        # If the broker is unavailable, fall back to a warning log but still
        # return the pending record — the task can be retried manually.
        import logging
        logging.getLogger(__name__).exception("Celery dispatch failed")

    return doc


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """List all generated documents for an azienda."""
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(DocumentoGenerato)
        .where(DocumentoGenerato.azienda_id == azienda_id)
        .order_by(DocumentoGenerato.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{document_id}/status", response_model=DocumentResponse)
async def get_document_status(
    azienda_id: uuid.UUID,
    document_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Check generation status for a specific document."""
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(DocumentoGenerato).where(
            DocumentoGenerato.id == document_id,
            DocumentoGenerato.azienda_id == azienda_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document not found")
    return doc


@router.post("/batch", response_model=list[DocumentResponse], status_code=202)
async def batch_generate_documents(
    azienda_id: uuid.UUID,
    body: DocumentBatchRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger async generation for multiple document types at once."""
    await _get_azienda(azienda_id, org_id, db)

    created_docs: list[DocumentoGenerato] = []

    for tipo in body.tipi_documento:
        # Determine the next version number for each document type
        result = await db.execute(
            select(DocumentoGenerato)
            .where(
                DocumentoGenerato.azienda_id == azienda_id,
                DocumentoGenerato.tipo_documento == tipo,
            )
            .order_by(DocumentoGenerato.versione.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        next_version = (latest.versione + 1) if latest else 1

        doc = DocumentoGenerato(
            azienda_id=azienda_id,
            tipo_documento=tipo,
            versione=next_version,
            status="pending",
            generated_by=user.id,
            generation_started_at=datetime.utcnow(),
        )
        db.add(doc)
        created_docs.append(doc)

    await db.commit()

    from app.tasks.document_tasks import generate_document_task

    for doc in created_docs:
        await db.refresh(doc)
        try:
            generate_document_task.delay(str(doc.id))
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Celery dispatch failed for %s", doc.id)

    return created_docs
