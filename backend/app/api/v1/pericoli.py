"""Pericoli endpoints — Phase 3 (1:N) catalog + per-azienda children.

Two surfaces:

  1. /aziende/{a}/ambienti/{e}/pericoli-suggeriti
       Read-only catalog filtered by ambiente.tipo + attrezzature.
       Drives the "Suggerimenti dalla libreria" panel in step-rischi.

  2. /aziende/{a}/ambienti/{e}/rischi/{r}/pericoli (CRUD + batch)
       Per-azienda child rows of a ValutazioneRischio. Mirrors the
       valutazioni_rischio batch shape so the wizard can sync the
       whole categoria in one round-trip.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.models.pericolo_libreria import PericoloLibreria
from app.models.pericolo_valutazione import PericoloValutazione
from app.models.valutazione_rischio import ValutazioneRischio
from app.schemas.pericolo import (
    PericoliBatchRequest,
    PericoloLibreriaResponse,
    PericoloSuggestionItem,
    PericoloSuggestionResponse,
    PericoloValutazioneCreate,
    PericoloValutazioneResponse,
    PericoloValutazioneUpdate,
)
from app.services.pericolo_suggester import normalize_ambiente_tipo, suggest_pericoli


router = APIRouter(prefix="/aziende/{azienda_id}", tags=["pericoli"])


async def _verify_azienda(
    azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> Azienda:
    azienda = (
        await db.execute(
            select(Azienda).where(
                Azienda.id == azienda_id, Azienda.organization_id == org_id
            )
        )
    ).scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


async def _verify_ambiente(
    ambiente_id: uuid.UUID, azienda_id: uuid.UUID, db: AsyncSession
) -> Ambiente:
    ambiente = (
        await db.execute(
            select(Ambiente).where(
                Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id
            )
        )
    ).scalar_one_or_none()
    if not ambiente:
        raise NotFoundError("Ambiente not found")
    return ambiente


async def _verify_valutazione(
    rischio_id: uuid.UUID, ambiente_id: uuid.UUID, db: AsyncSession
) -> ValutazioneRischio:
    val = (
        await db.execute(
            select(ValutazioneRischio).where(
                ValutazioneRischio.id == rischio_id,
                ValutazioneRischio.ambiente_id == ambiente_id,
            )
        )
    ).scalar_one_or_none()
    if not val:
        raise NotFoundError("Valutazione rischio not found")
    return val


# ---------------------------------------------------------------------------
# Catalog suggester
# ---------------------------------------------------------------------------


@router.get(
    "/ambienti/{ambiente_id}/pericoli-suggeriti",
    response_model=PericoloSuggestionResponse,
)
async def list_pericoli_suggeriti(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    categoria: str | None = None,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Return catalog rows applicable to this ambiente.

    Filter rules: ambiente_tipi match (or universal), or any attrezzatura
    in this ambiente triggers an equipment keyword. ``categoria`` query
    arg narrows to one of the 11 long-form categorie.
    """
    await _verify_azienda(azienda_id, org_id, db)
    ambiente = await _verify_ambiente(ambiente_id, azienda_id, db)
    attrezzature = (
        await db.execute(
            select(Attrezzatura).where(Attrezzatura.ambiente_id == ambiente_id)
        )
    ).scalars().all()

    raw = await suggest_pericoli(
        db, ambiente, list(attrezzature), categoria=categoria
    )
    items = [
        PericoloSuggestionItem(
            pericolo=PericoloLibreriaResponse.model_validate(r["pericolo"]),
            matches_ambiente=r["matches_ambiente"],
            triggered_by_attrezzature=r["triggered_by_attrezzature"],
        )
        for r in raw
    ]
    return PericoloSuggestionResponse(
        ambiente_tipo=normalize_ambiente_tipo(ambiente.tipo),
        attrezzature_count=len(attrezzature),
        items=items,
    )


@router.get(
    "/pericoli-libreria",
    response_model=list[PericoloLibreriaResponse],
)
async def list_pericoli_libreria(
    azienda_id: uuid.UUID,
    categoria: str | None = None,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Full catalog dump for browsing — used when the operator wants to
    pick a row that the suggester filtered out (override path).
    """
    await _verify_azienda(azienda_id, org_id, db)
    q = select(PericoloLibreria).order_by(
        PericoloLibreria.categoria, PericoloLibreria.code
    )
    if categoria:
        q = q.where(PericoloLibreria.categoria == categoria)
    rows = (await db.execute(q)).scalars().all()
    return rows


# ---------------------------------------------------------------------------
# Per-azienda children (PericoloValutazione)
# ---------------------------------------------------------------------------


@router.get(
    "/ambienti/{ambiente_id}/rischi/{rischio_id}/pericoli",
    response_model=list[PericoloValutazioneResponse],
)
async def list_pericoli_for_rischio(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    rischio_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    await _verify_ambiente(ambiente_id, azienda_id, db)
    await _verify_valutazione(rischio_id, ambiente_id, db)
    rows = (
        await db.execute(
            select(PericoloValutazione)
            .where(PericoloValutazione.valutazione_rischio_id == rischio_id)
            .order_by(PericoloValutazione.ordine, PericoloValutazione.created_at)
        )
    ).scalars().all()
    return rows


@router.post(
    "/ambienti/{ambiente_id}/rischi/{rischio_id}/pericoli",
    response_model=PericoloValutazioneResponse,
    status_code=201,
)
async def create_pericolo_valutazione(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    rischio_id: uuid.UUID,
    body: PericoloValutazioneCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    await _verify_ambiente(ambiente_id, azienda_id, db)
    await _verify_valutazione(rischio_id, ambiente_id, db)

    row = PericoloValutazione(
        **body.model_dump(),
        valutazione_rischio_id=rischio_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.put(
    "/ambienti/{ambiente_id}/rischi/{rischio_id}/pericoli/{pericolo_id}",
    response_model=PericoloValutazioneResponse,
)
async def update_pericolo_valutazione(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    rischio_id: uuid.UUID,
    pericolo_id: uuid.UUID,
    body: PericoloValutazioneUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    await _verify_ambiente(ambiente_id, azienda_id, db)
    await _verify_valutazione(rischio_id, ambiente_id, db)
    row = (
        await db.execute(
            select(PericoloValutazione).where(
                PericoloValutazione.id == pericolo_id,
                PericoloValutazione.valutazione_rischio_id == rischio_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise NotFoundError("Pericolo not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete(
    "/ambienti/{ambiente_id}/rischi/{rischio_id}/pericoli/{pericolo_id}",
    status_code=204,
)
async def delete_pericolo_valutazione(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    rischio_id: uuid.UUID,
    pericolo_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    await _verify_ambiente(ambiente_id, azienda_id, db)
    await _verify_valutazione(rischio_id, ambiente_id, db)
    row = (
        await db.execute(
            select(PericoloValutazione).where(
                PericoloValutazione.id == pericolo_id,
                PericoloValutazione.valutazione_rischio_id == rischio_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise NotFoundError("Pericolo not found")
    await db.delete(row)
    await db.commit()


@router.post(
    "/ambienti/{ambiente_id}/rischi/{rischio_id}/pericoli/batch",
    response_model=list[PericoloValutazioneResponse],
)
async def batch_upsert_pericoli(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    rischio_id: uuid.UUID,
    body: PericoliBatchRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Replace-all batch: any existing row whose id is not in body.items is
    deleted. New rows insert; matched rows update in-place. Designed to take
    the wizard's full snapshot of one categoria's pericoli.
    """
    await _verify_azienda(azienda_id, org_id, db)
    await _verify_ambiente(ambiente_id, azienda_id, db)
    await _verify_valutazione(rischio_id, ambiente_id, db)

    existing = (
        await db.execute(
            select(PericoloValutazione).where(
                PericoloValutazione.valutazione_rischio_id == rischio_id
            )
        )
    ).scalars().all()
    by_id = {r.id: r for r in existing}

    incoming_ids: set[uuid.UUID] = set()
    out: list[PericoloValutazione] = []
    for item in body.items:
        payload = item.model_dump(exclude={"id"})
        if item.id and item.id in by_id:
            row = by_id[item.id]
            for k, v in payload.items():
                setattr(row, k, v)
            incoming_ids.add(row.id)
            out.append(row)
        else:
            row = PericoloValutazione(
                **payload,
                valutazione_rischio_id=rischio_id,
            )
            db.add(row)
            out.append(row)

    # Delete any rows the wizard removed.
    for rid, row in by_id.items():
        if rid not in incoming_ids and row not in out:
            await db.delete(row)

    await db.commit()
    for r in out:
        await db.refresh(r)
    # Re-sort by ordine for stable response
    out.sort(key=lambda r: (r.ordine, r.created_at or 0))
    return out
