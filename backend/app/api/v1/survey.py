import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.models.persona import Persona
from app.models.sostanza_chimica import SostanzaChimica
from app.models.valutazione_rischio import ValutazioneRischio
from app.schemas.survey import SurveyCompleteResponse, SurveyResponse, SurveyStepData

router = APIRouter(prefix="/aziende/{azienda_id}/survey", tags=["survey"])


async def _get_azienda(azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Azienda:
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


@router.get("", response_model=SurveyResponse)
async def get_survey(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Return full survey state: azienda + all related entities."""
    azienda = await _get_azienda(azienda_id, org_id, db)

    persone_result = await db.execute(
        select(Persona).where(Persona.azienda_id == azienda_id)
    )
    ambienti_result = await db.execute(
        select(Ambiente).where(Ambiente.azienda_id == azienda_id)
    )
    attrezzature_result = await db.execute(
        select(Attrezzatura).where(Attrezzatura.azienda_id == azienda_id)
    )
    sostanze_result = await db.execute(
        select(SostanzaChimica).where(SostanzaChimica.azienda_id == azienda_id)
    )
    rischi_result = await db.execute(
        select(ValutazioneRischio)
        .join(Ambiente)
        .where(Ambiente.azienda_id == azienda_id)
    )

    return SurveyResponse(
        azienda=azienda,
        persone=persone_result.scalars().all(),
        ambienti=ambienti_result.scalars().all(),
        attrezzature=attrezzature_result.scalars().all(),
        sostanze_chimiche=sostanze_result.scalars().all(),
        rischi=rischi_result.scalars().all(),
    )


# Mapping of step number to the updatable fields on Azienda
_AZIENDA_STEP_FIELDS: dict[int, list[str]] = {
    1: [
        "ragione_sociale",
        "sede_legale_via",
        "sede_legale_citta",
        "sede_operativa_via",
        "sede_operativa_citta",
        "attivita",
        "codice_ateco",
        "orario_lavoro",
        "metratura_totale",
        "zona_sismica",
        "descrizione_attivita",
        "contesto_territoriale",
    ],
}


@router.put("/step/{step_number}", response_model=dict)
async def save_survey_step(
    azienda_id: uuid.UUID,
    step_number: int,
    body: SurveyStepData,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Auto-save a single survey step.

    Steps:
      1 = azienda company data
      2 = persone (managed via /persone CRUD)
      3 = ambienti (managed via /ambienti CRUD)
      4 = attrezzature (managed via /attrezzature CRUD)
      5 = rischi (managed via /rischi CRUD)
      6 = sostanze chimiche (managed via /sostanze-chimiche CRUD)
      7 = riepilogo (summary / review, no data save needed)

    For step 1 the body.data fields are applied directly to the Azienda record.
    For steps 2-6, data is managed through dedicated CRUD endpoints; this endpoint
    only updates the survey_status to track progress.
    Step 7 is the review step and triggers no data changes.
    """
    if step_number < 1 or step_number > 7:
        raise BadRequestError("Step number must be between 1 and 7")

    azienda = await _get_azienda(azienda_id, org_id, db)

    # Step 1: update azienda fields directly
    if step_number == 1:
        allowed = _AZIENDA_STEP_FIELDS[1]
        for field, value in body.data.items():
            if field in allowed:
                setattr(azienda, field, value)

    # Update survey status to track which step the user is on
    azienda.survey_status = f"step_{step_number}"
    await db.commit()

    return {"message": f"Step {step_number} saved", "survey_status": azienda.survey_status}


@router.post("/complete", response_model=SurveyCompleteResponse)
async def complete_survey(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Mark the survey as completed."""
    azienda = await _get_azienda(azienda_id, org_id, db)
    azienda.survey_status = "completed"
    await db.commit()

    return SurveyCompleteResponse(
        message="Survey completed successfully",
        survey_status="completed",
    )
