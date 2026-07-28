"""PayPal REST integration — the payment lifecycle, and nothing else.

INV-2: PayPal owns the *payment lifecycle* only. Entitlements and usage are
read from Postgres, joined to PayPal via ``plans.paypal_plan_id``. The webhook
is the sole writer of ``subscriptions.status`` and ``current_period_*`` — no
other code path may set them.

**Only the auth layer is implemented.** It exists so the configured sandbox
credentials are verifiable from the app (see ``scripts/paypal_check.py``).
The commerce calls arrive with their phases:

* ``MB-3.2`` — create a subscription for an organization, return the approval
  link the operator sends to the customer.
* ``MB-4.1`` — catalogue setup script: one Product + one annual Plan per row of
  ``plan_catalogue``, writing ``plans.paypal_plan_id`` back.
* ``MB-4.3`` — the webhook, idempotent by ``event.id`` and verified against
  ``PAYPAL_WEBHOOK_ID`` via ``/v1/notifications/verify-webhook-signature``.
  An unverified event must never be trusted to write subscription state.
* ``MB-4.4`` — cancel / revise. PayPal has no hosted billing portal equivalent
  to Stripe's, so MB-4.4 becomes our own screen calling
  ``/v1/billing/subscriptions/{id}/{cancel,revise}``.

Prices are exclusive of IVA 22%; PayPal Subscriptions applies tax via the
plan's ``taxes`` block. PayPal does not emit Italian e-invoices (SdI) —
see OPEN-DECISION-3.

PayPal ships no maintained Python SDK for Subscriptions, so this is plain
httpx against the REST API.
"""

import asyncio
import json
import logging
import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings

log = logging.getLogger(__name__)

# PayPal access tokens live ~9h. Cache and reuse: a token fetch per API call
# would double every request's latency and burn rate limit for nothing.
# Refresh early so a token never expires mid-flight.
_TOKEN_REFRESH_MARGIN_SECONDS = 300

_token: str | None = None
_token_expires_at: float = 0.0
_token_lock = asyncio.Lock()


class PayPalNotConfigured(RuntimeError):
    """Raised when a PayPal call is attempted without credentials.

    Deliberately distinct from an auth failure: an empty client id means the
    billing feature is dormant (the default in dev and CI), not that PayPal
    rejected us.
    """


def is_configured() -> bool:
    return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)


async def get_access_token(force_refresh: bool = False) -> str:
    """Return a cached OAuth2 access token, fetching one if needed."""
    global _token, _token_expires_at

    if not is_configured():
        raise PayPalNotConfigured(
            "PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are unset — billing is dormant."
        )

    if not force_refresh and _token and time.monotonic() < _token_expires_at:
        return _token

    async with _token_lock:
        # Re-check: another coroutine may have refreshed while we waited here.
        if not force_refresh and _token and time.monotonic() < _token_expires_at:
            return _token

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{settings.PAYPAL_API_BASE}/v1/oauth2/token",
                auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "client_credentials"},
            )
        resp.raise_for_status()
        payload = resp.json()

        _token = payload["access_token"]
        _token_expires_at = time.monotonic() + max(
            0, int(payload.get("expires_in", 0)) - _TOKEN_REFRESH_MARGIN_SECONDS
        )
        log.info(
            "paypal: token acquired env=%s app_id=%s expires_in=%ss",
            settings.PAYPAL_ENV,
            payload.get("app_id"),
            payload.get("expires_in"),
        )
        return _token


async def request(
    method: str,
    path: str,
    *,
    json: dict | None = None,
    content: str | bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> httpx.Response:
    """Call a PayPal REST endpoint with a bearer token attached.

    ``path`` is relative, e.g. ``/v1/billing/plans``. Retries once on 401 after
    forcing a token refresh — PayPal invalidates tokens when an app's secret is
    rotated in the dashboard, and the cached token would otherwise keep failing
    until the process restarts.

    ``content`` sends a pre-serialized body. Webhook verification needs it: the
    signature covers the exact bytes PayPal sent, so re-serializing the parsed
    event (key order, spacing, unicode escaping) can invalidate a genuine event.
    """

    base_headers = {"Content-Type": "application/json"} if content is not None else {}

    async def _send(client: httpx.AsyncClient, token: str) -> httpx.Response:
        return await client.request(
            method,
            f"{settings.PAYPAL_API_BASE}{path}",
            json=json,
            content=content,
            headers={
                "Authorization": f"Bearer {token}",
                **base_headers,
                **(headers or {}),
            },
        )

    token = await get_access_token()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await _send(client, token)
        if resp.status_code == 401:
            resp = await _send(client, await get_access_token(force_refresh=True))
    return resp


# --- Subscriptions ---------------------------------------------------------


class PayPalError(RuntimeError):
    """A PayPal call returned a non-success status."""

    def __init__(self, method: str, path: str, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"{method} {path} -> HTTP {status_code}: {body[:500]}")


async def _json(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    resp = await request(method, path, **kwargs)
    if resp.status_code >= 300:
        raise PayPalError(method, path, resp.status_code, resp.text)
    return resp.json() if resp.content else {}


async def create_subscription(
    paypal_plan_id: str,
    *,
    custom_id: str,
    return_url: str,
    cancel_url: str,
    brand_name: str,
    subscriber_email: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Create a subscription and return PayPal's resource (incl. approval link).

    ``custom_id`` carries our ``organization_id`` through PayPal and back on
    every webhook. It is how an event maps to a tenant when we have not yet
    stored the ``I-…`` id — which is always the case for the first event of a
    brand-new subscription.

    The plan is *not* recorded on our side here. PayPal's subscription knows its
    own ``plan_id``, and the webhook maps that back to a ``plan_code`` on
    activation — so an abandoned approval can never move a paying customer onto
    a plan they did not finish buying.
    """
    body: dict[str, Any] = {
        "plan_id": paypal_plan_id,
        "custom_id": custom_id,
        "application_context": {
            "brand_name": brand_name,
            "locale": "it-IT",
            "shipping_preference": "NO_SHIPPING",
            # Show "Subscribe Now" rather than "Continue" — the customer is
            # committing to a recurring charge and the button should say so.
            "user_action": "SUBSCRIBE_NOW",
            "payment_method": {
                "payer_selected": "PAYPAL",
                "payee_preferred": "IMMEDIATE_PAYMENT_REQUIRED",
            },
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
    }
    if subscriber_email:
        body["subscriber"] = {"email_address": subscriber_email}

    headers = {"PayPal-Request-Id": request_id} if request_id else None
    return await _json("POST", "/v1/billing/subscriptions", json=body, headers=headers)


async def get_subscription(subscription_id: str) -> dict[str, Any] | None:
    """Fetch a subscription. ``None`` if PayPal no longer knows it."""
    resp = await request("GET", f"/v1/billing/subscriptions/{subscription_id}")
    if resp.status_code == 404:
        return None
    if resp.status_code >= 300:
        raise PayPalError("GET", f"/v1/billing/subscriptions/{subscription_id}",
                          resp.status_code, resp.text)
    return resp.json()


async def cancel_subscription(subscription_id: str, reason: str) -> None:
    """Cancel at PayPal. Already-cancelled is treated as success (idempotent)."""
    resp = await request(
        "POST",
        f"/v1/billing/subscriptions/{subscription_id}/cancel",
        json={"reason": reason[:127]},
    )
    if resp.status_code < 300:
        return
    # 422 UNPROCESSABLE_ENTITY is what PayPal returns for "not in a state that
    # can be cancelled" — i.e. it is already gone. Nothing left to do.
    if resp.status_code == 422 and "SUBSCRIPTION_STATUS_INVALID" in resp.text:
        log.info("paypal: subscription %s already cancelled", subscription_id)
        return
    raise PayPalError("POST", f"/v1/billing/subscriptions/{subscription_id}/cancel",
                      resp.status_code, resp.text)


async def revise_subscription(
    subscription_id: str,
    new_paypal_plan_id: str,
    *,
    return_url: str,
    cancel_url: str,
) -> dict[str, Any]:
    """Move a live subscription to a different plan.

    Returns the revised resource, which carries a fresh ``approve`` link: a plan
    change alters what the customer is charged, so PayPal makes them re-approve.
    Nothing changes on our side until the resulting webhook lands.
    """
    return await _json(
        "POST",
        f"/v1/billing/subscriptions/{subscription_id}/revise",
        json={
            "plan_id": new_paypal_plan_id,
            "application_context": {"return_url": return_url, "cancel_url": cancel_url},
        },
    )


def approval_link(resource: dict[str, Any]) -> str | None:
    """Pull the customer-facing approval URL out of a subscription resource."""
    for link in resource.get("links", []):
        if link.get("rel") == "approve":
            return link.get("href")
    return None


# --- Orders (one-time payments — AI credit packs) --------------------------
#
# A pack is a single charge, not a recurring one, so it uses Orders v2 rather
# than the Subscriptions API above. That also means no PayPal-side catalogue to
# provision: the price travels in the request, so a pack is sellable the moment
# `credit_packs.py` lists it — no equivalent of `DEPLOY.md` §4b-bis.


async def create_order(
    *,
    amount_cents: int,
    currency: str,
    description: str,
    custom_id: str,
    reference_id: str,
    return_url: str,
    cancel_url: str,
    brand_name: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Create a one-time order and return PayPal's resource (incl. approve link).

    ``custom_id`` carries our ``organization_id`` so a webhook can be mapped back
    to a tenant, exactly as it does for subscriptions. ``reference_id`` carries
    our ``credit_purchases.id``, which is what the capture path reconciles
    against — the order id alone would not tell us *which* pending purchase row
    a stray webhook belongs to.

    ``PayPal-Request-Id`` makes the create idempotent at PayPal's end: a retried
    call returns the same order instead of opening a second one the customer
    could pay twice.
    """
    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": reference_id,
                "custom_id": custom_id,
                "description": description[:127],
                "amount": {
                    "currency_code": currency,
                    # PayPal wants a decimal string; our prices are integer cents.
                    "value": f"{amount_cents / 100:.2f}",
                },
            }
        ],
        "payment_source": {
            "paypal": {
                "experience_context": {
                    "brand_name": brand_name,
                    "locale": "it-IT",
                    "shipping_preference": "NO_SHIPPING",
                    # "Pay Now" rather than "Continue": the amount is final and
                    # there is no review step of ours after approval.
                    "user_action": "PAY_NOW",
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                }
            }
        },
    }
    headers = {"PayPal-Request-Id": request_id} if request_id else None
    return await _json("POST", "/v2/checkout/orders", json=body, headers=headers)


class PayPalOrderNotApproved(RuntimeError):
    """The customer has not (or no longer) approved this order.

    Distinct from :class:`PayPalError` because it is not a failure of ours: the
    normal cause is a customer who abandoned the PayPal window and came back, and
    the honest response is "nothing was charged", not "payment provider error".
    """


async def capture_order(order_id: str) -> dict[str, Any]:
    """Take the money for an approved order.

    Idempotent at PayPal's end for the case that matters: capturing an
    already-captured order returns 422 ``ORDER_ALREADY_CAPTURED``, which we
    resolve by re-reading the order so the caller still gets a completed
    resource. The grant is guarded by our own row status either way, so a double
    capture cannot double-credit — this only stops a harmless replay from
    surfacing as an error to the customer.
    """
    resp = await request("POST", f"/v2/checkout/orders/{order_id}/capture", json={})
    if resp.status_code < 300:
        return resp.json()

    text = resp.text or ""
    if resp.status_code == 422 and "ORDER_ALREADY_CAPTURED" in text:
        log.info("paypal: order %s was already captured — re-reading it", order_id)
        existing = await get_order(order_id)
        if existing is not None:
            return existing
    if resp.status_code == 422 and (
        "ORDER_NOT_APPROVED" in text or "PAYER_ACTION_REQUIRED" in text
    ):
        raise PayPalOrderNotApproved(order_id)
    raise PayPalError("POST", f"/v2/checkout/orders/{order_id}/capture", resp.status_code, text)


async def get_order(order_id: str) -> dict[str, Any] | None:
    """Fetch an order. ``None`` if PayPal no longer knows it."""
    resp = await request("GET", f"/v2/checkout/orders/{order_id}")
    if resp.status_code == 404:
        return None
    if resp.status_code >= 300:
        raise PayPalError("GET", f"/v2/checkout/orders/{order_id}", resp.status_code, resp.text)
    return resp.json()


def order_is_paid(resource: dict[str, Any]) -> bool:
    """Whether an order resource represents money actually taken.

    ``COMPLETED`` on the order is the top-level answer, but an order can also
    read ``APPROVED`` at the top while carrying a completed capture underneath
    when the read races the capture — checking both avoids refusing to grant
    credits for a payment that demonstrably went through.
    """
    if (resource.get("status") or "").upper() == "COMPLETED":
        return True
    for unit in resource.get("purchase_units") or []:
        for capture in (unit.get("payments") or {}).get("captures") or []:
            if (capture.get("status") or "").upper() == "COMPLETED":
                return True
    return False


def order_reference_id(resource: dict[str, Any]) -> str | None:
    """Our ``credit_purchases.id``, as stamped at creation."""
    for unit in resource.get("purchase_units") or []:
        reference = unit.get("reference_id")
        if reference:
            return str(reference)
    return None


# --- Webhook verification --------------------------------------------------

# PayPal signs with a cert it hosts. We forward the URL for PayPal to check, but
# refuse to forward one that isn't theirs: a header-supplied URL pointing at an
# attacker's host has no business travelling anywhere, even to a verifier that
# would reject it.
_TRUSTED_CERT_HOSTS = ("paypal.com", "paypalobjects.com")

_SIGNATURE_HEADERS = {
    "auth_algo": "paypal-auth-algo",
    "cert_url": "paypal-cert-url",
    "transmission_id": "paypal-transmission-id",
    "transmission_sig": "paypal-transmission-sig",
    "transmission_time": "paypal-transmission-time",
}


def _cert_url_is_trusted(cert_url: str) -> bool:
    try:
        host = urlparse(cert_url).hostname or ""
    except ValueError:
        return False
    return any(host == h or host.endswith(f".{h}") for h in _TRUSTED_CERT_HOSTS)


async def verify_webhook_signature(headers: Mapping[str, str], raw_body: bytes) -> bool:
    """Whether PayPal actually sent this event. Fails closed.

    Returns False — never raises — on a missing ``PAYPAL_WEBHOOK_ID``, missing
    signature headers, an untrusted cert host, or a verification call that
    errors. An event we cannot prove came from PayPal must not be allowed to
    write subscription state, and "the verifier was down" is not proof.
    """
    if not settings.PAYPAL_WEBHOOK_ID:
        log.error("paypal webhook: PAYPAL_WEBHOOK_ID is unset — refusing to trust event")
        return False

    lowered = {k.lower(): v for k, v in headers.items()}
    fields: dict[str, str] = {}
    for field, header in _SIGNATURE_HEADERS.items():
        value = lowered.get(header)
        if not value:
            log.warning("paypal webhook: missing %s header", header)
            return False
        fields[field] = value

    if not _cert_url_is_trusted(fields["cert_url"]):
        log.error("paypal webhook: untrusted cert_url %r", fields["cert_url"])
        return False

    # Build the body by hand so the event is byte-identical to what was signed.
    # json.dumps of the parsed event would re-order keys and re-escape unicode,
    # and PayPal would correctly call a genuine event invalid.
    envelope = ", ".join(f'"{k}": {json.dumps(v)}' for k, v in fields.items())
    payload = (
        "{"
        + envelope
        + f', "webhook_id": {json.dumps(settings.PAYPAL_WEBHOOK_ID)}'
        + ', "webhook_event": '
        + raw_body.decode("utf-8")
        + "}"
    )

    try:
        resp = await request(
            "POST",
            "/v1/notifications/verify-webhook-signature",
            content=payload,
        )
    except Exception:
        log.exception("paypal webhook: verification call failed — treating as unverified")
        return False

    if resp.status_code >= 300:
        log.error(
            "paypal webhook: verification HTTP %s: %s", resp.status_code, resp.text[:300]
        )
        return False

    status_value = resp.json().get("verification_status")
    if status_value != "SUCCESS":
        log.error("paypal webhook: verification_status=%s", status_value)
        return False
    return True


def _reset_token_cache_for_tests() -> None:
    global _token, _token_expires_at
    _token = None
    _token_expires_at = 0.0
