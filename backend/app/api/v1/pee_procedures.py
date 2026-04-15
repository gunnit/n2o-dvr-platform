"""PEE emergency procedures (A-E) — US-4.2.

CRUD for per-client overrides to the standard five-step emergency response
procedures. Uses ``PeePlan.scenari`` (JSONB) as the override store and merges
with ``app.data.pee_procedures`` defaults on read.
"""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.exceptions import BadRequestError, NotFoundError
from app.data.pee_procedures import (
    EVENT_CODES,
    PROCEDURE_LETTERS,
    get_standard_procedure,
    merge_with_overrides,
)
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.pee_plan import PeePlan

router = APIRouter(prefix="/aziende/{azienda_id}/pee", tags=["pee-procedures"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ProceduraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lettera: str
    titolo: str
    testo: str
    personalizzata: bool


class EventoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codice: str
    titolo: str
    procedure: list[ProceduraResponse]


class ProceduraOverrideBody(BaseModel):
    testo: str = Field(..., min_length=1, max_length=4000)


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


async def _get_or_create_pee(azienda_id: uuid.UUID, db: AsyncSession) -> PeePlan:
    result = await db.execute(
        select(PeePlan).where(
            PeePlan.azienda_id == azienda_id, PeePlan.tipo == "azienda"
        )
    )
    pee = result.scalar_one_or_none()
    if pee:
        return pee
    pee = PeePlan(azienda_id=azienda_id, tipo="azienda", scenari=[])
    db.add(pee)
    await db.flush()
    return pee


def _validate_event_letter(evento: str, lettera: str) -> tuple[str, str]:
    if evento not in EVENT_CODES:
        raise BadRequestError(
            f"Evento sconosciuto: {evento!r}. Ammessi: {', '.join(EVENT_CODES)}."
        )
    letter = lettera.upper()
    if letter not in PROCEDURE_LETTERS:
        raise BadRequestError(
            f"Lettera procedura non valida: {lettera!r}. Ammesse: A, B, C, D, E."
        )
    return evento, letter


def _upsert_override(
    scenari: list[dict] | None,
    evento: str,
    lettera: str,
    testo: str,
) -> list[dict]:
    """Return a new scenari list with this override applied."""
    scenari = [dict(e) for e in (scenari or [])]
    standard = get_standard_procedure(evento, lettera)
    assert standard is not None  # _validate_event_letter already ran

    target_event: dict | None = None
    for e in scenari:
        if e.get("codice") == evento:
            target_event = e
            break
    if target_event is None:
        target_event = {
            "codice": evento,
            "titolo": standard["titolo"],
            "procedure": [],
        }
        scenari.append(target_event)

    procedure = list(target_event.get("procedure") or [])
    row = {
        "lettera": lettera,
        "titolo": standard["titolo"],
        "testo": testo,
        "personalizzata": True,
    }
    for i, p in enumerate(procedure):
        if isinstance(p, dict) and p.get("lettera") == lettera:
            procedure[i] = row
            break
    else:
        procedure.append(row)
    target_event["procedure"] = procedure
    return scenari


def _remove_override(
    scenari: list[dict] | None, evento: str, lettera: str
) -> list[dict]:
    """Return a new scenari list with the (evento, lettera) override removed."""
    out: list[dict] = []
    for e in scenari or []:
        if e.get("codice") != evento:
            out.append(dict(e))
            continue
        procedure = [
            dict(p)
            for p in (e.get("procedure") or [])
            if not (isinstance(p, dict) and p.get("lettera") == lettera)
        ]
        if procedure:
            out.append({**e, "procedure": procedure})
        # If no overrides left for this event, drop it entirely.
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/procedure", response_model=list[EventoResponse])
async def list_procedures(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return the five standard events × A-E procedures, merged with overrides.

    Always returns the full 5×5 grid, even when no PeePlan exists yet.
    """
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(PeePlan).where(
            PeePlan.azienda_id == azienda_id, PeePlan.tipo == "azienda"
        )
    )
    pee = result.scalar_one_or_none()
    return merge_with_overrides(pee.scenari if pee else None)


@router.put(
    "/procedure/{evento}/{lettera}",
    response_model=ProceduraResponse,
)
async def save_procedure_override(
    azienda_id: uuid.UUID,
    evento: str,
    lettera: str,
    body: ProceduraOverrideBody,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Persist a per-client override for one procedure (US-4.2 AC2)."""
    await _get_azienda_or_404(azienda_id, org_id, db)
    evento, letter = _validate_event_letter(evento, lettera)

    pee = await _get_or_create_pee(azienda_id, db)
    pee.scenari = _upsert_override(pee.scenari, evento, letter, body.testo)
    flag_modified(pee, "scenari")
    await db.commit()

    return {
        "lettera": letter,
        "titolo": get_standard_procedure(evento, letter)["titolo"],  # type: ignore[index]
        "testo": body.testo,
        "personalizzata": True,
    }


@router.delete(
    "/procedure/{evento}/{lettera}",
    response_model=ProceduraResponse,
)
async def reset_procedure(
    azienda_id: uuid.UUID,
    evento: str,
    lettera: str,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Drop the per-client override and return the restored standard text (AC3)."""
    await _get_azienda_or_404(azienda_id, org_id, db)
    evento, letter = _validate_event_letter(evento, lettera)

    result = await db.execute(
        select(PeePlan).where(
            PeePlan.azienda_id == azienda_id, PeePlan.tipo == "azienda"
        )
    )
    pee = result.scalar_one_or_none()
    if pee is not None and pee.scenari:
        pee.scenari = _remove_override(pee.scenari, evento, letter)
        flag_modified(pee, "scenari")
        await db.commit()

    standard = get_standard_procedure(evento, letter)
    assert standard is not None  # validated
    return {
        "lettera": letter,
        "titolo": standard["titolo"],
        "testo": standard["testo"],
        "personalizzata": False,
    }
