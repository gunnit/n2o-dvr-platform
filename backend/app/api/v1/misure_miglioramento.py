"""CRUD API for the DVR §4.1 Programma di Miglioramento (T109).

The misure rows are operator-editable; the DVR generator auto-seeds an
initial set from pericoli with I>=7 the first time the document is built,
then hands ownership to the operator. This endpoint lets the frontend
render and edit the grid without touching the document generator.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.misura_miglioramento import MisuraMiglioramento
from app.schemas.misura_miglioramento import (
    MisuraMiglioramentoCreate,
    MisuraMiglioramentoResponse,
    MisuraMiglioramentoUpdate,
)


router = APIRouter(
    prefix="/aziende/{azienda_id}/misure-miglioramento",
    tags=["misure-miglioramento"],
)


async def _verify_azienda(
    azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> None:
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id, Azienda.organization_id == org_id
        )
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Azienda not found")


@router.get("", response_model=list[MisuraMiglioramentoResponse])
async def list_misure(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(MisuraMiglioramento)
        .where(MisuraMiglioramento.azienda_id == azienda_id)
        .order_by(
            MisuraMiglioramento.ordine,
            MisuraMiglioramento.created_at,
        )
    )
    return result.scalars().all()


@router.post(
    "", response_model=MisuraMiglioramentoResponse, status_code=201
)
async def create_misura(
    azienda_id: uuid.UUID,
    body: MisuraMiglioramentoCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    misura = MisuraMiglioramento(
        azienda_id=azienda_id,
        **body.model_dump(),
    )
    db.add(misura)
    await db.commit()
    await db.refresh(misura)
    return misura


@router.put(
    "/{misura_id}", response_model=MisuraMiglioramentoResponse
)
async def update_misura(
    azienda_id: uuid.UUID,
    misura_id: uuid.UUID,
    body: MisuraMiglioramentoUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(MisuraMiglioramento).where(
            MisuraMiglioramento.id == misura_id,
            MisuraMiglioramento.azienda_id == azienda_id,
        )
    )
    misura = result.scalar_one_or_none()
    if not misura:
        raise NotFoundError("Misura not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(misura, field, value)
    await db.commit()
    await db.refresh(misura)
    return misura


@router.delete("/{misura_id}", status_code=204)
async def delete_misura(
    azienda_id: uuid.UUID,
    misura_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(MisuraMiglioramento).where(
            MisuraMiglioramento.id == misura_id,
            MisuraMiglioramento.azienda_id == azienda_id,
        )
    )
    misura = result.scalar_one_or_none()
    if not misura:
        raise NotFoundError("Misura not found")
    await db.delete(misura)
    await db.commit()
