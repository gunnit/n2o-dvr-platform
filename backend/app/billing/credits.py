"""Credit pack purchases — the ledger, and the exactly-once grant.

Sits between ``api/v1/billing.py`` and ``models.credit_purchase`` for the same
reason ``catalogue.py`` sits in front of ``models.plan``: the ``.importlinter``
contract forbids the API layer from touching billing tables, so the rules about
*when* credits are granted live in one place instead of being re-derived at each
call site.

The rule that matters is :func:`complete_purchase`. Two independent paths learn
that an order was paid — the customer's browser returning to ``/billing`` and
PayPal's ``PAYMENT.CAPTURE.COMPLETED`` webhook — and they routinely race. The
conditional ``UPDATE … WHERE status = 'pending'`` is what makes the loser a
no-op instead of a second helping of credits.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import metering
from app.models.credit_purchase import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    CreditPurchase,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PurchaseRecord:
    """One receipt, flattened for the API layer."""

    id: uuid.UUID
    pack_code: str
    credits: int
    amount_cents: int
    currency: str
    status: str
    period_start: date
    created_at: datetime
    completed_at: datetime | None


def _to_record(row: CreditPurchase) -> PurchaseRecord:
    return PurchaseRecord(
        id=row.id,
        pack_code=row.pack_code,
        credits=row.credits,
        amount_cents=row.amount_cents,
        currency=row.currency,
        status=row.status,
        period_start=row.period_start,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


async def start_purchase(
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID | None,
    pack: dict[str, Any],
    period_start: date,
    db: AsyncSession,
) -> CreditPurchase:
    """Open a pending purchase. Committed by the caller.

    Written *before* PayPal is called so the order can carry our row id as its
    ``reference_id``. Doing it the other way round leaves a paid order with
    nothing on our side to attach it to — which is precisely the state a
    customer reports as "I paid and got nothing".

    Price and credit count are copied off the catalogue here and never read from
    it again: this row is a receipt, and repricing a pack next quarter must not
    retroactively change what someone bought.
    """
    row = CreditPurchase(
        organization_id=org_id,
        created_by_user_id=user_id,
        pack_code=pack["pack_code"],
        credits=int(pack["credits"]),
        amount_cents=int(pack["price_cents"]),
        currency="EUR",
        status=STATUS_PENDING,
        period_start=period_start,
    )
    db.add(row)
    await db.flush()
    return row


async def attach_order(purchase_id: uuid.UUID, order_id: str, db: AsyncSession) -> None:
    """Record the PayPal order id against a pending purchase."""
    row = await db.get(CreditPurchase, purchase_id)
    if row is not None:
        row.paypal_order_id = order_id


async def abandon(purchase_id: uuid.UUID, db: AsyncSession) -> None:
    """Mark a purchase failed. Only ever moves a *pending* row.

    Used when PayPal refuses to open the order and when the customer comes back
    through the cancel URL. Guarded on `pending` so a late cancel callback
    cannot un-grant a purchase that completed in the meantime — the browser can
    hit the cancel URL after the webhook has already banked the payment.
    """
    row = await db.get(CreditPurchase, purchase_id)
    if row is not None and row.status == STATUS_PENDING:
        row.status = STATUS_FAILED


async def find_by_order(order_id: str, db: AsyncSession) -> CreditPurchase | None:
    return (
        await db.execute(
            select(CreditPurchase).where(CreditPurchase.paypal_order_id == order_id)
        )
    ).scalar_one_or_none()


async def complete_purchase(order_id: str, db: AsyncSession) -> PurchaseRecord | None:
    """Grant the credits for a paid order, exactly once. Committed by the caller.

    Returns the receipt when *this* call was the one that granted, and ``None``
    when there was nothing to do — no such order, or someone else already
    completed it. The caller distinguishes the two only for logging: to the
    customer, "your credits are there" is the same answer either way.

    The ``UPDATE … WHERE status = 'pending'`` is the whole safety argument.
    Postgres serializes the row update, so of the browser return and the webhook
    exactly one sees a row change and goes on to call
    :func:`metering.grant_overage_credits`. The loser's UPDATE matches nothing.
    """
    row = await find_by_order(order_id, db)
    if row is None:
        logger.warning("billing: no credit purchase for PayPal order %s", order_id)
        return None

    # Re-read under a row lock, then test the status. `with_for_update` is what
    # makes "check then act" atomic against the concurrent path; without it both
    # callers could read `pending` before either writes.
    locked = (
        await db.execute(
            select(CreditPurchase)
            .where(CreditPurchase.id == row.id, CreditPurchase.status == STATUS_PENDING)
            .with_for_update(skip_locked=False)
        )
    ).scalar_one_or_none()
    if locked is None:
        logger.info(
            "billing: credit purchase for order %s already settled (%s) — not granting again",
            order_id, row.status,
        )
        return None

    locked.status = STATUS_COMPLETED
    locked.completed_at = datetime.now(timezone.utc)
    await db.flush()

    await metering.grant_overage_credits(
        locked.organization_id, locked.credits, locked.period_start, db
    )
    logger.info(
        "billing: org %s bought %s (+%d credits) for period %s",
        locked.organization_id, locked.pack_code, locked.credits, locked.period_start,
    )
    return _to_record(locked)


async def list_purchases(
    org_id: uuid.UUID, db: AsyncSession, limit: int = 24
) -> list[PurchaseRecord]:
    """Recent receipts, newest first.

    Pending rows are included on purpose: a customer who abandoned PayPal should
    see the attempt sitting there rather than wonder whether the click
    registered at all.
    """
    rows = (
        await db.execute(
            select(CreditPurchase)
            .where(CreditPurchase.organization_id == org_id)
            .order_by(CreditPurchase.created_at.desc())
            .limit(limit)
        )
    ).scalars()
    return [_to_record(r) for r in rows]


async def credits_purchased_in_period(
    org_id: uuid.UUID, period_start: date, db: AsyncSession
) -> int:
    """Completed pack credits added to one period. For the tracker's breakdown."""
    rows = (
        await db.execute(
            select(CreditPurchase.credits).where(
                CreditPurchase.organization_id == org_id,
                CreditPurchase.period_start == period_start,
                CreditPurchase.status == STATUS_COMPLETED,
            )
        )
    ).scalars()
    return sum(int(c) for c in rows)
