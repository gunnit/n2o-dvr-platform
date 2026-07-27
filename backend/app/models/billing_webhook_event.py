"""Webhook idempotency ledger — every PayPal event we have already handled.

INV-2 makes the webhook the sole writer of ``subscriptions.status``. PayPal
retries an event until it gets a 2xx, and retries can arrive concurrently, so
"handle exactly once" has to be enforced by the database rather than by hoping.

The PayPal event id is the primary key: claiming it with
``INSERT … ON CONFLICT DO NOTHING RETURNING`` is the lock. Whoever inserts the
row owns the event; everyone else returns 200 without re-applying it.

Rows are kept, not deleted — they are the audit trail for "why did this
subscription change state", which is the first question asked when a customer
disputes a charge.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BillingWebhookEvent(Base):
    __tablename__ = "billing_webhook_events"

    # PayPal's `id` (e.g. "WH-2WR32451HC0233532-67976317FL4543714"). Natural PK:
    # the uniqueness we need is exactly PayPal's own event identity.
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # PayPal's resource id (an `I-…` subscription id for subscription events).
    # Nullable because not every event type carries one. Indexed because "show
    # me everything that happened to this subscription" is the support query.
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Set when handling finished. NULL means the claim was taken but processing
    # did not complete — the row to look at when a subscription state looks
    # stale, and the signal that PayPal's retry should be allowed to redo it.
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # What we did, or why we did nothing ("ignored: unhandled type", an error).
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
