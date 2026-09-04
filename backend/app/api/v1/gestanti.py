"""Gestanti cross-reference & relocation decision API.

Closes US-3.9 (auto cross-reference mansione <-> D.Lgs. 151/2001) and
US-3.10 (accept/reject relocation with justification / misura alternativa).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.billing.entitlements import Entitlements, get_entitlements
from app.billing.metering import metered
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.permissions import ASSESSMENTS_WRITE
from app.data.dlgs_151_2001 import (
    INCOMPATIBLE_RISKS,
    find_matches_for_mansione,
    has_any_incompatible_risk,
)
from app.db.session import get_db
from app.dependencies import get_current_org, require_capability
from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.models.gestanti_valutazione import (
    GestantiMansioneValutazione,
    GestantiValutazione,
)
from app.models.persona import Persona
from app.models.persone_ambienti import persone_ambienti
from app.models.valutazione_rischio import ValutazioneRischio
from app.schemas.gestanti import (
    CatalogRisk,
    CrossReferenceRequest,
    CrossReferenceResponse,
    DecisionRequest,
    DecisionResponse,
    EsitoMansione,
    GestantiCreate,
    GestantiMansioneOverviewItem,
    GestantiMansioneResponse,
    GestantiMansioneSuggestRequest,
    GestantiMansioneUpsert,
    GestantiMansioniOverview,
    GestantiResponse,
    GestantiUpdate,
    RiskMatch,
)
from app.services.ai.gestanti_suggester import (
    PericoloContesto,
    suggest_gestanti_mansione,
)

router = APIRouter(tags=["gestanti"])


class GestantiMansioneSuggestResponse(BaseModel):
    """AI proposal for one mansione, as returned by .../mansioni/suggerisci.

    Flat: the suggester's fields plus ``rischi_dettaglio`` (the catalog rows
    for the proposed keys, so the UI can render Allegato + descrizione
    without its own copy of the catalog) and ``pericoli_considerati``.
    Never persisted — the operator applies it in the form and saves through
    PUT /gestanti/mansioni.
    """

    mansione: str
    rischi: list[str]
    rischi_dettaglio: list[CatalogRisk]
    rischi_aggiuntivi: list[str]
    limitazioni: list[str]
    esito_proposto: EsitoMansione
    motivazione: str
    riferimenti_normativi: list[str]
    pericoli_considerati: int


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


def _normalize_mansione(mansione: str | None) -> str:
    """Collapse whitespace so 'Cuoco ' and 'cuoco' upsert the same row."""
    return " ".join((mansione or "").strip().split())


def _catalog_risks_for(mansione: str) -> list[CatalogRisk]:
    """Prefill: catalog matches for a mansione as CatalogRisk items."""
    return [
        CatalogRisk(
            risk_key=key, allegato=info["allegato"], descrizione=info["descrizione"]
        )
        for key, info in find_matches_for_mansione(mansione)
    ]


def build_mansioni_overview(
    persone: list[Any],
    saved: list[Any],
) -> list[GestantiMansioneOverviewItem]:
    """Merge distinct mansioni from the organigramma with saved valutazioni.

    Pure function (no DB) so the preventive-assessment prefill logic is unit
    testable. ``persone`` are objects with ``.mansione``/``.sesso``; ``saved``
    are GestantiMansioneValutazione rows (or anything model_validate accepts).

    Every distinct mansione among the persone appears once — even with ZERO
    pregnant workers, per art. 11 D.Lgs. 151/2001 the valutazione must exist
    preventively. Saved valutazioni whose mansione no longer occurs among the
    persone are still listed (the assessment outlives staff turnover).
    """
    by_key: dict[str, GestantiMansioneOverviewItem] = {}

    for p in persone:
        mans = _normalize_mansione(getattr(p, "mansione", None))
        if not mans:
            continue
        key = mans.lower()
        item = by_key.get(key)
        if item is None:
            item = GestantiMansioneOverviewItem(
                mansione=mans, suggested_risks=_catalog_risks_for(mans)
            )
            by_key[key] = item
        item.num_persone += 1
        if (getattr(p, "sesso", None) or "").strip().upper() == "F":
            item.num_lavoratrici += 1

    for row in saved:
        mans = _normalize_mansione(getattr(row, "mansione", None))
        if not mans:
            continue
        key = mans.lower()
        item = by_key.get(key)
        if item is None:
            item = GestantiMansioneOverviewItem(
                mansione=mans, suggested_risks=_catalog_risks_for(mans)
            )
            by_key[key] = item
        item.valutazione = GestantiMansioneResponse.model_validate(row)

    return sorted(by_key.values(), key=lambda it: it.mansione.lower())


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
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
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

    # Existing valutazione (if any) for "is_new" comparison. If none exists
    # yet, create a stub so the operator can immediately record decisions —
    # the decision endpoint requires a valutazione_id and the form has no
    # other entry point to bootstrap one.
    result = await db.execute(
        select(GestantiValutazione).where(
            GestantiValutazione.azienda_id == azienda_id,
            GestantiValutazione.persona_id == persona.id,
        )
    )
    valutazione = result.scalar_one_or_none()
    if valutazione is None:
        valutazione = GestantiValutazione(
            azienda_id=azienda_id,
            persona_id=persona.id,
            stato="gestante",
            rischi_vietati=[],
        )
        db.add(valutazione)
        await db.commit()
        await db.refresh(valutazione)
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
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
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


# ---------------------------------------------------------------------------
# Preventive per-mansione assessment (art. 11 D.Lgs. 151/2001).
#
# The valutazione must exist for every mansione BEFORE any pregnancy is
# notified — no persona attached. NOTE: these routes MUST stay registered
# before the ``/gestanti/{valutazione_id}`` routes below, otherwise the
# literal segment "mansioni" is captured by the UUID path param and 422s.
# ---------------------------------------------------------------------------


@router.get(
    "/aziende/{azienda_id}/gestanti/mansioni",
    response_model=GestantiMansioniOverview,
)
async def list_gestanti_mansioni(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> GestantiMansioniOverview:
    """Overview of the preventive per-mansione assessment.

    Prefilled from the azienda's organigramma: every distinct mansione among
    the persone appears, each with the D.Lgs. 151/2001 catalog risks already
    matched (the operator reviews, never re-enters). Saved valutazioni are
    merged in; ones whose mansione no longer occurs among the persone are
    still listed.
    """
    await _get_azienda(azienda_id, org_id, db)

    result = await db.execute(
        select(Persona).where(Persona.azienda_id == azienda_id)
    )
    persone = list(result.scalars().all())

    result = await db.execute(
        select(GestantiMansioneValutazione).where(
            GestantiMansioneValutazione.azienda_id == azienda_id
        )
    )
    saved = list(result.scalars().all())

    return GestantiMansioniOverview(items=build_mansioni_overview(persone, saved))


@router.put(
    "/aziende/{azienda_id}/gestanti/mansioni",
    response_model=GestantiMansioneResponse,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def upsert_gestanti_mansione(
    azienda_id: uuid.UUID,
    body: GestantiMansioneUpsert,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> GestantiMansioneValutazione:
    """Create or update the objective valutazione for one mansione.

    Requires NO worker: the assessment is preventive (art. 11 D.Lgs.
    151/2001). Upsert key is (azienda_id, lower(mansione)). When ``rischi``
    is omitted (null) the server prefills the catalog matches for the
    mansione; an explicit empty list means "nessun rischio".
    """
    await _get_azienda(azienda_id, org_id, db)

    mansione = body.mansione  # already normalized by the schema validator
    if body.rischi is None:
        rischi_payload: list[dict[str, Any]] = [
            r.model_dump() for r in _catalog_risks_for(mansione)
        ]
    else:
        rischi_payload = [r.model_dump() for r in body.rischi]

    result = await db.execute(
        select(GestantiMansioneValutazione).where(
            GestantiMansioneValutazione.azienda_id == azienda_id,
            func.lower(GestantiMansioneValutazione.mansione) == mansione.lower(),
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.mansione = mansione
        row.esito = body.esito
        row.rischi = rischi_payload
        row.misure = body.misure
        row.note = body.note
    else:
        row = GestantiMansioneValutazione(
            azienda_id=azienda_id,
            mansione=mansione,
            esito=body.esito,
            rischi=rischi_payload,
            misure=body.misure,
            note=body.note,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete(
    "/aziende/{azienda_id}/gestanti/mansioni/{mansione_valutazione_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def delete_gestanti_mansione(
    azienda_id: uuid.UUID,
    mansione_valutazione_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(GestantiMansioneValutazione).where(
            GestantiMansioneValutazione.id == mansione_valutazione_id,
            GestantiMansioneValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione mansione non trovata")
    await db.delete(row)
    await db.commit()


async def _load_mansione_context(
    azienda_id: uuid.UUID, mansione: str, db: AsyncSession
) -> tuple[list[PericoloContesto], list[Attrezzatura]]:
    """DVR context for one mansione, shaped for the AI prompt. No PII.

    Ambienti: the ones assigned (persone_ambienti) to the persone holding
    the mansione; when none is assigned, every ambiente of the azienda, so
    the model still has something to reason from (the DPI suggester's
    fallback). From those ambienti: the applicabile pericoli — child rows
    first, the legacy single-block fields for older valutazioni — and the
    attrezzature. Persone are read for id + mansione only; the per-persona
    gestanti rows (health data) are never touched.
    """
    key = mansione.lower()
    result = await db.execute(
        select(Persona.id, Persona.mansione).where(Persona.azienda_id == azienda_id)
    )
    persona_ids = [
        pid for pid, mans in result.all() if _normalize_mansione(mans).lower() == key
    ]

    by_id: dict[uuid.UUID, Ambiente] = {}
    if persona_ids:
        result = await db.execute(
            select(Ambiente)
            .join(persone_ambienti, persone_ambienti.c.ambiente_id == Ambiente.id)
            .where(
                persone_ambienti.c.persona_id.in_(persona_ids),
                Ambiente.azienda_id == azienda_id,
            )
        )
        for amb in result.scalars().all():
            by_id.setdefault(amb.id, amb)
    if not by_id:
        result = await db.execute(
            select(Ambiente).where(Ambiente.azienda_id == azienda_id)
        )
        for amb in result.scalars().all():
            by_id.setdefault(amb.id, amb)
    if not by_id:
        return [], []
    ambiente_ids = list(by_id)

    result = await db.execute(
        select(ValutazioneRischio)
        .options(selectinload(ValutazioneRischio.pericoli))
        .where(
            ValutazioneRischio.ambiente_id.in_(ambiente_ids),
            ValutazioneRischio.applicabile.is_(True),
        )
    )
    pericoli: list[PericoloContesto] = []
    for val in result.scalars().all():
        amb = by_id.get(val.ambiente_id)
        nome = (amb.nome if amb else None) or "Ambiente"
        children = [
            p
            for p in (val.pericoli or [])
            if p.applicabile and (p.pericolo or "").strip()
        ]
        if children:
            for p in children:
                pericoli.append(
                    PericoloContesto(
                        ambiente=nome,
                        categoria=val.categoria_rischio,
                        pericolo=p.pericolo.strip(),
                        condizioni=p.condizioni_esposizione,
                        livello=p.livello_rischio,
                    )
                )
        elif (val.pericolo or "").strip():
            pericoli.append(
                PericoloContesto(
                    ambiente=nome,
                    categoria=val.categoria_rischio,
                    pericolo=val.pericolo.strip(),
                    condizioni=val.condizioni_esposizione,
                    livello=val.livello_rischio,
                )
            )

    result = await db.execute(
        select(Attrezzatura).where(Attrezzatura.ambiente_id.in_(ambiente_ids))
    )
    attrezzature = list(result.scalars().all())
    return pericoli, attrezzature


@router.post(
    "/aziende/{azienda_id}/gestanti/mansioni/suggerisci",
    response_model=GestantiMansioneSuggestResponse,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def suggerisci_gestanti_mansione(
    azienda_id: uuid.UUID,
    body: GestantiMansioneSuggestRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    ent: Entitlements = Depends(get_entitlements),
    db: AsyncSession = Depends(get_db),
) -> GestantiMansioneSuggestResponse:
    """AI-propose the D.Lgs. 151/2001 valutazione for one mansione.

    Segnalazione 2026-08-25: "un tasto AI che riconosce per ogni mansione i
    rischi a cui e' sottoposta una lavoratrice gestante e mi va a introdurre
    delle limitazioni [...] o mi definisce la lavoratrice non compatibile".

    The model sees the mansione, the azienda's activity, the pericoli
    assessed for the ambienti where that mansione works, the attrezzature
    and the catalog vocabulary — never a lavoratrice's name, codice
    fiscale or pregnancy data. It returns a PROPOSAL (rischi from the
    catalog, extra risks, limitazioni, esito, motivazione, riferimenti).
    Nothing is persisted here: the operator applies it in the form and
    confirms through PUT /gestanti/mansioni. ``non_compatibile`` is a
    suggestion to the RSPP / medico competente until that save.
    """
    azienda = await _get_azienda(azienda_id, org_id, db)
    mansione = body.mansione  # normalized by the schema validator
    pericoli, attrezzature = await _load_mansione_context(azienda_id, mansione, db)

    # MB-2.4 — charged before the call, keyed on the mansione so re-running
    # the suggester for the same one is one billable action, not one per
    # click. Same key shape the upsert uses (azienda + lower(mansione)).
    mansione_key = mansione.lower()
    async with metered(org_id, "reasoning", f"gestanti-mansione:{azienda_id}:{mansione_key}", db, ent):
        suggestion = await suggest_gestanti_mansione(
            mansione, azienda, pericoli, attrezzature
        )

    # Keys are already validated against INCOMPATIBLE_RISKS by the suggester;
    # resolve them so the UI can render Allegato + descrizione.
    dettaglio = [
        CatalogRisk(
            risk_key=k,
            allegato=INCOMPATIBLE_RISKS[k]["allegato"],
            descrizione=INCOMPATIBLE_RISKS[k]["descrizione"],
        )
        for k in suggestion.rischi
    ]
    return GestantiMansioneSuggestResponse(
        mansione=mansione,
        rischi=suggestion.rischi,
        rischi_dettaglio=dettaglio,
        rischi_aggiuntivi=suggestion.rischi_aggiuntivi,
        limitazioni=suggestion.limitazioni,
        esito_proposto=suggestion.esito_proposto,
        motivazione=suggestion.motivazione,
        riferimenti_normativi=suggestion.riferimenti_normativi,
        pericoli_considerati=len(pericoli),
    )


# ---------------------------------------------------------------------------
# CRUD endpoints — one row per (azienda, persona). Lets the frontend list
# saved valutazioni, edit signature/state, and remove records.
# ---------------------------------------------------------------------------


async def _validate_persona(
    azienda_id: uuid.UUID, persona_id: uuid.UUID, db: AsyncSession
) -> Persona:
    result = await db.execute(
        select(Persona).where(
            Persona.id == persona_id, Persona.azienda_id == azienda_id
        )
    )
    persona = result.scalar_one_or_none()
    if not persona:
        raise BadRequestError("persona_id non appartiene a questa azienda")
    return persona


@router.get(
    "/aziende/{azienda_id}/gestanti", response_model=list[GestantiResponse]
)
async def list_gestanti(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[GestantiValutazione]:
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(GestantiValutazione)
        .where(GestantiValutazione.azienda_id == azienda_id)
        .order_by(GestantiValutazione.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/aziende/{azienda_id}/gestanti",
    response_model=GestantiResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def create_gestanti(
    azienda_id: uuid.UUID,
    body: GestantiCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> GestantiValutazione:
    """Create or upsert a GestantiValutazione for one lavoratrice.

    Upsert by (azienda_id, persona_id): if a row already exists it is
    updated with the new fields (preserving rischi_vietati).
    """
    await _get_azienda(azienda_id, org_id, db)
    await _validate_persona(azienda_id, body.persona_id, db)

    existing = await db.execute(
        select(GestantiValutazione).where(
            GestantiValutazione.azienda_id == azienda_id,
            GestantiValutazione.persona_id == body.persona_id,
        )
    )
    row = existing.scalar_one_or_none()
    payload = body.model_dump()
    if row:
        for k, v in payload.items():
            if k == "persona_id":
                continue
            setattr(row, k, v)
    else:
        row = GestantiValutazione(
            azienda_id=azienda_id, rischi_vietati=[], **payload
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.get(
    "/aziende/{azienda_id}/gestanti/{valutazione_id}",
    response_model=GestantiResponse,
)
async def get_gestanti(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> GestantiValutazione:
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(GestantiValutazione).where(
            GestantiValutazione.id == valutazione_id,
            GestantiValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione Gestanti non trovata")
    return row


@router.patch(
    "/aziende/{azienda_id}/gestanti/{valutazione_id}",
    response_model=GestantiResponse,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def update_gestanti(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    body: GestantiUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> GestantiValutazione:
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(GestantiValutazione).where(
            GestantiValutazione.id == valutazione_id,
            GestantiValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione Gestanti non trovata")
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete(
    "/aziende/{azienda_id}/gestanti/{valutazione_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def delete_gestanti(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(GestantiValutazione).where(
            GestantiValutazione.id == valutazione_id,
            GestantiValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione Gestanti non trovata")
    await db.delete(row)
    await db.commit()
