"""VDT (Videoterminali) CRUD endpoints (US-3.4 / US-3.5).

One VdtValutazione row per (worker, workstation). Server derives:
  - ``esposto`` from ``ore_settimanali`` (>= 20 h/week per art. 173)
  - ``periodicita_sorveglianza`` from ``eta_50_plus`` (biennale / quinquennale)
  - ``data_prossima_visita`` from ``data_ultima_visita`` (or today as anchor)
    when the worker is esposto.

Mirrors the MMC pattern: input is the single source of truth, derived
fields cannot drift from it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.persona import Persona
from app.models.vdt_valutazione import VdtValutazione
from app.schemas.vdt import (
    VdtValutazioneCreate,
    VdtValutazioneResponse,
    VdtValutazioneUpdate,
)
from app.services.vdt_calculator import classify_exposure
from app.services.vdt_surveillance import (
    cadence_years_for,
    compute_next_visit,
    periodicita_label_for,
)

router = APIRouter(prefix="/aziende/{azienda_id}/vdt", tags=["vdt"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


async def _validate_persona(
    azienda_id: uuid.UUID, persona_id: uuid.UUID | None, db: AsyncSession
) -> None:
    if persona_id is None:
        return
    result = await db.execute(
        select(Persona).where(Persona.id == persona_id, Persona.azienda_id == azienda_id)
    )
    if result.scalar_one_or_none() is None:
        raise BadRequestError("persona_id non appartiene a questa azienda")


def _apply_derived(payload: dict[str, Any]) -> dict[str, Any]:
    """Fill in esposto + surveillance fields from the input."""
    out = dict(payload)
    ore = float(out.get("ore_settimanali") or 0)
    esposto = classify_exposure(ore) == "ESPOSTO"
    out["esposto"] = esposto

    over_50 = bool(out.get("eta_50_plus") or False)
    if esposto:
        out["periodicita_sorveglianza"] = periodicita_label_for(over_50)
        today = datetime.now(timezone.utc).date()
        schedule = compute_next_visit(
            data_ultima_visita=out.get("data_ultima_visita"),
            over_50=over_50,
            today=today,
        )
        # Only auto-fill data_prossima_visita; leave data_ultima_visita alone.
        out["data_prossima_visita"] = schedule.data_prossima_visita
    else:
        out["periodicita_sorveglianza"] = None
        out["data_prossima_visita"] = None
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[VdtValutazioneResponse])
async def list_vdt(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[VdtValutazione]:
    """List all VDT valutazioni for this azienda (newest first)."""
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(VdtValutazione)
        .where(VdtValutazione.azienda_id == azienda_id)
        .order_by(VdtValutazione.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=VdtValutazioneResponse, status_code=status.HTTP_201_CREATED)
async def create_vdt(
    azienda_id: uuid.UUID,
    body: VdtValutazioneCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> VdtValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    payload = body.model_dump()
    await _validate_persona(azienda_id, payload.get("persona_id"), db)

    enriched = _apply_derived(payload)
    row = VdtValutazione(azienda_id=azienda_id, **enriched)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/{vdt_id}", response_model=VdtValutazioneResponse)
async def get_vdt(
    azienda_id: uuid.UUID,
    vdt_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> VdtValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(VdtValutazione).where(
            VdtValutazione.id == vdt_id, VdtValutazione.azienda_id == azienda_id
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione VDT non trovata")
    return row


@router.patch("/{vdt_id}", response_model=VdtValutazioneResponse)
async def update_vdt(
    azienda_id: uuid.UUID,
    vdt_id: uuid.UUID,
    body: VdtValutazioneUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> VdtValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(VdtValutazione).where(
            VdtValutazione.id == vdt_id, VdtValutazione.azienda_id == azienda_id
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione VDT non trovata")

    updates = body.model_dump(exclude_unset=True)
    if "persona_id" in updates:
        await _validate_persona(azienda_id, updates.get("persona_id"), db)

    # Merge with current state so _apply_derived sees everything.
    current = {
        "ore_settimanali": float(row.ore_settimanali) if row.ore_settimanali is not None else 0.0,
        "eta_50_plus": row.eta_50_plus,
        "data_ultima_visita": row.data_ultima_visita,
    }
    current.update({k: v for k, v in updates.items() if k in current})
    derived = _apply_derived(current)

    for k, v in updates.items():
        setattr(row, k, v)
    for k in ("esposto", "periodicita_sorveglianza", "data_prossima_visita"):
        setattr(row, k, derived[k])

    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/{vdt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vdt(
    azienda_id: uuid.UUID,
    vdt_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(VdtValutazione).where(
            VdtValutazione.id == vdt_id, VdtValutazione.azienda_id == azienda_id
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione VDT non trovata")
    await db.delete(row)
    await db.commit()


# ``cadence_years_for`` is re-exported only to keep the symbol live for tests
# that want to assert the statutory cadence directly without importing the
# surveillance module separately.
__all__ = ["router", "cadence_years_for"]
