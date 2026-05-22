"""Rischio Incendio (D.M. 03/09/2021) CRUD — one row per (azienda, ambiente).

INF + SI + PI -> punteggio_totale and livello_rischio are PostgreSQL-generated
columns, so the server never has to compute them — it only validates that each
score is in 1-3 and lets the DB derive the rest. Mirrors the MMC/VDT pattern:
list/get/create/patch/delete scoped by azienda.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.ambiente import Ambiente
from app.models.azienda import Azienda
from app.models.incendio_valutazione import IncendioValutazione
from app.schemas.incendio import (
    IncendioCreate,
    IncendioResponse,
    IncendioUpdate,
)

router = APIRouter(
    prefix="/aziende/{azienda_id}/incendio-valutazioni", tags=["incendio"]
)


async def _get_azienda_or_404(
    azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> Azienda:
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id, Azienda.organization_id == org_id
        )
    )
    az = result.scalar_one_or_none()
    if not az:
        raise NotFoundError("Azienda non trovata")
    return az


async def _validate_ambiente(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID | None,
    db: AsyncSession,
) -> None:
    if ambiente_id is None:
        return
    result = await db.execute(
        select(Ambiente).where(
            Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise BadRequestError("ambiente_id non appartiene a questa azienda")


@router.get("", response_model=list[IncendioResponse])
async def list_incendio(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[IncendioValutazione]:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(IncendioValutazione)
        .where(IncendioValutazione.azienda_id == azienda_id)
        .order_by(IncendioValutazione.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "", response_model=IncendioResponse, status_code=status.HTTP_201_CREATED
)
async def create_incendio(
    azienda_id: uuid.UUID,
    body: IncendioCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> IncendioValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    payload = body.model_dump()
    await _validate_ambiente(azienda_id, payload.get("ambiente_id"), db)

    row = IncendioValutazione(azienda_id=azienda_id, **payload)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/{valutazione_id}", response_model=IncendioResponse)
async def get_incendio(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> IncendioValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(IncendioValutazione).where(
            IncendioValutazione.id == valutazione_id,
            IncendioValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione incendio non trovata")
    return row


@router.patch("/{valutazione_id}", response_model=IncendioResponse)
async def update_incendio(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    body: IncendioUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> IncendioValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(IncendioValutazione).where(
            IncendioValutazione.id == valutazione_id,
            IncendioValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione incendio non trovata")

    updates = body.model_dump(exclude_unset=True)
    if "ambiente_id" in updates:
        await _validate_ambiente(azienda_id, updates.get("ambiente_id"), db)

    for k, v in updates.items():
        setattr(row, k, v)

    await db.commit()
    # punteggio_totale + livello_rischio are PG-generated; force a refresh so
    # the response reflects the new derived values.
    await db.refresh(row)
    return row


@router.delete("/{valutazione_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incendio(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(IncendioValutazione).where(
            IncendioValutazione.id == valutazione_id,
            IncendioValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione incendio non trovata")
    await db.delete(row)
    await db.commit()
