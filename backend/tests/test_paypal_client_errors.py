"""Every failure out of ``paypal_client`` must arrive as ``PayPalError``.

Written after a production incident on 2026-07-28: `POST
/billing/credits/checkout` answered **500** because the configured client id and
secret were the *live* merchant's while ``PAYPAL_ENV=sandbox``. The OAuth call
401'd, ``resp.raise_for_status()`` raised ``httpx.HTTPStatusError``, and every
endpoint in ``app.api.v1.billing`` catches only ``PayPalError`` — so the
exception went all the way out as an unhandled server error.

The window was short — credit packs shipped at 21:36 UTC and this landed at
22:51, and the only requests inside it were diagnostic probes — but the defect
was never specific to credit packs. `get_access_token` is on the path of every
PayPal call, so `/subscribe`, `/cancel` and `/revise` would each have done the
same the moment a plan became checkoutable. It surfaced on the credit path first
only because that is the one endpoint whose PayPal call was not already
short-circuited by a `409` for an unprovisioned plan.

Two things went wrong, and both are pinned here:

* the customer saw a 500 with no explanation instead of the 502 and the Italian
  message the endpoint was written to return;
* ``checkout_credits`` writes a ``pending`` row in ``credit_purchases`` *before*
  calling PayPal and abandons it in the ``PayPalError`` handler — which never
  ran, so every attempt stranded a row. Confirmed against production either side
  of the fix: the pre-fix attempt is still ``pending``, the post-fix one went to
  ``failed``.

The tests drive the real ``httpx`` code path through a mock transport rather
than stubbing ``get_access_token``, because the bug lived precisely in the gap
between what httpx raises and what the callers catch.
"""

from __future__ import annotations

import ast
from pathlib import Path

import httpx
import pytest

from app.billing import paypal_client

BACKEND = Path(__file__).resolve().parents[1]
BILLING_API = BACKEND / "app" / "api" / "v1" / "billing.py"


@pytest.fixture(autouse=True)
def _configured_and_cold(monkeypatch):
    """Credentials present, token cache empty — every test forces a real fetch."""
    monkeypatch.setattr(paypal_client.settings, "PAYPAL_CLIENT_ID", "test-id")
    monkeypatch.setattr(paypal_client.settings, "PAYPAL_CLIENT_SECRET", "test-secret")
    paypal_client._reset_token_cache_for_tests()
    yield
    paypal_client._reset_token_cache_for_tests()


def _transport(monkeypatch, handler):
    """Route every ``httpx.AsyncClient`` in the module through ``handler``."""
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(paypal_client.httpx, "AsyncClient", factory)


# --- the token fetch -------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [401, 403])
async def test_rejected_credentials_raise_paypalerror_not_httpx(monkeypatch, code):
    """The production bug, in one assertion.

    A 401 from the OAuth endpoint means the configured keys belong to another
    PayPal environment. That is a configuration error we report as a bad
    gateway — never an unhandled exception.
    """
    _transport(
        monkeypatch,
        lambda request: httpx.Response(code, json={"error": "invalid_client"}),
    )

    with pytest.raises(paypal_client.PayPalError) as excinfo:
        await paypal_client.get_access_token()

    assert excinfo.value.status_code == code
    assert "invalid_client" in excinfo.value.body


@pytest.mark.asyncio
async def test_transport_failure_on_the_token_fetch_raises_paypalerror(monkeypatch):
    """A DNS or timeout failure is still a PayPalError, with status_code 0."""

    def boom(request):
        raise httpx.ConnectError("nope", request=request)

    _transport(monkeypatch, boom)

    with pytest.raises(paypal_client.PayPalError) as excinfo:
        await paypal_client.get_access_token()

    assert excinfo.value.status_code == 0
    assert "ConnectError" in excinfo.value.body


@pytest.mark.asyncio
async def test_unset_credentials_still_raise_notconfigured(monkeypatch):
    """Dormant billing stays distinguishable from rejected billing.

    The endpoints answer 503 ("pagamenti non configurati") for one and 502
    ("PayPal non ha potuto…") for the other, so collapsing the two would tell a
    misconfigured production environment that it simply has no payments.
    """
    monkeypatch.setattr(paypal_client.settings, "PAYPAL_CLIENT_ID", "")
    monkeypatch.setattr(paypal_client.settings, "PAYPAL_CLIENT_SECRET", "")

    with pytest.raises(paypal_client.PayPalNotConfigured):
        await paypal_client.get_access_token()


# --- calls made with a valid token -----------------------------------------


@pytest.mark.asyncio
async def test_transport_failure_on_a_commerce_call_raises_paypalerror(monkeypatch):
    """The token succeeds, then the actual API call never lands."""

    def handler(request):
        if request.url.path == paypal_client._TOKEN_PATH:
            return httpx.Response(
                200, json={"access_token": "tok", "expires_in": 32000}
            )
        raise httpx.ReadTimeout("slow", request=request)

    _transport(monkeypatch, handler)

    with pytest.raises(paypal_client.PayPalError) as excinfo:
        await paypal_client.create_order(
            amount_cents=7_900,
            currency="EUR",
            description="test",
            custom_id="org",
            reference_id="ref",
            return_url="https://example.test/ok",
            cancel_url="https://example.test/ko",
            brand_name="N2O DVR",
        )

    assert excinfo.value.status_code == 0
    assert "ReadTimeout" in excinfo.value.body


@pytest.mark.asyncio
async def test_a_valid_token_is_cached_and_reused(monkeypatch):
    """The retry-on-401 path must not turn into a token fetch per request."""
    fetches = 0

    def handler(request):
        nonlocal fetches
        if request.url.path == paypal_client._TOKEN_PATH:
            fetches += 1
            return httpx.Response(
                200, json={"access_token": "tok", "expires_in": 32000}
            )
        return httpx.Response(200, json={"id": "ORDER-1"})

    _transport(monkeypatch, handler)

    await paypal_client.request("GET", "/v2/checkout/orders/ORDER-1")
    await paypal_client.request("GET", "/v2/checkout/orders/ORDER-1")

    assert fetches == 1


# --- the contract the endpoints rely on ------------------------------------


def test_every_paypal_call_site_in_the_api_catches_paypalerror():
    """No endpoint may call PayPal without handling the failure.

    Source-level because the alternative is booting the whole app with a broken
    merchant account. The rule is narrow and mechanical: any `await
    paypal_client.<something>` inside an endpoint sits under a `try` whose
    handler names `PayPalError`.
    """
    tree = ast.parse(BILLING_API.read_text(encoding="utf-8"))

    # Calls that cannot raise PayPalError, so they need no handler at the call
    # site: `is_configured` and the response parsers touch no network, and
    # `verify_webhook_signature` wraps its own request in `except Exception:
    # return False` because an unverifiable event must fail closed rather than
    # make PayPal retry.
    CANNOT_RAISE = {
        "is_configured",
        "approval_link",
        "order_approval_link",
        "order_is_paid",
        "order_reference_id",
        "order_custom_id",
        "verify_webhook_signature",
    }

    unguarded: list[str] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Calls that sit inside a try/except naming PayPalError are fine.
        protected: set[int] = set()
        for node in ast.walk(fn):
            if not isinstance(node, ast.Try):
                continue
            handles = any(
                "PayPalError" in ast.unparse(h.type)
                for h in node.handlers
                if h.type is not None
            ) or any(h.type is None for h in node.handlers)
            if handles:
                for body_node in node.body:
                    for child in ast.walk(body_node):
                        protected.add(id(child))

        for child in ast.walk(fn):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "paypal_client"
                and func.attr not in CANNOT_RAISE
                and id(child) not in protected
            ):
                unguarded.append(f"{fn.name} -> paypal_client.{func.attr}")

    assert not unguarded, (
        "these PayPal calls would escape as a 500 instead of a 502: "
        + ", ".join(unguarded)
    )
