"""Microclima CRUD (UNI EN ISO 7730 / 7933 / 11079) — one row per (azienda,
ambiente, tipo_ambiente). Mirrors the MMC/VDT shape: list / get / create /
patch / delete scoped by azienda, plus a stateless IREQ preview for the
severe-cold flow. The 6 thermal inputs are stored verbatim so the doc
generator can re-run the calculators at render time.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.permissions import ASSESSMENTS_WRITE
from app.db.session import get_db
from app.dependencies import get_current_org, require_capability
from app.models.ambiente import Ambiente
from app.models.azienda import Azienda
from app.models.microclima_valutazione import MicroclimaValutazione
from app.schemas.microclima import (
    IreqCalcRequest,
    IreqCalcResponse,
    MicroclimaCreate,
    MicroclimaResponse,
    MicroclimaUpdate,
)
from app.services.microclima_calculator import calculate_ireq

router = APIRouter(
    prefix="/aziende/{azienda_id}/microclima-valutazioni", tags=["microclima"]
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


@router.get("", response_model=list[MicroclimaResponse])
async def list_microclima(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[MicroclimaValutazione]:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(MicroclimaValutazione)
        .where(MicroclimaValutazione.azienda_id == azienda_id)
        .order_by(MicroclimaValutazione.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "",
    response_model=MicroclimaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def create_microclima(
    azienda_id: uuid.UUID,
    body: MicroclimaCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> MicroclimaValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    payload = body.model_dump()
    await _validate_ambiente(azienda_id, payload.get("ambiente_id"), db)

    row = MicroclimaValutazione(azienda_id=azienda_id, **payload)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.post(
    "/calc/ireq",
    response_model=IreqCalcResponse,
    # Persists nothing, but declaring the capability keeps the "unguarded
    # writes" review list pinned; all three roles hold assessments:write, so
    # nobody is narrowed (see test_feature_map.py).
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def calculate_ireq_preview(
    azienda_id: uuid.UUID,
    body: IreqCalcRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> IreqCalcResponse:
    """Stateless severe-cold (IREQ, UNI EN ISO 11079) live calculation.

    Mirrors POST /calculate/microclima/{pmv,phs} for the freddo evaluation
    type, but is hosted on the microclima router so the whole cold-stress
    surface stays inside this module. It creates no rows — the frontend
    calls it debounced while the operator edits, then persists the chosen
    scenario via POST "" with tipo_ambiente="severo_freddo".

    Classification (see `calculate_ireq` for the cited thresholds):
      - ACCETTABILE: Icl worn >= IREQneutral (thermal balance, whole shift)
      - LIMITE: IREQminimal <= Icl < IREQneutral (progressive slight cooling)
      - CRITICO: Icl < IREQminimal — exposure limited to DLE minutes
    Wind-chill frostbite bands (Annex D) escalate the level when stricter.
    """
    await _get_azienda_or_404(azienda_id, org_id, db)
    return IreqCalcResponse(
        **calculate_ireq(
            air_temp=body.air_temp,
            mean_radiant_temp=body.mean_radiant_temp,
            air_velocity=body.air_velocity,
            humidity=body.humidity,
            metabolic_rate=body.metabolic_rate,
            clothing_insulation=body.clothing_insulation,
            duration_min=body.duration_min,
        )
    )


@router.get("/{valutazione_id}", response_model=MicroclimaResponse)
async def get_microclima(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> MicroclimaValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(MicroclimaValutazione).where(
            MicroclimaValutazione.id == valutazione_id,
            MicroclimaValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione microclima non trovata")
    return row


@router.patch(
    "/{valutazione_id}",
    response_model=MicroclimaResponse,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def update_microclima(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    body: MicroclimaUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> MicroclimaValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(MicroclimaValutazione).where(
            MicroclimaValutazione.id == valutazione_id,
            MicroclimaValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione microclima non trovata")

    updates = body.model_dump(exclude_unset=True)
    if "ambiente_id" in updates:
        await _validate_ambiente(azienda_id, updates.get("ambiente_id"), db)

    for k, v in updates.items():
        setattr(row, k, v)

    await db.commit()
    await db.refresh(row)
    return row


@router.delete(
    "/{valutazione_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def delete_microclima(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(MicroclimaValutazione).where(
            MicroclimaValutazione.id == valutazione_id,
            MicroclimaValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione microclima non trovata")
    await db.delete(row)
    await db.commit()
