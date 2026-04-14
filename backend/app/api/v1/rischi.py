import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.ambiente import Ambiente
from app.models.azienda import Azienda
from app.models.valutazione_rischio import ValutazioneRischio
from app.schemas.rischio import RischioCreate, RischioResponse, RischioUpdate
from app.services.ai import MisuraSuggerita, suggest_measures


class SuggestMeasuresResponse(BaseModel):
    misure: list[MisuraSuggerita]

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
