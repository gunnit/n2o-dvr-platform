import os
import shutil
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org, get_current_user
from app.models.azienda import Azienda
from app.models.documento_generato import DocumentoGenerato
from app.models.user import User
from app.schemas.document import (
    DocumentBatchRequest,
    DocumentGenerateRequest,
    DocumentResponse,
    DocumentSnapshotResponse,
)


def _doc_to_response(doc: DocumentoGenerato, generated_by_name: str | None) -> DocumentResponse:
    """Serialise a DocumentoGenerato row adding the resolved user name.

    The `generated_by_name` is resolved via a join on users.full_name in
    the caller (US-2.9) since SQLAlchemy relationships for `generated_by`
    aren't wired on the model.
    """
    return DocumentResponse(
        id=doc.id,
        azienda_id=doc.azienda_id,
        tipo_documento=doc.tipo_documento,
        versione=doc.versione,
        status=doc.status,
        file_path=doc.file_path,
        gdrive_file_id=doc.gdrive_file_id,
        error_message=doc.error_message,
        created_at=doc.created_at,
        generated_by_name=generated_by_name,
    )


async def _resolve_user_name(user_id: uuid.UUID | None, db: AsyncSession) -> str | None:
    if user_id is None:
        return None
    result = await db.execute(select(User.full_name).where(User.id == user_id))
    return result.scalar_one_or_none()

router = APIRouter(prefix="/aziende/{azienda_id}/documents", tags=["documents"])

# Global (non-nested) router for download-by-id endpoint
download_router = APIRouter(prefix="/documenti", tags=["documents"])


# US-4.1: document types that require the DVR Master to already exist before
# they can be generated. The DVR carries the anagrafica + environments that
# these dependent documents reuse, so generating them first would produce
# incomplete output.
_DVR_DEPENDENT_TYPES: set[str] = {"pee_azienda", "pee_comune"}


async def _ensure_dvr_exists_for_dependent(
    azienda_id: uuid.UUID, tipo_documento: str, db: AsyncSession
) -> None:
    """If tipo_documento depends on the DVR Master, raise 400 when none exists.

    Matches US-4.1 AC2: "Given no DVR exists yet, When I attempt to generate the
    PEE, Then the action is blocked with the message 'Genera prima il DVR Master'."
    A DVR counts as "existing" when at least one DocumentoGenerato row exists
    with tipo_documento == 'dvr_master' and a successful status
    (completed / ready). Bozza / failed / pending rows do not unblock.
    """
    if tipo_documento not in _DVR_DEPENDENT_TYPES:
        return
    result = await db.execute(
        select(DocumentoGenerato.id)
        .where(
            DocumentoGenerato.azienda_id == azienda_id,
            DocumentoGenerato.tipo_documento == "dvr_master",
            DocumentoGenerato.status.in_(("completed", "ready")),
        )
        .limit(1)
    )
    if result.scalar_one_or_none() is None:
        raise BadRequestError("Genera prima il DVR Master")


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
    # US-4.1 AC2: block dependent documents (PEE) until the DVR Master exists.
    await _ensure_dvr_exists_for_dependent(azienda_id, body.tipo_documento, db)

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
        # US-4.4: persist the dialog-supplied options (e.g. HACCP forms
        # selected_codes) so the async worker can read them back.
        options=body.options,
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

    return _doc_to_response(doc, await _resolve_user_name(doc.generated_by, db))


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """List all generated documents for an azienda."""
    await _get_azienda(azienda_id, org_id, db)
    # Left-join on users so rows with a NULL generated_by (legacy records)
    # still appear, just without an author name.
    result = await db.execute(
        select(DocumentoGenerato, User.full_name)
        .outerjoin(User, User.id == DocumentoGenerato.generated_by)
        .where(DocumentoGenerato.azienda_id == azienda_id)
        .order_by(DocumentoGenerato.created_at.desc())
    )
    return [_doc_to_response(doc, name) for doc, name in result.all()]


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
        select(DocumentoGenerato, User.full_name)
        .outerjoin(User, User.id == DocumentoGenerato.generated_by)
        .where(
            DocumentoGenerato.id == document_id,
            DocumentoGenerato.azienda_id == azienda_id,
        )
    )
    row = result.one_or_none()
    if not row:
        raise NotFoundError("Document not found")
    doc, name = row
    return _doc_to_response(doc, name)


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

    responses: list[DocumentResponse] = []
    for doc in created_docs:
        await db.refresh(doc)
        try:
            generate_document_task.delay(str(doc.id))
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Celery dispatch failed for %s", doc.id)
        responses.append(
            _doc_to_response(doc, await _resolve_user_name(doc.generated_by, db))
        )

    return responses


@router.get("/{document_id}/snapshot", response_model=DocumentSnapshotResponse)
async def get_document_snapshot(
    azienda_id: uuid.UUID,
    document_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Return a structured text snapshot of a generated .docx (US-2.9).

    Used by the frontend diff viewer. Since we don't persist snapshots,
    we parse the .docx on demand. If the file is missing (e.g. bozza
    rollback per US-2.8), we 404 — there's nothing to diff.
    """
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
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise NotFoundError("Snapshot non disponibile per questo documento")

    paragraphs: list[str] = []
    tables: list[list[list[str]]] = []
    # Only parse .docx files; .zip bundles (e.g. haccp_forms) are not
    # structurally diffable — fall back to empty lists so the frontend
    # can still show the metadata header.
    if doc.file_path.endswith(".docx"):
        try:
            from docx import Document

            document = Document(doc.file_path)
            paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
            for table in document.tables:
                rows: list[list[str]] = []
                for row in table.rows:
                    rows.append([cell.text.strip() for cell in row.cells])
                tables.append(rows)
        except Exception:
            # Swallow parse errors — return what we have so the UI can
            # still render the version metadata. Diff will just be empty.
            import logging
            logging.getLogger(__name__).exception(
                "Failed to parse .docx for snapshot %s", doc.id
            )

    generated_by_name = await _resolve_user_name(doc.generated_by, db)
    return DocumentSnapshotResponse(
        id=doc.id,
        versione=doc.versione,
        generated_at=doc.generation_completed_at or doc.created_at,
        generated_by_name=generated_by_name,
        paragraphs=paragraphs,
        tables=tables,
    )


@router.post("/{document_id}/restore", response_model=DocumentResponse, status_code=201)
async def restore_document(
    azienda_id: uuid.UUID,
    document_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Restore a historical version as a new version (US-2.9).

    MVP approach: rather than re-running the generator (templates and
    live data may have drifted), we copy the source .docx on disk and
    register it as a new `DocumentoGenerato` row with status=completed.
    This preserves the exact bytes the user is trying to "go back to".
    """
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(DocumentoGenerato).where(
            DocumentoGenerato.id == document_id,
            DocumentoGenerato.azienda_id == azienda_id,
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        raise NotFoundError("Document not found")
    if not source.file_path or not os.path.exists(source.file_path):
        raise BadRequestError("Impossibile ripristinare una bozza")

    # Next version number for this document type
    result = await db.execute(
        select(DocumentoGenerato)
        .where(
            DocumentoGenerato.azienda_id == azienda_id,
            DocumentoGenerato.tipo_documento == source.tipo_documento,
        )
        .order_by(DocumentoGenerato.versione.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    next_version = (latest.versione + 1) if latest else 1

    # Fresh copy on disk — isolate the new version from the source file
    # so later regenerations / deletes don't affect it.
    src_dir, src_name = os.path.split(source.file_path)
    stem, ext = os.path.splitext(src_name)
    new_name = f"{stem}_v{next_version}_restored{ext}"
    new_path = os.path.join(src_dir, new_name)
    try:
        shutil.copy2(source.file_path, new_path)
    except OSError as exc:  # pragma: no cover — filesystem-level failure
        raise BadRequestError(f"Copia del file fallita: {exc}") from exc

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    new_doc = DocumentoGenerato(
        azienda_id=azienda_id,
        tipo_documento=source.tipo_documento,
        versione=next_version,
        status="completed",
        file_path=new_path,
        error_message=None,
        generated_by=user.id,
        generation_started_at=now,
        generation_completed_at=now,
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)

    return _doc_to_response(new_doc, await _resolve_user_name(new_doc.generated_by, db))
