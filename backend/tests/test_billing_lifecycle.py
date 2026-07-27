"""Subscription lifecycle mapping and webhook trust, without a network.

Everything here decides either (a) what state a customer ends up in, or (b)
whether we believe an event at all. Both are places where a quiet mistake is
expensive: a wrong mapping downgrades a paying tenant, and a lenient signature
check lets anyone grant themselves a plan.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.billing import paypal_client
from app.billing.lifecycle import map_status, period_bounds
from app.billing.paypal_client import _cert_url_is_trusted, approval_link
from app.config import settings


# --- PayPal status -> ours -------------------------------------------------


@pytest.mark.parametrize(
    "paypal,ours",
    [
        ("APPROVAL_PENDING", "trialing"),
        ("APPROVED", "trialing"),
        ("ACTIVE", "active"),
        ("SUSPENDED", "past_due"),
        ("CANCELLED", "canceled"),
        ("EXPIRED", "canceled"),
        # Case is normalised — PayPal has been known to vary it.
        ("active", "active"),
    ],
)
def test_status_mapping(paypal, ours):
    assert map_status(paypal) == ours


@pytest.mark.parametrize("value", [None, "", "SOMETHING_NEW"])
def test_unknown_status_maps_to_none_rather_than_guessing(value):
    """An unrecognised status must leave the row alone.

    Defaulting to anything — especially `canceled` — would let a new PayPal
    state silently cut off a paying customer.
    """
    assert map_status(value) is None


def test_our_statuses_are_all_reachable():
    from app.billing.constants import SUBSCRIPTION_STATUSES

    produced = {map_status(s) for s in
                ("APPROVAL_PENDING", "ACTIVE", "SUSPENDED", "CANCELLED")}
    assert produced == SUBSCRIPTION_STATUSES


# --- period bounds ---------------------------------------------------------


def test_period_start_prefers_last_payment_over_subscription_start():
    """The meters key on period_start, so it must roll forward on renewal.

    Using start_time forever would keep a customer in year one's period and
    never refresh their credit allowance.
    """
    start, end = period_bounds(
        {
            "start_time": "2025-01-01T00:00:00Z",
            "billing_info": {
                "last_payment": {"time": "2026-01-01T00:00:00Z"},
                "next_billing_time": "2027-01-01T00:00:00Z",
            },
        }
    )
    assert start == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert end == datetime(2027, 1, 1, tzinfo=timezone.utc)


def test_period_start_falls_back_to_start_time_before_first_payment():
    start, _ = period_bounds({"start_time": "2026-07-27T09:30:00Z", "billing_info": {}})
    assert start == datetime(2026, 7, 27, 9, 30, tzinfo=timezone.utc)


def test_period_bounds_are_timezone_aware():
    """A naive timestamp compared against an aware one raises at runtime, and
    renewal boundaries decide whether someone can generate a document."""
    start, end = period_bounds(
        {"start_time": "2026-01-01T00:00:00Z",
         "billing_info": {"next_billing_time": "2027-01-01T00:00:00Z"}}
    )
    assert start.tzinfo is not None and end.tzinfo is not None


@pytest.mark.parametrize(
    "resource",
    [{}, {"billing_info": {}}, {"start_time": None}, {"start_time": "not-a-date"}],
)
def test_period_bounds_tolerate_missing_or_junk_dates(resource):
    assert period_bounds(resource) == (None, None)


# --- approval link ---------------------------------------------------------


def test_approval_link_picks_the_approve_rel():
    assert approval_link(
        {
            "links": [
                {"rel": "self", "href": "https://api/self"},
                {"rel": "approve", "href": "https://paypal/approve"},
                {"rel": "edit", "href": "https://api/edit"},
            ]
        }
    ) == "https://paypal/approve"


@pytest.mark.parametrize("resource", [{}, {"links": []}, {"links": [{"rel": "self", "href": "x"}]}])
def test_approval_link_absent(resource):
    assert approval_link(resource) is None


# --- webhook cert trust ----------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-abc",
        "https://api.paypal.com/v1/notifications/certs/CERT-abc",
        "https://www.paypalobjects.com/certs/CERT-abc",
    ],
)
def test_paypal_cert_urls_are_trusted(url):
    assert _cert_url_is_trusted(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/cert.pem",
        # The classic suffix-confusion attack: a domain that merely *ends with*
        # the trusted string.
        "https://notpaypal.com/cert.pem",
        "https://paypal.com.evil.com/cert.pem",
        "",
        "not a url",
    ],
)
def test_untrusted_cert_urls_are_rejected(url):
    assert _cert_url_is_trusted(url) is False


# --- webhook verification fails closed -------------------------------------


def _headers(**overrides: str) -> dict[str, str]:
    base = {
        "paypal-auth-algo": "SHA256withRSA",
        "paypal-cert-url": "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-1",
        "paypal-transmission-id": "tx-1",
        "paypal-transmission-sig": "sig-1",
        "paypal-transmission-time": "2026-07-27T10:00:00Z",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_verification_fails_closed_without_a_webhook_id(monkeypatch):
    """No configured webhook id means we cannot verify anything — so we don't.

    This is the state of a fresh deploy, and it must not be the state in which
    anyone can POST themselves an ACTIVE subscription.
    """
    monkeypatch.setattr(settings, "PAYPAL_WEBHOOK_ID", "")
    assert await paypal_client.verify_webhook_signature(_headers(), b"{}") is False


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", list(_headers().keys()))
async def test_verification_fails_closed_on_any_missing_signature_header(monkeypatch, missing):
    monkeypatch.setattr(settings, "PAYPAL_WEBHOOK_ID", "WH-TEST")
    headers = {k: v for k, v in _headers().items() if k != missing}
    assert await paypal_client.verify_webhook_signature(headers, b"{}") is False


@pytest.mark.asyncio
async def test_verification_fails_closed_on_untrusted_cert_url(monkeypatch):
    monkeypatch.setattr(settings, "PAYPAL_WEBHOOK_ID", "WH-TEST")
    headers = _headers(**{"paypal-cert-url": "https://evil.com/cert.pem"})
    assert await paypal_client.verify_webhook_signature(headers, b"{}") is False


@pytest.mark.asyncio
async def test_verification_fails_closed_when_paypal_call_raises(monkeypatch):
    """A verifier outage must not become an open door."""
    monkeypatch.setattr(settings, "PAYPAL_WEBHOOK_ID", "WH-TEST")

    async def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(paypal_client, "request", boom)
    assert await paypal_client.verify_webhook_signature(_headers(), b"{}") is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,payload",
    [(200, {"verification_status": "FAILURE"}), (200, {}), (500, {})],
)
async def test_verification_requires_an_explicit_success(monkeypatch, status_code, payload):
    monkeypatch.setattr(settings, "PAYPAL_WEBHOOK_ID", "WH-TEST")

    class Resp:
        def __init__(self):
            self.status_code = status_code
            self.text = "boom"

        def json(self):
            return payload

    async def fake_request(*a, **k):
        return Resp()

    monkeypatch.setattr(paypal_client, "request", fake_request)
    assert await paypal_client.verify_webhook_signature(_headers(), b"{}") is False


@pytest.mark.asyncio
async def test_verification_passes_and_sends_the_raw_body(monkeypatch):
    """The signature covers the exact bytes PayPal sent.

    Re-serializing the parsed event would reorder keys and re-escape unicode,
    and PayPal would reject a genuine event. Assert the raw text travels intact.
    """
    monkeypatch.setattr(settings, "PAYPAL_WEBHOOK_ID", "WH-TEST")
    raw = b'{"id":"WH-1","event_type":"BILLING.SUBSCRIPTION.ACTIVATED","z":"\\u00e8"}'
    seen: dict = {}

    class Resp:
        status_code = 200
        text = ""

        def json(self):
            return {"verification_status": "SUCCESS"}

    async def fake_request(method, path, *, content=None, **k):
        seen["path"] = path
        seen["content"] = content
        return Resp()

    monkeypatch.setattr(paypal_client, "request", fake_request)
    assert await paypal_client.verify_webhook_signature(_headers(), raw) is True

    assert seen["path"] == "/v1/notifications/verify-webhook-signature"
    # The event body appears verbatim, not re-encoded.
    assert raw.decode() in seen["content"]
    assert '"webhook_id": "WH-TEST"' in seen["content"]
