"""Protocollo sanitario aziendale per mansione (segnalazione 2026-08-25).

Per mansione, never per person: the endpoints aggregate the rischi
specifici + DPI flags of the persone holding a role (the same union the
DVR §4.3 renders) and let the operator record the accertamenti, their
cadence and the correlated occupational diseases the Medico Competente
prescribes for that role. ``POST /mansioni/suggerisci`` asks the AI for a
proposal that the operator applies, edits or discards — it never persists.

Read path is ungated (D.Lgs. 81/2008 retention); every write and the AI
call require ``assessments:write`` and the AI call is metered.
"""

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.entitlements import Entitlements, get_entitlements
from app.billing.metering import metered
from app.core.exceptions import NotFoundError
from app.core.permissions import ASSESSMENTS_WRITE
from app.db.session import get_db
from app.dependencies import get_current_org, require_capability
from app.models.azienda import Azienda
from app.models.persona import Persona
from app.models.protocollo_sanitario import ProtocolloSanitarioMansione
from app.schemas.protocollo_sanitario import (
    AccertamentoProposto,
    MalattiaCorrelata,
    MalattiaRiferimento,
    ProtocolloMansioneItem,
    ProtocolloMansioniOverview,
    ProtocolloSanitarioResponse,
    ProtocolloSanitarioUpsert,
    ProtocolloSuggeritoResponse,
    SuggerisciProtocolloRequest,
)
from app.services.ai.protocollo_sanitario_suggester import suggest_protocollo
from app.services.protocollo_sanitario import (
    MansioneAggregate,
    aggregate_per_mansione,
    mansione_key,
)

router = APIRouter(
    prefix="/aziende/{azienda_id}/protocollo-sanitario",
    tags=["protocollo-sanitario"],
)


async def _load_azienda(
    azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> Azienda:
    azienda = (
        await db.execute(
            select(Azienda).where(
                Azienda.id == azienda_id, Azienda.organization_id == org_id
            )
        )
    ).scalar_one_or_none()
    if azienda is None:
        raise NotFoundError("Azienda not found")
    return azienda


async def _load_persone(azienda_id: uuid.UUID, db: AsyncSession) -> list[Persona]:
    # Only the columns the aggregation reads leave this function's callers:
    # mansione + the two code lists + the external-consultant flags.
    result = await db.execute(select(Persona).where(Persona.azienda_id == azienda_id))
    return list(result.scalars().all())


async def _load_protocolli(
    azienda_id: uuid.UUID, db: AsyncSession
) -> list[ProtocolloSanitarioMansione]:
    result = await db.execute(
        select(ProtocolloSanitarioMansione)
        .where(ProtocolloSanitarioMansione.azienda_id == azienda_id)
        .order_by(ProtocolloSanitarioMansione.mansione)
    )
    return list(result.scalars().all())


async def _find_protocollo(
    azienda_id: uuid.UUID, mansione: str, db: AsyncSession
) -> ProtocolloSanitarioMansione | None:
    result = await db.execute(
        select(ProtocolloSanitarioMansione).where(
            ProtocolloSanitarioMansione.azienda_id == azienda_id,
            func.lower(ProtocolloSanitarioMansione.mansione) == mansione_key(mansione),
        )
    )
    return result.scalar_one_or_none()


def build_overview(
    persone: list, saved: list[ProtocolloSanitarioMansione]
) -> list[ProtocolloMansioneItem]:
    """Merge the organigramma's distinct mansioni with the saved protocols.

    Pure so it is testable without a DB. Every mansione among the persone
    appears once; a saved protocol whose mansione no longer occurs among
    the persone is still listed (with zero persone) so the operator can
    see and delete it rather than have it silently linger in the DVR.
    """
    aggregates = aggregate_per_mansione(persone)
    items: dict[str, ProtocolloMansioneItem] = {}
    for key, agg in aggregates.items():
        items[key] = ProtocolloMansioneItem(
            mansione=agg.mansione,
            num_persone=agg.num_persone,
            rischi_specifici=agg.rischi_items(),
            dpi=agg.dpi_items(),
            malattie_riferimento=[
                MalattiaRiferimento(**m) for m in agg.malattie_riferimento()
            ],
        )
    for row in saved:
        key = mansione_key(row.mansione)
        item = items.get(key)
        if item is None:
            item = ProtocolloMansioneItem(mansione=row.mansione, num_persone=0)
            items[key] = item
        item.protocollo = ProtocolloSanitarioResponse.model_validate(row)
    return sorted(items.values(), key=lambda it: it.mansione.lower())


@router.get("/mansioni", response_model=ProtocolloMansioniOverview)
async def list_protocolli_mansioni(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Every distinct mansione of the azienda with its aggregated rischi /
    DPI, the reference diseases matching those rischi, and the saved
    protocol when one exists."""
    await _load_azienda(azienda_id, org_id, db)
    persone = await _load_persone(azienda_id, db)
    saved = await _load_protocolli(azienda_id, db)
    return ProtocolloMansioniOverview(items=build_overview(persone, saved))


@router.put(
    "/mansioni",
    response_model=ProtocolloSanitarioResponse,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def upsert_protocollo_mansione(
    azienda_id: uuid.UUID,
    body: ProtocolloSanitarioUpsert,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Create or replace the protocol for a mansione (matched
    case-insensitively). ``rischi_specifici`` omitted → snapshot of the
    current aggregation from the persone."""
    await _load_azienda(azienda_id, org_id, db)

    rischi = body.rischi_specifici
    if rischi is None:
        persone = await _load_persone(azienda_id, db)
        agg = aggregate_per_mansione(persone).get(mansione_key(body.mansione))
        rischi_payload = agg.rischi_items() if agg else []
    else:
        rischi_payload = [r.model_dump() for r in rischi]

    row = await _find_protocollo(azienda_id, body.mansione, db)
    if row is None:
        row = ProtocolloSanitarioMansione(azienda_id=azienda_id, mansione=body.mansione)
        db.add(row)
    else:
        # Keep the operator's latest spelling of the role name.
        row.mansione = body.mansione
    row.rischi_specifici = rischi_payload
    row.accertamenti = [a.model_dump() for a in body.accertamenti]
    row.periodicita = body.periodicita
    row.malattie_correlate = [m.model_dump() for m in body.malattie_correlate]
    row.note = body.note
    row.fonte = body.fonte

    await db.commit()
    await db.refresh(row)
    return row


@router.delete(
    "/mansioni/{protocollo_id}",
    status_code=204,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def delete_protocollo_mansione(
    azienda_id: uuid.UUID,
    protocollo_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _load_azienda(azienda_id, org_id, db)
    row = (
        await db.execute(
            select(ProtocolloSanitarioMansione).where(
                ProtocolloSanitarioMansione.id == protocollo_id,
                ProtocolloSanitarioMansione.azienda_id == azienda_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Protocollo sanitario not found")
    await db.delete(row)
    await db.commit()
    return Response(status_code=204)


@router.post(
    "/mansioni/suggerisci",
    response_model=ProtocolloSuggeritoResponse,
    dependencies=[Depends(require_capability(ASSESSMENTS_WRITE))],
)
async def suggerisci_protocollo_mansione(
    azienda_id: uuid.UUID,
    body: SuggerisciProtocolloRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    ent: Entitlements = Depends(get_entitlements),
    db: AsyncSession = Depends(get_db),
):
    """AI proposal for one mansione's protocol. Never persists.

    The prompt is built from the aggregated codes, the azienda's activity
    and the reference disease rows — nothing about any individual.
    """
    azienda = await _load_azienda(azienda_id, org_id, db)
    persone = await _load_persone(azienda_id, db)
    key = mansione_key(body.mansione)
    agg = aggregate_per_mansione(persone).get(key)
    if agg is None:
        # A saved protocol for a role that no longer has persone can still be
        # (re)proposed; anything else is a typo, not a role of this azienda.
        saved = await _find_protocollo(azienda_id, body.mansione, db)
        if saved is None:
            raise NotFoundError("Mansione not found among the azienda's persone")
        agg = MansioneAggregate(
            mansione=saved.mansione,
            rischi_codes={r.get("code") for r in (saved.rischi_specifici or []) if r.get("code")},
        )

    rischi_codes = sorted(agg.rischi_codes)
    dpi_codes = sorted(agg.dpi_codes)
    riferimento = agg.malattie_riferimento()

    # MB-2.4 — charged before the call; keyed on the role so a retry for the
    # same mansione is free.
    async with metered(org_id, "reasoning", f"protocollo-sanitario:{azienda_id}:{key}", db, ent):
        proposta = await suggest_protocollo(
            mansione=agg.mansione,
            rischi_codes=rischi_codes,
            dpi_codes=dpi_codes,
            azienda=azienda,
            malattie_riferimento=riferimento,
        )

    by_code = {m["codice"]: m for m in riferimento}
    malattie = [
        MalattiaCorrelata(
            codice=m.codice,
            malattia=by_code[m.codice]["malattia"],
            riferimento=by_code[m.codice]["tabella"],
        )
        for m in proposta.malattie_correlate
        if m.codice in by_code
    ]
    return ProtocolloSuggeritoResponse(
        mansione=agg.mansione,
        accertamenti=[
            AccertamentoProposto(
                esame=a.esame, periodicita=a.periodicita, motivazione=a.motivazione
            )
            for a in proposta.accertamenti
        ],
        periodicita=proposta.periodicita,
        malattie_correlate=malattie,
        motivazione=proposta.motivazione,
    )
