import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.ambiente import Ambiente
from app.models.ambiente_foto import AmbienteFoto
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.schemas.attrezzatura import AttrezzaturaCreate, AttrezzaturaResponse, AttrezzaturaUpdate
from app.services.ai import (
    AttrezzaturaIdentificata,
    AttrezzaturaSuggerita,
    extract_attrezzature_from_photos,
    suggest_attrezzature,
)

# Photos sent to OpenAI input_image must be in one of these formats; HEIC
# is rejected (would need server-side conversion).
_OPENAI_VISION_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class SuggestAttrezzatureResponse(BaseModel):
    items: list[AttrezzaturaSuggerita]


class ExtractAttrezzatureFromPhotosResponse(BaseModel):
    items: list[AttrezzaturaIdentificata]
    photos_used: int


router = APIRouter(prefix="/aziende/{azienda_id}/attrezzature", tags=["attrezzature"])


async def _get_azienda(azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Azienda:
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


async def _validate_ambiente(
    ambiente_id: uuid.UUID, azienda_id: uuid.UUID, db: AsyncSession
) -> None:
    """Phase 2.3: ensure the ambiente exists and belongs to this azienda.

    Reject mismatched IDs with a 422 so the frontend can surface the error
    without leaking other companies' data through 404 timing.
    """
    result = await db.execute(
        select(Ambiente.id).where(
            Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=422,
            detail="ambiente_id does not belong to this azienda",
        )


@router.get("", response_model=list[AttrezzaturaResponse])
async def list_attrezzature(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(select(Attrezzatura).where(Attrezzatura.azienda_id == azienda_id))
    return result.scalars().all()


@router.post("", response_model=AttrezzaturaResponse, status_code=201)
async def create_attrezzatura(
    azienda_id: uuid.UUID,
    body: AttrezzaturaCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    await _validate_ambiente(body.ambiente_id, azienda_id, db)
    attrezzatura = Attrezzatura(**body.model_dump(), azienda_id=azienda_id)
    db.add(attrezzatura)
    await db.commit()
    await db.refresh(attrezzatura)
    return attrezzatura


@router.get("/{attrezzatura_id}", response_model=AttrezzaturaResponse)
async def get_attrezzatura(
    azienda_id: uuid.UUID,
    attrezzatura_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Attrezzatura).where(
            Attrezzatura.id == attrezzatura_id, Attrezzatura.azienda_id == azienda_id
        )
    )
    attrezzatura = result.scalar_one_or_none()
    if not attrezzatura:
        raise NotFoundError("Attrezzatura not found")
    return attrezzatura


@router.put("/{attrezzatura_id}", response_model=AttrezzaturaResponse)
async def update_attrezzatura(
    azienda_id: uuid.UUID,
    attrezzatura_id: uuid.UUID,
    body: AttrezzaturaUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Attrezzatura).where(
            Attrezzatura.id == attrezzatura_id, Attrezzatura.azienda_id == azienda_id
        )
    )
    attrezzatura = result.scalar_one_or_none()
    if not attrezzatura:
        raise NotFoundError("Attrezzatura not found")

    update_fields = body.model_dump(exclude_unset=True)
    if "ambiente_id" in update_fields and update_fields["ambiente_id"] is not None:
        await _validate_ambiente(update_fields["ambiente_id"], azienda_id, db)

    for field, value in update_fields.items():
        setattr(attrezzatura, field, value)

    await db.commit()
    await db.refresh(attrezzatura)
    return attrezzatura


@router.post(
    "/suggerisci/{ambiente_id}",
    response_model=SuggestAttrezzatureResponse,
)
async def suggerisci_attrezzature(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Phase 5.3 — AI-suggest typical equipment for an ambiente.

    Returns 3-8 candidates the operator can review and tick into actual
    Attrezzatura rows. The endpoint never persists; only the explicit POST
    on the existing /aziende/{id}/attrezzature does.
    """
    azienda = await _get_azienda(azienda_id, org_id, db)
    amb = (
        await db.execute(
            select(Ambiente).where(
                Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id
            )
        )
    ).scalar_one_or_none()
    if amb is None:
        raise NotFoundError("Ambiente not found")

    # Pass already-declared equipment in this ambiente so the model doesn't
    # re-suggest items the operator already ticked.
    existing = (
        await db.execute(
            select(Attrezzatura.descrizione).where(
                Attrezzatura.ambiente_id == ambiente_id
            )
        )
    ).scalars().all()

    items = await suggest_attrezzature(amb, azienda, list(existing))
    return SuggestAttrezzatureResponse(items=items)


@router.post(
    "/estrai-foto/{ambiente_id}",
    response_model=ExtractAttrezzatureFromPhotosResponse,
)
async def estrai_attrezzature_da_foto(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Vision-extract attrezzature visible in the ambiente's photos.

    The model identifies equipment in the photos uploaded to step-ambienti.
    Returns suggestions the operator can review and tick into actual
    Attrezzatura rows. Never persists; only the explicit POST on
    /aziende/{id}/attrezzature does.

    Returns 400 if no usable photos are attached (HEIC photos are skipped
    because OpenAI input_image rejects them).
    """
    azienda = await _get_azienda(azienda_id, org_id, db)
    amb = (
        await db.execute(
            select(Ambiente).where(
                Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id
            )
        )
    ).scalar_one_or_none()
    if amb is None:
        raise NotFoundError("Ambiente not found")

    foto_rows = (
        await db.execute(
            select(AmbienteFoto).where(AmbienteFoto.ambiente_id == ambiente_id)
        )
    ).scalars().all()
    if not foto_rows:
        raise BadRequestError(
            "Nessuna foto caricata per questo ambiente. Carica almeno una "
            "foto prima di estrarre con AI."
        )

    # Keep only formats OpenAI can ingest; HEIC silently skipped to avoid
    # blowing up when an iPhone upload sneaks through. Verify the file is
    # actually on disk too — Render Disk attaches across deploys but a
    # missing file shouldn't crash the whole call.
    usable_paths: list[Path] = []
    for foto in foto_rows:
        if foto.content_type not in _OPENAI_VISION_MIME_TYPES:
            continue
        path = Path(foto.file_path)
        if not path.is_file():
            continue
        usable_paths.append(path)

    if not usable_paths:
        raise BadRequestError(
            "Nessuna foto utilizzabile per l'estrazione (formati supportati: "
            "JPEG, PNG, WebP, GIF). Le foto HEIC non sono supportate."
        )

    existing = (
        await db.execute(
            select(Attrezzatura.descrizione).where(
                Attrezzatura.ambiente_id == ambiente_id
            )
        )
    ).scalars().all()

    items = await extract_attrezzature_from_photos(
        amb, azienda, list(usable_paths), list(existing)
    )
    return ExtractAttrezzatureFromPhotosResponse(
        items=items,
        photos_used=len(usable_paths),
    )


@router.delete("/{attrezzatura_id}", status_code=204)
async def delete_attrezzatura(
    azienda_id: uuid.UUID,
    attrezzatura_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Attrezzatura).where(
            Attrezzatura.id == attrezzatura_id, Attrezzatura.azienda_id == azienda_id
        )
    )
    attrezzatura = result.scalar_one_or_none()
    if not attrezzatura:
        raise NotFoundError("Attrezzatura not found")

    await db.delete(attrezzatura)
    await db.commit()
