"""Subscription — which plan an organization is on, right now.

One live subscription per org, enforced by a UNIQUE constraint on
``organization_id``. This table (joined to ``plans``) is the source of truth
for entitlements; Stripe owns only the payment lifecycle (INV-2). Once the
Phase 4 webhook lands it is the **sole writer** of ``status`` and
``current_period_*`` — nothing else may set them.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    plan_code: Mapped[str] = mapped_column(
        ForeignKey("plans.plan_code"), nullable=False
    )
    # 'trialing' | 'active' | 'past_due' | 'canceled'
    # — see billing.constants.SUBSCRIPTION_STATUSES.
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")

    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Timezone-aware throughout: renewal and trial boundaries decide whether a
    # customer can generate a document, so a naive local timestamp is a bug.
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
