import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.schemas.attrezzatura import AttrezzaturaCreate, AttrezzaturaResponse, AttrezzaturaUpdate

router = APIRouter(prefix="/aziende/{azienda_id}/attrezzature", tags=["attrezzature"])


async def _get_azienda(azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Azienda:
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


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

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(attrezzatura, field, value)

    await db.commit()
    await db.refresh(attrezzatura)
    return attrezzatura


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
