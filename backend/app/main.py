import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.billing import catalogue
from app.config import settings
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

# Uvicorn configures its own `uvicorn.*` loggers and leaves the root logger
# alone, so without this nothing under `app.*` has a handler and Python's
# last-resort fallback drops everything below WARNING. Production therefore had
# uvicorn's access lines and our own errors, and *none* of our INFO — which is
# where every interesting billing outcome is written.
#
# It cost a day on 2026-07-29: a customer paid for B_BASE, all three PayPal
# webhooks answered 200, and the one line that says which branch ran —
# `billing webhook: <id> (<type>) -> <outcome>` in `api/v1/billing.py` — was
# never emitted, so the only record of what happened to the money was the
# `billing_webhook_events.outcome` column. Configured at import rather than in
# `lifespan` so anything logged while the app is still being constructed is
# captured too.
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    force=True,
)


async def _warn_on_unescapable_paywall() -> None:
    """Refuse to be quietly misconfigured into a dead end (MB-6.2).

    With `ENTITLEMENTS_ENFORCE` on, an organization holding no subscription row
    is correctly refused document generation — it has not bought anything. That
    is only fair if it *can* buy: checkout needs PayPal credentials, and needs
    `plans.paypal_plan_id` populated for this environment by
    `scripts/paypal_setup.py`. Miss either and every new signup lands in a state
    it cannot pay its way out of, while the only visible symptom is a price list
    that renders empty — which looks like a UI bug, not a config one.

    **The credential check alone is not enough, and the day it mattered it said
    nothing.** Production ran from 2026-07-28 with `PAYPAL_CLIENT_ID` and
    `PAYPAL_CLIENT_SECRET` both *set* — to a live-merchant pair being offered to
    the sandbox host, which authenticates nowhere — and with no plan row
    carrying a `paypal_plan_id`. Both signup funnels were dead ends for a day
    and this function stayed quiet, because non-empty is not the same as
    working. So ask the question the customer's browser actually asks: is there
    anything `GET /billing/plans` could return? `paypal_plan_id` is only ever
    written by a successful `paypal_setup.py` run, so a checkoutable row is
    evidence that credentials worked at least once against *this* environment —
    which no amount of reading the environment can tell you.

    A log line rather than a hard failure: the founding tenant is grandfathered
    and entirely unaffected, so refusing to boot would turn a signup-funnel
    problem into an outage for a customer who is fine. Logged at ERROR, not
    WARNING — a self-serve funnel that cannot take money is not a caveat.
    """
    if not settings.ENTITLEMENTS_ENFORCE:
        return

    if not settings.paypal_is_configured:
        logger.error(
            "ENTITLEMENTS_ENFORCE is on but PayPal is not configured "
            "(PAYPAL_ENV=%s, client id EMPTY). New tenants will be refused work "
            "with no way to subscribe. See DEPLOY.md 4b.",
            settings.PAYPAL_ENV,
        )
        return

    try:
        async with async_session_factory() as session:
            sellable = await catalogue.list_purchasable(session)
    except Exception:
        # Boot must not depend on this. A database that is not up yet is the
        # normal case for the first seconds of a deploy, not a billing fault.
        logger.exception("could not check the plan catalogue at startup")
        return

    if not sellable:
        logger.error(
            "ENTITLEMENTS_ENFORCE is on but no plan is checkoutable in "
            "PAYPAL_ENV=%s — every plans.paypal_plan_id is NULL, so "
            "GET /billing/plans is empty and POST /billing/subscribe answers "
            "409 for every plan. New tenants are refused work with no way to "
            "subscribe. Run scripts/paypal_setup.py — see DEPLOY.md 4b.",
            settings.PAYPAL_ENV,
        )
        return

    logger.info(
        "billing: %d plan(s) checkoutable in PAYPAL_ENV=%s (%s)",
        len(sellable),
        settings.PAYPAL_ENV,
        ", ".join(p.plan_code for p in sellable),
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    await _warn_on_unescapable_paywall()
    yield


app = FastAPI(
    title=settings.APP_NAME, docs_url="/docs", redoc_url="/redoc", lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Needed so the browser lets the frontend read Content-Disposition
    # (otherwise authenticated downloads lose their server-provided filename).
    expose_headers=["Content-Disposition"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
