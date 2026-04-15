"""AI feedback endpoint (US-2.6 thumbs-down, US-5.3 provenance audit).

Accepts thumbs_up / thumbs_down signals on AI-generated content. Used today
for US-2.6 Rifiuta actions on improvement-measure suggestions; designed to be
reusable for future AI surfaces (SDS extraction corrections, company description
regenerations, etc.).

Also exposes admin-only read endpoints (US-5.3) so the admin AI Feedback
panel can surface where suggestions are being rejected most often.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, require_role
from app.models.ai_feedback import AiFeedback
from app.models.azienda import Azienda
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


# ---------------------------------------------------------------------------
# Admin views (US-5.3)
# ---------------------------------------------------------------------------


class FeedbackSummaryRow(BaseModel):
    """One row of the by-entity-type rejection summary."""

    entity_type: str
    thumbs_down_count: int
    thumbs_up_count: int


class FeedbackSummary(BaseModel):
    """Counts grouped by entity_type — feeds the admin panel KPI cards."""

    rows: list[FeedbackSummaryRow]
    total_thumbs_down: int
    total_thumbs_up: int


class RecentFeedbackRow(BaseModel):
    """A single recent feedback entry, joined with azienda + user labels."""

    id: uuid.UUID
    signal: str
    entity_type: str
    entity_id: str | None
    reason: str | None
    azienda_id: uuid.UUID | None
    azienda_label: str | None
    user_id: uuid.UUID | None
    user_label: str | None
    context_preview: str | None = Field(
        default=None,
        description=(
            "Truncated string preview of context.testo or the first ~120 chars"
            " of the JSON dump — lets the admin scan reasons without expanding."
        ),
    )
    created_at: datetime


def _context_preview(context: dict | None) -> str | None:
    """Return a short string preview of the JSONB context.

    Returns None when the context is empty, missing, or contains only
    whitespace / non-string values — the panel just skips that cell
    instead of rendering a useless empty preview.
    """
    if not context or not isinstance(context, dict):
        return None
    # Most rejection signals coming from measures-panel.tsx carry the
    # original AI suggestion text at context.testo. Fall back to the
    # first stringifiable value if that's not present or is whitespace.
    candidate = context.get("testo")
    if not (isinstance(candidate, str) and candidate.strip()):
        candidate = None
        for v in context.values():
            if isinstance(v, str) and v.strip():
                candidate = v
                break
    if candidate is None:
        return None
    text = candidate.strip()
    if not text:
        return None
    return text[:140] + ("…" if len(text) > 140 else "")


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


@router.get("/admin/summary", response_model=FeedbackSummary)
async def get_feedback_summary(
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> FeedbackSummary:
    """Per-entity-type counts of thumbs_down / thumbs_up.

    Drives the admin AI Feedback panel KPI cards so the team can see at a
    glance which AI surfaces (misure_suggerita, company_description, etc.)
    are getting rejected most.
    """
    stmt = (
        select(
            AiFeedback.entity_type,
            AiFeedback.signal,
            func.count(AiFeedback.id),
        )
        .group_by(AiFeedback.entity_type, AiFeedback.signal)
    )
    result = await db.execute(stmt)
    by_type: dict[str, dict[str, int]] = {}
    for entity_type, signal, count in result.all():
        bucket = by_type.setdefault(entity_type, {"thumbs_down": 0, "thumbs_up": 0})
        if signal in bucket:
            bucket[signal] = int(count)
    rows = [
        FeedbackSummaryRow(
            entity_type=entity_type,
            thumbs_down_count=counts.get("thumbs_down", 0),
            thumbs_up_count=counts.get("thumbs_up", 0),
        )
        # Sort by rejection count desc — biggest pain points first.
        for entity_type, counts in sorted(
            by_type.items(),
            key=lambda kv: (-kv[1].get("thumbs_down", 0), kv[0]),
        )
    ]
    return FeedbackSummary(
        rows=rows,
        total_thumbs_down=sum(r.thumbs_down_count for r in rows),
        total_thumbs_up=sum(r.thumbs_up_count for r in rows),
    )


@router.get("/admin/recent", response_model=list[RecentFeedbackRow])
async def get_recent_feedback(
    signal: Literal["thumbs_down", "thumbs_up"] | None = Query(
        default="thumbs_down",
        description="Filter by signal kind. Default is thumbs_down so the panel surfaces rejections.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[RecentFeedbackRow]:
    """Recent feedback entries with joined azienda + user labels.

    Admin-only. Used by the AI Feedback panel to show the most recent
    rejections (or, optionally, accepts) so the team can review individual
    cases and decide whether the prompt / model needs adjusting.

    No ORM relationships are declared on AiFeedback (the model stays
    lean), so we do explicit outer joins onto Azienda + User to pull
    display labels in a single round trip.
    """
    stmt = (
        select(
            AiFeedback,
            Azienda.ragione_sociale,
            User.full_name,
            User.email,
        )
        .join(Azienda, Azienda.id == AiFeedback.azienda_id, isouter=True)
        .join(User, User.id == AiFeedback.user_id, isouter=True)
    )
    if signal is not None:
        stmt = stmt.where(AiFeedback.signal == signal)
    stmt = stmt.order_by(desc(AiFeedback.created_at)).limit(limit)
    result = await db.execute(stmt)

    out: list[RecentFeedbackRow] = []
    for fb, azienda_label, user_full_name, user_email in result.all():
        out.append(
            RecentFeedbackRow(
                id=fb.id,
                signal=fb.signal,
                entity_type=fb.entity_type,
                entity_id=fb.entity_id,
                reason=fb.reason,
                azienda_id=fb.azienda_id,
                azienda_label=azienda_label,
                user_id=fb.user_id,
                user_label=user_full_name or user_email,
                context_preview=_context_preview(fb.context),
                created_at=fb.created_at,
            )
        )
    return out
