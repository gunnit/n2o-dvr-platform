import io
import os
import shutil
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org, get_current_user
from app.models.ambiente import Ambiente
from app.models.azienda import Azienda
from app.models.documento_generato import DocumentoGenerato
from app.models.persona import Persona
from app.models.user import User
from app.schemas.document import (
    DocumentBatchRequest,
    DocumentEditLinkResponse,
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
    gdoc_file_id = getattr(doc, "gdoc_file_id", None)
    gdoc_edit_url = (
        f"https://docs.google.com/document/d/{gdoc_file_id}/edit"
        if gdoc_file_id else None
    )
    edited_in_gdocs = bool((getattr(doc, "options", None) or {}).get("edited_in_gdocs"))
    return DocumentResponse(
        id=doc.id,
        azienda_id=doc.azienda_id,
        tipo_documento=doc.tipo_documento,
        versione=doc.versione,
        status=doc.status,
        file_path=doc.file_path,
        gdrive_file_id=doc.gdrive_file_id,
        gdoc_file_id=gdoc_file_id,
        gdoc_edit_url=gdoc_edit_url,
        edited_in_gdocs=edited_in_gdocs,
        error_message=doc.error_message,
        created_at=doc.created_at,
        generated_by_name=generated_by_name,
        # US-5.2 AC2: pass the worker-set drift flag to the documents
        # page. Defaults to False on legacy rows where the column was
        # NULL before the d3e4f5a6b7c8 migration applied a default.
        stale_snapshot=bool(getattr(doc, "stale_snapshot", False)),
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


async def _ensure_anagrafica_complete_for_dvr(
    azienda: Azienda, tipo_documento: str
) -> None:
    """Block DVR generation when ALL legally-required contact fields are NULL.

    Audit F-004 (2026-04-29 rerun): the DVR Anagrafica section requires
    Codice Fiscale, Telefono, Email and PEC. When all four are NULL the
    document renders four "Non comunicato" rows that an inspector will
    reject. Allowing generation with at least one field populated keeps
    the door open for small artigiani without (e.g.) a PEC yet.
    """
    if tipo_documento != "dvr_master":
        return
    fields = (
        azienda.codice_fiscale,
        azienda.telefono,
        azienda.email,
        azienda.pec,
    )
    if not any((f or "").strip() for f in fields):
        raise BadRequestError(
            "Anagrafica incompleta: inserisci almeno uno tra "
            "Codice Fiscale, Telefono, Email o PEC sull'Azienda "
            "prima di generare il DVR."
        )


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
    """Stream back the generated file (.docx or .zip).

    Prefers the ``file_content`` bytes stored in Postgres (works across
    Render's separate API / Worker disks). Falls back to ``file_path``
    on the local filesystem for backwards compatibility with documents
    generated before the DB-storage migration.
    """
    result = await db.execute(
        select(DocumentoGenerato)
        .join(Azienda, Azienda.id == DocumentoGenerato.azienda_id)
        .where(DocumentoGenerato.id == document_id, Azienda.organization_id == org_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document not found")
    if doc.status != "completed":
        raise NotFoundError("Document not ready yet")

    # Determine filename and MIME type from whichever source is available
    filename = doc.file_name or (os.path.basename(doc.file_path) if doc.file_path else None)
    if not filename:
        raise NotFoundError("Document not ready yet")
    media_type = "application/zip" if filename.endswith(".zip") else (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    # Prefer DB content (works cross-service on Render)
    if doc.file_content:
        return StreamingResponse(
            io.BytesIO(doc.file_content),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Fallback: serve from local disk (pre-migration documents or local dev)
    if doc.file_path and os.path.exists(doc.file_path):
        return FileResponse(doc.file_path, media_type=media_type, filename=filename)

    raise NotFoundError("File non disponibile. Rigenera il documento.")


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
    azienda = await _get_azienda(azienda_id, org_id, db)
    # Audit F-004: refuse DVR Master with all anagrafica contact fields NULL.
    await _ensure_anagrafica_complete_for_dvr(azienda, body.tipo_documento)
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
    """List all generated documents for an azienda.

    US-5.2 AC2 — drift detection runs on every list call: we compute the
    current survey hash once and update any completed rows whose stored
    hash no longer matches. This catches the case where the operator
    edits the survey *after* a job completes (the worker can't see those
    edits since it's already done). Cost: one extra SHA256 + small UPDATE
    per page load.
    """
    await _get_azienda(azienda_id, org_id, db)

    # Recompute the live hash + flip any completed docs whose snapshot is
    # now stale. Done in a single helper so the survey-edit endpoints can
    # call the same code path proactively.
    try:
        from app.services.survey_snapshot import mark_documents_stale_for

        await mark_documents_stale_for(azienda_id, db)
        await db.commit()
    except Exception:  # pragma: no cover — never fail the list call on this
        import logging

        logging.getLogger(__name__).exception(
            "Stale-snapshot recompute failed for %s", azienda_id
        )

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


# B1 — survey statuses that count as "submitted" for the Genera-Documenti
# precondition. ``draft`` (the survey was never started) and ``in_progress``
# (mid-wizard) both fail the gate; once /survey/complete or /survey/sign
# has run we trust the operator decided the survey is fit to generate
# against. Mirrors how survey.py advances the status (step_N -> completed
# -> firmato -> in_revisione).
_SURVEY_SUBMITTED_STATUSES: set[str] = {"completed", "firmato", "in_revisione"}


async def _check_batch_preconditions(
    azienda_id: uuid.UUID, db: AsyncSession
) -> list[str]:
    """Return a list of Italian descriptions for any missing prerequisites.

    The batch generator is a foot-gun on an empty azienda — every dependent
    document silently produces a placeholder file with "Nessun ambiente
    registrato" boilerplate. We require the survey to be at least submitted
    once and to carry the minimal entities the DVR Master needs (>=1
    ambiente, >=1 persona, >=1 RSPP).
    """
    missing: list[str] = []

    # Resolve the survey_status alongside the entity counts in three small
    # queries instead of one mega-join — clearer and fast on the row counts
    # we actually deal with (tens, not thousands).
    az_status = (
        await db.execute(
            select(Azienda.survey_status).where(Azienda.id == azienda_id)
        )
    ).scalar_one_or_none()
    if az_status is None or az_status not in _SURVEY_SUBMITTED_STATUSES:
        missing.append("Sopralluogo non completato o non firmato")

    ambienti_count = (
        await db.execute(
            select(func.count(Ambiente.id)).where(Ambiente.azienda_id == azienda_id)
        )
    ).scalar_one()
    if not ambienti_count:
        missing.append("Nessun ambiente di lavoro registrato")

    persone_count = (
        await db.execute(
            select(func.count(Persona.id)).where(Persona.azienda_id == azienda_id)
        )
    ).scalar_one()
    if not persone_count:
        missing.append("Nessuna persona registrata")

    # RSPP gate matches the survey/sign flow's expectation that the survey
    # carries a designated safety manager before any document is produced.
    rspp_count = (
        await db.execute(
            select(func.count(Persona.id)).where(
                Persona.azienda_id == azienda_id,
                Persona.ruolo_rspp.is_(True),
            )
        )
    ).scalar_one()
    if not rspp_count:
        missing.append("Nessun RSPP designato")

    return missing


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

    # B1 — refuse to enqueue tasks against an incomplete sopralluogo. The
    # frontend disables the button when survey_status == draft, but we
    # double-check server-side because curl + stale tabs both bypass that.
    missing = await _check_batch_preconditions(azienda_id, db)
    if missing:
        raise HTTPException(
            status_code=409,
            detail=f"Sopralluogo incompleto: {', '.join(missing)}",
        )

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

    # Resolve the document source — DB content or disk file
    file_source: io.BytesIO | str | None = None
    filename = doc.file_name or (os.path.basename(doc.file_path) if doc.file_path else "")
    if doc.file_content:
        file_source = io.BytesIO(doc.file_content)
    elif doc.file_path and os.path.exists(doc.file_path):
        file_source = doc.file_path
    else:
        raise NotFoundError("Snapshot non disponibile per questo documento")

    paragraphs: list[str] = []
    tables: list[list[list[str]]] = []
    # Only parse .docx files; .zip bundles (e.g. haccp_forms) are not
    # structurally diffable — fall back to empty lists so the frontend
    # can still show the metadata header.
    if filename.endswith(".docx"):
        try:
            from docx import Document

            document = Document(file_source)
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
    if not source.file_content and (not source.file_path or not os.path.exists(source.file_path)):
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

    # Build restored filename
    src_name = source.file_name or (os.path.basename(source.file_path) if source.file_path else f"{source.tipo_documento}_v{source.versione}")
    stem, ext = os.path.splitext(src_name)
    new_name = f"{stem}_v{next_version}_restored{ext}"

    # Copy the file content (prefer DB, fall back to disk)
    restored_content: bytes | None = source.file_content
    new_path: str | None = None
    if not restored_content and source.file_path and os.path.exists(source.file_path):
        try:
            with open(source.file_path, "rb") as f:
                restored_content = f.read()
        except OSError as exc:
            raise BadRequestError(f"Copia del file fallita: {exc}") from exc

    # Also write to disk if local filesystem is available (backwards compat)
    if source.file_path:
        src_dir = os.path.dirname(source.file_path)
        new_path = os.path.join(src_dir, new_name)
        try:
            if restored_content:
                os.makedirs(src_dir, exist_ok=True)
                with open(new_path, "wb") as f:
                    f.write(restored_content)
            elif os.path.exists(source.file_path):
                shutil.copy2(source.file_path, new_path)
        except OSError:
            new_path = None  # disk write failed, DB content will suffice

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    new_doc = DocumentoGenerato(
        azienda_id=azienda_id,
        tipo_documento=source.tipo_documento,
        versione=next_version,
        status="completed",
        file_path=new_path,
        file_content=restored_content,
        file_name=new_name,
        error_message=None,
        generated_by=user.id,
        generation_started_at=now,
        generation_completed_at=now,
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)

    return _doc_to_response(new_doc, await _resolve_user_name(new_doc.generated_by, db))


# ---------------------------------------------------------------------------
# Google Docs round-trip: open-for-editing + sync-from-gdoc (DVR Master only)
# ---------------------------------------------------------------------------

# Document types eligible for the in-browser Google Docs editing flow.
# Start with DVR Master; add attachments once the round-trip is proven.
_GDOC_EDITABLE_TYPES: set[str] = {"dvr_master"}


@download_router.post("/{document_id}/open-for-editing", response_model=DocumentEditLinkResponse)
async def open_document_for_editing(
    document_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Return an editable Google Docs URL for the document.

    First call: upload the .docx bytes to Drive with conversion to Google Doc,
    grant "anyone with link can edit" permission, persist the new Google Doc
    file ID on the row, and return the edit URL.
    Subsequent calls: return the existing edit URL (idempotent).
    """
    from fastapi import HTTPException, status

    result = await db.execute(
        select(DocumentoGenerato)
        .join(Azienda, Azienda.id == DocumentoGenerato.azienda_id)
        .where(DocumentoGenerato.id == document_id, Azienda.organization_id == org_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document not found")

    if doc.tipo_documento not in _GDOC_EDITABLE_TYPES:
        raise BadRequestError(
            "La modifica in Google Docs è disponibile solo per il DVR Master"
        )
    if doc.status != "completed":
        raise NotFoundError("Document not ready yet")

    # Idempotent reopen: if we already have the Google Doc, just return its URL.
    if doc.gdoc_file_id:
        return DocumentEditLinkResponse(
            gdoc_file_id=doc.gdoc_file_id,
            edit_url=f"https://docs.google.com/document/d/{doc.gdoc_file_id}/edit",
        )

    if not doc.file_content:
        raise NotFoundError("File non disponibile. Rigenera il documento.")

    # Resolve the azienda name for the Drive folder
    azienda_result = await db.execute(select(Azienda).where(Azienda.id == doc.azienda_id))
    azienda = azienda_result.scalar_one()

    from app.services.gdrive_service import (
        create_gdoc_from_docx_bytes,
        share_anyone_with_link,
    )

    filename = doc.file_name or f"{doc.tipo_documento}_v{doc.versione}.docx"
    gdoc_id = await create_gdoc_from_docx_bytes(
        doc.file_content, filename, azienda.ragione_sociale[:100]
    )
    if not gdoc_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Drive non configurato o errore di conversione",
        )

    await share_anyone_with_link(gdoc_id)

    doc.gdoc_file_id = gdoc_id
    await db.commit()
    await db.refresh(doc)

    return DocumentEditLinkResponse(
        gdoc_file_id=gdoc_id,
        edit_url=f"https://docs.google.com/document/d/{gdoc_id}/edit",
    )


@download_router.post(
    "/{document_id}/sync-from-gdoc", response_model=DocumentResponse, status_code=201
)
async def sync_document_from_gdoc(
    document_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pull the latest Google Doc content back into a new version row.

    Exports the live Google Doc as .docx via Drive API, inserts a new
    DocumentoGenerato row with incremented `versione` and status=completed,
    and tags `options.edited_in_gdocs=True` for the version history UI.
    """
    from fastapi import HTTPException, status

    result = await db.execute(
        select(DocumentoGenerato)
        .join(Azienda, Azienda.id == DocumentoGenerato.azienda_id)
        .where(DocumentoGenerato.id == document_id, Azienda.organization_id == org_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise NotFoundError("Document not found")

    if not source.gdoc_file_id:
        raise BadRequestError("Nessuna modifica in Google Docs da sincronizzare")

    from app.services.gdrive_service import (
        delete_gdoc,
        export_gdoc_as_docx,
        get_gdoc_times,
    )

    # Dirty-check: if the Google Doc's modifiedTime is within a few seconds of
    # its createdTime, the user never actually edited. Reject so double-clicks
    # or stale sync attempts don't produce a spurious v+1 identical to v.
    times = await get_gdoc_times(source.gdoc_file_id)
    if times is not None:
        from datetime import datetime as _dt
        try:
            created_dt = _dt.fromisoformat(times[0].replace("Z", "+00:00"))
            modified_dt = _dt.fromisoformat(times[1].replace("Z", "+00:00"))
            # 5s tolerance covers Drive's own post-conversion writes.
            if (modified_dt - created_dt).total_seconds() < 5:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Nessuna modifica rilevata in Google Docs",
                )
        except ValueError:
            # Fall through if Drive returned something we couldn't parse.
            pass

    exported = await export_gdoc_as_docx(source.gdoc_file_id)
    if not exported:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Impossibile esportare il documento da Google Docs",
        )

    # Next version for this document type
    result = await db.execute(
        select(DocumentoGenerato)
        .where(
            DocumentoGenerato.azienda_id == source.azienda_id,
            DocumentoGenerato.tipo_documento == source.tipo_documento,
        )
        .order_by(DocumentoGenerato.versione.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    next_version = (latest.versione + 1) if latest else 1

    # Build filename: append -edited to stem
    src_name = source.file_name or f"{source.tipo_documento}_v{source.versione}.docx"
    stem, ext = os.path.splitext(src_name)
    new_name = f"{stem}_v{next_version}_edited{ext or '.docx'}"

    merged_options = dict(source.options or {})
    merged_options["edited_in_gdocs"] = True
    merged_options["source_version_id"] = str(source.id)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    new_doc = DocumentoGenerato(
        azienda_id=source.azienda_id,
        tipo_documento=source.tipo_documento,
        versione=next_version,
        status="completed",
        file_content=exported,
        file_name=new_name,
        options=merged_options,
        generated_by=user.id,
        generation_started_at=now,
        generation_completed_at=now,
    )
    db.add(new_doc)
    # Self-cleanup: once we've captured the edits as a new DB-backed version,
    # the Google Doc is no longer authoritative. Clear the source row's
    # gdoc_file_id and delete the Drive file so the UI stops offering sync on
    # a stale link. Best-effort — a Drive delete failure is logged and the
    # commit still proceeds (the user can manually clean up from Drive).
    stale_gdoc_id = source.gdoc_file_id
    source.gdoc_file_id = None
    await db.commit()
    await db.refresh(new_doc)
    try:
        await delete_gdoc(stale_gdoc_id)
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "Post-sync Drive cleanup failed for %s", stale_gdoc_id
        )

    return _doc_to_response(new_doc, await _resolve_user_name(new_doc.generated_by, db))


@download_router.delete("/{document_id}/gdoc", response_model=DocumentResponse)
async def discard_gdoc_edits(
    document_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Delete the editable Google Doc for this row without importing its content.

    Used when the user realises they don't want to keep the in-browser edits —
    removes the Drive file and clears ``gdoc_file_id`` so the UI hides the
    sync/discard buttons. Idempotent: if the Doc is already gone on Drive,
    still clears the DB state.
    """
    result = await db.execute(
        select(DocumentoGenerato)
        .join(Azienda, Azienda.id == DocumentoGenerato.azienda_id)
        .where(DocumentoGenerato.id == document_id, Azienda.organization_id == org_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document not found")
    if not doc.gdoc_file_id:
        # Nothing to discard — return current state without error so the
        # frontend treats a double-click as a no-op.
        return _doc_to_response(doc, await _resolve_user_name(doc.generated_by, db))

    from app.services.gdrive_service import delete_gdoc as _delete_gdoc

    stale_id = doc.gdoc_file_id
    doc.gdoc_file_id = None
    await db.commit()
    await db.refresh(doc)
    try:
        await _delete_gdoc(stale_id)
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "Drive delete failed on discard for %s", stale_id
        )

    return _doc_to_response(doc, await _resolve_user_name(doc.generated_by, db))
