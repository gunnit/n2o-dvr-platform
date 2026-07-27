"""Verify the configured PayPal credentials actually work.

    python -m scripts.paypal_check

Read-only: fetches a token, then lists the catalogue Products and billing Plans
visible to the configured merchant account. Nothing is created or changed.

Run this after setting PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET (and again after
rotating the secret in the PayPal dashboard) to confirm the app can reach the
Subscriptions API before any of MB-3/MB-4 depends on it.
"""

import asyncio
import logging
import sys

from app.billing import paypal_client
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def check() -> int:
    if not paypal_client.is_configured():
        log.error("PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are unset.")
        return 1

    log.info("env=%s base=%s", settings.PAYPAL_ENV, settings.PAYPAL_API_BASE)

    try:
        await paypal_client.get_access_token()
    except Exception as exc:  # noqa: BLE001 — surface whatever PayPal said
        log.error("token request failed: %s", exc)
        return 1

    for label, path in (
        ("products", "/v1/catalogs/products?page_size=20"),
        ("plans", "/v1/billing/plans?page_size=20"),
    ):
        resp = await paypal_client.request("GET", path)
        if resp.status_code != 200:
            log.error("%s: HTTP %s %s", label, resp.status_code, resp.text[:300])
            return 1
        items = resp.json().get(label, [])
        log.info("%s: %d", label, len(items))
        for item in items:
            # The sandbox merchant account is shared with other Niuexa projects,
            # so expect rows that aren't ours. Phase 4's setup script must match
            # on name and be idempotent rather than assuming an empty catalogue.
            log.info("  %s  %s", item["id"], item.get("name", ""))

    log.info("OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(check()))
