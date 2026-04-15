"""Admin backup status panel — US-5.4.

Surfaces the Render Postgres backup configuration plus recent backup events
captured in the AuditLog. Wraps the existing `app.core.audit.log_audit`
helper so backup webhooks (or admins) can record success/failure events
through `POST /admin/backups/event`.

The Render backup itself runs outside this app (managed Postgres). The
endpoints here are the *visibility layer* the admin needs:

* `GET /admin/backups/status` — config metadata, last successful backup
  timestamp, last failure (with message), and a 30-event history.
* `POST /admin/backups/event` — admin-only audit trail entry. Used by the
  Render webhook (or a manual cron) to record `backup_completed` /
  `backup_failed` so the panel and AC2 alerting work.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.audit import log_audit
from app.db.session import get_db
from app.dependencies import require_role
from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/backups", tags=["admin-backups"])


# Audit-log conventions — keep in lockstep with the Render webhook payload.
BACKUP_ENTITY_TYPE = "backup"
BACKUP_ACTION_COMPLETED = "backup_completed"
BACKUP_ACTION_FAILED = "backup_failed"


class BackupEventResponse(BaseModel):
    id: uuid.UUID
    action: str
    occurred_at: datetime
    user_id: uuid.UUID | None = None
    backup_id: str | None = Field(
        default=None,
        description="The Render backup snapshot ID (entity_id on the audit row).",
    )
    message: str | None = Field(
        default=None,
        description="Short Italian explanation. For failures, what went wrong.",
    )


class BackupStatusResponse(BaseModel):
    """Everything the admin panel needs for the AC1 'status' card."""

    provider: str
    region: str
    schedule: str
    retention_days: int
    alert_email: str
    last_successful_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_failure_message: str | None = None
    history: list[BackupEventResponse]


class BackupEventBody(BaseModel):
    """Webhook / manual event payload (AC2)."""

    status: Literal["completed", "failed"]
    backup_id: str | None = None
    message: str | None = None


def _audit_to_response(row: AuditLog) -> BackupEventResponse:
    msg = None
    if isinstance(row.changes, dict):
        msg = row.changes.get("message")
    return BackupEventResponse(
        id=row.id,
        action=row.action,
        occurred_at=row.created_at,
        user_id=row.user_id,
        backup_id=row.entity_id,
        message=msg,
    )


@router.get("/status", response_model=BackupStatusResponse)
async def get_backup_status(
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> BackupStatusResponse:
    """Return the backup config + latest backup events.

    Admin-only. The history is a flat slice of the AuditLog filtered to
    backup actions; we cap it at 30 entries to keep the panel snappy.
    """
    history_q = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_type == BACKUP_ENTITY_TYPE,
            AuditLog.action.in_((BACKUP_ACTION_COMPLETED, BACKUP_ACTION_FAILED)),
        )
        .order_by(desc(AuditLog.created_at))
        .limit(30)
    )
    rows = list(history_q.scalars().all())

    last_success = next(
        (r for r in rows if r.action == BACKUP_ACTION_COMPLETED), None
    )
    last_failure = next(
        (r for r in rows if r.action == BACKUP_ACTION_FAILED), None
    )
    last_failure_message: str | None = None
    if last_failure and isinstance(last_failure.changes, dict):
        last_failure_message = last_failure.changes.get("message")

    return BackupStatusResponse(
        provider=settings.BACKUP_PROVIDER,
        region=settings.BACKUP_REGION,
        schedule=settings.BACKUP_SCHEDULE,
        retention_days=settings.BACKUP_RETENTION_DAYS,
        alert_email=settings.BACKUP_ALERT_EMAIL,
        last_successful_at=last_success.created_at if last_success else None,
        last_failure_at=last_failure.created_at if last_failure else None,
        last_failure_message=last_failure_message,
        history=[_audit_to_response(r) for r in rows],
    )


@router.post("/event", response_model=BackupEventResponse, status_code=201)
async def record_backup_event(
    body: BackupEventBody,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> BackupEventResponse:
    """Record a backup completion or failure event in the audit trail.

    AC2: failures are visible in the audit log within 5 minutes — Render's
    webhook (or our own cron) calls this endpoint as soon as the backup job
    settles. We also fire an admin-email alert on failure (best-effort log
    line for now; SMTP wiring is a follow-up).
    """
    action = (
        BACKUP_ACTION_COMPLETED
        if body.status == "completed"
        else BACKUP_ACTION_FAILED
    )
    changes: dict | None = None
    if body.message:
        changes = {"message": body.message}

    await log_audit(
        db,
        action=action,
        entity_type=BACKUP_ENTITY_TYPE,
        entity_id=body.backup_id,
        user=user,
        changes=changes,
    )

    if body.status == "failed":
        # AC2 alerting hook. Render emails on managed-Postgres backup
        # failures already; this log line is the in-app trail and a
        # placeholder for the SMTP/Slack relay we'll wire in a follow-up.
        logger.error(
            "[BACKUP ALERT] backup_failed alert for %s — should notify %s. Reason: %s",
            body.backup_id or "<unknown>",
            settings.BACKUP_ALERT_EMAIL,
            body.message or "(no detail provided)",
        )

    await db.commit()
    # Round-trip the freshly inserted row so we return real created_at.
    refetched = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_type == BACKUP_ENTITY_TYPE,
            AuditLog.action == action,
            (AuditLog.entity_id == body.backup_id)
            if body.backup_id is not None
            else (AuditLog.entity_id.is_(None)),
        )
        .order_by(desc(AuditLog.created_at))
        .limit(1)
    )
    row = refetched.scalar_one_or_none()
    if row is None:
        # Defensive fallback — shouldn't happen, but never crash the request.
        return BackupEventResponse(
            id=uuid.uuid4(),
            action=action,
            occurred_at=datetime.now(timezone.utc).replace(tzinfo=None),
            user_id=user.id,
            backup_id=body.backup_id,
            message=body.message,
        )
    return _audit_to_response(row)
