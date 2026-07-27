"""Usage metering — AI credits and active companies.

Two writes, both of which must survive being executed more than once (INV-6).
Celery retries, document restore, Google-Doc sync, save-edited-version and a
user double-clicking all replay the same logical action.

Credits are charged **before** the OpenAI call (INV-7): the spend is a single
atomic conditional UPDATE that either reserves the credits or matches zero rows,
and zero rows means 402 — so an over-budget request never reaches OpenAI and
there is nothing to refund. On a failed call the caller may release the
reservation with :func:`refund_credits`.

Like :mod:`app.billing.gates`, everything here honours
``settings.ENTITLEMENTS_ENFORCE``: while it is false the meters still *record*
usage but never deny, and a would-be denial is logged as ``WOULD_402``.
"""

import logging
import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.constants import CREDIT_WEIGHTS
from app.billing.entitlements import Entitlements
from app.config import settings

logger = logging.getLogger(__name__)

_PAYMENT_REQUIRED = status.HTTP_402_PAYMENT_REQUIRED

_ENSURE_COUNTER = text(
    """
    INSERT INTO usage_counters (id, organization_id, period_start)
    VALUES (gen_random_uuid(), :org, :period)
    ON CONFLICT (organization_id, period_start) DO NOTHING
    """
)

# The race-safe spend. The allowance test lives in the WHERE clause, so two
# concurrent requests for the last credit cannot both win: Postgres serializes
# the row update and the loser's predicate is false by the time it runs.
_SPEND = text(
    """
    UPDATE usage_counters
       SET ai_credits_used = ai_credits_used + :weight,
           updated_at = now()
     WHERE organization_id = :org
       AND period_start = :period
       AND ai_credits_used + :weight <= (:allowance + overage_credits)
    RETURNING ai_credits_used
    """
)

_RECORD_EVENT = text(
    """
    INSERT INTO ai_usage_events (id, organization_id, kind, weight, idempotency_key)
    VALUES (gen_random_uuid(), :org, :kind, :weight, :key)
    ON CONFLICT (idempotency_key) DO NOTHING
    RETURNING id
    """
)

_RELEASE = text(
    """
    UPDATE usage_counters
       SET ai_credits_used = GREATEST(0, ai_credits_used - :weight),
           updated_at = now()
     WHERE organization_id = :org AND period_start = :period
    """
)

_RECORD_ACTIVE_COMPANY = text(
    """
    INSERT INTO active_company_periods (organization_id, azienda_id, period_start)
    VALUES (:org, :azienda, :period)
    ON CONFLICT DO NOTHING
    RETURNING azienda_id
    """
)

_COUNT_ACTIVE = text(
    """
    SELECT count(*) FROM active_company_periods
     WHERE organization_id = :org AND period_start = :period
    """
)

_IS_ACTIVE = text(
    """
    SELECT 1 FROM active_company_periods
     WHERE organization_id = :org AND azienda_id = :azienda AND period_start = :period
    """
)


def credit_weight(kind: str) -> int:
    """Credits an action of ``kind`` costs. Unknown kinds cost the minimum."""
    return CREDIT_WEIGHTS.get(kind, 1)


async def spend_credits(
    org_id: uuid.UUID,
    kind: str,
    idem_key: str,
    db: AsyncSession,
    ent: Entitlements,
) -> bool:
    """Reserve credits for one AI action. Call **before** the OpenAI request.

    Returns True when the action may proceed. Raises 402 when the allowance is
    exhausted *and* enforcement is on; in shadow mode it logs ``WOULD_402`` and
    returns True.

    ``idem_key`` must be deterministic for the action (``f"sds:{sostanza_id}"``,
    ``f"vision:{foto_id}"``) — never random, or a retry charges twice.
    """
    # Pooled/unmetered plans (A_ENTERPRISE) short-circuit: nothing to count.
    if ent.credits_unmetered:
        return True

    weight = credit_weight(kind)
    period = ent.meter_period_start

    # A replay of an action already charged must not charge again. Claiming the
    # idempotency key first makes the whole operation exactly-once: whoever
    # inserts the event row is the one who spends.
    claimed = (
        await db.execute(
            _RECORD_EVENT,
            {"org": org_id, "kind": kind, "weight": weight, "key": idem_key},
        )
    ).first()
    if claimed is None:
        logger.debug(
            "credit spend replayed, not charging again: org=%s key=%s", org_id, idem_key
        )
        return True

    await db.execute(_ENSURE_COUNTER, {"org": org_id, "period": period})
    row = (
        await db.execute(
            _SPEND,
            {
                "weight": weight,
                "org": org_id,
                "period": period,
                "allowance": ent.ai_credits_year,
            },
        )
    ).first()

    if row is not None:
        return True

    # Zero rows: the spend would have exceeded the allowance.
    if settings.ENTITLEMENTS_ENFORCE:
        # Don't keep the idempotency claim for an action that never ran, or the
        # customer could never retry it after topping up.
        await db.execute(
            text("DELETE FROM ai_usage_events WHERE idempotency_key = :key"),
            {"key": idem_key},
        )
        raise HTTPException(
            status_code=_PAYMENT_REQUIRED,
            detail=(
                "Crediti AI esauriti per il periodo corrente. "
                "Acquista un pacchetto aggiuntivo o effettua l'upgrade del piano."
            ),
        )

    logger.info(
        "WOULD_402 reason=credits org=%s plan=%s detail=need %d of %s allowance kind=%s",
        org_id, ent.plan_code, weight, ent.ai_credits_year, kind,
    )
    return True


async def refund_credits(
    org_id: uuid.UUID, kind: str, idem_key: str, db: AsyncSession, ent: Entitlements
) -> None:
    """Release a reservation whose AI call then failed.

    Charging before the call means a provider error would otherwise bill for
    nothing. Clamped at zero so a double refund can't drive the meter negative.
    """
    if ent.credits_unmetered:
        return
    weight = credit_weight(kind)
    deleted = await db.execute(
        text("DELETE FROM ai_usage_events WHERE idempotency_key = :key RETURNING id"),
        {"key": idem_key},
    )
    if deleted.first() is None:
        # Nothing was charged under this key — nothing to give back.
        return
    await db.execute(
        _RELEASE, {"weight": weight, "org": org_id, "period": ent.meter_period_start}
    )


async def is_company_active(
    org_id: uuid.UUID, azienda_id: uuid.UUID, db: AsyncSession, ent: Entitlements
) -> bool:
    """Whether this company already consumed a slot this period."""
    row = (
        await db.execute(
            _IS_ACTIVE,
            {"org": org_id, "azienda": azienda_id, "period": ent.meter_period_start},
        )
    ).first()
    return row is not None


async def count_active_companies(
    org_id: uuid.UUID, db: AsyncSession, ent: Entitlements
) -> int:
    """Client companies activated this period (the Model A meter)."""
    return (
        await db.execute(
            _COUNT_ACTIVE, {"org": org_id, "period": ent.meter_period_start}
        )
    ).scalar() or 0


async def record_active_company(
    org_id: uuid.UUID, azienda_id: uuid.UUID, db: AsyncSession, ent: Entitlements
) -> bool:
    """Mark a company active for this period. Returns True on first activation.

    Called from the worker the moment a document reaches ``completed``, and
    from the other paths that mint completed rows (restore, Google-Doc sync,
    save-edited-version). The composite primary key makes every one of those a
    no-op after the first, so a company is billed once per period however many
    documents it generates.

    This is the *record*. The ceiling is enforced synchronously at the API
    (``gates.ensure_company_slot``) so the user gets a 402 instead of a
    background job that silently fails.
    """
    row = (
        await db.execute(
            _RECORD_ACTIVE_COMPANY,
            {"org": org_id, "azienda": azienda_id, "period": ent.meter_period_start},
        )
    ).first()
    return row is not None


def period_of(ent: Entitlements) -> date:
    """The period key every meter for this org agrees on."""
    return ent.meter_period_start
