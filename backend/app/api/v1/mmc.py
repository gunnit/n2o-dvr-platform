"""MMC (Movimentazione Manuale dei Carichi) CRUD endpoints (US-3.1 - US-3.3).

One MmcValutazione row per (worker, lifting task). Server runs NIOSH math
(via app.data.niosh_factors) so the input form is the single source of truth
and stale multipliers can never drift from inputs.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.data.niosh_cp import get_default_cp
from app.data.niosh_factors import classify_ir, compute_plr
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.mmc_valutazione import MmcValutazione
from app.models.persona import Persona
from app.schemas.mmc import (
    MmcValutazioneCreate,
    MmcValutazioneResponse,
    MmcValutazioneUpdate,
)

router = APIRouter(prefix="/aziende/{azienda_id}/mmc", tags=["mmc"])


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


def _resolve_cp(sesso: str, fascia_eta: str, override: float | None) -> float:
    """Pick CP either from explicit override or the standard table."""
    if override is not None and override > 0:
        return float(override)
    eta = 30 if fascia_eta.startswith(">") else 16
    try:
        return float(get_default_cp(sesso, eta))  # type: ignore[arg-type]
    except ValueError:
        return 25.0


def _apply_niosh(payload: dict[str, Any]) -> dict[str, Any]:
    """Compute (or accept) NIOSH multipliers + PLR + IR + level + area.

    Mutates a copy of `payload` and returns it. Strategy:
      1. CP: use override if provided, else default table by sex+age band.
      2. If all 7 inputs are present, recompute multipliers from inputs
         (lookup tables in `app.data.niosh_factors`). Otherwise, accept any
         pre-supplied multipliers from the caller (defaulting to 1.0).
      3. Compute PLR, IR, level, area.
    """
    out = dict(payload)
    sesso = out.get("sesso") or "M"
    fascia_eta = out.get("fascia_eta") or ">18"
    cp = _resolve_cp(sesso, fascia_eta, out.get("cp"))
    out["cp"] = cp

    inputs_present = all(
        out.get(k) is not None
        for k in (
            "altezza_cm",
            "dislocazione_cm",
            "distanza_cm",
            "angolo_gradi",
            "giudizio_presa",
            "frequenza_atti_min",
            "durata_min",
        )
    )

    if inputs_present:
        derived = compute_plr(
            cp=cp,
            altezza_cm=float(out["altezza_cm"]),
            dislocazione_cm=float(out["dislocazione_cm"]),
            distanza_cm=float(out["distanza_cm"]),
            angolo_gradi=float(out["angolo_gradi"]),
            giudizio_presa=str(out["giudizio_presa"]),
            frequenza_atti_min=float(out["frequenza_atti_min"]),
            durata_min=float(out["durata_min"]),
        )
        out.update(derived)
    else:
        # Fall back to provided multipliers (default 1.0 each).
        for k in ("fattore_a", "fattore_b", "fattore_c", "fattore_d", "fattore_e", "fattore_f"):
            if out.get(k) is None:
                out[k] = 1.0
        plr = (
            cp
            * float(out["fattore_a"])
            * float(out["fattore_b"])
            * float(out["fattore_c"])
            * float(out["fattore_d"])
            * float(out["fattore_e"])
            * float(out["fattore_f"])
        )
        out["plr"] = round(plr, 4)

    peso = float(out.get("peso_kg") or 0)
    plr = float(out.get("plr") or 0)
    ir = peso / plr if plr > 0 else 0.0
    out["indice_ir"] = round(ir, 4)
    livello = classify_ir(ir)
    out["livello_rischio"] = livello
    out["area_classificazione"] = {
        "VERDE": "Verde",
        "GIALLO": "Gialla",
        "ROSSO": "Rossa",
    }[livello]
    return out


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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[MmcValutazioneResponse])
async def list_mmc(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[MmcValutazione]:
    """List all MMC valutazioni for this azienda (newest first)."""
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(MmcValutazione)
        .where(MmcValutazione.azienda_id == azienda_id)
        .order_by(MmcValutazione.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=MmcValutazioneResponse, status_code=status.HTTP_201_CREATED)
async def create_mmc(
    azienda_id: uuid.UUID,
    body: MmcValutazioneCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> MmcValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    payload = body.model_dump()
    await _validate_persona(azienda_id, payload.get("persona_id"), db)

    enriched = _apply_niosh(payload)
    row = MmcValutazione(azienda_id=azienda_id, **enriched)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/{mmc_id}", response_model=MmcValutazioneResponse)
async def get_mmc(
    azienda_id: uuid.UUID,
    mmc_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> MmcValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(MmcValutazione).where(
            MmcValutazione.id == mmc_id, MmcValutazione.azienda_id == azienda_id
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione MMC non trovata")
    return row


# Fields that, when changed, force NIOSH multipliers to be recomputed.
_NIOSH_INPUT_FIELDS = (
    "sesso",
    "fascia_eta",
    "peso_kg",
    "altezza_cm",
    "dislocazione_cm",
    "distanza_cm",
    "angolo_gradi",
    "giudizio_presa",
    "frequenza_atti_min",
    "durata_min",
    "cp",
)

_NIOSH_DERIVED_FIELDS = (
    "cp",
    "fattore_a",
    "fattore_b",
    "fattore_c",
    "fattore_d",
    "fattore_e",
    "fattore_f",
    "plr",
    "indice_ir",
    "livello_rischio",
    "area_classificazione",
)


def _build_patch_assignments(
    row: MmcValutazione, updates: dict[str, Any]
) -> dict[str, Any]:
    """Decide which attributes to write back on a PATCH.

    Always writes the fields the client actually sent (from `updates`, which
    is `model_dump(exclude_unset=True)`). Additionally, if any NIOSH input
    field changed, recomputes the derived multipliers (cp, fattore_a..f,
    plr, indice_ir, livello_rischio, area_classificazione) from the merged
    state and writes those too.

    Pure function — no DB I/O — so the merge logic is unit-testable.
    """
    # Start with exactly what the client sent. Non-NIOSH fields like compito,
    # note, misure_proposte, ambiente_id, persona_id pass straight through.
    assignments: dict[str, Any] = dict(updates)

    niosh_inputs_changed = any(k in updates for k in _NIOSH_INPUT_FIELDS)
    if not niosh_inputs_changed:
        return assignments

    # Recompute multipliers from merged (current row + updates) state.
    current = {
        "sesso": row.sesso,
        "fascia_eta": row.fascia_eta,
        "peso_kg": float(row.peso_kg) if row.peso_kg is not None else 0.0,
        "altezza_cm": row.altezza_cm,
        "dislocazione_cm": row.dislocazione_cm,
        "distanza_cm": row.distanza_cm,
        "angolo_gradi": row.angolo_gradi,
        "giudizio_presa": row.giudizio_presa,
        "frequenza_atti_min": (
            float(row.frequenza_atti_min) if row.frequenza_atti_min is not None else None
        ),
        "durata_min": row.durata_min,
        "cp": float(row.cp) if row.cp is not None else None,
    }
    current.update({k: updates[k] for k in _NIOSH_INPUT_FIELDS if k in updates})
    enriched = _apply_niosh(current)
    for k in _NIOSH_DERIVED_FIELDS:
        assignments[k] = enriched[k]
    return assignments


@router.patch("/{mmc_id}", response_model=MmcValutazioneResponse)
async def update_mmc(
    azienda_id: uuid.UUID,
    mmc_id: uuid.UUID,
    body: MmcValutazioneUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> MmcValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(MmcValutazione).where(
            MmcValutazione.id == mmc_id, MmcValutazione.azienda_id == azienda_id
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione MMC non trovata")

    updates = body.model_dump(exclude_unset=True)
    if "persona_id" in updates:
        await _validate_persona(azienda_id, updates.get("persona_id"), db)

    assignments = _build_patch_assignments(row, updates)
    for k, v in assignments.items():
        setattr(row, k, v)

    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/{mmc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mmc(
    azienda_id: uuid.UUID,
    mmc_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(MmcValutazione).where(
            MmcValutazione.id == mmc_id, MmcValutazione.azienda_id == azienda_id
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione MMC non trovata")
    await db.delete(row)
    await db.commit()
