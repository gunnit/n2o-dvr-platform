"""User feedback endpoints.

POST /feedback          — any authed user creates a bug/idea/observation
GET  /feedback          — admin lists org-scoped feedback, filterable
PATCH /feedback/{id}    — admin updates status

Every successful create is mirrored to a GitHub issue (best-effort) so
the team triages from the repo. Status changes flow back: `risolto` and
`non_fara` close the issue; reopening a triaged item reopens it.
"""

import logging
import re
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.permissions import ADMIN_TOOLS
from app.dependencies import get_current_user, require_capability
from app.models.user import User
from app.models.user_feedback import UserFeedback
from app.services import github_issues

router = APIRouter(prefix="/feedback", tags=["feedback"])
log = logging.getLogger(__name__)

FeedbackType = Literal["bug", "idea", "observation"]
FeedbackStatus = Literal["nuovo", "in_revisione", "risolto", "non_fara"]

# Bounds for the context the browser attaches by itself. They cap what we
# store; they never reject a submission — see FeedbackCreate.
PAGE_URL_MAX = 2048
ROUTE_MAX = 512
USER_AGENT_MAX = 512

_WEB_URL = re.compile(r"^https?://", re.IGNORECASE)


class FeedbackCreate(BaseModel):
    type: FeedbackType
    description: str = Field(min_length=1, max_length=5000)
    page_url: str | None = None
    route: str | None = None
    user_agent: str | None = None

    # `description` is what the operator wrote, so an oversized one is a
    # real 422. The three fields below are not: the browser fills them in
    # and the operator never sees them. A 2100-character URL used to fail
    # the whole call, and the report the operator typed was lost with it.
    # Clamp instead, and keep the request.
    @field_validator("route")
    @classmethod
    def _clamp_route(cls, value: str | None) -> str | None:
        return None if value is None else value[:ROUTE_MAX]

    @field_validator("user_agent")
    @classmethod
    def _clamp_user_agent(cls, value: str | None) -> str | None:
        return None if value is None else value[:USER_AGENT_MAX]

    @field_validator("page_url")
    @classmethod
    def _web_url_only(cls, value: str | None) -> str | None:
        # The triage table renders this as a clickable link, so anything
        # that is not a plain web URL is dropped rather than handed to an
        # admin as something to click.
        if value is None or not _WEB_URL.match(value):
            return None
        return value[:PAGE_URL_MAX]


class FeedbackUpdate(BaseModel):
    status: FeedbackStatus


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    description: str
    page_url: str | None
    route: str | None
    user_agent: str | None
    status: str
    github_issue_number: int | None
    github_issue_url: str | None
    created_at: datetime
    updated_at: datetime


class FeedbackAdminRow(BaseModel):
    """Admin list row — joins user label so the table doesn't need a second fetch."""

    id: uuid.UUID
    type: str
    description: str
    page_url: str | None
    route: str | None
    user_agent: str | None
    status: str
    github_issue_number: int | None
    github_issue_url: str | None
    user_id: uuid.UUID | None
    user_label: str | None
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=FeedbackOut, status_code=201)
async def create_feedback(
    body: FeedbackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserFeedback:
    fb = UserFeedback(
        organization_id=user.organization_id,
        user_id=user.id,
        type=body.type,
        description=body.description,
        page_url=body.page_url,
        route=body.route,
        user_agent=body.user_agent,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)

    # Best-effort mirror. Inline because the GitHub call is cheap (one
    # POST, ~200ms p95) and we want the issue URL in the response so the
    # admin UI can link straight to it. Failures are swallowed inside
    # github_issues — they never break this endpoint.
    number, html_url = await github_issues.create_issue_from_feedback(fb)
    if number is not None:
        fb.github_issue_number = number
        fb.github_issue_url = html_url
        await db.commit()
        await db.refresh(fb)

    return fb


@router.get("", response_model=list[FeedbackAdminRow])
async def list_feedback(
    status: FeedbackStatus | None = Query(default=None),
    type: FeedbackType | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(require_capability(ADMIN_TOOLS)),
    db: AsyncSession = Depends(get_db),
) -> list[FeedbackAdminRow]:
    stmt = (
        select(UserFeedback, User.full_name, User.email)
        .join(User, User.id == UserFeedback.user_id, isouter=True)
        .where(UserFeedback.organization_id == admin.organization_id)
    )
    if status is not None:
        stmt = stmt.where(UserFeedback.status == status)
    if type is not None:
        stmt = stmt.where(UserFeedback.type == type)
    stmt = (
        stmt.order_by(desc(UserFeedback.created_at), desc(UserFeedback.id))
        .offset(offset)
        .limit(limit)
    )

    rows = (await db.execute(stmt)).all()
    return [
        FeedbackAdminRow(
            id=fb.id,
            type=fb.type,
            description=fb.description,
            page_url=fb.page_url,
            route=fb.route,
            user_agent=fb.user_agent,
            status=fb.status,
            github_issue_number=fb.github_issue_number,
            github_issue_url=fb.github_issue_url,
            user_id=fb.user_id,
            user_label=full_name or email,
            created_at=fb.created_at,
            updated_at=fb.updated_at,
        )
        for fb, full_name, email in rows
    ]


_CLOSE_REASON: dict[str, github_issues.CloseReason] = {
    "risolto": "completed",
    "non_fara": "not_planned",
}


@router.patch("/{feedback_id}", response_model=FeedbackOut)
async def update_feedback(
    feedback_id: uuid.UUID,
    body: FeedbackUpdate,
    admin: User = Depends(require_capability(ADMIN_TOOLS)),
    db: AsyncSession = Depends(get_db),
) -> UserFeedback:
    result = await db.execute(
        select(UserFeedback).where(
            UserFeedback.id == feedback_id,
            UserFeedback.organization_id == admin.organization_id,
        )
    )
    fb = result.scalar_one_or_none()
    if fb is None:
        raise HTTPException(status_code=404, detail="Feedback non trovato")

    prev_status = fb.status
    fb.status = body.status
    await db.commit()
    await db.refresh(fb)

    # Sync the GitHub issue state. Idempotent against GitHub — patching
    # an already-closed issue to closed is a no-op there.
    if fb.github_issue_number is not None and prev_status != body.status:
        close_reason = _CLOSE_REASON.get(body.status)
        if close_reason is not None:
            await github_issues.close_issue(fb.github_issue_number, close_reason)
        elif prev_status in _CLOSE_REASON:
            # Going from a closed status back to nuovo/in_revisione.
            await github_issues.reopen_issue(fb.github_issue_number)

    return fb
