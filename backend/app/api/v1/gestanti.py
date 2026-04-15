"""Gestanti cross-reference & relocation decision API.

Closes US-3.9 (auto cross-reference mansione <-> D.Lgs. 151/2001) and
US-3.10 (accept/reject relocation with justification / misura alternativa).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.data.dlgs_151_2001 import (
    INCOMPATIBLE_RISKS,
    find_matches_for_mansione,
    has_any_incompatible_risk,
)
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.gestanti_valutazione import GestantiValutazione
from app.models.persona import Persona
from app.schemas.gestanti import (
    CrossReferenceRequest,
    CrossReferenceResponse,
    DecisionRequest,
    DecisionResponse,
    RiskMatch,
)

router = APIRouter(tags=["gestanti"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_azienda(
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


def _suggest_alternative_mansione(
    worker_mansione: str,
    all_persone_in_azienda: list[Persona],
) -> str | None:
    """Pick another mansione from the same azienda that has zero matches.

    Preferred: a *different* mansione string from a different worker. We return
    the first clean mansione we find. If none exist, return None.
    """
    if not all_persone_in_azienda:
        return None

    seen: set[str] = set()
    current = (worker_mansione or "").strip().lower()
    for pers in all_persone_in_azienda:
        mans = (pers.mansione or "").strip()
        if not mans:
            continue
        norm = mans.lower()
        if norm == current or norm in seen:
            continue
        seen.add(norm)
        if not has_any_incompatible_risk(mans):
            return mans
    return None


def _index_existing_decisions(
    valutazione: GestantiValutazione | None,
) -> dict[str, dict[str, Any]]:
    """Build a {risk_key: decision_row} map from the persisted JSONB."""
    if valutazione is None or not valutazione.rischi_vietati:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in valutazione.rischi_vietati:
        if not isinstance(row, dict):
            continue
        key = row.get("risk_key")
        if isinstance(key, str):
            out[key] = row
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/aziende/{azienda_id}/gestanti/cross-reference",
    response_model=CrossReferenceResponse,
)
async def cross_reference(
    azienda_id: uuid.UUID,
    body: CrossReferenceRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> CrossReferenceResponse:
    """Cross-reference a worker's mansione against the D.Lgs. 151/2001 catalog.

    Returns the list of matching incompatible risks (each carrying the
    Allegato letter and descrizione). Also returns a suggested alternative
    mansione chosen from other workers in the same azienda that have zero
    matches. `is_new` flags matches that weren't present in the persisted
    GestantiValutazione for this worker (if any).
    """
    await _get_azienda(azienda_id, org_id, db)

    result = await db.execute(
        select(Persona).where(
            Persona.id == body.worker_id, Persona.azienda_id == azienda_id
        )
    )
    persona = result.scalar_one_or_none()
    if not persona:
        raise NotFoundError("Lavoratrice non trovata")

    # Existing valutazione (if any) for "is_new" comparison.
    result = await db.execute(
        select(GestantiValutazione).where(
            GestantiValutazione.azienda_id == azienda_id,
            GestantiValutazione.persona_id == persona.id,
        )
    )
    valutazione = result.scalar_one_or_none()
    existing = _index_existing_decisions(valutazione)

    # Collect all workers (used to propose an alternative mansione).
    result = await db.execute(
        select(Persona).where(Persona.azienda_id == azienda_id)
    )
    all_workers = list(result.scalars().all())

    matches_raw = find_matches_for_mansione(persona.mansione or "")
    suggested = _suggest_alternative_mansione(persona.mansione or "", all_workers)

    matches: list[RiskMatch] = []
    for key, info in matches_raw:
        prior = existing.get(key)
        matches.append(
            RiskMatch(
                risk_key=key,
                allegato=info["allegato"],
                descrizione=info["descrizione"],
                suggested_alternative_mansione=suggested,
                is_new=(prior is None),
                decision=prior.get("action") if prior else None,
                justification=prior.get("justification") if prior else None,
                misura_alternativa=prior.get("misura_alternativa") if prior else None,
            )
        )

    return CrossReferenceResponse(
        worker_id=persona.id,
        worker_nominativo=persona.nominativo,
        worker_mansione=persona.mansione,
        cleared=len(matches) == 0,
        matches=matches,
        valutazione_id=valutazione.id if valutazione else None,
    )


@router.post(
    "/aziende/{azienda_id}/gestanti/{valutazione_id}/decision",
    response_model=DecisionResponse,
)
async def record_decision(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    body: DecisionRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> DecisionResponse:
    """Persist the operator's accept/reject decision for one risk match.

    Accept requires `justification`; reject requires `misura_alternativa`
    (both >= 10 chars, enforced by the schema). The decision list is stored
    as a list of dicts in `GestantiValutazione.rischi_vietati` (JSONB). A
    second decision for the same risk_key replaces the previous one.
    """
    await _get_azienda(azienda_id, org_id, db)

    if body.risk_key not in INCOMPATIBLE_RISKS:
        raise BadRequestError(f"risk_key sconosciuto: {body.risk_key}")

    if body.action == "accept" and not body.justification:
        raise BadRequestError(
            "La motivazione (justification) e' obbligatoria quando action = 'accept'."
        )
    if body.action == "reject" and not body.misura_alternativa:
        raise BadRequestError(
            "La misura alternativa e' obbligatoria quando action = 'reject'."
        )

    result = await db.execute(
        select(GestantiValutazione).where(
            GestantiValutazione.id == valutazione_id,
            GestantiValutazione.azienda_id == azienda_id,
        )
    )
    val = result.scalar_one_or_none()
    if not val:
        raise NotFoundError("Valutazione Gestanti non trovata")

    info = INCOMPATIBLE_RISKS[body.risk_key]
    # Load current list, swap-or-append the decision for this risk_key.
    current = list(val.rischi_vietati or [])
    replaced = False
    new_row: dict[str, Any] = {
        "risk_key": body.risk_key,
        "allegato": info["allegato"],
        "descrizione": info["descrizione"],
        "action": body.action,
        "justification": body.justification,
        "misura_alternativa": body.misura_alternativa,
    }
    for i, row in enumerate(current):
        if isinstance(row, dict) and row.get("risk_key") == body.risk_key:
            current[i] = new_row
            replaced = True
            break
    if not replaced:
        current.append(new_row)

    val.rischi_vietati = current
    # SQLAlchemy's JSONB change detection needs an explicit flag_modified for
    # in-place list mutations on older setups; re-assignment above is enough
    # because we build a new list object.

    await db.commit()
    await db.refresh(val)

    return DecisionResponse(
        valutazione_id=val.id,
        persisted_decisions=list(val.rischi_vietati or []),
    )
