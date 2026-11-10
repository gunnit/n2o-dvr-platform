"""Company presentation photo ("foto di presentazione") for the DVR.

Survey data, not billable work: PUT and DELETE need ``SURVEY_WRITE`` (every
role has it today) and no entitlement gate, like the ambiente photos. GET is
org-scoped but never role-gated, so a lapsed tenant keeps seeing its photo.
The photo is never sent to any AI service.
"""

import asyncio
import datetime as dt
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.permissions import SURVEY_WRITE
from app.db.session import get_db
from app.dependencies import get_current_org, require_capability
from app.models.azienda import Azienda
from app.models.azienda_foto_presentazione import AziendaFotoPresentazione
from app.services.ambiente_photo import (
    MAX_ORIGINAL_IMAGE_BYTES,
    DocumentImageNormalizationError,
    normalize_document_image,
)

router = APIRouter(prefix="/aziende/{azienda_id}/foto-presentazione", tags=["aziende"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/heic"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic"}
BAD_FILE_MESSAGE = "Formato non supportato o file troppo grande (max 10 MB)"


class FotoPresentazioneResponse(BaseModel):
    azienda_id: uuid.UUID
    content_type: str
    size_bytes: int
    updated_at: dt.datetime


async def _require_azienda_in_org(azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> None:
    found = await db.execute(
        select(Azienda.id).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    if found.scalar_one_or_none() is None:
        raise NotFoundError("Azienda not found")


@router.put(
    "",
    response_model=FotoPresentazioneResponse,
    dependencies=[Depends(require_capability(SURVEY_WRITE))],
)
async def put_foto_presentazione(
    azienda_id: uuid.UUID,
    file: UploadFile = File(...),
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Store (or replace) the azienda's presentation photo."""
    await _require_azienda_in_org(azienda_id, org_id, db)

    ext = Path(file.filename or "").suffix.lower()
    if not (file.content_type in ALLOWED_CONTENT_TYPES or ext in ALLOWED_EXTENSIONS):
        raise BadRequestError(BAD_FILE_MESSAGE)

    # Read one byte past the ceiling so an oversized upload is detected without
    # buffering all of it.
    content = await file.read(MAX_ORIGINAL_IMAGE_BYTES + 1)
    if not content or len(content) > MAX_ORIGINAL_IMAGE_BYTES:
        raise BadRequestError(BAD_FILE_MESSAGE)

    try:
        image = await asyncio.to_thread(normalize_document_image, content)
    except DocumentImageNormalizationError as exc:
        raise BadRequestError(BAD_FILE_MESSAGE) from exc

    values = {
        "document_image_bytes": image.content,
        "content_type": image.content_type,
        "size_bytes": len(image.content),
    }
    # Atomic upsert on the unique azienda_id: two concurrent uploads cannot both insert.
    stmt = pg_insert(AziendaFotoPresentazione).values(
        id=uuid.uuid4(), azienda_id=azienda_id, **values
    )
    # A Core upsert skips the ORM's onupdate, so the replace path stamps
    # updated_at itself, from the database clock like the insert's default.
    stmt = stmt.on_conflict_do_update(
        index_elements=[AziendaFotoPresentazione.azienda_id],
        set_={**values, "updated_at": func.now()},
    ).returning(AziendaFotoPresentazione.updated_at)
    updated_at = (await db.execute(stmt)).scalar_one()
    await db.commit()
    return FotoPresentazioneResponse(
        azienda_id=azienda_id,
        content_type=image.content_type,
        size_bytes=len(image.content),
        updated_at=updated_at,
    )


@router.get("")
async def get_foto_presentazione(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Stream the stored image bytes for the authenticated preview."""
    await _require_azienda_in_org(azienda_id, org_id, db)
    foto = (
        await db.execute(
            select(AziendaFotoPresentazione).where(
                AziendaFotoPresentazione.azienda_id == azienda_id
            )
        )
    ).scalar_one_or_none()
    if foto is None:
        raise NotFoundError("Foto not found")
    return Response(
        content=foto.document_image_bytes,
        media_type=foto.content_type,
        headers={"Cache-Control": "private, no-cache"},
    )


@router.delete(
    "",
    status_code=204,
    dependencies=[Depends(require_capability(SURVEY_WRITE))],
)
async def delete_foto_presentazione(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Remove the azienda's presentation photo; the DVR then prints no photo
    slot. Idempotent: 204 whether or not there was one."""
    await _require_azienda_in_org(azienda_id, org_id, db)
    foto = (
        await db.execute(
            select(AziendaFotoPresentazione).where(
                AziendaFotoPresentazione.azienda_id == azienda_id
            )
        )
    ).scalar_one_or_none()
    if foto is not None:
        await db.delete(foto)
        await db.commit()
    return Response(status_code=204)
