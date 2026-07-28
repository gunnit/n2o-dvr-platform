"""AI credit packs — catalogue, grant semantics, and the exactly-once guard.

Closes the test half of D-14. The property that actually matters is the one the
schema cannot express: a paid order must credit the account **once**, however
many of the two settlement paths (browser return, PayPal webhook) get there.
That guard is `credits.complete_purchase`'s conditional UPDATE, so these tests
pin its shape as well as its arithmetic.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from app.billing import credit_packs
from app.billing import paypal_client

BACKEND = Path(__file__).resolve().parents[1]
CREDITS = BACKEND / "app" / "billing" / "credits.py"
BILLING_API = BACKEND / "app" / "api" / "v1" / "billing.py"
FRONTEND_BILLING = BACKEND.parent / "frontend" / "src" / "lib" / "billing.ts"


# --- The catalogue ---------------------------------------------------------


def test_catalogue_is_valid():
    """Ascending sizes, descending unit price, nothing free or duplicated."""
    credit_packs.validate_catalogue()


def test_prices_match_the_pricing_docs():
    """€79 / €249 / €990, as `docs/pricing/00-FONDAMENTA.md` §7 sells them.

    Pinned literally rather than derived: the pricing docs are the commercial
    authority, and a "harmless" refactor of the catalogue silently repricing a
    pack is exactly the change that must not pass unnoticed.
    """
    assert credit_packs.get_pack("PACK_500")["price_cents"] == 7_900
    assert credit_packs.get_pack("PACK_2000")["price_cents"] == 24_900
    assert credit_packs.get_pack("PACK_10000")["price_cents"] == 99_000

    assert credit_packs.get_pack("PACK_500")["credits"] == 500
    assert credit_packs.get_pack("PACK_2000")["credits"] == 2_000
    assert credit_packs.get_pack("PACK_10000")["credits"] == 10_000


def test_bigger_packs_are_better_value():
    units = [credit_packs.price_per_credit_cents(p) for p in credit_packs.CREDIT_PACKS]
    assert units == sorted(units, reverse=True), (
        "a larger pack must never cost more per credit than a smaller one"
    )


def test_lookup_is_case_insensitive_and_safe_on_junk():
    assert credit_packs.get_pack("pack_500") is credit_packs.get_pack("PACK_500")
    assert credit_packs.get_pack("  pack_2000  ") is credit_packs.get_pack("PACK_2000")
    assert credit_packs.get_pack("PACK_999") is None
    assert credit_packs.get_pack(None) is None
    assert credit_packs.get_pack("") is None


def test_exactly_one_pack_is_recommended():
    """The UI renders one highlighted card; two would be a design bug."""
    recommended = [p for p in credit_packs.CREDIT_PACKS if p.get("recommended")]
    assert len(recommended) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        {"pack_code": "PACK_500", "credits": 100, "price_cents": 100},  # duplicate code
        {"pack_code": "PACK_FREE", "credits": 100, "price_cents": 0},  # free
        {"pack_code": "PACK_TINY", "credits": 1, "price_cents": 100},  # out of order
        {"pack_code": "pack_lower", "credits": 99_999, "price_cents": 1},  # lowercase
    ],
)
def test_validator_rejects_a_broken_catalogue(monkeypatch, mutation):
    broken = credit_packs.CREDIT_PACKS + [
        {"display_name": "x", "description": "x", **mutation}
    ]
    monkeypatch.setattr(credit_packs, "CREDIT_PACKS", broken)
    with pytest.raises(ValueError):
        credit_packs.validate_catalogue()


def test_validator_rejects_a_pack_that_is_worse_value(monkeypatch):
    """The one commercial error nobody notices until a customer does the maths."""
    broken = credit_packs.CREDIT_PACKS + [
        {
            "pack_code": "PACK_20000",
            "display_name": "20.000 crediti",
            "credits": 20_000,
            # 10c/credit against the 10.000 pack's 9.9c — a bad deal.
            "price_cents": 200_000,
            "description": "x",
        }
    ]
    monkeypatch.setattr(credit_packs, "CREDIT_PACKS", broken)
    with pytest.raises(ValueError, match="worse value"):
        credit_packs.validate_catalogue()


# --- PayPal order helpers --------------------------------------------------


def test_order_is_paid_reads_both_levels():
    """An order can be COMPLETED at the top or only in its capture.

    The second shape happens when we read an order in the same instant it is
    captured. Refusing to grant there would withhold credits for a payment that
    demonstrably went through, so both are accepted.
    """
    assert paypal_client.order_is_paid({"status": "COMPLETED"})
    assert paypal_client.order_is_paid(
        {
            "status": "APPROVED",
            "purchase_units": [{"payments": {"captures": [{"status": "COMPLETED"}]}}],
        }
    )
    # Approved but never captured is not paid — granting here would be giving
    # the product away.
    assert not paypal_client.order_is_paid({"status": "APPROVED"})
    assert not paypal_client.order_is_paid(
        {
            "status": "APPROVED",
            "purchase_units": [{"payments": {"captures": [{"status": "PENDING"}]}}],
        }
    )
    assert not paypal_client.order_is_paid({})


def test_reference_id_round_trips_our_purchase_id():
    resource = {"purchase_units": [{"reference_id": "abc-123"}]}
    assert paypal_client.order_reference_id(resource) == "abc-123"
    assert paypal_client.order_reference_id({"purchase_units": [{}]}) is None
    assert paypal_client.order_reference_id({}) is None


def test_capture_webhook_resolves_the_order_id():
    """A `PAYMENT.CAPTURE.COMPLETED` resource's own id is the *capture* id.

    Using it to look up a purchase would match nothing and silently drop every
    webhook-settled top-up, so the order id has to come out of
    `supplementary_data` (or the `up` link as a fallback).
    """
    from app.api.v1.billing import _order_id_of_capture

    assert (
        _order_id_of_capture(
            {
                "id": "CAPTURE-1",
                "supplementary_data": {"related_ids": {"order_id": "ORDER-9"}},
            }
        )
        == "ORDER-9"
    )
    assert (
        _order_id_of_capture(
            {
                "id": "CAPTURE-1",
                "links": [
                    {"rel": "self", "href": "https://api.paypal.com/v2/payments/captures/CAPTURE-1"},
                    {"rel": "up", "href": "https://api.paypal.com/v2/checkout/orders/ORDER-9"},
                ],
            }
        )
        == "ORDER-9"
    )
    # A subscription renewal also arrives as a capture and carries neither —
    # answering None makes the webhook a no-op instead of a mismatch.
    assert _order_id_of_capture({"id": "CAPTURE-1"}) is None


# --- The exactly-once guard (structural) -----------------------------------


def test_grant_happens_only_behind_the_status_flip():
    """`grant_overage_credits` has exactly one caller: `complete_purchase`.

    The grant itself is deliberately not idempotent — two customers buying the
    same pack in the same second must both be credited — so its safety comes
    entirely from being reachable only through the conditional status update.
    A second call site anywhere would be a way to credit an account twice.
    """
    app_dir = BACKEND / "app"
    callers: list[str] = []
    for path in app_dir.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "grant_overage_credits"
            ):
                callers.append(f"{path.relative_to(BACKEND)}:{node.lineno}")

    assert len(callers) == 1, f"expected one grant site, found {callers}"
    assert callers[0].startswith("app/billing/credits.py"), callers


def test_complete_purchase_locks_on_pending():
    """The settle path must test `status == pending` under a row lock.

    Without `with_for_update`, the browser return and the webhook can both read
    `pending` before either writes, and the same payment credits twice. This
    reads the source because the race needs two concurrent sessions to
    reproduce and a unit test that "passes" by never interleaving proves
    nothing.
    """
    source = CREDITS.read_text(encoding="utf-8")
    body = source[source.index("async def complete_purchase") :]
    body = body[: body.index("\nasync def ") if "\nasync def " in body else len(body)]

    assert "STATUS_PENDING" in body, "the settle path must filter on pending"
    assert "with_for_update" in body, "the pending check must hold a row lock"
    assert "STATUS_COMPLETED" in body


def test_checkout_requires_a_live_metered_subscription():
    """Packs extend an allowance; they are not a way to buy AI without a plan.

    Selling one to an unsubscribed tenant hands them credits that
    `ensure_subscription_active` still refuses to let them use, and selling one
    to a pooled (Enterprise) tenant sells a ceiling raise where there is no
    ceiling.
    """
    source = BILLING_API.read_text(encoding="utf-8")
    body = source[source.index("async def checkout_credits") :]
    body = body[: body.index("\n@router.")]

    assert "ent.subscribed" in body
    assert "ent.is_active" in body
    assert "ent.credits_unmetered" in body


def test_purchase_row_is_written_before_paypal_is_called():
    """A paid order we cannot map back to a purchase has no automatic recovery.

    `reference_id` carries our row id into PayPal, which means the row must
    exist first. The ordering is the whole reason `start_purchase` is separate
    from `attach_order`.
    """
    source = BILLING_API.read_text(encoding="utf-8")
    body = source[source.index("async def checkout_credits") :]
    body = body[: body.index("\n@router.")]

    assert body.index("start_purchase") < body.index("create_order"), (
        "the pending purchase row must be committed before PayPal opens the order"
    )


def test_frontend_pack_type_matches_the_api_shape():
    """`CreditPack` in the frontend names every field the endpoint returns."""
    if not FRONTEND_BILLING.exists():  # pragma: no cover — backend-only checkout
        pytest.skip("frontend not present in this checkout")

    source = FRONTEND_BILLING.read_text(encoding="utf-8")
    block = re.search(r"export type CreditPack = \{(.*?)\};", source, re.S)
    assert block, "CreditPack type not found"
    fields = set(re.findall(r"^\s*(\w+):", block.group(1), re.M))

    api = BILLING_API.read_text(encoding="utf-8")
    api_block = re.search(r"class CreditPackOut\(BaseModel\):(.*?)\n\n\n", api, re.S)
    assert api_block, "CreditPackOut not found"
    api_fields = set(re.findall(r"^\s{4}(\w+):", api_block.group(1), re.M))

    assert api_fields <= fields, (
        f"frontend CreditPack is missing: {sorted(api_fields - fields)}"
    )
