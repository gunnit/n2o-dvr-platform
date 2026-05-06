import base64
import binascii
import uuid
from datetime import datetime, timezone

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
from app.schemas.survey import (
    SurveyCompleteResponse,
    SurveyResponse,
    SurveyRevisionResponse,
    SurveySignRequest,
    SurveySignResponse,
    SurveyStepData,
)

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
        select(Persona)
        .where(Persona.azienda_id == azienda_id)
        # US-1.4: eager-load ambienti so PersonaResponse.ambiente_ids serializes.
        .options(selectinload(Persona.ambienti))
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

    Steps (post-2026-04-30 rischi extract — see frontend
    survey-wizard.tsx STEPS for the canonical order):
      1 = azienda company data
      2 = ambienti (managed via /ambienti CRUD)
      3 = attrezzature (managed via /attrezzature CRUD)
      4 = persone (managed via /persone CRUD)
      5 = dpi & rischi specifici per persona (managed via /persone CRUD)
      6 = sostanze chimiche (managed via /sostanze-chimiche CRUD)
      7 = riepilogo (summary / review, no data save needed)

    Note: la valutazione rischi (un tempo step 6) è stata estratta in una
    pagina dedicata su /assessments/risk/[aziendaId] (admin feedback #2,
    2026-04-30) — il backend continua ad accettare i POST /rischi/batch
    come prima, ma il survey wizard non la gestisce più.

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


@router.post("/sign", response_model=SurveySignResponse)
async def sign_survey(
    azienda_id: uuid.UUID,
    body: SurveySignRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Persist the client signature PNG + server-side timestamp.

    US-1.6 AC3: once signed the survey moves to status "firmato". The wizard
    gates navigation on this status.
    """
    azienda = await _get_azienda(azienda_id, org_id, db)

    # Strip the "data:image/png;base64," prefix if present.
    raw = body.signature_data_url
    if "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        png_bytes = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BadRequestError(f"Firma non valida: {exc}")
    if len(png_bytes) < 32:
        raise BadRequestError("Firma troppo breve o canvas vuoto")

    azienda.firma_png = png_bytes
    azienda.firma_signed_at = datetime.now(timezone.utc)
    azienda.firma_signed_by_name = body.signed_by_name
    azienda.survey_status = "firmato"
    await db.commit()

    return SurveySignResponse(
        survey_status=azienda.survey_status,
        firma_signed_at=azienda.firma_signed_at,
        firma_signed_by_name=azienda.firma_signed_by_name,
    )


@router.post("/revision", response_model=SurveyRevisionResponse)
async def open_revision(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """US-1.6 AC4: flip status from "firmato" back to "in_revisione" so the
    wizard re-enables nav. The PNG stays on disk as a prior-signature record.
    """
    azienda = await _get_azienda(azienda_id, org_id, db)
    azienda.survey_status = "in_revisione"
    await db.commit()
    return SurveyRevisionResponse(survey_status=azienda.survey_status)
