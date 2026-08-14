"""DUVRI CRUD endpoints (US-4.5).

A DUVRI document represents one appalto (contract) between the principal
Azienda (committente) and one contractor (appaltatore). The principal data
is implicit — read from the parent Azienda — so the operator only enters
contractor + contract details. We surface a ``committente_outdated`` flag
when the parent Azienda has been modified after the Duvri was last touched,
so the frontend can show the AC3 sync banner.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.entitlements import Entitlements, get_entitlements
from app.billing.metering import metered
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.permissions import ASSESSMENTS_WRITE
from app.data.duvri_interference_rules import (
    evaluate_rules,
    get_rule,
    list_equipment_types,
)
from app.db.session import get_db
from app.dependencies import get_current_org, require_capability
from app.models.ambiente import Ambiente
from app.models.azienda import Azienda
from app.models.duvri import Duvri
from app.schemas.duvri import (
    AnalyzeInterferencesResponse,
    DuvriCreate,
    DuvriResponse,
    DuvriUpdate,
    InterferenceDecisionBody,
    InterferenceSuggestion,
    SuggestInterferenzeAIRequest,
)
from app.services.ai import InterferenzeSuggerite, suggest_interferenze
from sqlalchemy.orm.attributes import flag_modified

router = APIRouter(prefix="/aziende/{azienda_id}/duvri", tags=["duvri"])


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


def _serialize(duvri: Duvri, azienda: Azienda) -> dict[str, Any]:
    """Build the response payload, including derived committente fields."""
    snapshot = {
        "ragione_sociale": azienda.ragione_sociale,
        "partita_iva": azienda.partita_iva,
        "sede_legale_via": azienda.sede_legale_via,
        "sede_legale_citta": azienda.sede_legale_citta,
        "sede_operativa_via": azienda.sede_operativa_via,
        "sede_operativa_citta": azienda.sede_operativa_citta,
    }
    # AC3: flag a stale Duvri when committente data has moved since we last
    # touched the document. We compare timestamps rather than diffing fields
    # because the Duvri doesn't snapshot principal data — it always reads it
    # from the live Azienda at generation time.
    outdated = (
        azienda.updated_at is not None
        and duvri.updated_at is not None
        and azienda.updated_at > duvri.updated_at
    )
    return {
        "id": duvri.id,
        "azienda_id": duvri.azienda_id,
        "appaltatore_ragione_sociale": duvri.appaltatore_ragione_sociale,
        "appaltatore_partita_iva": duvri.appaltatore_partita_iva,
        "appaltatore_referente": duvri.appaltatore_referente,
        "oggetto_appalto": duvri.oggetto_appalto,
        "data_inizio": duvri.data_inizio,
        "data_fine": duvri.data_fine,
        "interferenze": duvri.interferenze or [],
        "attrezzature_appaltatore": duvri.attrezzature_appaltatore or [],
        "interferenze_decisioni": duvri.interferenze_decisioni or [],
        "note": duvri.note,
        "created_at": duvri.created_at,
        "updated_at": duvri.updated_at,
        "committente_outdated": outdated,
        "committente_snapshot": snapshot,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[DuvriResponse])
async def list_duvri(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all DUVRI documents for this azienda, newest first."""
    azienda = await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(Duvri)
        .where(Duvri.azienda_id == azienda_id)
        .order_by(Duvri.created_at.desc())
    )
    return [_serialize(d, azienda) for d in result.scalars().all()]


@router.post(
    "",
    response_model=DuvriResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def create_duvri(
    azienda_id: uuid.UUID,
    body: DuvriCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    azienda = await _get_azienda_or_404(azienda_id, org_id, db)
    payload = body.model_dump()
    # Pydantic gave us list[…Model]; persist as plain dicts in JSONB.
    for key in ("interferenze", "attrezzature_appaltatore", "interferenze_decisioni"):
        payload[key] = [
            item if isinstance(item, dict) else item.model_dump()
            for item in payload.get(key) or []
        ]
    duvri = Duvri(azienda_id=azienda_id, **payload)
    db.add(duvri)
    await db.commit()
    await db.refresh(duvri)
    return _serialize(duvri, azienda)


@router.get("/{duvri_id}", response_model=DuvriResponse)
async def get_duvri(
    azienda_id: uuid.UUID,
    duvri_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    azienda = await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(Duvri).where(Duvri.id == duvri_id, Duvri.azienda_id == azienda_id)
    )
    duvri = result.scalar_one_or_none()
    if not duvri:
        raise NotFoundError("DUVRI non trovato")
    return _serialize(duvri, azienda)


@router.patch(
    "/{duvri_id}",
    response_model=DuvriResponse,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def update_duvri(
    azienda_id: uuid.UUID,
    duvri_id: uuid.UUID,
    body: DuvriUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    azienda = await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(Duvri).where(Duvri.id == duvri_id, Duvri.azienda_id == azienda_id)
    )
    duvri = result.scalar_one_or_none()
    if not duvri:
        raise NotFoundError("DUVRI non trovato")

    updates = body.model_dump(exclude_unset=True)
    for key in ("interferenze", "attrezzature_appaltatore", "interferenze_decisioni"):
        if key in updates and updates[key] is not None:
            updates[key] = [
                item if isinstance(item, dict) else item.model_dump()
                for item in updates[key]
            ]
    for k, v in updates.items():
        setattr(duvri, k, v)
    await db.commit()
    await db.refresh(duvri)
    return _serialize(duvri, azienda)


@router.get(
    "/{duvri_id}/analyze-interferences",
    response_model=AnalyzeInterferencesResponse,
)
async def analyze_interferences(
    azienda_id: uuid.UUID,
    duvri_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> AnalyzeInterferencesResponse:
    """Run the rules engine on the contractor equipment list (US-4.6).

    Returns one suggestion per fired rule plus a no_interference_detected
    flag the frontend uses to render the "Nessuna interferenza rilevata"
    fallback. Suggestions surface any prior accept/reject decision so the
    operator can re-review without losing context.
    """
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(Duvri).where(Duvri.id == duvri_id, Duvri.azienda_id == azienda_id)
    )
    duvri = result.scalar_one_or_none()
    if not duvri:
        raise NotFoundError("DUVRI non trovato")

    equipment_types = [
        item.get("tipo")
        for item in (duvri.attrezzature_appaltatore or [])
        if isinstance(item, dict) and item.get("tipo")
    ]
    rules = evaluate_rules(equipment_types)

    decisions_by_rule: dict[str, str] = {}
    for d in duvri.interferenze_decisioni or []:
        if isinstance(d, dict) and isinstance(d.get("rule_id"), str):
            decisions_by_rule[d["rule_id"]] = d.get("decision") or ""

    suggestions = [
        InterferenceSuggestion(
            rule_id=rule["rule_id"],
            contractor_eq=rule["contractor_eq"],
            titolo=rule["titolo"],
            rischio=rule["rischio"],
            misure=rule["misure"],
            dpi=rule["dpi"],
            riferimento=rule["riferimento"],
            decision=decisions_by_rule.get(rule["rule_id"]) or None,
        )
        for rule in rules
    ]
    return AnalyzeInterferencesResponse(
        suggestions=suggestions,
        no_interference_detected=len(suggestions) == 0,
        contractor_equipment=equipment_types,
    )


@router.post(
    "/interferenze/suggerisci",
    response_model=InterferenzeSuggerite,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def suggerisci_interferenze_ai(
    azienda_id: uuid.UUID,
    body: SuggestInterferenzeAIRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    ent: Entitlements = Depends(get_entitlements),
    db: AsyncSession = Depends(get_db),
) -> InterferenzeSuggerite:
    """AI-suggest additional rischi interferenziali from the form context.

    The body carries the *current* form state (equipment chips, oggetto,
    interferenze already listed) so unsaved edits are respected and the
    endpoint also works while the operator is still creating the DUVRI.
    The committente's ambienti provide the "luoghi" context; the static
    rules that fire for the selected equipment are passed to the model so
    it complements the rules engine instead of replaying it.

    Never persists — accepted suggestions land through the normal DUVRI
    create/update path after operator review.

    Inputs to the model: equipment/activity labels, works description,
    ambiente names, existing risk texts. No PII (no contractor names,
    referenti, or partita IVA) is ever sent.
    """
    await _get_azienda_or_404(azienda_id, org_id, db)
    if not body.attrezzature_appaltatore:
        raise BadRequestError(
            "Seleziona almeno un'attrezzatura/attività dell'appaltatore "
            "prima di generare le interferenze con AI."
        )

    # Luoghi context: the committente's ambienti (work-related only).
    ambienti = (
        (
            await db.execute(
                select(Ambiente).where(Ambiente.azienda_id == azienda_id)
            )
        )
        .scalars()
        .all()
    )
    luoghi = [
        f"{amb.nome or '—'} (tipo: {amb.tipo or '—'})" for amb in ambienti
    ]

    attrezzature = [
        (a.tipo, a.descrizione) for a in body.attrezzature_appaltatore
    ]
    equipment_types = [tipo for tipo, _ in attrezzature]
    regole_standard = [
        f"{rule['titolo']}: {rule['rischio']}"
        for rule in evaluate_rules(equipment_types)
    ]
    esistenti = [
        i.rischio.strip() for i in body.interferenze_esistenti if i.rischio.strip()
    ]

    # MB-2.4 — the endpoint persists nothing, so there is no row id to key
    # on (the DUVRI may not even be saved yet). Azienda plus a digest of the
    # form context is the right key: a re-run with the same chips/oggetto is
    # free, asking again after changing them is genuinely new work.
    context_digest = hashlib.sha1(
        "|".join(
            sorted(equipment_types)
            + sorted(esistenti)
            + [(body.oggetto_appalto or "").strip()]
        ).encode()
    ).hexdigest()[:12]
    async with metered(
        org_id,
        "reasoning",
        f"duvri-interferenze:{azienda_id}:{context_digest}",
        db,
        ent,
    ):
        return await suggest_interferenze(
            oggetto_appalto=body.oggetto_appalto,
            attrezzature=attrezzature,
            luoghi=luoghi,
            interferenze_esistenti=esistenti,
            regole_standard_attive=regole_standard,
        )


@router.post(
    "/{duvri_id}/interferences/decision",
    response_model=DuvriResponse,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def record_interference_decision(
    azienda_id: uuid.UUID,
    duvri_id: uuid.UUID,
    body: InterferenceDecisionBody,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Persist (or replace) the operator's decision for one rule.

    'accept' adds the rule's canonical narrative to the live interferenze
    list (where it lands in the generated DUVRI); 'reject' drops it. A
    second call for the same rule_id replaces the previous decision.
    """
    azienda = await _get_azienda_or_404(azienda_id, org_id, db)
    if get_rule(body.rule_id) is None:
        raise BadRequestError(f"rule_id sconosciuto: {body.rule_id}")

    result = await db.execute(
        select(Duvri).where(Duvri.id == duvri_id, Duvri.azienda_id == azienda_id)
    )
    duvri = result.scalar_one_or_none()
    if not duvri:
        raise NotFoundError("DUVRI non trovato")

    rule = get_rule(body.rule_id)
    assert rule is not None  # validated above

    # Upsert decision
    decisions = list(duvri.interferenze_decisioni or [])
    new_decision = {
        "rule_id": body.rule_id,
        "decision": body.decision,
        "custom_text": body.custom_text,
    }
    replaced = False
    for i, d in enumerate(decisions):
        if isinstance(d, dict) and d.get("rule_id") == body.rule_id:
            decisions[i] = new_decision
            replaced = True
            break
    if not replaced:
        decisions.append(new_decision)
    duvri.interferenze_decisioni = decisions

    # Mirror into interferenze list for generator consumption.
    interferenze = list(duvri.interferenze or [])
    misure_text = (body.custom_text or rule["misure"]).strip()
    canonical_entry = {
        "rischio": rule["rischio"],
        "misure": misure_text,
        "dpi": rule["dpi"],
        "rule_id": body.rule_id,  # marker so we can find/replace later
    }
    interferenze = [
        i for i in interferenze
        if not (isinstance(i, dict) and i.get("rule_id") == body.rule_id)
    ]
    if body.decision == "accept":
        interferenze.append(canonical_entry)
    duvri.interferenze = interferenze

    flag_modified(duvri, "interferenze_decisioni")
    flag_modified(duvri, "interferenze")
    await db.commit()
    await db.refresh(duvri)

    return _serialize(duvri, azienda)


@router.get("/_meta/equipment-types", response_model=list[str])
async def equipment_types(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Canonical contractor equipment types (frontend selector source)."""
    await _get_azienda_or_404(azienda_id, org_id, db)
    return list_equipment_types()


@router.delete(
    "/{duvri_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def delete_duvri(
    azienda_id: uuid.UUID,
    duvri_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(Duvri).where(Duvri.id == duvri_id, Duvri.azienda_id == azienda_id)
    )
    duvri = result.scalar_one_or_none()
    if not duvri:
        raise NotFoundError("DUVRI non trovato")
    await db.delete(duvri)
    await db.commit()
