"""Entitlement resolver tests (MB-0.9).

The resolver decides whether a paying customer may generate a legally-required
document, so its two failure modes matter more than its happy path:

* it must never raise — an org with no subscription row gets a permissive
  fallback, not a 500 or a 402 (INV-1);
* it must never trust the caller's casing — the wire form of
  ``tipo_documento`` is lowercase while the dispatcher registry is uppercase.

No pytest-asyncio in this repo's environment, so coroutines are driven with
``asyncio.run`` rather than a marker that would silently not run.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import uuid
from datetime import date, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.billing.constants import ALL_DOC_TYPES, CREDIT_WEIGHTS, normalize_doc_type
from app.billing.entitlements import (
    Entitlements,
    build_entitlements_query,
    resolve_entitlements,
)

ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


class _FakeResult:
    def __init__(self, row: Any) -> None:
        self._row = row

    def first(self) -> Any:
        return self._row


class _FakeSession:
    """Minimal stand-in for AsyncSession: the resolver only executes one SELECT."""

    def __init__(self, row: Any) -> None:
        self._row = row
        self.executed = 0

    async def execute(self, _stmt: Any) -> _FakeResult:
        self.executed += 1
        return _FakeResult(self._row)


def _plan(**overrides: Any) -> Any:
    defaults: dict[str, Any] = dict(
        plan_code="A_STUDIO",
        model="A",
        display_name="Studio",
        price_year_cents=390000,
        seats=5,
        max_companies=60,
        max_sites=None,
        ai_credits_year=9000,
        allowed_doc_types=None,
        features={"api": "read"},
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _subscription(**overrides: Any) -> Any:
    defaults: dict[str, Any] = dict(
        plan_code="A_STUDIO",
        status="active",
        current_period_start=datetime(2026, 4, 1),
        current_period_end=datetime(2029, 4, 1),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _resolve(row: Any) -> Entitlements:
    return asyncio.run(resolve_entitlements(ORG_ID, _FakeSession(row)))


# --- constants -------------------------------------------------------------


def test_all_doc_types_is_the_seventeen_lowercase_wire_forms():
    # The canary in constants.py already asserts the count at import; this
    # pins the *form*, which is what entitlement comparisons depend on.
    assert len(ALL_DOC_TYPES) == 17
    assert all(t == t.lower() for t in ALL_DOC_TYPES)
    assert "dvr_master" in ALL_DOC_TYPES
    assert "DVR_MASTER" not in ALL_DOC_TYPES


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("DVR_MASTER", "dvr_master"),
        ("dvr_master", "dvr_master"),
        ("Allegato-MMC", "allegato_mmc"),
        ("  pos  ", "pos"),
        (None, ""),
        ("", ""),
    ],
)
def test_normalize_doc_type(raw, expected):
    assert normalize_doc_type(raw) == expected


def test_credit_weights_are_the_documented_scale():
    assert CREDIT_WEIGHTS == {"reasoning": 1, "vision": 4, "sds": 8, "visura": 15}


# --- happy path ------------------------------------------------------------


def test_model_a_plan_resolves_with_no_doc_type_restriction():
    ent = _resolve(("consultant", _subscription(), _plan()))

    assert ent.plan_code == "A_STUDIO"
    assert ent.account_type == "consultant"
    assert ent.seats == 5
    assert ent.max_companies == 60
    assert ent.ai_credits_year == 9000
    assert ent.features == {"api": "read"}
    # NULL allowed_doc_types means all 17, not "none".
    assert ent.allowed_doc_types is None
    assert all(ent.allows_doc_type(t) for t in ALL_DOC_TYPES)
    # Meters key on the subscription period, not the calendar month.
    assert ent.period_start == date(2026, 4, 1)
    assert ent.meter_period_start == date(2026, 4, 1)


def test_model_b_plan_restricts_doc_types_and_normalizes_casing():
    row = (
        "direct",
        _subscription(plan_code="B_BASE", status="trialing"),
        _plan(
            plan_code="B_BASE",
            model="B",
            seats=2,
            max_companies=None,
            max_sites=1,
            ai_credits_year=500,
            # Stored uppercase on purpose: the resolver must fold it.
            allowed_doc_types=["DVR_MASTER", "allegato_mmc"],
            features={},
        ),
    )
    ent = _resolve(row)

    assert ent.account_type == "direct"
    assert ent.max_sites == 1
    assert ent.allowed_doc_types == frozenset({"dvr_master", "allegato_mmc"})
    # Entitled, in either casing the caller happens to send.
    assert ent.allows_doc_type("dvr_master")
    assert ent.allows_doc_type("DVR_MASTER")
    assert ent.allows_doc_type("allegato-mmc")
    # Not entitled — this is the channel-conflict guardrail (INV-9).
    assert not ent.allows_doc_type("pos")
    assert not ent.allows_doc_type("haccp")


def test_pooled_credits_plan_is_unmetered():
    ent = _resolve(("consultant", _subscription(plan_code="A_ENTERPRISE"),
                    _plan(plan_code="A_ENTERPRISE", ai_credits_year=None, max_companies=None)))
    assert ent.credits_unmetered is True
    assert ent.max_companies is None


def test_null_features_becomes_an_empty_dict():
    ent = _resolve(("consultant", _subscription(), _plan(features=None)))
    assert ent.features == {}
    assert ent.feature("api", "none") == "none"


# --- INV-1: never lock anyone out -----------------------------------------


def test_org_without_subscription_gets_permissive_fallback(caplog):
    with caplog.at_level(logging.WARNING):
        ent = _resolve(("consultant", None, None))

    assert ent.plan_code == "A_FOUNDING"
    assert ent.account_type == "consultant"
    # Fully permissive: a data gap must not 402 a paying tenant.
    assert ent.allowed_doc_types is None
    assert ent.max_companies is None
    assert ent.max_sites is None
    assert ent.credits_unmetered is True
    assert ent.is_active
    assert all(ent.allows_doc_type(t) for t in ALL_DOC_TYPES)
    # ...but loudly, so the missing row gets fixed.
    assert any("no resolvable subscription" in r.getMessage() for r in caplog.records)


def test_fallback_preserves_account_type():
    ent = _resolve(("direct", None, None))
    assert ent.account_type == "direct"
    assert ent.plan_code == "A_FOUNDING"


def test_missing_organization_does_not_raise(caplog):
    with caplog.at_level(logging.WARNING):
        ent = _resolve(None)
    assert ent.plan_code == "A_FOUNDING"
    assert ent.allowed_doc_types is None


def test_subscription_without_plan_row_falls_back():
    # FK makes this unreachable in practice; the resolver still must not blow up.
    ent = _resolve(("consultant", _subscription(plan_code="GHOST"), None))
    assert ent.plan_code == "A_FOUNDING"
    assert ent.allowed_doc_types is None


def test_null_account_type_defaults_to_consultant():
    ent = _resolve((None, _subscription(), _plan()))
    assert ent.account_type == "consultant"


# --- status semantics ------------------------------------------------------


@pytest.mark.parametrize(
    "status,active",
    [
        ("active", True),
        ("trialing", True),
        # Dunning grace: Stripe Smart Retries run for days and a customer must
        # not lose access to their DVR mid-retry. Read-only comes at MB-4.5.
        ("past_due", True),
        ("canceled", False),
    ],
)
def test_is_active_by_status(status, active):
    ent = _resolve(("consultant", _subscription(status=status), _plan()))
    assert ent.status == status
    assert ent.is_active is active


# --- shape -----------------------------------------------------------------


def test_entitlements_are_immutable():
    ent = _resolve(("consultant", _subscription(), _plan()))
    with pytest.raises(dataclasses.FrozenInstanceError):
        ent.seats = 999  # type: ignore[misc]


def test_query_compiles_to_valid_postgres_with_outer_joins():
    """The resolver's SELECT is never executed in these tests (the session is
    faked), so compile it against the real Postgres dialect to catch a malformed
    join or a column that does not exist."""
    from sqlalchemy.dialects import postgresql

    sql = str(
        build_entitlements_query(ORG_ID).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    compact = " ".join(sql.split())

    assert "FROM organizations" in compact
    # LEFT joins, not inner: an org with no subscription must still return a
    # row so the resolver can tell "missing org" from "missing subscription".
    assert compact.count("LEFT OUTER JOIN") == 2
    assert "LEFT OUTER JOIN subscriptions ON subscriptions.organization_id = organizations.id" in compact
    assert "LEFT OUTER JOIN plans ON plans.plan_code = subscriptions.plan_code" in compact
    # Tenant scoping is in the query itself, not applied by the caller.
    assert f"WHERE organizations.id = '{ORG_ID}'" in compact
    # Selects the org's account_type plus both entities, in the order the
    # resolver unpacks them.
    assert compact.index("organizations.account_type") < compact.index("subscriptions.id")
    assert compact.index("subscriptions.id") < compact.index("plans.plan_code")


def test_resolver_issues_a_single_query():
    session = _FakeSession(("consultant", _subscription(), _plan()))
    asyncio.run(resolve_entitlements(ORG_ID, session))
    # Resolution runs on every request (INV-3); it must stay one round trip.
    assert session.executed == 1
