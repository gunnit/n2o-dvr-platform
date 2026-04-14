import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.sostanza_chimica import SostanzaChimica
from app.schemas.sostanza_chimica import (
    SostanzaChimicaCreate,
    SostanzaChimicaResponse,
    SostanzaChimicaUpdate,
)

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
