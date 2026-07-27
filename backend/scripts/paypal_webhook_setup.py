"""MB-4.3 — register (or re-point) the PayPal webhook listener.

    python -m scripts.paypal_webhook_setup --list
    python -m scripts.paypal_webhook_setup --url https://n2o-dvr-api.onrender.com
    python -m scripts.paypal_webhook_setup --url https://…  --live

Prints the webhook id to put in ``PAYPAL_WEBHOOK_ID``. Nothing verifies a
signature until that value is set, and ``verify_webhook_signature`` fails
closed without it — so an unset id means every event is rejected, never
silently trusted.

Idempotent: a listener already pointing at the same URL is updated in place
(PayPal allows only ten per app, so creating a duplicate on every deploy would
eventually wedge the account).

``--url`` takes the API origin; the endpoint path is appended for you. Must be
publicly reachable over HTTPS — PayPal will not deliver to localhost, so use a
tunnel when testing against a dev machine.
"""

import argparse
import asyncio
import json
import logging
import sys

from app.billing import paypal_client
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

WEBHOOK_PATH = "/api/v1/billing/webhook"

# Exactly what api/v1/billing.py acts on. Subscribing to more would fill the
# ledger with events we ignore; subscribing to fewer would silently miss a
# state change and leave a customer on the wrong plan.
EVENT_TYPES = [
    "BILLING.SUBSCRIPTION.CREATED",
    "BILLING.SUBSCRIPTION.ACTIVATED",
    "BILLING.SUBSCRIPTION.UPDATED",
    "BILLING.SUBSCRIPTION.SUSPENDED",
    "BILLING.SUBSCRIPTION.CANCELLED",
    "BILLING.SUBSCRIPTION.EXPIRED",
    "BILLING.SUBSCRIPTION.PAYMENT.FAILED",
    "PAYMENT.SALE.COMPLETED",
    "PAYMENT.SALE.DENIED",
    "PAYMENT.SALE.REFUNDED",
]


async def _list() -> list[dict]:
    payload = await paypal_client._json("GET", "/v1/notifications/webhooks")
    return payload.get("webhooks", [])


async def run(url: str | None, do_list: bool) -> int:
    if not paypal_client.is_configured():
        log.error("PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are unset.")
        return 1

    log.info("env=%s base=%s", settings.PAYPAL_ENV, settings.PAYPAL_API_BASE)
    existing = await _list()

    if do_list or not url:
        if not existing:
            log.info("no webhooks registered")
        for w in existing:
            events = [e["name"] for e in w.get("event_types", [])]
            log.info("%s  %s  (%d events)", w["id"], w["url"], len(events))
        if not url:
            log.info("pass --url <api-origin> to register one")
        return 0

    target = url.rstrip("/") + WEBHOOK_PATH
    if not target.startswith("https://"):
        log.error("PayPal only delivers to HTTPS endpoints; got %s", target)
        return 1

    body = {"url": target, "event_types": [{"name": n} for n in EVENT_TYPES]}

    same_url = next((w for w in existing if w["url"] == target), None)
    if same_url:
        # Re-point the event list rather than create a second listener for the
        # same URL — PayPal caps an app at ten.
        await paypal_client._json(
            "PATCH",
            f"/v1/notifications/webhooks/{same_url['id']}",
            json=[{"op": "replace", "path": "/event_types", "value": body["event_types"]}],
        )
        log.info("updated existing webhook %s -> %s", same_url["id"], target)
        webhook_id = same_url["id"]
    else:
        created = await paypal_client._json("POST", "/v1/notifications/webhooks", json=body)
        webhook_id = created["id"]
        log.info("created webhook %s -> %s", webhook_id, target)

    log.info("")
    log.info("Set this in the API environment, then redeploy:")
    log.info("  PAYPAL_WEBHOOK_ID=%s", webhook_id)
    log.info("")
    log.info("subscribed events: %s", json.dumps(EVENT_TYPES, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="public API origin, e.g. https://n2o-dvr-api.onrender.com")
    parser.add_argument("--list", action="store_true", help="show registered webhooks and exit")
    parser.add_argument("--live", action="store_true", help="required when PAYPAL_ENV=live")
    args = parser.parse_args()

    if settings.PAYPAL_ENV == "live" and not args.live and not args.list:
        log.error("PAYPAL_ENV=live — pass --live to confirm.")
        return 1

    try:
        return asyncio.run(run(args.url, args.list))
    except paypal_client.PayPalError as exc:
        log.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
