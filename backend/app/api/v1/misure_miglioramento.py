"""CRUD API for the DVR §4.1 Programma di Miglioramento (T109).

The misure rows are operator-editable; the DVR generator auto-seeds an
initial set from pericoli with I>=7 the first time the document is built,
then hands ownership to the operator. This endpoint lets the frontend
render and edit the grid without touching the document generator.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from types import SimpleNamespace

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.ambiente import Ambiente
from app.models.azienda import Azienda
from app.models.misura_miglioramento import MisuraMiglioramento
from app.models.pericolo_valutazione import PericoloValutazione
from app.models.valutazione_rischio import ValutazioneRischio
from app.schemas.misura_miglioramento import (
    MisuraMiglioramentoCreate,
    MisuraMiglioramentoResponse,
    MisuraMiglioramentoUpdate,
)
from app.services.ai import suggest_measures

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/aziende/{azienda_id}/misure-miglioramento",
    tags=["misure-miglioramento"],
)


async def _verify_azienda(
    azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> None:
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id, Azienda.organization_id == org_id
        )
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Azienda not found")


@router.get("", response_model=list[MisuraMiglioramentoResponse])
async def list_misure(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(MisuraMiglioramento)
        .where(MisuraMiglioramento.azienda_id == azienda_id)
        .order_by(
            MisuraMiglioramento.ordine,
            MisuraMiglioramento.created_at,
        )
    )
    return result.scalars().all()


@router.post(
    "", response_model=MisuraMiglioramentoResponse, status_code=201
)
async def create_misura(
    azienda_id: uuid.UUID,
    body: MisuraMiglioramentoCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    misura = MisuraMiglioramento(
        azienda_id=azienda_id,
        **body.model_dump(),
    )
    db.add(misura)
    await db.commit()
    await db.refresh(misura)
    return misura


@router.put(
    "/{misura_id}", response_model=MisuraMiglioramentoResponse
)
async def update_misura(
    azienda_id: uuid.UUID,
    misura_id: uuid.UUID,
    body: MisuraMiglioramentoUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(MisuraMiglioramento).where(
            MisuraMiglioramento.id == misura_id,
            MisuraMiglioramento.azienda_id == azienda_id,
        )
    )
    misura = result.scalar_one_or_none()
    if not misura:
        raise NotFoundError("Misura not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(misura, field, value)
    await db.commit()
    await db.refresh(misura)
    return misura


@router.delete("/{misura_id}", status_code=204)
async def delete_misura(
    azienda_id: uuid.UUID,
    misura_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(MisuraMiglioramento).where(
            MisuraMiglioramento.id == misura_id,
            MisuraMiglioramento.azienda_id == azienda_id,
        )
    )
    misura = result.scalar_one_or_none()
    if not misura:
        raise NotFoundError("Misura not found")
    await db.delete(misura)
    await db.commit()


class GeneraDaRischiResponse(BaseModel):
    generated: int
    skipped: int
    pericoli_considered: int
    rows: list[MisuraMiglioramentoResponse]


# Concurrency cap for the OpenAI calls — avoids opening 50 sockets at once
# when an azienda has many high-indice pericoli. gpt-5.4-mini at `low`
# effort responds in ~2-4s, so 5 in flight covers a typical fan-out under
# 30s wall-clock.
_AI_CONCURRENCY = 5


@router.post(
    "/genera-da-rischi",
    response_model=GeneraDaRischiResponse,
)
async def genera_da_rischi(
    azienda_id: uuid.UUID,
    soglia: int = Query(
        default=5,
        ge=3,
        le=12,
        description=(
            "Soglia minima sull'indice I (=2D+P) per generare misure. "
            "Default 5 (MODESTO+); usare 7 per limitare ai soli GRAVE+."
        ),
    ),
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI improvement measures for every applicable PericoloValutazione
    whose ``indice_i >= soglia`` and that does NOT already have a linked
    ``misure_miglioramento`` row.

    Idempotent: re-running won't duplicate rows for pericoli already covered.
    Each pericolo yields 2-5 measures (one MisuraMiglioramento row each),
    all linked back via ``pericolo_valutazione_id`` so the DVR generator and
    the UI can track provenance. Returns the count and the new rows.
    """
    await _verify_azienda(azienda_id, org_id, db)

    # Pericoli to evaluate — applicable, scored, above threshold, in this
    # azienda. Eager-load the parent ValutazioneRischio so we can read the
    # categoria_rischio without a per-row roundtrip in the AI loop.
    stmt = (
        select(PericoloValutazione)
        .join(ValutazioneRischio)
        .join(Ambiente)
        .where(
            Ambiente.azienda_id == azienda_id,
            PericoloValutazione.applicabile == True,  # noqa: E712
            PericoloValutazione.indice_i >= soglia,
        )
        .options(selectinload(PericoloValutazione.valutazione_rischio))
    )
    pericoli = list((await db.execute(stmt)).scalars().all())

    # Exclude pericoli already covered by an existing misura row.
    existing_links_stmt = (
        select(MisuraMiglioramento.pericolo_valutazione_id)
        .where(
            MisuraMiglioramento.azienda_id == azienda_id,
            MisuraMiglioramento.pericolo_valutazione_id.is_not(None),
        )
        .distinct()
    )
    already_linked: set[uuid.UUID] = {
        row[0] for row in (await db.execute(existing_links_stmt)).all()
    }

    pending = [p for p in pericoli if p.id not in already_linked]
    skipped = len(pericoli) - len(pending)

    if not pending:
        return GeneraDaRischiResponse(
            generated=0,
            skipped=skipped,
            pericoli_considered=len(pericoli),
            rows=[],
        )

    # Current max ordine so new rows append at the bottom of the operator's
    # existing list rather than reshuffling everything.
    max_ordine_stmt = (
        select(MisuraMiglioramento.ordine)
        .where(MisuraMiglioramento.azienda_id == azienda_id)
        .order_by(MisuraMiglioramento.ordine.desc())
        .limit(1)
    )
    current_max = (await db.execute(max_ordine_stmt)).scalar()
    next_ordine = (current_max or 0) + 1

    sem = asyncio.Semaphore(_AI_CONCURRENCY)

    async def _gen_one(per: PericoloValutazione):
        async with sem:
            # The suggester reads attrs off a duck-typed object; wrap the
            # pericolo so its parent's categoria_rischio shows up where the
            # prompt expects it.
            ctx = SimpleNamespace(
                id=per.id,
                categoria_rischio=getattr(
                    per.valutazione_rischio, "categoria_rischio", ""
                ),
                pericolo=per.pericolo,
                condizioni_esposizione=per.condizioni_esposizione,
                rischio=per.rischio,
                misure_prevenzione=per.misure_prevenzione,
                probabilita_p=per.probabilita_p,
                danno_d=per.danno_d,
                indice_i=per.indice_i,
                livello_rischio=per.livello_rischio,
            )
            try:
                return per, await suggest_measures(ctx)
            except Exception as exc:  # noqa: BLE001
                # One pericolo failure shouldn't block the whole batch.
                logger.warning(
                    "suggest_measures failed for pericolo %s: %s", per.id, exc
                )
                return per, []

    results = await asyncio.gather(*(_gen_one(p) for p in pending))

    new_rows: list[MisuraMiglioramento] = []
    ordine = next_ordine
    for per, misure in results:
        # Build a concise risk label from the pericolo so the "Rischio"
        # column surfaces what the measure addresses rather than
        # repeating the AI's measure title.
        risk_label_parts: list[str] = []
        if per.pericolo:
            risk_label_parts.append(per.pericolo)
        if per.rischio:
            risk_label_parts.append(per.rischio)
        risk_label = " — ".join(risk_label_parts) if risk_label_parts else "Rischio non specificato"

        for m in misure:
            # Concatenate the AI's structured fields into the T109 grid:
            # misura = risk description (UI: "Rischio")
            # misura_miglioramento = AI-generated measure (UI: "Misura di Miglioramento")
            # procedura = operational description (UI: "Attivita")
            procedura_parts: list[str] = [m.descrizione]
            if m.riferimento_normativo:
                procedura_parts.append(
                    f"Riferimento: {m.riferimento_normativo}"
                )
            row = MisuraMiglioramento(
                azienda_id=azienda_id,
                pericolo_valutazione_id=per.id,
                misura=risk_label,
                misura_miglioramento=m.titolo,
                procedura="\n".join(procedura_parts),
                # `tipo` is the lever (tecnica/dpi/formazione/...) — useful
                # for the operator deciding how to allocate budget.
                risorse=f"Tipo: {m.tipo}",
                responsabile=None,  # operator assigns via inline edit
                scadenza=m.tempistica,
                # Prefer the pericolo's own livello so the priorita pill
                # matches the rest of the system's color band.
                priorita=per.livello_rischio,
                ordine=ordine,
            )
            db.add(row)
            new_rows.append(row)
            ordine += 1

    await db.commit()
    for r in new_rows:
        await db.refresh(r)

    return GeneraDaRischiResponse(
        generated=len(new_rows),
        skipped=skipped,
        pericoli_considered=len(pericoli),
        rows=[MisuraMiglioramentoResponse.model_validate(r) for r in new_rows],
    )
