import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.persona import Persona
from app.schemas.persona import PersonaCreate, PersonaResponse, PersonaUpdate

router = APIRouter(prefix="/aziende/{azienda_id}/persone", tags=["persone"])


async def _get_azienda(azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Azienda:
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


@router.get("", response_model=list[PersonaResponse])
async def list_persone(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(select(Persona).where(Persona.azienda_id == azienda_id))
    return result.scalars().all()


@router.post("", response_model=PersonaResponse, status_code=201)
async def create_persona(
    azienda_id: uuid.UUID,
    body: PersonaCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    persona = Persona(**body.model_dump(), azienda_id=azienda_id)
    db.add(persona)
    await db.commit()
    await db.refresh(persona)
    return persona


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    azienda_id: uuid.UUID,
    persona_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Persona).where(Persona.id == persona_id, Persona.azienda_id == azienda_id)
    )
    persona = result.scalar_one_or_none()
    if not persona:
        raise NotFoundError("Persona not found")
    return persona


@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    azienda_id: uuid.UUID,
    persona_id: uuid.UUID,
    body: PersonaUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Persona).where(Persona.id == persona_id, Persona.azienda_id == azienda_id)
    )
    persona = result.scalar_one_or_none()
    if not persona:
        raise NotFoundError("Persona not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(persona, field, value)

    await db.commit()
    await db.refresh(persona)
    return persona


@router.delete("/{persona_id}", status_code=204)
async def delete_persona(
    azienda_id: uuid.UUID,
    persona_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Persona).where(Persona.id == persona_id, Persona.azienda_id == azienda_id)
    )
    persona = result.scalar_one_or_none()
    if not persona:
        raise NotFoundError("Persona not found")

    await db.delete(persona)
    await db.commit()
