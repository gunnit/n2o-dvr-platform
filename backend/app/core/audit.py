"""Lightweight audit logging helper (US-5.3).

Call `log_audit(db, action, entity_type, entity_id, user, changes=...)` from
mutation endpoints. Non-blocking — logs to AuditLog table. On failure, swallows
the exception to avoid breaking the primary request.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User

log = logging.getLogger(__name__)


async def log_audit(
    db: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: Any,
    user: User | None = None,
    changes: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Insert an audit log row. Caller is responsible for committing the
    surrounding transaction — this function only stages the row.
    """
    try:
        entry = AuditLog(
            organization_id=user.organization_id if user else None,
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(entry)
    except Exception as e:
        log.warning("Audit logging failed (non-fatal): %s", e)
