"""AI-driven suggestions for the stress lavoro-correlato assessment.

Endpoints under /aziende/{azienda_id}/stress:
  * POST "/ai-misure" — generate 3-6 Italian misure correttive based on
    the operator's INAIL checklist answers. Returned as a plain text
    SUGGESTION; the frontend must let the operator review/edit before
    saving to `misure_correttive`.

Privacy: only aggregated INAIL indicator answers + computed scores are
sent to the AI. No codice fiscale, ID document, or personal health data.
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.services.ai.stress_misure_ai import suggest_stress_misure
from app.services.stress_calculator import calculate_stress

router = APIRouter(prefix="/aziende/{azienda_id}/stress", tags=["stress-ai"])


class StressAiMisureRequest(BaseModel):
    answers: dict[str, str] = Field(
        ...,
        description=(
            "Mapping of INAIL indicator id (e.g. 'A.1', 'B1.3', 'C4.8') "
            "to the operator's answer string. Same shape as "
            "/api/v1/calculate/stress."
        ),
    )


class StressAiMisureResponse(BaseModel):
    suggestion: str = Field(
        description=(
            "Italian newline-separated list of 3-6 corrective measures. "
            "Suggested by the AI based on the answers — must be reviewed "
            "by the operator before persisting into misure_correttive."
        )
    )


async def _verify_azienda(
    azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> None:
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id, Azienda.organization_id == org_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise NotFoundError("Azienda not found")


@router.post("/ai-misure", response_model=StressAiMisureResponse)
async def ai_misure_correttive(
    azienda_id: uuid.UUID,
    body: StressAiMisureRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Suggest AI-generated misure correttive for the stress assessment.

    Computes the INAIL score from `answers`, then asks gpt-5.4-mini for
    3-6 concrete Italian measures tailored to the livello and the
    sub-areas that scored highest. Returns the raw suggestion text — the
    frontend lets the operator review/edit before saving.
    """
    await _verify_azienda(azienda_id, org_id, db)
    calc = calculate_stress(body.answers)
    suggestion = await suggest_stress_misure(body.answers, calc)
    return StressAiMisureResponse(suggestion=suggestion)
