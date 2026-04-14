import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.ambiente import Ambiente
from app.models.azienda import Azienda
from app.schemas.ambiente import AmbienteCreate, AmbienteResponse, AmbienteUpdate

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
