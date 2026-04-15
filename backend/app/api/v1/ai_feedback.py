"""AI feedback endpoint (US-2.6 thumbs-down, US-5.3 provenance audit).

Accepts thumbs_up / thumbs_down signals on AI-generated content. Used today
for US-2.6 Rifiuta actions on improvement-measure suggestions; designed to be
reusable for future AI surfaces (SDS extraction corrections, company description
regenerations, etc.).
"""

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.ai_feedback import AiFeedback
from app.models.user import User

router = APIRouter(prefix="/ai-feedback", tags=["ai-feedback"])


class AiFeedbackCreate(BaseModel):
    entity_type: str = Field(..., max_length=64)
    entity_id: str | None = Field(None, max_length=255)
    signal: Literal["thumbs_up", "thumbs_down"]
    reason: str | None = None
    azienda_id: uuid.UUID | None = None
    context: dict[str, Any] | None = None


class AiFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    signal: str
    entity_type: str
    entity_id: str | None


@router.post("", response_model=AiFeedbackResponse, status_code=201)
async def record_feedback(
    body: AiFeedbackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AiFeedback:
    feedback = AiFeedback(
        organization_id=user.organization_id,
        azienda_id=body.azienda_id,
        user_id=user.id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        signal=body.signal,
        reason=body.reason,
        context=body.context,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback
