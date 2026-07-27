"""AI usage event — append-only credit ledger and idempotency guard.

Every credit spend writes one row. The UNIQUE ``idempotency_key`` is what makes
metering safe under Celery retries, double-clicks, and the restore/sync/
save-edited paths (INV-6): the insert is attempted with ON CONFLICT DO NOTHING,
and a conflict means "already charged, don't charge again".

Keys are deterministic per action, e.g. ``sds:{sostanza_id}``,
``vision:{foto_id}`` — never random.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AiUsageEvent(Base):
    __tablename__ = "ai_usage_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Indexed: the ledger is read per-org for the usage panel and for billing
    # disputes; Postgres does not index foreign keys on its own.
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 'reasoning' | 'vision' | 'sds' | 'visura' — see billing.constants.CREDIT_WEIGHTS.
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # Credits charged. Denormalized from CREDIT_WEIGHTS so historical rows stay
    # accurate if the price list is ever re-tuned.
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
    # Text, not String(n): keys embed UUIDs and action names and must never be
    # silently truncated into a collision with another action's key.
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
