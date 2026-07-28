"""Schema guarantees the billing layer depends on, verified against a real DB.

The Phase 2 metering code (MB-2.3/2.4) is built on three SQL behaviors that a
unit test with a mocked session cannot check, and that a future migration could
silently take away:

* a UNIQUE target for every ``ON CONFLICT`` the metering path uses;
* a conditional ``UPDATE`` that matches **zero rows** when a spend would exceed
  the allowance — that zero-row result *is* the 402 (INV-6, INV-7);
* ``organizations.account_type`` defaulting to ``'consultant'`` server-side, so
  an INSERT written before this column existed still grandfathers correctly
  (INV-1).

Skipped when no Postgres is reachable, so the default local run stays
dependency-free. CI provides one (see .github/workflows/backend-ci.yml).

Each test runs in exactly one event loop, engine included: asyncpg connections
are bound to the loop that opened them, so an engine shared across two
``asyncio.run`` calls blows up on the second.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
import uuid
from typing import Any, Callable

import pytest
from sqlalchemy import text

from app.billing.entitlements import resolve_entitlements
from app.db.session import _normalize_async_url

PERIOD = dt.date(2026, 7, 1)

_URL = _normalize_async_url(os.environ["DATABASE_URL"]) if os.environ.get("DATABASE_URL") else None


def _in_one_loop(body: Callable[..., Any], *, needs_org: bool = True) -> Any:
    """Run ``body(session, org_id)`` with a scratch org, all in one event loop."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    async def _go() -> Any:
        engine = create_async_engine(_URL)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        org_id = uuid.uuid4()
        try:
            async with factory() as s:
                if needs_org:
                    await s.execute(
                        text("INSERT INTO organizations (id, name) VALUES (:i, :n)"),
                        {"i": org_id, "n": f"pytest-billing-{org_id}"},
                    )
                    await s.commit()
                return await body(s, org_id)
        finally:
            async with factory() as s:
                # aziende has no ON DELETE on its org FK, so it goes first.
                await s.execute(
                    text("DELETE FROM aziende WHERE organization_id=:o"), {"o": org_id}
                )
                await s.execute(text("DELETE FROM organizations WHERE id=:o"), {"o": org_id})
                await s.commit()
            await engine.dispose()

    return asyncio.run(_go())


def _reachable() -> bool:
    if not _URL:
        return False
    try:
        return _in_one_loop(
            lambda s, _org: s.execute(text("SELECT 1")), needs_org=False
        ) is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _reachable(),
    reason="no reachable Postgres in DATABASE_URL; billing schema checks need one",
)


# --- INV-1 -----------------------------------------------------------------


def test_account_type_defaults_to_consultant_server_side():
    """An INSERT that names no account_type — i.e. every row written before this
    column existed — must come back grandfathered, not NULL."""

    async def body(s, org_id):
        return (
            await s.execute(
                text("SELECT account_type FROM organizations WHERE id=:i"), {"i": org_id}
            )
        ).scalar()

    assert _in_one_loop(body) == "consultant"


def test_resolver_reports_an_org_without_subscription_as_unsubscribed():
    """An org with no `subscriptions` row has never bought anything (MB-6.1).

    This assertion was inverted until MB-6.1: the resolver used to hand such an
    org the fully permissive `A_FOUNDING` fallback, which was the INV-1 safety
    net for a *paying* tenant whose row went missing. Self-serve signup then
    made "no subscription row" the normal state of every new direct tenant, so
    the safety net silently became the product's default — unlimited everything,
    for free, for anyone who registered.

    `_unsubscribed_entitlements` is now distinct from the data-gap fallback:
    not active, no plan, one seat. What makes that safe is migration
    `e7f8a9b0c1d2`, which gave every pre-existing org a real `A_FOUNDING`
    subscription — without it, `ENTITLEMENTS_ENFORCE=true` would 402 the live
    tenant (INV-1).
    """
    async def body(s, org_id):
        return await resolve_entitlements(org_id, s)

    ent = _in_one_loop(body)
    assert ent.plan_code is None
    assert ent.status == "none"
    assert not ent.is_active
    assert not ent.subscribed
    assert ent.seats == 1
    # Not the permissive fallback: that one reports itself active with a
    # 2**31-1 seat count, and confusing the two is how the paywall leaks.
    assert not ent.credits_unmetered


# --- the plan catalogue drives everything (INV-4) --------------------------


def test_resolver_reads_plan_through_the_join():
    async def body(s, org_id):
        await s.execute(
            text(
                """
                INSERT INTO plans (plan_code, model, display_name, price_year_cents,
                                   seats, max_sites, ai_credits_year, allowed_doc_types, features)
                VALUES ('TEST_B','B','Test Base',49000,2,1,500,
                        CAST(:types AS jsonb), CAST('{"data_certa": false}' AS jsonb))
                ON CONFLICT (plan_code) DO NOTHING
                """
            ),
            # Stored uppercase on purpose: the resolver must fold the casing.
            {"types": '["DVR_MASTER","allegato_mmc"]'},
        )
        await s.execute(
            text(
                """
                INSERT INTO subscriptions (id, organization_id, plan_code, status)
                VALUES (:i, :o, 'TEST_B', 'trialing')
                """
            ),
            {"i": uuid.uuid4(), "o": org_id},
        )
        await s.commit()
        return await resolve_entitlements(org_id, s)

    ent = _in_one_loop(body)
    assert ent.plan_code == "TEST_B"
    assert ent.status == "trialing"
    assert ent.max_sites == 1
    assert ent.ai_credits_year == 500
    assert ent.features == {"data_certa": False}
    assert ent.allowed_doc_types == frozenset({"dvr_master", "allegato_mmc"})
    # The doc-type gate this plan implies, in both casings the API might send.
    assert ent.allows_doc_type("dvr_master") and ent.allows_doc_type("DVR_MASTER")
    assert not ent.allows_doc_type("pos")


# --- INV-6 / INV-7: the metering SQL ---------------------------------------

_SPEND = text(
    """
    UPDATE usage_counters
       SET ai_credits_used = ai_credits_used + :w
     WHERE organization_id = :o AND period_start = :p
       AND ai_credits_used + :w <= (:plan + overage_credits)
    RETURNING ai_credits_used
    """
)

_ENSURE_COUNTER = text(
    """
    INSERT INTO usage_counters (id, organization_id, period_start)
    VALUES (:i, :o, :p) ON CONFLICT (organization_id, period_start) DO NOTHING
    """
)


def test_credit_spend_stops_exactly_at_the_allowance():
    async def body(s, org_id):
        # Lazy-create must be idempotent — two racing requests, one row.
        for _ in range(2):
            await s.execute(_ENSURE_COUNTER, {"i": uuid.uuid4(), "o": org_id, "p": PERIOD})
        await s.commit()
        rows = (
            await s.execute(
                text("SELECT count(*) FROM usage_counters WHERE organization_id=:o"),
                {"o": org_id},
            )
        ).scalar()

        args = {"o": org_id, "p": PERIOD, "plan": 100}
        spent = [
            len((await s.execute(_SPEND, {**args, "w": 40})).fetchall()),  # -> 40
            len((await s.execute(_SPEND, {**args, "w": 40})).fetchall()),  # -> 80
            len((await s.execute(_SPEND, {**args, "w": 40})).fetchall()),  # 120: blocked
            len((await s.execute(_SPEND, {**args, "w": 20})).fetchall()),  # -> exactly 100
            len((await s.execute(_SPEND, {**args, "w": 1})).fetchall()),   # 101: blocked
        ]
        used = (
            await s.execute(
                text("SELECT ai_credits_used FROM usage_counters WHERE organization_id=:o"),
                {"o": org_id},
            )
        ).scalar()
        await s.commit()
        return rows, spent, used

    rows, spent, used = _in_one_loop(body)
    assert rows == 1, "ON CONFLICT (organization_id, period_start) has no unique target"
    # A zero-row UPDATE is the 402: the request never reaches OpenAI.
    assert spent == [1, 1, 0, 1, 0]
    assert used == 100, "the meter must land exactly on the allowance, never past it"


def test_overage_credits_extend_the_allowance():
    async def body(s, org_id):
        await s.execute(_ENSURE_COUNTER, {"i": uuid.uuid4(), "o": org_id, "p": PERIOD})
        await s.execute(
            text(
                "UPDATE usage_counters SET ai_credits_used=100, overage_credits=50 "
                "WHERE organization_id=:o"
            ),
            {"o": org_id},
        )
        await s.commit()
        allowed = len(
            (await s.execute(_SPEND, {"o": org_id, "p": PERIOD, "plan": 100, "w": 50})).fetchall()
        )
        await s.commit()
        return allowed

    # Plan allowance is exhausted; a purchased pack must still let the call through.
    assert _in_one_loop(body) == 1


def test_retried_spend_does_not_double_charge():
    stmt = text(
        """
        INSERT INTO ai_usage_events (id, organization_id, kind, weight, idempotency_key)
        VALUES (:i, :o, 'sds', 8, :k) ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING id
        """
    )

    async def body(s, org_id):
        key = f"sds:{uuid.uuid4()}"
        first = (await s.execute(stmt, {"i": uuid.uuid4(), "o": org_id, "k": key})).fetchall()
        # Celery retry / double-click / restore path replays the same key.
        again = (await s.execute(stmt, {"i": uuid.uuid4(), "o": org_id, "k": key})).fetchall()
        await s.commit()
        return len(first), len(again)

    assert _in_one_loop(body) == (1, 0)


def test_every_completion_path_yields_one_active_company_row():
    """generate, restore, gdoc-sync and save-edited-version all mint a completed
    document. The composite PK must collapse them into a single billable row."""

    async def body(s, org_id):
        azienda_id = uuid.uuid4()
        await s.execute(
            text(
                "INSERT INTO aziende (id, organization_id, ragione_sociale, survey_status) "
                "VALUES (:a, :o, 'Cliente Test', 'draft')"
            ),
            {"a": azienda_id, "o": org_id},
        )
        stmt = text(
            """
            INSERT INTO active_company_periods (organization_id, azienda_id, period_start)
            VALUES (:o, :a, :p) ON CONFLICT DO NOTHING
            """
        )
        for _ in range(4):
            await s.execute(stmt, {"o": org_id, "a": azienda_id, "p": PERIOD})
        await s.commit()
        return (
            await s.execute(
                text(
                    "SELECT count(DISTINCT azienda_id) FROM active_company_periods "
                    "WHERE organization_id=:o AND period_start=:p"
                ),
                {"o": org_id, "p": PERIOD},
            )
        ).scalar()

    assert _in_one_loop(body) == 1


# --- the metering helpers themselves (MB-1.5) ------------------------------


def _metered_ent(credits: int | None = 100):
    """An entitlement whose meters key on a fixed period."""
    from app.billing.entitlements import Entitlements

    return Entitlements(
        account_type="consultant",
        plan_code="A_SOLO",
        allowed_doc_types=None,
        seats=1,
        max_companies=2,
        max_sites=None,
        ai_credits_year=credits,
        features={},
        status="active",
        period_start=PERIOD,
    )


def test_spend_credits_charges_once_and_then_402s(monkeypatch):
    """The real helper, not hand-written SQL: a replayed key is free, and the
    request that would exceed the allowance raises rather than calling OpenAI."""
    from app.billing import metering
    from app.config import settings
    from fastapi import HTTPException

    monkeypatch.setattr(settings, "ENTITLEMENTS_ENFORCE", True, raising=False)
    ent = _metered_ent(credits=16)  # exactly two SDS extractions

    async def body(s, org_id):
        key = f"sds:{uuid.uuid4()}"
        first = await metering.spend_credits(org_id, "sds", key, s, ent)
        # Same action replayed (Celery retry): must not charge again.
        replay = await metering.spend_credits(org_id, "sds", key, s, ent)
        # A different action fits exactly.
        second = await metering.spend_credits(org_id, "sds", f"sds:{uuid.uuid4()}", s, ent)
        used = (
            await s.execute(
                text("SELECT ai_credits_used FROM usage_counters WHERE organization_id=:o"),
                {"o": org_id},
            )
        ).scalar()
        # The third exceeds 16 and must raise.
        try:
            await metering.spend_credits(org_id, "sds", f"sds:{uuid.uuid4()}", s, ent)
            raised = None
        except HTTPException as exc:
            raised = exc.status_code
        # A rejected spend must not leave its idempotency claim behind, or the
        # customer could never retry it after buying more credits.
        events = (
            await s.execute(
                text("SELECT count(*) FROM ai_usage_events WHERE organization_id=:o"),
                {"o": org_id},
            )
        ).scalar()
        await s.commit()
        return first, replay, second, used, raised, events

    first, replay, second, used, raised, events = _in_one_loop(body)
    assert (first, replay, second) == (True, True, True)
    assert used == 16, "two 8-credit extractions, the replay charging nothing"
    assert raised == 402
    assert events == 2, "the rejected spend must not keep an idempotency claim"


def test_spend_credits_never_raises_in_shadow_mode(monkeypatch):
    """INV-1: with enforcement off, an exhausted org still gets through."""
    from app.billing import metering
    from app.config import settings

    monkeypatch.setattr(settings, "ENTITLEMENTS_ENFORCE", False, raising=False)
    ent = _metered_ent(credits=1)

    async def body(s, org_id):
        results = [
            await metering.spend_credits(org_id, "sds", f"sds:{i}:{org_id}", s, ent)
            for i in range(3)
        ]
        await s.commit()
        return results

    assert _in_one_loop(body) == [True, True, True]


def test_pooled_plan_skips_metering_entirely(monkeypatch):
    from app.billing import metering
    from app.config import settings

    monkeypatch.setattr(settings, "ENTITLEMENTS_ENFORCE", True, raising=False)
    ent = _metered_ent(credits=None)  # A_ENTERPRISE

    async def body(s, org_id):
        allowed = await metering.spend_credits(org_id, "sds", f"k:{org_id}", s, ent)
        counters = (
            await s.execute(
                text("SELECT count(*) FROM usage_counters WHERE organization_id=:o"),
                {"o": org_id},
            )
        ).scalar()
        await s.commit()
        return allowed, counters

    # Unmetered means no rows written at all, not "a counter that never fills".
    assert _in_one_loop(body) == (True, 0)


def test_refund_releases_a_reservation_whose_call_failed(monkeypatch):
    from app.billing import metering
    from app.config import settings

    monkeypatch.setattr(settings, "ENTITLEMENTS_ENFORCE", True, raising=False)
    ent = _metered_ent(credits=100)

    async def body(s, org_id):
        key = f"sds:{uuid.uuid4()}"
        await metering.spend_credits(org_id, "sds", key, s, ent)
        await metering.refund_credits(org_id, "sds", key, s, ent)
        used = (
            await s.execute(
                text("SELECT ai_credits_used FROM usage_counters WHERE organization_id=:o"),
                {"o": org_id},
            )
        ).scalar()
        # Refunding twice must not drive the meter negative.
        await metering.refund_credits(org_id, "sds", key, s, ent)
        after = (
            await s.execute(
                text("SELECT ai_credits_used FROM usage_counters WHERE organization_id=:o"),
                {"o": org_id},
            )
        ).scalar()
        # The key is free again, so the customer can retry the action.
        retry = await metering.spend_credits(org_id, "sds", key, s, ent)
        await s.commit()
        return used, after, retry

    assert _in_one_loop(body) == (0, 0, True)


def test_active_company_recording_and_counting():
    from app.billing import metering

    ent = _metered_ent()

    async def body(s, org_id):
        az = uuid.uuid4()
        await s.execute(
            text("INSERT INTO aziende (id, organization_id, ragione_sociale, survey_status) "
                 "VALUES (:a, :o, 'Cliente', 'draft')"),
            {"a": az, "o": org_id},
        )
        before = await metering.is_company_active(org_id, az, s, ent)
        first = await metering.record_active_company(org_id, az, s, ent)
        again = await metering.record_active_company(org_id, az, s, ent)
        after = await metering.is_company_active(org_id, az, s, ent)
        count = await metering.count_active_companies(org_id, s, ent)
        await s.commit()
        return before, first, again, after, count

    # First activation is billable; every later completion for the same company
    # in the same period is not.
    assert _in_one_loop(body) == (False, True, False, True, 1)


def test_one_subscription_per_organization():
    insert = text(
        "INSERT INTO subscriptions (id, organization_id, plan_code, status) "
        "VALUES (:i, :o, 'TEST_UNIQ', 'active')"
    )

    async def body(s, org_id):
        await s.execute(
            text(
                "INSERT INTO plans (plan_code, model, display_name) "
                "VALUES ('TEST_UNIQ','A','Uniq') ON CONFLICT (plan_code) DO NOTHING"
            )
        )
        await s.execute(insert, {"i": uuid.uuid4(), "o": org_id})
        await s.commit()
        try:
            await s.execute(insert, {"i": uuid.uuid4(), "o": org_id})
            await s.commit()
            return False
        except Exception:
            await s.rollback()
            return True

    # The resolver's join assumes at most one row; the DB must guarantee it.
    assert _in_one_loop(body) is True


# --- Credit packs (D-14) ---------------------------------------------------


def test_granting_a_pack_extends_the_period_allowance():
    """The write half of `overage_credits`, end to end against real SQL.

    Two properties in one pass: the upsert creates the counter row when the org
    has never spent anything, and a second grant *adds* rather than replaces —
    a customer who buys two packs in a period must get both.
    """
    from app.billing import metering
    from app.billing.entitlements import Entitlements

    async def body(s, org_id):
        ent = Entitlements(
            account_type="consultant",
            plan_code="A_SOLO",
            allowed_doc_types=None,
            seats=1,
            max_companies=15,
            max_sites=None,
            ai_credits_year=100,
            period_start=PERIOD,
        )
        # No counter row exists yet — the upsert has to create it.
        first = await metering.grant_overage_credits(org_id, 500, PERIOD, s)
        second = await metering.grant_overage_credits(org_id, 2_000, PERIOD, s)
        await s.commit()

        # And the spend query must now let a call through that the plan alone
        # would refuse: 100 included + 2,500 purchased.
        summary = await metering.usage_summary(org_id, s, ent)
        spent = await metering.spend_credits(org_id, "sds", f"sds:{uuid.uuid4()}", s, ent)
        await s.commit()
        return first, second, summary, spent

    first, second, summary, spent = _in_one_loop(body)
    assert (first, second) == (500, 2_500), "a second pack must add, not replace"
    assert summary["ai_credits_overage"] == 2_500
    assert summary["ai_credits_allowance"] == 2_600
    assert summary["ai_credits_remaining"] == 2_600
    assert spent is True


def test_a_pack_only_credits_the_period_it_was_bought_in():
    """`overage_credits` is per (org, period) and deliberately does not roll over.

    Pinned because the UI promises exactly this next to the buy button
    ("valgono per il periodo in corso"), and a silent change to the key would
    make that copy wrong in the customer's favour or ours.
    """
    from app.billing import metering

    next_period = dt.date(PERIOD.year + 1, PERIOD.month, PERIOD.day)

    async def body(s, org_id):
        await metering.grant_overage_credits(org_id, 500, PERIOD, s)
        await s.commit()
        rows = (
            await s.execute(
                text(
                    "SELECT period_start, overage_credits FROM usage_counters "
                    "WHERE organization_id=:o ORDER BY period_start"
                ),
                {"o": org_id},
            )
        ).all()
        return [(r[0], r[1]) for r in rows], next_period

    rows, following = _in_one_loop(body)
    assert rows == [(PERIOD, 500)]
    assert all(period != following for period, _ in rows)


def test_one_purchase_row_per_paypal_order():
    """The UNIQUE index is what makes the settle path exactly-once.

    Without it, the browser return and the webhook could each insert their own
    row for the same order and each grant its credits.
    """
    insert = text(
        """
        INSERT INTO credit_purchases
            (id, organization_id, pack_code, credits, amount_cents, paypal_order_id,
             status, period_start)
        VALUES (:i, :o, 'PACK_500', 500, 7900, 'ORDER-DUP', 'pending', :p)
        """
    )

    async def body(s, org_id):
        await s.execute(insert, {"i": uuid.uuid4(), "o": org_id, "p": PERIOD})
        await s.commit()
        try:
            await s.execute(insert, {"i": uuid.uuid4(), "o": org_id, "p": PERIOD})
            await s.commit()
            return False
        except Exception:
            await s.rollback()
            return True

    assert _in_one_loop(body) is True


def test_settling_the_same_order_twice_credits_once():
    """The property the whole credit-pack design exists to guarantee.

    Simulates the real race outcome: the browser's `/credits/capture` and the
    webhook both call `complete_purchase` for one paid order. The first must
    grant and return a receipt; the second must find nothing to do and leave the
    balance alone.
    """
    from app.billing import credits as ledger

    async def body(s, org_id):
        await s.execute(
            text(
                """
                INSERT INTO credit_purchases
                    (id, organization_id, pack_code, credits, amount_cents,
                     paypal_order_id, status, period_start)
                VALUES (:i, :o, 'PACK_2000', 2000, 24900, 'ORDER-ONCE', 'pending', :p)
                """
            ),
            {"i": uuid.uuid4(), "o": org_id, "p": PERIOD},
        )
        await s.commit()

        first = await ledger.complete_purchase("ORDER-ONCE", s)
        await s.commit()
        second = await ledger.complete_purchase("ORDER-ONCE", s)
        await s.commit()

        overage = (
            await s.execute(
                text(
                    "SELECT overage_credits FROM usage_counters "
                    "WHERE organization_id=:o AND period_start=:p"
                ),
                {"o": org_id, "p": PERIOD},
            )
        ).scalar()
        purchased = await ledger.credits_purchased_in_period(org_id, PERIOD, s)
        return first, second, overage, purchased

    first, second, overage, purchased = _in_one_loop(body)
    assert first is not None and first.credits == 2_000
    assert second is None, "the second settle must be a no-op, not a second grant"
    assert overage == 2_000, "the balance must reflect exactly one pack"
    assert purchased == 2_000


def test_settling_an_unknown_order_is_a_no_op():
    """A subscription renewal also arrives as `PAYMENT.CAPTURE.COMPLETED`.

    Its order id matches no `credit_purchases` row, and that must read as
    "nothing to do" rather than as an error that makes PayPal retry forever.
    """
    from app.billing import credits as ledger

    async def body(s, _org_id):
        return await ledger.complete_purchase("ORDER-DOES-NOT-EXIST", s)

    assert _in_one_loop(body) is None


def test_usage_by_kind_reports_the_breakdown():
    """The tracker's "dove sono andati" list, against real rows."""
    from app.billing import metering
    from app.billing.entitlements import Entitlements

    async def body(s, org_id):
        ent = Entitlements(
            account_type="consultant",
            plan_code="A_SOLO",
            allowed_doc_types=None,
            seats=1,
            max_companies=15,
            max_sites=None,
            ai_credits_year=1_000,
            period_start=PERIOD,
        )
        for kind, key in [
            ("sds", "a"),
            ("sds", "b"),
            ("reasoning", "c"),
            ("vision", "d"),
        ]:
            await metering.spend_credits(org_id, kind, f"{kind}:{key}:{org_id}", s, ent)
        await s.commit()
        return await metering.usage_by_kind(org_id, s, ent)

    rows = _in_one_loop(body)
    by_kind = {r["kind"]: r for r in rows}
    # Ordered by credits descending: 16 for two SDS, 4 for vision, 1 reasoning.
    assert [r["kind"] for r in rows] == ["sds", "vision", "reasoning"]
    assert by_kind["sds"] == {"kind": "sds", "actions": 2, "credits": 16}
    assert by_kind["vision"]["credits"] == 4
    assert by_kind["reasoning"]["credits"] == 1
