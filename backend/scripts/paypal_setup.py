"""MB-4.1 — mirror the plan catalogue into PayPal's Product/Plan catalogue.

    python -m scripts.paypal_setup --dry-run    # report what would change
    python -m scripts.paypal_setup              # apply (sandbox)
    python -m scripts.paypal_setup --live       # apply against PAYPAL_ENV=live
    python -m scripts.paypal_setup --bind-only  # write back existing ids only

``--bind-only`` is the deploy-path subset: it resolves plan ids that already
exist at PayPal, writes them onto ``plans.paypal_plan_id``, and creates nothing.
It runs from ``preDeployCommand`` so the id binding cannot silently go missing —
see :func:`bind`. Provisioning a merchant for the first time is still the full
run above, because that creates commercial objects.

Creates one Product ("N2O DVR Platform") and one annual billing Plan per
sellable row of ``app.billing.plan_catalogue``, then writes each PayPal plan id
back onto ``plans.paypal_plan_id`` — the INV-2 join key.

**Idempotent, and it has to be.** The sandbox merchant account is shared with
other Niuexa projects and already holds unrelated products and plans, so this
never assumes an empty catalogue: it resolves an existing plan by the stored
``paypal_plan_id`` first, then by exact name within *our* product, and only
creates when neither matches. Creates carry a deterministic ``PayPal-Request-Id``
so a retried call after a network blip cannot produce a duplicate.

Two things this deliberately does NOT do:

* **No setup fees.** First-year setup fees (§5 of the build plan) are one-time
  line items at checkout, not plan fields — the catalogue holds no fee data and
  a PayPal ``setup_fee`` would be charged on every subscription created from
  the plan. MB-4.2 owns them.
* **No silent repricing.** A price change in the catalogue is reported but not
  pushed unless ``--update-pricing`` is passed. Changing a live plan's price is
  a commercial act, not a side effect of running a setup script.

``A_FOUNDING`` is skipped: it is the €0 grandfather row (MB-1.3), never sold, so
it has no PayPal counterpart. Model B plans are created but left **INACTIVE** in
PayPal to mirror ``active=False`` — nobody can subscribe to them before Phase 5
flips them on, even if a plan id leaks.

⚠️ ``plans.paypal_plan_id`` holds ids for exactly one PayPal environment.
Sandbox and live issue different ids, so a database belongs to one or the other:
dev/staging DB ↔ sandbox, production DB ↔ live. Never run this against
production Postgres with ``PAYPAL_ENV=sandbox``.
"""

import argparse
import asyncio
import logging
import sys
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select

from app.billing import paypal_client
from app.billing.plan_catalogue import PLAN_CATALOGUE, validate_catalogue
from app.config import settings
from app.db.session import async_session_factory
from app.models.plan import Plan

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# [DEFER] multi-currency, monthly (+20%) and 3-year (−15%) variants — each is a
# separate PayPal plan under the same product.
CURRENCY = "EUR"
# Prices in the catalogue are ex-IVA; PayPal adds it as an exclusive tax so the
# customer sees the same split as on the invoice.
IVA_PERCENTAGE = "22"
PRODUCT_NAME = "N2O DVR Platform"
PLAN_NAME_PREFIX = "N2O DVR"
# Bump if a body ever needs recreating under a fresh idempotency key.
REQUEST_ID_VERSION = "v1"
# How many times PayPal retries a failed payment before suspending. Mirrors the
# dunning grace that `past_due` grants in billing.constants (MB-4.5).
PAYMENT_FAILURE_THRESHOLD = 3


def euro(cents: int) -> str:
    """149_000 -> '1490.00'. PayPal wants a decimal string, not a float."""
    return f"{cents // 100}.{cents % 100:02d}"


def plan_name(plan: dict[str, Any]) -> str:
    """Customer-facing, and our idempotency key inside the product.

    Shown on the PayPal approval page, so it stays readable; the machine
    identifier lives in the description.
    """
    return f"{PLAN_NAME_PREFIX} — {plan['display_name']}"


def product_body() -> dict[str, Any]:
    return {
        "name": PRODUCT_NAME,
        "description": "Generazione automatica della documentazione di sicurezza sul lavoro (D.Lgs. 81/2008).",
        "type": "SERVICE",
        "category": "SOFTWARE",
    }


def plan_body(plan: dict[str, Any], product_id: str) -> dict[str, Any]:
    """The desired PayPal plan for a catalogue row.

    One infinite annual REGULAR cycle. `total_cycles: 0` means "until
    cancelled" — a finite count would silently stop billing a customer.
    """
    return {
        "product_id": product_id,
        "name": plan_name(plan),
        # PayPal caps plan descriptions at 127 chars; keep the plan_code in
        # there so a human in the dashboard can map it back to our catalogue.
        "description": f"Abbonamento annuale {plan['display_name']} ({plan['plan_code']}). Prezzi IVA esclusa.",
        "status": "ACTIVE" if plan["active"] else "CREATED",
        "billing_cycles": [
            {
                "frequency": {"interval_unit": "YEAR", "interval_count": 1},
                "tenure_type": "REGULAR",
                "sequence": 1,
                "total_cycles": 0,
                "pricing_scheme": {
                    "fixed_price": {
                        "value": euro(plan["price_year_cents"]),
                        "currency_code": CURRENCY,
                    }
                },
            }
        ],
        "payment_preferences": {
            "auto_bill_outstanding": True,
            "setup_fee_failure_action": "CANCEL",
            "payment_failure_threshold": PAYMENT_FAILURE_THRESHOLD,
        },
        "taxes": {"percentage": IVA_PERCENTAGE, "inclusive": False},
    }


def sellable_plans() -> list[dict[str, Any]]:
    """Catalogue rows that get a PayPal plan.

    Excludes the €0 grandfather row: PayPal has nothing to bill for it, and a
    zero-price plan would be a footgun sitting in the merchant catalogue.
    """
    return [p for p in PLAN_CATALOGUE if p["price_year_cents"] > 0]


class SetupError(RuntimeError):
    """A PayPal call failed in a way that should stop the run."""


async def _call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    resp = await paypal_client.request(method, path, **kwargs)
    if resp.status_code >= 300:
        raise SetupError(f"{method} {path} -> HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.json() if resp.content else {}


async def _list_all(path: str, key: str) -> list[dict[str, Any]]:
    """Page through a PayPal list endpoint until it stops returning a full page."""
    items: list[dict[str, Any]] = []
    page = 1
    sep = "&" if "?" in path else "?"
    while True:
        payload = await _call("GET", f"{path}{sep}page_size=20&page={page}")
        batch = payload.get(key, [])
        items.extend(batch)
        if len(batch) < 20:
            return items
        page += 1


async def ensure_product(dry_run: bool) -> str | None:
    """Return our product's id, creating it if absent.

    Matches on exact name. Other projects' products live in the same merchant
    account, so a name match is the only safe discriminator we control.
    """
    products = await _list_all("/v1/catalogs/products", "products")
    mine = [p for p in products if p.get("name") == PRODUCT_NAME]

    if len(mine) > 1:
        raise SetupError(
            f"{len(mine)} products named {PRODUCT_NAME!r} "
            f"({', '.join(p['id'] for p in mine)}) — resolve by hand before re-running."
        )
    if mine:
        log.info("product: %s (exists)", mine[0]["id"])
        return mine[0]["id"]

    log.info(
        "product: %r not found among %d existing product(s) — would create",
        PRODUCT_NAME, len(products),
    )
    if dry_run:
        return None

    created = await _call(
        "POST",
        "/v1/catalogs/products",
        json=product_body(),
        headers={"PayPal-Request-Id": f"n2o-product-{REQUEST_ID_VERSION}"},
    )
    log.info("product: %s (created)", created["id"])
    return created["id"]


async def _fetch_plan(plan_id: str) -> dict[str, Any] | None:
    resp = await paypal_client.request("GET", f"/v1/billing/plans/{plan_id}")
    if resp.status_code == 404:
        return None
    if resp.status_code >= 300:
        raise SetupError(f"GET plan {plan_id} -> HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _current_price(remote: dict[str, Any]) -> str | None:
    for cycle in remote.get("billing_cycles", []):
        if cycle.get("tenure_type") == "REGULAR":
            return cycle.get("pricing_scheme", {}).get("fixed_price", {}).get("value")
    return None


def prices_differ(have: str | None, want: str) -> bool:
    """Compare amounts numerically — PayPal echoes '1490.00' back as '1490.0'.

    A string comparison here reports drift on every re-run, and with
    ``--update-pricing`` would issue a pointless repricing call each time.
    """
    if have is None:
        return False
    try:
        return Decimal(have) != Decimal(want)
    except InvalidOperation:
        # An amount we cannot parse is worth surfacing, not swallowing.
        return True


async def _reconcile(
    plan: dict[str, Any],
    remote: dict[str, Any],
    dry_run: bool,
    update_pricing: bool,
) -> list[str]:
    """Bring an existing PayPal plan back in line with the catalogue."""
    actions: list[str] = []
    code = plan["plan_code"]
    plan_id = remote["id"]

    # --- status: our `active` flag is the source of truth ------------------
    want_active = plan["active"]
    is_active = remote.get("status") == "ACTIVE"
    if want_active and not is_active:
        actions.append("activate")
        if not dry_run:
            await _call("POST", f"/v1/billing/plans/{plan_id}/activate")
    elif not want_active and is_active:
        actions.append("deactivate")
        if not dry_run:
            await _call("POST", f"/v1/billing/plans/{plan_id}/deactivate")

    # --- price -------------------------------------------------------------
    want_price = euro(plan["price_year_cents"])
    have_price = _current_price(remote)
    if prices_differ(have_price, want_price):
        if not update_pricing:
            log.warning(
                "  %s PRICE DRIFT: PayPal has %s %s, catalogue says %s — "
                "re-run with --update-pricing to push it",
                code, have_price, CURRENCY, want_price,
            )
            actions.append(f"price-drift({have_price}->{want_price}, not pushed)")
        else:
            actions.append(f"reprice {have_price}->{want_price}")
            if not dry_run:
                await _call(
                    "POST",
                    f"/v1/billing/plans/{plan_id}/update-pricing-schemes",
                    json={
                        "pricing_schemes": [
                            {
                                "billing_cycle_sequence": 1,
                                "pricing_scheme": {
                                    "fixed_price": {
                                        "value": want_price,
                                        "currency_code": CURRENCY,
                                    }
                                },
                            }
                        ]
                    },
                )
    return actions


async def bind() -> int:
    """Write back plan ids that already exist at PayPal. Creates nothing.

    The deploy-path half of this script, and deliberately a different function
    rather than a flag threaded through :func:`sync` — the safety argument here
    is "no code path in it can write to PayPal", and that has to be readable at
    a glance rather than traced through branches.

    It exists because of how production broke on 2026-07-28: the sandbox
    merchant held all seven plans, the ``plans`` table held all seven rows, and
    the *join between them* was missing, so `GET /billing/plans` returned `[]`
    and both signup funnels became dead ends nobody could pay their way out of.
    Nothing about that needed a human decision — the ids existed and simply had
    not been copied — so a deploy now reconciles it.

    **Always exits 0.** It runs in `preDeployCommand`, so a raised exception
    would abort a production deploy over a reconcile that is advisory by
    construction. Unconfigured credentials, a merchant that has never been
    provisioned, an unreachable PayPal — all are logged and skipped. The one
    thing that *should* still fail a deploy is an import error, which would mean
    the app's own billing package is broken; that is why nothing here is
    wrapped in a shell ``|| true``.

    What it will not do, all of which stay in :func:`sync`: create a product,
    create a plan, change a price, or activate one. Those are commercial acts
    against a merchant account and belong to a human running DEPLOY.md §4b.
    """
    if not paypal_client.is_configured():
        log.info("bind: PayPal is not configured — nothing to bind")
        return 0

    log.info("bind: env=%s base=%s", settings.PAYPAL_ENV, settings.PAYPAL_API_BASE)

    try:
        # dry_run=True is what makes this read-only: `ensure_product` reports a
        # missing product instead of creating one.
        product_id = await ensure_product(dry_run=True)

        remote_by_name: dict[str, dict[str, Any]] = {}
        if product_id:
            for p in await _list_all(f"/v1/billing/plans?product_id={product_id}", "plans"):
                remote_by_name.setdefault(p["name"], p)

        bound: list[str] = []
        intact: list[str] = []
        unresolved: list[str] = []

        async with async_session_factory() as session:
            rows = {p.plan_code: p for p in (await session.execute(select(Plan))).scalars()}

            for plan in sellable_plans():
                code = plan["plan_code"]
                row = rows.get(code)
                if row is None:
                    # No row to bind to. `seed_plans` owns that, not this.
                    unresolved.append(code)
                    continue

                remote: dict[str, Any] | None = None
                if row.paypal_plan_id:
                    remote = await _fetch_plan(row.paypal_plan_id)
                    if remote is not None:
                        intact.append(code)
                        continue
                    # A stored id PayPal does not recognise is the signature of
                    # a database pointed at the other environment (§4b-bis), so
                    # fall through and re-resolve rather than trusting it.
                    log.warning(
                        "bind: %s stored paypal_plan_id %s is unknown in %s — re-resolving",
                        code, row.paypal_plan_id, settings.PAYPAL_ENV,
                    )

                remote = remote_by_name.get(plan_name(plan))
                if remote is None:
                    unresolved.append(code)
                    continue

                log.info("bind: %s paypal_plan_id %r -> %r", code, row.paypal_plan_id, remote["id"])
                row.paypal_plan_id = remote["id"]
                bound.append(code)

            if bound:
                await session.commit()
    except Exception:
        log.exception("bind: reconcile failed — leaving plan ids as they are")
        return 0

    if unresolved:
        # Not a failure of this run: the merchant catalogue has never been
        # provisioned for these, which only the full script can do.
        log.error(
            "bind: %d plan(s) still have no PayPal counterpart in %s (%s). "
            "GET /billing/plans will omit them and POST /billing/subscribe will "
            "answer 409. Run `python -m scripts.paypal_setup` — see DEPLOY.md 4b.",
            len(unresolved), settings.PAYPAL_ENV, ", ".join(unresolved),
        )

    log.info(
        "bind: %d newly bound, %d already correct, %d unresolved",
        len(bound), len(intact), len(unresolved),
    )
    return 0


async def sync(
    dry_run: bool = False,
    update_pricing: bool = False,
) -> int:
    validate_catalogue()

    if not paypal_client.is_configured():
        log.error("PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are unset.")
        return 1

    log.info("env=%s base=%s", settings.PAYPAL_ENV, settings.PAYPAL_API_BASE)
    if dry_run:
        log.info("DRY RUN — no PayPal or database writes")

    product_id = await ensure_product(dry_run)

    # Existing plans under our product, by name. One list call beats one GET
    # per plan, and it is also the recovery path when the database has lost
    # its paypal_plan_id values.
    remote_by_name: dict[str, dict[str, Any]] = {}
    if product_id:
        for p in await _list_all(f"/v1/billing/plans?product_id={product_id}", "plans"):
            remote_by_name.setdefault(p["name"], p)

    async with async_session_factory() as session:
        rows = {p.plan_code: p for p in (await session.execute(select(Plan))).scalars()}

        created, reconciled, unchanged = [], [], []
        writeback: dict[str, str] = {}

        for plan in sellable_plans():
            code = plan["plan_code"]
            row = rows.get(code)
            if row is None:
                log.warning("  %s has no row in `plans` — run seed_plans first; skipping", code)
                continue

            remote: dict[str, Any] | None = None

            # 1. Trust the stored id first.
            if row.paypal_plan_id:
                remote = await _fetch_plan(row.paypal_plan_id)
                if remote is None:
                    log.warning(
                        "  %s stored paypal_plan_id %s does not exist in %s — "
                        "wrong environment, or the plan was removed; re-resolving",
                        code, row.paypal_plan_id, settings.PAYPAL_ENV,
                    )

            # 2. Fall back to an exact name match inside our product.
            if remote is None:
                remote = remote_by_name.get(plan_name(plan))

            # 3. Create.
            if remote is None:
                created.append(code)
                if dry_run or not product_id:
                    log.info("  %s -> would create %r", code, plan_name(plan))
                    continue
                remote = await _call(
                    "POST",
                    "/v1/billing/plans",
                    json=plan_body(plan, product_id),
                    headers={"PayPal-Request-Id": f"n2o-plan-{code}-{REQUEST_ID_VERSION}"},
                )
                log.info("  %s -> %s (created, status=%s)", code, remote["id"], remote.get("status"))
            else:
                actions = await _reconcile(plan, remote, dry_run, update_pricing)
                if actions:
                    log.info("  %s -> %s (%s)", code, remote["id"], ", ".join(actions))
                    reconciled.append(code)
                else:
                    unchanged.append(code)

            if remote and row.paypal_plan_id != remote["id"]:
                writeback[code] = remote["id"]

        for code, plan_id in writeback.items():
            log.info("  %s paypal_plan_id: %r -> %r", code, rows[code].paypal_plan_id, plan_id)
            if not dry_run:
                rows[code].paypal_plan_id = plan_id

        if not dry_run:
            await session.commit()

    skipped = [p["plan_code"] for p in PLAN_CATALOGUE if p["price_year_cents"] <= 0]
    log.info(
        "%s created %d, reconciled %d, unchanged %d, skipped %d (%s)",
        "DRY RUN —" if dry_run else "Done:",
        len(created), len(reconciled), len(unchanged), len(skipped), ", ".join(skipped),
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing")
    parser.add_argument(
        "--update-pricing",
        action="store_true",
        help="push catalogue prices onto existing PayPal plans (affects new subscriptions)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="required acknowledgement when PAYPAL_ENV=live",
    )
    parser.add_argument(
        "--bind-only",
        action="store_true",
        help=(
            "write back plan ids that already exist at PayPal and nothing else; "
            "never creates, reprices or activates. Safe on the deploy path."
        ),
    )
    args = parser.parse_args()

    if args.bind_only:
        # No `--live` acknowledgement: binding creates nothing, so there is no
        # commercial act to acknowledge. Re-binding is in fact exactly what a
        # sandbox→live switch needs (§4b-bis step 3) once the live plans exist.
        return asyncio.run(bind())

    # A live run creates real, customer-visible commercial objects. Make it a
    # deliberate act rather than whatever PAYPAL_ENV happened to be exported.
    if settings.PAYPAL_ENV == "live" and not args.live and not args.dry_run:
        log.error("PAYPAL_ENV=live — pass --live to confirm, or --dry-run to inspect.")
        return 1
    if args.live and settings.PAYPAL_ENV != "live":
        log.error("--live passed but PAYPAL_ENV=%s; refusing to guess.", settings.PAYPAL_ENV)
        return 1

    try:
        return asyncio.run(sync(dry_run=args.dry_run, update_pricing=args.update_pricing))
    except SetupError as exc:
        log.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
