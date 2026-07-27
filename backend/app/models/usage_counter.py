"""Usage counter — the per-period AI credit meter.

One row per (organization, period). Deliberately a *counter*, not a
``COUNT(*)`` over ``ai_usage_events``: the spend path is a single atomic
conditional UPDATE so two concurrent requests can never both win the last
credit (INV-6):

    UPDATE usage_counters
       SET ai_credits_used = ai_credits_used + :w
     WHERE organization_id = :org AND period_start = :ps
       AND ai_credits_used + :w <= (:plan_credits + overage_credits)
    RETURNING ai_credits_used;   -- 0 rows == over budget == 402

``ai_usage_events`` is the audit trail and idempotency key for the same spend.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsageCounter(Base):
    __tablename__ = "usage_counters"
    __table_args__ = (
        # Makes the meter addressable by (org, period) and lets the spend path
        # use INSERT … ON CONFLICT DO NOTHING to create the row lazily.
        UniqueConstraint("organization_id", "period_start", name="uq_usage_counters_org_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    # Start of the subscription period this meter covers. A DATE (not a
    # timestamp) so the key is stable regardless of the time of day a period
    # rolls over.
    period_start: Mapped[date] = mapped_column(Date, nullable=False)

    # server_default (not just a Python default) because the spend path writes
    # this row with raw SQL that bypasses the ORM.
    ai_credits_used: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    # Credits from purchased overage packs, added to the plan allowance for
    # this period. Written by the Phase 4 one-time-payment webhook.
    overage_credits: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
