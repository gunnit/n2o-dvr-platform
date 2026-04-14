import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.schemas.azienda import AziendaCreate, AziendaResponse, AziendaUpdate
from app.services.ai import generate_company_description


class DescriptionResponse(BaseModel):
    description: str

router = APIRouter(prefix="/aziende", tags=["aziende"])


@router.get("", response_model=list[AziendaResponse])
async def list_aziende(
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Azienda).where(Azienda.organization_id == org_id).order_by(Azienda.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=AziendaResponse, status_code=201)
async def create_azienda(
    body: AziendaCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    azienda = Azienda(**body.model_dump(), organization_id=org_id)
    db.add(azienda)
    await db.commit()
    await db.refresh(azienda)
    return azienda


@router.get("/{azienda_id}", response_model=AziendaResponse)
async def get_azienda(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


@router.put("/{azienda_id}", response_model=AziendaResponse)
async def update_azienda(
    azienda_id: uuid.UUID,
    body: AziendaUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(azienda, field, value)

    await db.commit()
    await db.refresh(azienda)
    return azienda


@router.delete("/{azienda_id}", status_code=204)
async def delete_azienda(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")

    await db.delete(azienda)
    await db.commit()


@router.post("/{azienda_id}/genera-descrizione", response_model=DescriptionResponse)
async def genera_descrizione(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI company description for DVR Part I (US-2.1).

    Returns the generated text. The caller (frontend editor) is responsible
    for persisting it via PUT /aziende/{id} with descrizione_attivita set.
    This lets the user review/edit before committing.
    """
    result = await db.execute(
        select(Azienda)
        .where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
        .options(
            selectinload(Azienda.ambienti),
            selectinload(Azienda.persone),
        )
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")

    description = await generate_company_description(azienda)
    return DescriptionResponse(description=description)
