"""Subscription lifecycle — the only place ``subscriptions`` rows are written.

INV-2: PayPal owns the payment lifecycle, Postgres owns entitlements, and the
webhook is the sole writer of ``status`` / ``current_period_*``. That invariant
is only worth anything if there is exactly one code path doing the writing, so
it lives here rather than in ``api/v1/billing.py`` — which also keeps the
``.importlinter`` contract (the API layer may not touch ``models.subscription``)
enforceable.

**PayPal's subscription resource is the authority, not the webhook payload.**
Every handler re-fetches the subscription and reconciles from that. Webhooks
arrive out of order and can be replayed days later; applying a stale
``SUSPENDED`` event after a customer has already paid would wrongly downgrade a
paying tenant. Re-reading means the last write always reflects current truth.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import paypal_client
from app.models.plan import Plan
from app.models.subscription import Subscription

logger = logging.getLogger(__name__)

# PayPal's vocabulary -> ours (billing.constants.SUBSCRIPTION_STATUSES).
# APPROVAL_PENDING/APPROVED mean "created, customer has not completed approval":
# `trialing` is our closest state — it grants access but is not yet paid.
_STATUS_MAP = {
    "APPROVAL_PENDING": "trialing",
    "APPROVED": "trialing",
    "ACTIVE": "active",
    "SUSPENDED": "past_due",
    "CANCELLED": "canceled",
    "EXPIRED": "canceled",
}


def map_status(paypal_status: str | None) -> str | None:
    """Our status for a PayPal one, or None if PayPal sent something new.

    Returning None rather than guessing matters: an unrecognised status must
    leave the row alone, not silently downgrade a paying customer.
    """
    if not paypal_status:
        return None
    return _STATUS_MAP.get(paypal_status.upper())


def _parse_time(value: str | None) -> datetime | None:
    """PayPal's RFC 3339 timestamps ('2026-07-27T10:00:00Z')."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("paypal: unparseable timestamp %r", value)
        return None


def period_bounds(resource: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    """Current period start/end from a PayPal subscription resource.

    Start is the last payment when there is one, falling back to the
    subscription's start — this is the date every usage meter keys on, so it has
    to move forward exactly once per renewal. End is the next billing time.
    """
    billing_info = resource.get("billing_info") or {}
    last_payment = (billing_info.get("last_payment") or {}).get("time")
    start = _parse_time(last_payment) or _parse_time(resource.get("start_time"))
    end = _parse_time(billing_info.get("next_billing_time"))
    return start, end


async def plan_code_for_paypal_plan(paypal_plan_id: str | None, db: AsyncSession) -> str | None:
    if not paypal_plan_id:
        return None
    return (
        await db.execute(
            select(Plan.plan_code).where(Plan.paypal_plan_id == paypal_plan_id)
        )
    ).scalar_one_or_none()


async def find_org_for_subscription(
    resource: dict[str, Any], db: AsyncSession
) -> uuid.UUID | None:
    """Which tenant does this PayPal subscription belong to?

    Two routes, in order of reliability:

    1. the stored ``paypal_subscription_id`` — set once we've seen it activate;
    2. ``custom_id``, which we stamp with the organization id at creation.

    (2) is what carries the very first event of a new subscription, before we
    have ever stored its id.
    """
    subscription_id = resource.get("id")
    if subscription_id:
        org_id = (
            await db.execute(
                select(Subscription.organization_id).where(
                    Subscription.paypal_subscription_id == subscription_id
                )
            )
        ).scalar_one_or_none()
        if org_id:
            return org_id

    custom_id = resource.get("custom_id")
    if custom_id:
        try:
            return uuid.UUID(str(custom_id))
        except (ValueError, TypeError):
            logger.warning("paypal: custom_id %r is not a UUID", custom_id)
    return None


async def _cancel_superseded(
    existing_id: str | None, new_id: str | None, org_id: uuid.UUID
) -> None:
    """Cancel a subscription this org is replacing.

    Without this, a customer who starts checkout twice (or upgrades) ends up
    with two live PayPal subscriptions billing the same tenant, and only one of
    them visible to us. Best-effort: failing to cancel the old one must not stop
    us recording the new one, or we would lose track of both.
    """
    if not existing_id or not new_id or existing_id == new_id:
        return
    logger.warning(
        "billing: org %s superseding subscription %s with %s — cancelling the old one",
        org_id, existing_id, new_id,
    )
    try:
        await paypal_client.cancel_subscription(
            existing_id, reason="Sostituito da un nuovo abbonamento"
        )
    except Exception:
        logger.exception(
            "billing: could not cancel superseded subscription %s for org %s "
            "— CANCEL IT BY HAND, the customer may be billed twice",
            existing_id, org_id,
        )


async def apply_subscription_resource(
    org_id: uuid.UUID,
    resource: dict[str, Any],
    db: AsyncSession,
) -> str:
    """Reconcile one org's subscription row from PayPal's resource.

    Returns a short human-readable outcome for the webhook ledger. Does not
    commit — the caller owns the transaction so the event claim and the state
    change land together.
    """
    paypal_status = resource.get("status")
    status = map_status(paypal_status)
    if status is None:
        return f"ignored: unknown PayPal status {paypal_status!r}"

    subscription_id = resource.get("id")
    row = (
        await db.execute(
            select(Subscription).where(Subscription.organization_id == org_id)
        )
    ).scalar_one_or_none()

    if row is None:
        # MB-1.3 gives every org a row; reaching here means a tenant created
        # outside that path. Refuse rather than invent one: a subscription row
        # with no grandfathered history is exactly the state INV-1 protects.
        logger.error(
            "billing: org %s has no subscription row; cannot apply PayPal %s",
            org_id, subscription_id,
        )
        return "error: organization has no subscription row"

    plan_code = await plan_code_for_paypal_plan(resource.get("plan_id"), db)
    start, end = period_bounds(resource)
    changes: list[str] = []

    # Only a subscription that actually reached ACTIVE may move the customer's
    # plan. An abandoned approval for a bigger plan must never upgrade someone
    # who never paid for it — nor downgrade them if they abandon a smaller one.
    if status == "active" and plan_code and row.plan_code != plan_code:
        changes.append(f"plan {row.plan_code}->{plan_code}")
        row.plan_code = plan_code

    if status == "active" and subscription_id and row.paypal_subscription_id != subscription_id:
        await _cancel_superseded(row.paypal_subscription_id, subscription_id, org_id)
        row.paypal_subscription_id = subscription_id
        changes.append(f"paypal_subscription_id={subscription_id}")

    payer_id = (resource.get("subscriber") or {}).get("payer_id")
    if payer_id and row.paypal_payer_id != payer_id:
        row.paypal_payer_id = payer_id
        changes.append("payer_id")

    if row.status != status:
        changes.append(f"status {row.status}->{status}")
        row.status = status

    # Period dates drive every usage meter, so only move them for a subscription
    # we actually recognise as this org's current one — a stale event for a
    # superseded subscription must not reset the live meters.
    if not subscription_id or row.paypal_subscription_id in (None, subscription_id):
        if start and row.current_period_start != start:
            row.current_period_start = start
            changes.append(f"period_start={start.date()}")
        if end and row.current_period_end != end:
            row.current_period_end = end
            changes.append(f"period_end={end.date()}")

    outcome = ", ".join(changes) if changes else "no change"
    logger.info(
        "billing: org %s subscription %s (%s) -> %s",
        org_id, subscription_id, paypal_status, outcome,
    )
    return outcome


async def sync_from_paypal(
    subscription_id: str, db: AsyncSession, org_id: uuid.UUID | None = None
) -> str:
    """Re-fetch a subscription from PayPal and apply it. The webhook's workhorse."""
    resource = await paypal_client.get_subscription(subscription_id)
    if resource is None:
        return f"ignored: PayPal does not know subscription {subscription_id}"

    target_org = org_id or await find_org_for_subscription(resource, db)
    if target_org is None:
        logger.error(
            "billing: cannot map PayPal subscription %s to an organization "
            "(custom_id=%r) — event dropped",
            subscription_id, resource.get("custom_id"),
        )
        return "error: no organization for subscription"

    return await apply_subscription_resource(target_org, resource, db)


async def get_paypal_subscription_id(org_id: uuid.UUID, db: AsyncSession) -> str | None:
    """The org's live PayPal subscription id, if it has ever activated one.

    Exists so the API layer can answer "is there something to cancel/revise"
    without reaching into ``models.subscription`` itself.
    """
    return (
        await db.execute(
            select(Subscription.paypal_subscription_id).where(
                Subscription.organization_id == org_id
            )
        )
    ).scalar_one_or_none()


async def set_plan_manually(
    org_id: uuid.UUID,
    plan_code: str,
    status: str,
    period_start: datetime,
    period_end: datetime,
    db: AsyncSession,
) -> Subscription:
    """MB-3.1 — put an org on a plan by hand (invoice paid off-platform).

    The escape hatch for enterprise deals and bank transfers, which is how the
    first consultant invoices are actually collected. Deliberately does not
    touch the PayPal ids: a manually-billed subscription has none, and clearing
    them for a customer who later self-serves would orphan their live PayPal
    subscription.
    """
    row = (
        await db.execute(
            select(Subscription).where(Subscription.organization_id == org_id)
        )
    ).scalar_one_or_none()

    if row is None:
        row = Subscription(organization_id=org_id, plan_code=plan_code, status=status)
        db.add(row)
    else:
        row.plan_code = plan_code
        row.status = status

    row.current_period_start = period_start
    row.current_period_end = period_end
    logger.info(
        "billing: org %s manually set to %s/%s until %s",
        org_id, plan_code, status, period_end.date(),
    )
    return row
