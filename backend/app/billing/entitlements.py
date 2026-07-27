"""Entitlement resolution — what is this organization allowed to do, right now.

Read from Postgres on **every request** (INV-3). Entitlements deliberately do
not live in the JWT: a token minted before an upgrade, a downgrade, or credit
exhaustion would keep granting access it no longer has. The request already
loads the ``User`` row from Postgres, so this is one extra join, not one extra
round trip's worth of latency to care about.

This module is the only thing endpoints may use to learn about plans; reading
``Subscription`` or ``Plan`` directly from ``app.api.*`` is forbidden by
``.importlinter`` so the seam can't erode.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.billing.constants import (
    ACCOUNT_TYPE_CONSULTANT,
    ACTIVE_STATUSES,
    FOUNDING_PLAN_CODE,
    normalize_doc_type,
)
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.subscription import Subscription

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Entitlements:
    """A resolved, immutable snapshot of one org's commercial rights.

    ``None`` means "unlimited / not metered" consistently across every limit
    field, matching the NULL semantics in the ``plans`` table.
    """

    account_type: str
    plan_code: str
    # None = all 17 document types (every Model A plan).
    allowed_doc_types: frozenset[str] | None
    seats: int
    max_companies: int | None
    max_sites: int | None
    # None = pooled/unmetered; the credit check short-circuits to allow.
    ai_credits_year: int | None
    features: dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    # Start of the current subscription period. Every meter — AI credits and
    # active companies — is keyed on this date, so the whole system must agree
    # on one value. Plans are annual (three years for founding), so this is NOT
    # the calendar month. None only in the no-subscription fallback, where
    # `meter_period_start` substitutes a stable stand-in.
    period_start: date | None = None
    period_end: date | None = None

    @property
    def meter_period_start(self) -> date:
        """The date the usage meters key on.

        Falls back to the start of the current month when there is no
        subscription — the fallback path is unmetered anyway, so the value only
        needs to be stable and non-null.
        """
        return self.period_start or date.today().replace(day=1)

    @property
    def is_active(self) -> bool:
        """Whether the subscription is in a state that still grants access.

        ``past_due`` counts as active: PayPal retries a failed payment over
        several days and a customer must not lose their DVR mid-dunning. The
        read-only downgrade on final failure is MB-4.5.
        """
        return self.status in ACTIVE_STATUSES

    @property
    def credits_unmetered(self) -> bool:
        return self.ai_credits_year is None

    def allows_doc_type(self, tipo: str | None) -> bool:
        """Whether this plan may generate ``tipo``.

        Always compare through here — the caller's casing is untrusted (the
        wire form is lowercase, the dispatcher registry is uppercase).
        """
        if self.allowed_doc_types is None:
            return True
        return normalize_doc_type(tipo) in self.allowed_doc_types

    def feature(self, name: str, default: Any = None) -> Any:
        return self.features.get(name, default)


def _fallback_entitlements(account_type: str) -> Entitlements:
    """The INV-1 safety net: an org with no resolvable subscription.

    Deliberately **fully permissive** — every limit ``None``, no doc-type
    restriction. This is a data-integrity gap (MB-1.3 should have given every
    org a subscription row), and the correct failure mode for a gap is to let
    the customer keep working while we get paged, never to 402 a paying tenant.

    Note this is more permissive than the *seeded* ``A_FOUNDING`` row, which has
    finite seats/companies/credits. Reusing those finite numbers here would mean
    a data gap could still block someone, which is exactly what INV-1 forbids.
    """
    return Entitlements(
        account_type=account_type,
        plan_code=FOUNDING_PLAN_CODE,
        allowed_doc_types=None,
        seats=2**31 - 1,
        max_companies=None,
        max_sites=None,
        ai_credits_year=None,
        features={},
        status="active",
    )


def build_entitlements_query(org_id: uuid.UUID) -> Select:
    """The single SELECT behind :func:`resolve_entitlements`.

    Outer joins, so the three "org exists but the billing rows don't" cases all
    come back as one row with NULLs rather than as an empty result — the caller
    can then tell "no such organization" apart from "organization without a
    subscription" and log accordingly.

    Exposed separately so a test can compile it without a database.
    """
    return (
        select(Organization.account_type, Subscription, Plan)
        .select_from(Organization)
        .outerjoin(Subscription, Subscription.organization_id == Organization.id)
        .outerjoin(Plan, Plan.plan_code == Subscription.plan_code)
        .where(Organization.id == org_id)
    )


async def resolve_entitlements(org_id: uuid.UUID, db: AsyncSession) -> Entitlements:
    """Resolve the current entitlements for ``org_id``. Never raises."""
    row = (await db.execute(build_entitlements_query(org_id))).first()

    if row is None:
        # No such organization. Callers reach this through an authenticated
        # user, so this means the org was deleted mid-session.
        logger.warning("entitlements: organization %s not found; using permissive fallback", org_id)
        return _fallback_entitlements(ACCOUNT_TYPE_CONSULTANT)

    account_type, subscription, plan = row
    account_type = account_type or ACCOUNT_TYPE_CONSULTANT

    if subscription is None or plan is None:
        logger.warning(
            "entitlements: org %s has no resolvable subscription (subscription=%s, plan=%s); "
            "using permissive fallback — every org should own a subscription row after MB-1.3",
            org_id,
            getattr(subscription, "plan_code", None),
            None if plan is None else plan.plan_code,
        )
        return _fallback_entitlements(account_type)

    allowed = plan.allowed_doc_types
    return Entitlements(
        account_type=account_type,
        plan_code=plan.plan_code,
        allowed_doc_types=(
            None if allowed is None else frozenset(normalize_doc_type(t) for t in allowed)
        ),
        seats=plan.seats,
        max_companies=plan.max_companies,
        max_sites=plan.max_sites,
        ai_credits_year=plan.ai_credits_year,
        features=dict(plan.features or {}),
        status=subscription.status,
        period_start=(
            subscription.current_period_start.date()
            if subscription.current_period_start
            else None
        ),
        period_end=(
            subscription.current_period_end.date()
            if subscription.current_period_end
            else None
        ),
    )


async def get_entitlements(
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Entitlements:
    """FastAPI dependency: `ent: Entitlements = Depends(get_entitlements)`."""
    return await resolve_entitlements(org_id, db)
