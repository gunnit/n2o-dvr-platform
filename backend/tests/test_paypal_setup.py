"""MB-4.1 — the PayPal catalogue bodies we send, checked without a network.

Every assertion here is about a value PayPal charges money on, or a guardrail
that keeps an unsellable plan unsellable. The HTTP plumbing is not covered;
the parts that would silently overcharge or mis-list a plan are.
"""

from __future__ import annotations

import pytest

from app.billing.plan_catalogue import PLANS_BY_CODE
from scripts.paypal_setup import (
    CURRENCY,
    IVA_PERCENTAGE,
    euro,
    plan_body,
    plan_name,
    prices_differ,
    sellable_plans,
)


@pytest.mark.parametrize(
    "cents,expected",
    [
        (149_000, "1490.00"),
        (390_000, "3900.00"),
        (1_800_000, "18000.00"),
        (49_000, "490.00"),
        # Cents must survive: a plan priced at €490.50 must not become €490.5,
        # which PayPal reads as a different amount.
        (49_050, "490.50"),
        (5, "0.05"),
    ],
)
def test_euro_formats_cents_as_a_paypal_decimal_string(cents, expected):
    assert euro(cents) == expected


def test_every_catalogue_price_round_trips_through_euro():
    """The string we send must equal the cents we hold, to the cent."""
    for plan in PLANS_BY_CODE.values():
        assert round(float(euro(plan["price_year_cents"])) * 100) == plan["price_year_cents"]


def test_founding_row_gets_no_paypal_plan():
    """A_FOUNDING is the €0 grandfather row (MB-1.3) — never sold."""
    codes = {p["plan_code"] for p in sellable_plans()}
    assert "A_FOUNDING" not in codes
    assert len(codes) == 7, codes


def test_sellable_plans_are_all_priced():
    assert all(p["price_year_cents"] > 0 for p in sellable_plans())


def test_plan_names_are_unique():
    """Name is the idempotency key when the stored id is missing — a collision
    would make two catalogue rows resolve to the same PayPal plan."""
    names = [plan_name(p) for p in sellable_plans()]
    assert len(set(names)) == len(names), names


def test_plan_body_prices_annually_and_forever():
    body = plan_body(PLANS_BY_CODE["A_STUDIO"], "PROD-X")
    (cycle,) = body["billing_cycles"]
    assert cycle["tenure_type"] == "REGULAR"
    assert cycle["frequency"] == {"interval_unit": "YEAR", "interval_count": 1}
    # 0 = until cancelled. A finite count would stop billing a live customer.
    assert cycle["total_cycles"] == 0
    assert cycle["pricing_scheme"]["fixed_price"] == {
        "value": "3900.00",
        "currency_code": CURRENCY,
    }


def test_plan_body_applies_iva_exclusively():
    """Catalogue prices are ex-IVA; an inclusive tax would silently cut revenue 22%."""
    body = plan_body(PLANS_BY_CODE["A_SOLO"], "PROD-X")
    assert body["taxes"] == {"percentage": IVA_PERCENTAGE, "inclusive": False}


def test_plan_body_carries_no_setup_fee():
    """Setup fees are one-time checkout line items (§5), not plan fields — a
    PayPal setup_fee would be charged on every subscription from this plan."""
    assert "setup_fee" not in body_payment_prefs("A_SOLO")


def body_payment_prefs(code: str) -> dict:
    return plan_body(PLANS_BY_CODE[code], "PROD-X")["payment_preferences"]


@pytest.mark.parametrize("code", ["A_SOLO", "A_STUDIO", "A_NETWORK", "A_ENTERPRISE"])
def test_model_a_plans_are_created_active(code):
    assert plan_body(PLANS_BY_CODE[code], "PROD-X")["status"] == "ACTIVE"


@pytest.mark.parametrize("code", ["B_BASE", "B_PLUS", "B_MULTISEDE"])
def test_model_b_plans_are_not_subscribable_before_phase_5(code):
    """INV-9 / OPEN-DECISION-1: Model B is seeded inactive. The PayPal plan must
    mirror that, so a leaked plan id still cannot be subscribed to."""
    assert PLANS_BY_CODE[code]["active"] is False
    assert plan_body(PLANS_BY_CODE[code], "PROD-X")["status"] == "CREATED"


@pytest.mark.parametrize(
    "have,want,differs",
    [
        # PayPal stores what we send but reads back trailing-zero-trimmed. This
        # is not drift, and treating it as such made every re-run warn on all 7
        # plans (and would have repriced them on every --update-pricing run).
        ("1490.0", "1490.00", False),
        ("18000.0", "18000.00", False),
        ("490", "490.00", False),
        # Genuine changes must still be caught.
        ("1490.00", "1590.00", True),
        ("490.00", "490.50", True),
        # Nothing to compare against — not drift.
        (None, "1490.00", False),
        # Unparseable is surfaced rather than silently ignored.
        ("not-a-number", "1490.00", True),
    ],
)
def test_prices_differ_compares_numerically(have, want, differs):
    assert prices_differ(have, want) is differs


def test_plan_description_fits_paypals_limit_and_names_the_code():
    for plan in sellable_plans():
        body = plan_body(plan, "PROD-X")
        assert len(body["description"]) <= 127, body["description"]
        assert plan["plan_code"] in body["description"]
        assert len(body["name"]) <= 127
