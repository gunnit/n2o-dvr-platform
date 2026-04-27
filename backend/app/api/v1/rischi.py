import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.models.valutazione_rischio import ValutazioneRischio
from app.schemas.rischio import RischioCreate, RischioResponse, RischioUpdate
from app.services.ai import (
    MisuraSuggerita,
    RischioSuggerito,
    suggest_measures,
    suggest_rischi,
)


class SuggestMeasuresResponse(BaseModel):
    misure: list[MisuraSuggerita]


class SuggestRischiResponse(BaseModel):
    items: list[RischioSuggerito]
    sintesi: str

router = APIRouter(prefix="/aziende/{azienda_id}", tags=["rischi"])


async def _verify_azienda(azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession):
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Azienda not found")


@router.get("/rischi", response_model=list[RischioResponse])
async def list_rischi(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(ValutazioneRischio)
        .join(Ambiente)
        .where(Ambiente.azienda_id == azienda_id)
    )
    return result.scalars().all()


class RischiBatchItem(RischioCreate):
    # Optional id — if present and matches an existing row, update in place;
    # otherwise create. Lets the wizard sync its local state in one round-trip.
    id: uuid.UUID | None = None


class RischiBatchRequest(BaseModel):
    items: list[RischiBatchItem]


@router.post(
    "/ambienti/{ambiente_id}/rischi/batch",
    response_model=list[RischioResponse],
)
async def batch_upsert_rischi(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    body: RischiBatchRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """US-2.3 companion — upsert all valutazioni for an ambiente in one call.

    Matches existing rows by (ambiente_id, categoria_rischio) so the wizard
    can send the whole snapshot of sliders without tracking id assignment.
    """
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Ambiente).where(
            Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id
        )
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Ambiente not found")

    # Load existing rows keyed by categoria so we can decide create/update.
    existing = (
        await db.execute(
            select(ValutazioneRischio).where(
                ValutazioneRischio.ambiente_id == ambiente_id
            )
        )
    ).scalars().all()
    by_cat = {r.categoria_rischio: r for r in existing}

    out: list[ValutazioneRischio] = []
    for item in body.items:
        row = by_cat.get(item.categoria_rischio)
        payload = item.model_dump(exclude={"id"})
        if row is None:
            row = ValutazioneRischio(**payload, ambiente_id=ambiente_id)
            db.add(row)
            out.append(row)
        else:
            for field, value in payload.items():
                setattr(row, field, value)
            out.append(row)

    await db.commit()
    for r in out:
        await db.refresh(r)
    return out


@router.post("/ambienti/{ambiente_id}/rischi", response_model=RischioResponse, status_code=201)
async def create_rischio(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    body: RischioCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Ambiente).where(Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Ambiente not found")

    rischio = ValutazioneRischio(**body.model_dump(), ambiente_id=ambiente_id)
    db.add(rischio)
    await db.commit()
    await db.refresh(rischio)
    return rischio


@router.put("/ambienti/{ambiente_id}/rischi/{rischio_id}", response_model=RischioResponse)
async def update_rischio(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    rischio_id: uuid.UUID,
    body: RischioUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(ValutazioneRischio).where(
            ValutazioneRischio.id == rischio_id,
            ValutazioneRischio.ambiente_id == ambiente_id,
        )
    )
    rischio = result.scalar_one_or_none()
    if not rischio:
        raise NotFoundError("Valutazione rischio not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rischio, field, value)

    await db.commit()
    await db.refresh(rischio)
    return rischio


@router.post(
    "/rischi/{rischio_id}/suggerisci-misure",
    response_model=SuggestMeasuresResponse,
)
async def suggerisci_misure(
    azienda_id: uuid.UUID,
    rischio_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Generate 2-5 AI-suggested improvement measures for a risk (US-2.6).

    Returns the suggestions for the user to Accept / Modify / Reject in the
    Risk Scoring Interface. Persistence of accepted measures is done via
    PUT /ambienti/{a}/rischi/{r} with misure_prevenzione set by the frontend.
    """
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(ValutazioneRischio)
        .join(Ambiente)
        .where(
            ValutazioneRischio.id == rischio_id,
            Ambiente.azienda_id == azienda_id,
        )
    )
    rischio = result.scalar_one_or_none()
    if not rischio:
        raise NotFoundError("Valutazione rischio not found")

    misure = await suggest_measures(rischio)
    return SuggestMeasuresResponse(misure=misure)


@router.post(
    "/ambienti/{ambiente_id}/rischi/suggerisci",
    response_model=SuggestRischiResponse,
)
async def suggerisci_rischi(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Phase 8.3 — AI-suggest applicable risks + scoring for an ambiente.

    Returns 11 entries (one per canonical category) with AI-proposed
    applicabile flag, pericolo description, and starter P/D scores. The
    endpoint never persists; the wizard merges accepted suggestions via
    POST /aziende/{a}/ambienti/{e}/rischi/batch.
    """
    azienda = (
        await db.execute(
            select(Azienda).where(
                Azienda.id == azienda_id, Azienda.organization_id == org_id
            )
        )
    ).scalar_one_or_none()
    if azienda is None:
        raise NotFoundError("Azienda not found")

    ambiente = (
        await db.execute(
            select(Ambiente).where(
                Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id
            )
        )
    ).scalar_one_or_none()
    if ambiente is None:
        raise NotFoundError("Ambiente not found")

    # Equipment context helps the model reason about exposures
    # (e.g. cappa aspirante → chimici lower; saldatrice → fisici/chimici).
    attrezzature = (
        await db.execute(
            select(Attrezzatura).where(Attrezzatura.ambiente_id == ambiente_id)
        )
    ).scalars().all()

    response = await suggest_rischi(ambiente, azienda, list(attrezzature))
    return SuggestRischiResponse(items=response.items, sintesi=response.sintesi)
