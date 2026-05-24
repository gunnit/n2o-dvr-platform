"""Per-azienda Stress Lavoro-Correlato valutazione (INAIL Metodo Indicatori
Oggettivi).

Endpoints under /aziende/{azienda_id}/stress/valutazione:
  * GET ""  — fetch the latest persisted valutazione (or 404 / null body)
  * PUT ""  — upsert: run the INAIL calculator on the submitted answers,
              persist raw answers (split by area) + computed scores + level.

Org scope enforced via the same _get_azienda pattern used in
stress_misure.py — any request against an azienda the caller's org does
not own returns 404.

Feedback #31 (2026-05-18): the "Conferma valutazione" button on
/assessments/stress used to call the stateless /calculate/stress endpoint
which never persisted anything. This module gives the page a real
persistence target so a returning operator sees the previous run instead
of an empty checklist, and so downstream document generation can read a
canonical row.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.stress_valutazione import StressValutazione
from app.schemas.stress_valutazione import (
    StressValutazioneResponse,
    StressValutazioneUpsert,
)
from app.services.stress_calculator import calculate_stress

router = APIRouter(
    prefix="/aziende/{azienda_id}/stress/valutazione",
    tags=["stress-valutazione"],
)


async def _get_azienda(
    azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> Azienda:
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id, Azienda.organization_id == org_id
        )
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


def _split_answers_by_area(
    answers: dict[str, str],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Split the flat indicator->answer map into the three JSONB columns.

    Area A indicators are "A.*"; Area B covers B1..B6 sub-areas; Area C
    covers C1..C4 sub-areas. We persist the raw answer strings (not the
    numeric scores) so a future re-tweak of the calculator can re-score
    historical valutazioni without losing operator input.
    """
    area_a: dict[str, str] = {}
    area_b: dict[str, str] = {}
    area_c: dict[str, str] = {}
    for ind_id, ans in answers.items():
        if not ans:
            continue
        if ind_id.startswith("A."):
            area_a[ind_id] = ans
        elif ind_id.startswith("B"):
            area_b[ind_id] = ans
        elif ind_id.startswith("C"):
            area_c[ind_id] = ans
    return area_a, area_b, area_c


def _serialize(val: StressValutazione, calc: dict | None = None) -> StressValutazioneResponse:
    azione = calc.get("azione") if calc else None
    unanswered = calc.get("unanswered", []) if calc else []
    return StressValutazioneResponse(
        id=val.id,
        azienda_id=val.azienda_id,
        gruppo_omogeneo=val.gruppo_omogeneo,
        mansione=val.mansione,
        area_a_eventi_sentinella=val.area_a_eventi_sentinella or {},
        area_b_contenuto_lavoro=val.area_b_contenuto_lavoro or {},
        area_c_contesto_lavoro=val.area_c_contesto_lavoro or {},
        punteggio_a=val.punteggio_a,
        punteggio_b=val.punteggio_b,
        punteggio_c=val.punteggio_c,
        punteggio_totale=val.punteggio_totale,
        livello_rischio=val.livello_rischio,
        misure_correttive=val.misure_correttive,
        note=val.note,
        created_at=val.created_at,
        updated_at=val.updated_at,
        unanswered=unanswered,
        azione=azione,
    )


@router.get(
    "",
    response_model=StressValutazioneResponse | None,
    responses={200: {"description": "Latest valutazione, or null if none"}},
)
async def get_valutazione(
    azienda_id: uuid.UUID,
    response: Response,
    mansione: Optional[str] = Query(None, description="Filter by mansione (null = Generale)"),
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    q = select(StressValutazione).where(
        StressValutazione.azienda_id == azienda_id,
    )
    # Filter by mansione: explicit value or NULL (Generale)
    if mansione is not None:
        q = q.where(StressValutazione.mansione == mansione)
    else:
        q = q.where(StressValutazione.mansione.is_(None))
    q = q.order_by(StressValutazione.updated_at.desc()).limit(1)
    result = await db.execute(q)
    val = result.scalar_one_or_none()
    if val is None:
        # 200 with null body — the frontend distinguishes "no run yet"
        # from "auth failed", and a 404 would be ambiguous against the
        # azienda-not-found case.
        response.status_code = 200
        return None
    # Re-run the calculator so the response always carries azione +
    # unanswered alongside the persisted scores — cheaper than storing
    # those derived fields and keeps the calculator as the single source
    # of truth for the action text.
    flat = {
        **(val.area_a_eventi_sentinella or {}),
        **(val.area_b_contenuto_lavoro or {}),
        **(val.area_c_contesto_lavoro or {}),
    }
    calc = calculate_stress(flat)
    return _serialize(val, calc)


@router.get(
    "/all",
    response_model=list[StressValutazioneResponse],
    responses={200: {"description": "All valutazioni for the azienda"}},
)
async def list_valutazioni(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Return every stress valutazione for the azienda (all mansioni)."""
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(StressValutazione)
        .where(StressValutazione.azienda_id == azienda_id)
        .order_by(StressValutazione.mansione.asc().nullsfirst(), StressValutazione.updated_at.desc())
    )
    rows = result.scalars().all()
    out: list[StressValutazioneResponse] = []
    for val in rows:
        flat = {
            **(val.area_a_eventi_sentinella or {}),
            **(val.area_b_contenuto_lavoro or {}),
            **(val.area_c_contesto_lavoro or {}),
        }
        calc = calculate_stress(flat)
        out.append(_serialize(val, calc))
    return out


@router.get(
    "/mansioni",
    response_model=list[str],
    responses={200: {"description": "Distinct mansioni with saved valutazioni"}},
)
async def list_mansioni(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Return distinct mansioni that have a persisted stress valutazione."""
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(distinct(StressValutazione.mansione))
        .where(StressValutazione.azienda_id == azienda_id)
    )
    # Return non-null mansioni. The NULL entry (Generale) is implicit.
    return [r for r in result.scalars().all() if r is not None]


@router.put("", response_model=StressValutazioneResponse)
async def upsert_valutazione(
    azienda_id: uuid.UUID,
    body: StressValutazioneUpsert,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)

    gruppo = (body.gruppo_omogeneo or "Azienda intera").strip() or "Azienda intera"
    # Feedback #17: per-mansione stress assessments. Normalize empty
    # string to NULL (= Generale).
    mansione = (body.mansione or "").strip() or None

    calc = calculate_stress(body.answers)
    area_a, area_b, area_c = _split_answers_by_area(body.answers)

    # Upsert keyed by (azienda_id, gruppo_omogeneo, mansione). One
    # valutazione per group+role: re-confirming overwrites scores so
    # the fascicolo always shows the most recent run.
    q = select(StressValutazione).where(
        StressValutazione.azienda_id == azienda_id,
        StressValutazione.gruppo_omogeneo == gruppo,
    )
    if mansione is not None:
        q = q.where(StressValutazione.mansione == mansione)
    else:
        q = q.where(StressValutazione.mansione.is_(None))
    result = await db.execute(q)
    val = result.scalar_one_or_none()

    if val is None:
        val = StressValutazione(
            azienda_id=azienda_id,
            gruppo_omogeneo=gruppo,
            mansione=mansione,
        )
        db.add(val)

    val.area_a_eventi_sentinella = area_a
    val.area_b_contenuto_lavoro = area_b
    val.area_c_contesto_lavoro = area_c
    val.punteggio_a = calc["area_a_converted"]
    val.punteggio_b = calc["area_b_total"]
    val.punteggio_c = calc["area_c_total"]
    val.punteggio_totale = calc["totale"]
    val.livello_rischio = calc["livello"]
    if body.misure_correttive is not None:
        val.misure_correttive = body.misure_correttive
    if body.note is not None:
        val.note = body.note

    await db.commit()
    await db.refresh(val)
    return _serialize(val, calc)
