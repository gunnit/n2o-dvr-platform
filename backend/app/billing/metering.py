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
from contextlib import asynccontextmanager
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select, text
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


def _denial_detail(ent: Entitlements) -> str:
    """Why the spend was refused, in terms the operator can act on.

    Three different states all fail the same allowance test, and until now
    they all said "crediti esauriti":

    * **No subscription resolved.** ``no_subscription`` sets
      ``ai_credits_year=0`` deliberately (MB-6.2) so an unsubscribed tenant
      cannot spend our OpenAI budget. Zero allowance means the very first
      credit is refused. The AI endpoints meter but never call
      ``ensure_subscription_active``, so this branch — not the subscription
      gate — is what actually speaks to the operator, and "hai finito i
      crediti" is simply false: nothing was ever granted to finish.
    * **Lapsed subscription.** Credits were granted, the period is over.
    * **Genuinely exhausted.** The only case the old wording described.

    A segnalazione on 2026-07-31 read "MI DICE CHE HO FINITO I CREDITI MA IN
    REALTA' LI HO", days after the billing rollout. With one message for
    three causes there was no way to tell from the report which had fired.
    Naming the state makes the next occurrence self-diagnosing, and points
    the first two at the fix that actually helps.
    """
    if not ent.subscribed:
        return (
            "Nessun piano attivo per questa organizzazione, quindi non ci sono "
            "crediti AI disponibili. Se hai già sottoscritto un piano, ricarica "
            "la pagina tra un minuto: la conferma del pagamento potrebbe non "
            "essere ancora arrivata. Altrimenti attiva un piano per continuare."
        )
    if not ent.is_active:
        return (
            f"L'abbonamento non è attivo (stato: {ent.status}), quindi i crediti "
            "AI non sono utilizzabili. Rinnova il piano per riprendere a usare "
            "le funzioni AI. I documenti già generati restano consultabili e "
            "scaricabili."
        )
    return (
        "Crediti AI esauriti per il periodo corrente. "
        "Acquista un pacchetto aggiuntivo o effettua l'upgrade del piano."
    )


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
        logger.info(
            "402 reason=credits org=%s plan=%s status=%s subscribed=%s "
            "detail=need %d of %s allowance kind=%s",
            org_id, ent.plan_code, ent.status, ent.subscribed,
            weight, ent.ai_credits_year, kind,
        )
        raise HTTPException(
            status_code=_PAYMENT_REQUIRED,
            detail=_denial_detail(ent),
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


@asynccontextmanager
async def metered(
    org_id: uuid.UUID,
    kind: str,
    idem_key: str,
    db: AsyncSession,
    ent: Entitlements,
):
    """Charge for one AI action, releasing the charge if the call fails.

        async with metered(org_id, "reasoning", f"misure:{rischio_id}", db, ent):
            misure = await suggest_measures(rischio)

    Reserves before the body runs (INV-7 — a 402 is raised before the provider
    is contacted), releases on exception, and **commits either way**. The commit
    matters: most suggester endpoints are otherwise read-only and never commit,
    so without it the ledger and counter writes would be discarded when the
    request's session closes and the customer would be using AI for free.
    """
    await spend_credits(org_id, kind, idem_key, db, ent)
    try:
        yield
    except Exception:
        # The work never happened — give the credits back rather than bill for
        # a provider outage.
        await refund_credits(org_id, kind, idem_key, db, ent)
        await db.commit()
        raise
    await db.commit()


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


async def record_activation_for_azienda(azienda_id: uuid.UUID, db: AsyncSession) -> bool:
    """Resolve the owning org and mark the company active for its period.

    The one entry point every completion path uses — the Celery worker when a
    generation finishes, and the API when ``restore``, ``sync-from-gdoc`` or
    ``save-edited-version`` mints a completed row directly. Each resolves the
    org itself, so callers need only the azienda.

    **Best-effort by design.** A metering failure must never fail a document:
    the document is the legally-required product, the meter is an accounting
    record that can be reconciled. The ceiling is enforced at the API
    (``gates.ensure_company_slot``), not here.

    Returns True if this was the company's first activation of the period.
    """
    from app.billing.entitlements import resolve_entitlements
    from app.models.azienda import Azienda

    try:
        org_id = (
            await db.execute(
                select(Azienda.organization_id).where(Azienda.id == azienda_id)
            )
        ).scalar_one_or_none()
        if org_id is None:
            return False
        ent = await resolve_entitlements(org_id, db)
        first = await record_active_company(org_id, azienda_id, db, ent)
        await db.commit()
        if first:
            logger.info(
                "billing: azienda %s activated for org %s period %s",
                azienda_id, org_id, ent.meter_period_start,
            )
        return first
    except Exception:  # pragma: no cover — never break a document over billing
        logger.exception("billing: failed to record activation for azienda %s", azienda_id)
        try:
            await db.rollback()
        except Exception:
            pass
        return False


_GRANT_OVERAGE = text(
    """
    INSERT INTO usage_counters (id, organization_id, period_start, overage_credits)
    VALUES (gen_random_uuid(), :org, :period, :credits)
    ON CONFLICT (organization_id, period_start)
    DO UPDATE SET overage_credits = usage_counters.overage_credits + :credits,
                  updated_at = now()
    RETURNING overage_credits
    """
)


async def grant_overage_credits(
    org_id: uuid.UUID, credits: int, period: date, db: AsyncSession
) -> int:
    """Add purchased credits to a period's allowance. Returns the new total.

    The write half of ``usage_counters.overage_credits``, which the spend query
    has read since Phase 0 and nothing has ever written (D-14). A single upsert,
    so it is safe against a concurrent first spend creating the counter row.

    Deliberately **not** idempotent on its own: two identical calls grant twice,
    because two customers buying the same pack in the same second is a real
    thing that must credit both. Exactly-once is the caller's job and belongs
    where the natural key is — the ``credit_purchases.status`` flip in
    ``api/v1/billing.py``. Do not call this from anywhere that lacks that guard.

    ``period`` is passed rather than taken from an ``Entitlements`` so the
    webhook path, which resolves entitlements for a tenant that is not the
    request's own, cannot silently credit the wrong meter.
    """
    total = (
        await db.execute(
            _GRANT_OVERAGE, {"org": org_id, "period": period, "credits": credits}
        )
    ).scalar_one()
    logger.info(
        "billing: granted %d overage credits to org %s for period %s (now %d)",
        credits, org_id, period, total,
    )
    return int(total)


_USAGE = text(
    """
    SELECT ai_credits_used, overage_credits
      FROM usage_counters
     WHERE organization_id = :org AND period_start = :period
    """
)


async def usage_summary(
    org_id: uuid.UUID, db: AsyncSession, ent: Entitlements
) -> dict[str, int | None]:
    """Current-period consumption, for the billing screen (MB-3.3).

    Read-only and safe to call on every page load. A missing counter row means
    the org has not spent anything this period, which reads as zero rather than
    as an error — the row is created lazily on first spend.
    """
    row = (
        await db.execute(_USAGE, {"org": org_id, "period": ent.meter_period_start})
    ).first()
    used, overage = (row[0], row[1]) if row is not None else (0, 0)

    allowance: int | None = None
    remaining: int | None = None
    if not ent.credits_unmetered and ent.ai_credits_year is not None:
        allowance = ent.ai_credits_year + (overage or 0)
        remaining = max(0, allowance - (used or 0))

    return {
        "ai_credits_used": used or 0,
        "ai_credits_included": ent.ai_credits_year,
        "ai_credits_overage": overage or 0,
        # None = pooled/unmetered (A_ENTERPRISE); the UI shows "illimitato".
        "ai_credits_allowance": allowance,
        "ai_credits_remaining": remaining,
        "active_companies": await count_active_companies(org_id, db, ent),
        "max_companies": ent.max_companies,
    }


_USAGE_BY_KIND = text(
    """
    SELECT kind, count(*) AS actions, coalesce(sum(weight), 0) AS credits
      FROM ai_usage_events
     WHERE organization_id = :org
       AND created_at >= :period
     GROUP BY kind
     ORDER BY credits DESC
    """
)


async def usage_by_kind(
    org_id: uuid.UUID, db: AsyncSession, ent: Entitlements
) -> list[dict[str, int | str]]:
    """Where this period's credits went, one row per action type.

    Answers the question the single "1.240 / 2.500" number cannot: *what* is
    burning the allowance. An SDS extraction costs eight times a measure
    suggestion, so "you have used half your credits" is not actionable on its
    own — "you have used half your credits, 80% of them on schede di sicurezza"
    is.

    Dated from ``created_at`` rather than a period column, because
    ``ai_usage_events`` deliberately has none: the row is an idempotency claim
    first and a ledger entry second. That makes this a *reporting* query, not
    a metering one — the authoritative balance is always ``usage_counters``,
    which is what the spend path reads. The two agree except across a renewal
    boundary, where a refunded-and-re-spent action could shift a row by a day;
    that is acceptable for a breakdown chart and unacceptable for a balance,
    which is why they are separate queries.
    """
    rows = (
        await db.execute(_USAGE_BY_KIND, {"org": org_id, "period": ent.meter_period_start})
    ).all()
    return [
        {"kind": row[0], "actions": int(row[1]), "credits": int(row[2])} for row in rows
    ]


def period_of(ent: Entitlements) -> date:
    """The period key every meter for this org agrees on."""
    return ent.meter_period_start
