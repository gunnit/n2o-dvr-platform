import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.ambiente import Ambiente
from app.models.ambiente_foto import AmbienteFoto
from app.models.azienda import Azienda
from app.schemas.ambiente import AmbienteCreate, AmbienteResponse, AmbienteUpdate
from app.schemas.ambiente_foto import AmbienteFotoResponse

router = APIRouter(prefix="/aziende/{azienda_id}/ambienti", tags=["ambienti"])


async def _get_azienda(azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Azienda:
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


@router.get("", response_model=list[AmbienteResponse])
async def list_ambienti(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(select(Ambiente).where(Ambiente.azienda_id == azienda_id))
    return result.scalars().all()


@router.post("", response_model=AmbienteResponse, status_code=201)
async def create_ambiente(
    azienda_id: uuid.UUID,
    body: AmbienteCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    ambiente = Ambiente(**body.model_dump(), azienda_id=azienda_id)
    db.add(ambiente)
    await db.commit()
    await db.refresh(ambiente)
    return ambiente


@router.get("/{ambiente_id}", response_model=AmbienteResponse)
async def get_ambiente(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Ambiente).where(Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id)
    )
    ambiente = result.scalar_one_or_none()
    if not ambiente:
        raise NotFoundError("Ambiente not found")
    return ambiente


@router.put("/{ambiente_id}", response_model=AmbienteResponse)
async def update_ambiente(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    body: AmbienteUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Ambiente).where(Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id)
    )
    ambiente = result.scalar_one_or_none()
    if not ambiente:
        raise NotFoundError("Ambiente not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(ambiente, field, value)

    await db.commit()
    await db.refresh(ambiente)
    return ambiente


@router.delete("/{ambiente_id}", status_code=204)
async def delete_ambiente(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Ambiente).where(Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id)
    )
    ambiente = result.scalar_one_or_none()
    if not ambiente:
        raise NotFoundError("Ambiente not found")

    await db.delete(ambiente)
    await db.commit()


# --- Foto uploads (US-1.3) --------------------------------------------------
# Up to 10 JPG/PNG/HEIC photos (<=10 MB each) per ambiente. Files live under
# FILE_STORAGE_PATH/foto_ambienti/{ambiente_id}/{uuid}.{ext}; the DB row keeps
# the original filename so the UI can render it alongside the thumbnail.

MAX_FOTO_PER_AMBIENTE = 10
MAX_FOTO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_FOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/heic"}
ALLOWED_FOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic"}
# Keep extension → content-type mapping for octet-stream fallback
EXT_TO_CONTENT_TYPE = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".heic": "image/heic",
}


async def _get_ambiente_for_org(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    org_id: uuid.UUID,
    db: AsyncSession,
) -> Ambiente:
    """Load an ambiente verifying it belongs to an azienda owned by the org."""
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Ambiente).where(
            Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id
        )
    )
    ambiente = result.scalar_one_or_none()
    if not ambiente:
        raise NotFoundError("Ambiente not found")
    return ambiente


@router.post(
    "/{ambiente_id}/foto",
    response_model=AmbienteFotoResponse,
    status_code=201,
)
async def upload_ambiente_foto(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    file: UploadFile = File(...),
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Attach a single photo to an ambiente.

    US-1.3 acceptance criteria:
      1. Up to 10 photos per ambiente (11th is rejected)
      2. JPG/PNG/HEIC only, <=10 MB each — others get the exact Italian error
         string specified in the user story
    """
    await _get_ambiente_for_org(azienda_id, ambiente_id, org_id, db)

    # Enforce 10-photo ceiling per ambiente
    count_result = await db.execute(
        select(func.count()).select_from(AmbienteFoto).where(
            AmbienteFoto.ambiente_id == ambiente_id
        )
    )
    current_count = count_result.scalar_one()
    if current_count >= MAX_FOTO_PER_AMBIENTE:
        raise BadRequestError("Massimo 10 foto per ambiente")

    filename = file.filename or "foto"
    ext = Path(filename).suffix.lower()

    # Accept by content-type OR (octet-stream fallback) by file extension
    content_type = file.content_type or ""
    is_allowed_type = content_type in ALLOWED_FOTO_CONTENT_TYPES
    is_allowed_ext = ext in ALLOWED_FOTO_EXTENSIONS
    if not (is_allowed_type or is_allowed_ext):
        raise BadRequestError("Formato non supportato o file troppo grande (max 10 MB)")

    # Normalize content_type when the browser sent octet-stream but the
    # extension is whitelisted.
    if not is_allowed_type and is_allowed_ext:
        content_type = EXT_TO_CONTENT_TYPE[ext]

    # Validate size (read into memory — 10 MB ceiling keeps memory bounded)
    content = await file.read()
    if len(content) == 0:
        raise BadRequestError("Formato non supportato o file troppo grande (max 10 MB)")
    if len(content) > MAX_FOTO_SIZE_BYTES:
        raise BadRequestError("Formato non supportato o file troppo grande (max 10 MB)")

    # Persist to disk with a uuid-named file to avoid collisions and injection
    foto_dir = Path(settings.FILE_STORAGE_PATH) / "foto_ambienti" / str(ambiente_id)
    foto_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    # Fall back to the content-type-derived extension if the filename had none
    if ext not in ALLOWED_FOTO_EXTENSIONS:
        ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/heic": ".heic",
        }.get(content_type, ".bin")
    file_path = foto_dir / f"{file_id}{ext}"
    file_path.write_bytes(content)

    foto = AmbienteFoto(
        id=file_id,
        ambiente_id=ambiente_id,
        filename=filename[:255],
        file_path=str(file_path),
        content_type=content_type,
        size_bytes=len(content),
    )
    db.add(foto)
    await db.commit()
    await db.refresh(foto)
    return foto


@router.get("/{ambiente_id}/foto", response_model=list[AmbienteFotoResponse])
async def list_ambiente_foto(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_ambiente_for_org(azienda_id, ambiente_id, org_id, db)
    result = await db.execute(
        select(AmbienteFoto)
        .where(AmbienteFoto.ambiente_id == ambiente_id)
        .order_by(AmbienteFoto.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{ambiente_id}/foto/{foto_id}/content")
async def get_ambiente_foto_content(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    foto_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Stream raw photo bytes for inline preview in the survey UI.

    Feedback issue #7 (2026-05-14): operators want to see what they
    uploaded, not just a filename + size. The frontend fetches this with
    a bearer token, wraps the response in a blob URL, and assigns it to
    an <img>. We don't expose a publicly signed URL because the photo
    can contain people / planimetrie / sensitive workplace details —
    keeping auth on the bytes is the simpler privacy posture.
    """
    await _get_ambiente_for_org(azienda_id, ambiente_id, org_id, db)
    result = await db.execute(
        select(AmbienteFoto).where(
            AmbienteFoto.id == foto_id, AmbienteFoto.ambiente_id == ambiente_id
        )
    )
    foto = result.scalar_one_or_none()
    if not foto:
        raise NotFoundError("Foto not found")
    file_path = Path(foto.file_path)
    # Storage volumes can be wiped during dev/test resets even while the
    # DB row survives — surface that as 404 rather than a 500.
    if not file_path.exists():
        raise NotFoundError("Foto file missing on storage")
    return FileResponse(
        path=str(file_path),
        media_type=foto.content_type or "application/octet-stream",
        filename=foto.filename or f"{foto_id}",
    )


@router.delete("/{ambiente_id}/foto/{foto_id}", status_code=204)
async def delete_ambiente_foto(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    foto_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_ambiente_for_org(azienda_id, ambiente_id, org_id, db)
    result = await db.execute(
        select(AmbienteFoto).where(
            AmbienteFoto.id == foto_id, AmbienteFoto.ambiente_id == ambiente_id
        )
    )
    foto = result.scalar_one_or_none()
    if not foto:
        raise NotFoundError("Foto not found")

    # Best-effort: remove the on-disk artefact; DB row removal is the source
    # of truth for the UI so we never block on a missing/locked file.
    try:
        Path(foto.file_path).unlink(missing_ok=True)
    except OSError:
        pass

    await db.delete(foto)
    await db.commit()
