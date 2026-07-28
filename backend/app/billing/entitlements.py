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
    STATUS_NONE,
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
    # None = this organization owns no subscription row (never bought anything).
    # Callers must not treat it as a plan lookup key; see `subscribed`.
    plan_code: str | None
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
    def subscribed(self) -> bool:
        """Whether this org owns a subscription row at all.

        ``False`` means "has never bought", not "lapsed" — a canceled tenant is
        subscribed but not :attr:`is_active`. The UI needs the distinction to
        choose between "attiva un piano" and "rinnova".
        """
        return self.status != STATUS_NONE

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


def _data_gap_entitlements(account_type: str) -> Entitlements:
    """The INV-1 safety net: the organization row itself cannot be read.

    Deliberately **fully permissive** — every limit ``None``, no doc-type
    restriction, reported as active. The correct failure mode for a data gap is
    to let the customer keep working while we get paged, never to 402 a paying
    tenant over our own bookkeeping.

    Note this is more permissive than the *seeded* ``A_FOUNDING`` row, which has
    finite seats/companies/credits. Reusing those finite numbers here would mean
    a data gap could still block someone, which is exactly what INV-1 forbids.

    This is **not** the path for "signed up, hasn't paid" — that is
    :func:`_unsubscribed_entitlements`. Conflating the two is what made every
    new signup look like an active founding partner (MB-6.1).
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


def _unsubscribed_entitlements(account_type: str) -> Entitlements:
    """A real organization that has never bought a plan.

    The normal state of a fresh self-serve signup between ``POST /auth/register``
    and the ``BILLING.SUBSCRIPTION.ACTIVATED`` webhook — so it must read
    honestly rather than borrow the founding partner's rights:

    * ``plan_code`` is ``None`` — the UI renders "nessun piano attivo" and a
      call to action, instead of an internal code the customer never bought.
    * ``status`` is :data:`STATUS_NONE`, so :attr:`is_active` is ``False`` and
      ``ensure_subscription_active`` is the single gate that speaks for this
      case. Under shadow mode it logs ``WOULD_402 reason=subscription``, which
      is exactly the evidence GATE 2 needs and which the old permissive
      fallback silently withheld.
    * ``seats`` is 1 — the admin who signed up.
    * ``ai_credits_year`` is **0, not None** (MB-6.2). ``None`` means *pooled and
      unmetered* — the Enterprise tier — and :attr:`credits_unmetered` makes
      ``spend_credits`` short-circuit to "allow". The AI endpoints meter but do
      not call ``ensure_subscription_active``, so a ``None`` here handed every
      unsubscribed and every lapsed tenant unlimited OpenAI spend at our cost.
      Zero is the honest value: nothing was bought, so nothing is included.

    ``max_companies`` / ``max_sites`` do stay ``None``, because unlike credits
    those are only ever consulted on paths that already pass through
    ``ensure_subscription_active`` — the subscription gate speaks for them, and
    duplicating the refusal would just make the shadow log noisier.

    Safe to be non-active only because migration ``e7f8a9b0c1d2`` gave every
    pre-existing organization an explicit ``A_FOUNDING`` row (INV-1).
    """
    return Entitlements(
        account_type=account_type,
        plan_code=None,
        allowed_doc_types=None,
        seats=1,
        max_companies=None,
        max_sites=None,
        ai_credits_year=0,
        features={},
        status=STATUS_NONE,
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
        # user, so this means the org was deleted mid-session — a genuine data
        # gap, and INV-1 says a gap must not cost anyone their access.
        logger.warning("entitlements: organization %s not found; using permissive fallback", org_id)
        return _data_gap_entitlements(ACCOUNT_TYPE_CONSULTANT)

    account_type, subscription, plan = row
    account_type = account_type or ACCOUNT_TYPE_CONSULTANT

    if subscription is None:
        # Expected, not exceptional: every self-serve signup lives here until
        # its first ACTIVATED webhook. Reported honestly rather than granted
        # the founding partner's rights (MB-6.1). Logged at debug because on
        # the direct channel this is the single most common state there is.
        logger.debug("entitlements: org %s has no subscription yet (never purchased)", org_id)
        return _unsubscribed_entitlements(account_type)

    if plan is None:
        # A subscription pointing at a plan_code that no longer resolves. The
        # customer *did* buy something, so this is our bookkeeping failing, not
        # their entitlement lapsing — soft-fail permissively and page someone.
        logger.warning(
            "entitlements: org %s has subscription on unknown plan %s; using permissive fallback",
            org_id,
            subscription.plan_code,
        )
        return _data_gap_entitlements(account_type)

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
