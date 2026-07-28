import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings

logger = logging.getLogger(__name__)


def _warn_on_unescapable_paywall() -> None:
    """Refuse to be quietly misconfigured into a dead end (MB-6.2).

    With `ENTITLEMENTS_ENFORCE` on, an organization holding no subscription row
    is correctly refused document generation — it has not bought anything. That
    is only fair if it *can* buy: checkout needs PayPal credentials, and needs
    `plans.paypal_plan_id` populated for this environment by
    `scripts/paypal_setup.py`. Credentials missing means every new signup lands
    in a state it cannot pay its way out of, and the only visible symptom is a
    price list that renders empty — which looks like a UI bug, not a config one.

    A warning rather than a hard failure: the founding tenant is grandfathered
    and entirely unaffected, so refusing to boot would turn a signup-funnel
    problem into an outage for a customer who is fine.
    """
    if settings.ENTITLEMENTS_ENFORCE and not settings.paypal_is_configured:
        logger.warning(
            "ENTITLEMENTS_ENFORCE is on but PayPal is not configured "
            "(PAYPAL_ENV=%s, client id %s). New tenants will be refused work "
            "with no way to subscribe. See DEPLOY.md 4b.",
            settings.PAYPAL_ENV,
            "set" if settings.PAYPAL_CLIENT_ID else "EMPTY",
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    _warn_on_unescapable_paywall()
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
