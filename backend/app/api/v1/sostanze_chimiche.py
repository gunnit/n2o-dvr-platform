import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AIError, BadRequestError, NotFoundError
from app.db.session import async_session_factory, get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.sostanza_chimica import SostanzaChimica
from app.schemas.sostanza_chimica import (
    BatchStatusItem,
    BatchStatusResponse,
    BatchUploadFileResult,
    BatchUploadResponse,
    SostanzaChimicaCreate,
    SostanzaChimicaResponse,
    SostanzaChimicaUpdate,
)
from app.services.ai import extract_sds, to_db_dict

logger = logging.getLogger(__name__)

# US-1.8 hard limits (acceptance criteria 1-3)
MAX_FILES_PER_BATCH = 20
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

router = APIRouter(prefix="/aziende/{azienda_id}/sostanze-chimiche", tags=["sostanze-chimiche"])


async def _get_azienda(azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Azienda:
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


@router.get("", response_model=list[SostanzaChimicaResponse])
async def list_sostanze_chimiche(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(SostanzaChimica).where(SostanzaChimica.azienda_id == azienda_id)
    )
    return result.scalars().all()


@router.post("", response_model=SostanzaChimicaResponse, status_code=201)
async def create_sostanza_chimica(
    azienda_id: uuid.UUID,
    body: SostanzaChimicaCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    sostanza = SostanzaChimica(**body.model_dump(), azienda_id=azienda_id)
    db.add(sostanza)
    await db.commit()
    await db.refresh(sostanza)
    return sostanza


# --- Batch SDS upload (US-1.8, US-1.9) -------------------------------------
# These routes MUST be declared before /{sostanza_id} so that "batch-upload"
# and "batch-status" are matched as literal paths rather than UUIDs.


@router.post(
    "/batch-upload",
    response_model=BatchUploadResponse,
    status_code=202,
)
async def batch_upload_sds(
    azienda_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Accept up to 20 SDS PDFs, queue each for async AI extraction.

    US-1.8 acceptance criteria:
      1. >20 files in one batch -> entire request rejected
      2. Non-PDF or >10 MB -> individual file marked failed, others proceed
      3. Valid files -> queued with per-row sostanza_id for progress polling
    """
    await _get_azienda(azienda_id, org_id, db)

    if len(files) == 0:
        raise BadRequestError("Nessun file caricato")
    if len(files) > MAX_FILES_PER_BATCH:
        raise BadRequestError(f"Massimo {MAX_FILES_PER_BATCH} file per caricamento")

    sds_dir = Path(settings.FILE_STORAGE_PATH) / "sds" / str(azienda_id)
    sds_dir.mkdir(parents=True, exist_ok=True)

    results: list[BatchUploadFileResult] = []
    pending_ids: list[uuid.UUID] = []

    for upload in files:
        filename = upload.filename or "unknown.pdf"

        # Validate content type (some browsers send application/octet-stream;
        # accept that if the extension is .pdf).
        is_pdf = (
            upload.content_type == "application/pdf"
            or filename.lower().endswith(".pdf")
        )
        if not is_pdf:
            results.append(
                BatchUploadFileResult(
                    filename=filename, status="failed", reason="Solo file PDF ammessi"
                )
            )
            continue

        # Validate size (read into memory -- 10 MB max is safe)
        content = await upload.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            results.append(
                BatchUploadFileResult(
                    filename=filename,
                    status="failed",
                    reason=f"Dimensione > {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
                )
            )
            continue
        if len(content) == 0:
            results.append(
                BatchUploadFileResult(filename=filename, status="failed", reason="File vuoto")
            )
            continue

        # Persist to disk with a uuid-named file (avoid collisions/injection)
        file_id = uuid.uuid4()
        file_path = sds_dir / f"{file_id}.pdf"
        file_path.write_bytes(content)

        # Create pending row; nome_prodotto is NOT NULL so seed with filename
        sostanza = SostanzaChimica(
            azienda_id=azienda_id,
            nome_prodotto=filename[:255],
            ai_extracted=True,
            extraction_status="pending",
            sds_file_path=str(file_path),
        )
        db.add(sostanza)
        await db.flush()  # populate sostanza.id without committing yet

        results.append(
            BatchUploadFileResult(
                filename=filename, sostanza_id=sostanza.id, status="queued"
            )
        )
        pending_ids.append(sostanza.id)

    # Commit all pending rows before kicking off background tasks so they see
    # the rows via their own sessions.
    await db.commit()

    for sid in pending_ids:
        background_tasks.add_task(_run_sds_extraction, sid)

    return BatchUploadResponse(results=results)


@router.get("/batch-status", response_model=BatchStatusResponse)
async def batch_status(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Return lightweight extraction progress for all SDS rows under an azienda.

    Frontend polls this endpoint (~2s) until every item is `completed` or
    `failed`. Manual entries (extraction_status IS NULL) are excluded.
    """
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(
            SostanzaChimica.id,
            SostanzaChimica.nome_prodotto,
            SostanzaChimica.extraction_status,
            SostanzaChimica.extraction_error,
            SostanzaChimica.ai_confidence,
        )
        .where(
            SostanzaChimica.azienda_id == azienda_id,
            SostanzaChimica.extraction_status.is_not(None),
        )
        .order_by(SostanzaChimica.created_at.desc())
    )
    items = [
        BatchStatusItem(
            sostanza_id=row.id,
            nome_prodotto=row.nome_prodotto,
            extraction_status=row.extraction_status,
            extraction_error=row.extraction_error,
            ai_confidence=float(row.ai_confidence) if row.ai_confidence is not None else None,
        )
        for row in result.all()
    ]
    return BatchStatusResponse(items=items)


@router.get("/{sostanza_id}", response_model=SostanzaChimicaResponse)
async def get_sostanza_chimica(
    azienda_id: uuid.UUID,
    sostanza_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(SostanzaChimica).where(
            SostanzaChimica.id == sostanza_id, SostanzaChimica.azienda_id == azienda_id
        )
    )
    sostanza = result.scalar_one_or_none()
    if not sostanza:
        raise NotFoundError("Sostanza chimica not found")
    return sostanza


@router.put("/{sostanza_id}", response_model=SostanzaChimicaResponse)
async def update_sostanza_chimica(
    azienda_id: uuid.UUID,
    sostanza_id: uuid.UUID,
    body: SostanzaChimicaUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(SostanzaChimica).where(
            SostanzaChimica.id == sostanza_id, SostanzaChimica.azienda_id == azienda_id
        )
    )
    sostanza = result.scalar_one_or_none()
    if not sostanza:
        raise NotFoundError("Sostanza chimica not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(sostanza, field, value)

    await db.commit()
    await db.refresh(sostanza)
    return sostanza


@router.patch("/{sostanza_id}/review", response_model=SostanzaChimicaResponse)
async def mark_reviewed(
    azienda_id: uuid.UUID,
    sostanza_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Mark an AI-extracted chemical substance as human reviewed."""
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(SostanzaChimica).where(
            SostanzaChimica.id == sostanza_id, SostanzaChimica.azienda_id == azienda_id
        )
    )
    sostanza = result.scalar_one_or_none()
    if not sostanza:
        raise NotFoundError("Sostanza chimica not found")

    sostanza.human_reviewed = True
    await db.commit()
    await db.refresh(sostanza)
    return sostanza


@router.delete("/{sostanza_id}", status_code=204)
async def delete_sostanza_chimica(
    azienda_id: uuid.UUID,
    sostanza_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(SostanzaChimica).where(
            SostanzaChimica.id == sostanza_id, SostanzaChimica.azienda_id == azienda_id
        )
    )
    sostanza = result.scalar_one_or_none()
    if not sostanza:
        raise NotFoundError("Sostanza chimica not found")

    await db.delete(sostanza)
    await db.commit()


# --- Batch SDS upload helper (route handlers are declared earlier in the
#     file to ensure /batch-upload and /batch-status match before /{sostanza_id})


async def _run_sds_extraction(sostanza_id: uuid.UUID) -> None:
    """Background task: extract SDS data for one sostanza row and persist.

    Runs in its own DB session since the request session is already closed
    by the time BackgroundTasks fire. Never raises — errors are captured in
    extraction_error and extraction_status=failed so the UI can surface them.
    """
    async with async_session_factory() as db:
        sostanza = await db.get(SostanzaChimica, sostanza_id)
        if sostanza is None:
            logger.error("SDS extraction: sostanza %s not found", sostanza_id)
            return
        if not sostanza.sds_file_path:
            logger.error("SDS extraction: sostanza %s has no file path", sostanza_id)
            sostanza.extraction_status = "failed"
            sostanza.extraction_error = "File PDF non trovato"
            await db.commit()
            return

        sostanza.extraction_status = "processing"
        await db.commit()

        try:
            extraction = await extract_sds(sostanza.sds_file_path)
            db_fields = to_db_dict(extraction, sds_file_path=sostanza.sds_file_path)
            for field, value in db_fields.items():
                setattr(sostanza, field, value)
            sostanza.extraction_status = "completed"
            sostanza.extraction_error = None
        except AIError as exc:
            logger.warning("SDS extraction failed for %s: %s", sostanza_id, exc.detail)
            sostanza.extraction_status = "failed"
            sostanza.extraction_error = str(exc.detail)
            # Keep original filename-based nome_prodotto so user can still identify
            # the row in the UI; extraction_status drives the "Estrazione fallita" badge.
        except Exception as exc:  # noqa: BLE001 -- we *must* not leak from bg task
            logger.exception("SDS extraction crashed for %s", sostanza_id)
            sostanza.extraction_status = "failed"
            sostanza.extraction_error = f"Errore imprevisto: {exc}"

        await db.commit()


