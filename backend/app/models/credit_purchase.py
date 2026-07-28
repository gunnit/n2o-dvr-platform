"""Credit purchase — one bought AI credit pack, and whether it was granted.

The ledger behind ``usage_counters.overage_credits``. That column is a running
total with no history; on its own it cannot answer "who bought what, when, and
did PayPal actually take the money", which is the first question a customer asks
about a top-up that didn't appear.

**This table is also the idempotency guard.** Granting credits is the one
billing write with no natural key to fall back on: PayPal can deliver
``PAYMENT.CAPTURE.COMPLETED`` while the browser is still on the return URL
calling ``/credits/capture``, and both paths grant the same pack. The status
flip is what serializes them —

    UPDATE credit_purchases SET status='completed'
     WHERE paypal_order_id = :id AND status = 'pending'
    RETURNING credits;      -- 0 rows == someone else already granted it

— so exactly one caller ever adds the credits, whichever arrives first.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

#: Created, PayPal order opened, customer has not paid (or we have not seen it).
STATUS_PENDING = "pending"
#: Captured and the credits are on the counter. Terminal.
STATUS_COMPLETED = "completed"
#: The customer abandoned checkout, or PayPal refused the capture. Terminal.
STATUS_FAILED = "failed"


class CreditPurchase(Base):
    __tablename__ = "credit_purchases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Who clicked buy. Nullable so deleting a user never destroys the financial
    # record — the purchase belongs to the organization, not the person.
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # From `app.billing.credit_packs`. Stored as a plain string, not an FK:
    # packs are code-level data, and a retired pack must not orphan the receipt
    # of someone who bought it while it was on sale.
    pack_code: Mapped[str] = mapped_column(String(32), nullable=False)
    # Denormalised from the catalogue on purpose — this is a receipt. If the
    # 2,000-credit pack is later repriced, what this customer actually paid and
    # actually received must not change with it.
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="EUR")

    # PayPal Orders v2 id. UNIQUE: it is the key both the browser return and the
    # webhook use to find this row, and two rows for one order would let the
    # same payment grant credits twice.
    paypal_order_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    #: pending | completed | failed
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=STATUS_PENDING)

    # Which usage period the credits were added to. Recorded rather than derived
    # so a later renewal cannot make it look as though a pack was applied to the
    # wrong period — `overage_credits` does not roll over.
    period_start: Mapped[date] = mapped_column(Date, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
