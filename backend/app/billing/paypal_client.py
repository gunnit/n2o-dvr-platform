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
import logging
import time

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
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> httpx.Response:
    """Call a PayPal REST endpoint with a bearer token attached.

    ``path`` is relative, e.g. ``/v1/billing/plans``. Retries once on 401 after
    forcing a token refresh — PayPal invalidates tokens when an app's secret is
    rotated in the dashboard, and the cached token would otherwise keep failing
    until the process restarts.
    """

    async def _send(client: httpx.AsyncClient, token: str) -> httpx.Response:
        return await client.request(
            method,
            f"{settings.PAYPAL_API_BASE}{path}",
            json=json,
            headers={"Authorization": f"Bearer {token}", **(headers or {})},
        )

    token = await get_access_token()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await _send(client, token)
        if resp.status_code == 401:
            resp = await _send(client, await get_access_token(force_refresh=True))
    return resp


def _reset_token_cache_for_tests() -> None:
    global _token, _token_expires_at
    _token = None
    _token_expires_at = 0.0
