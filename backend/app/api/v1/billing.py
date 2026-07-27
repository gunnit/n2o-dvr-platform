"""Billing endpoints — plans, checkout, the webhook, and cancel/revise.

Covers MB-3.1, MB-3.3 and MB-4.2/4.3/4.4. Two rules shape everything here:

* **INV-2 — this module never writes ``subscriptions`` directly.** Every state
  change goes through ``app.billing.lifecycle``, and for customer-driven changes
  the *webhook* is the writer: `/subscribe` and `/cancel` ask PayPal to do
  something and return; our row moves when PayPal tells us it moved. A cancel
  that optimistically flipped our status would lock a customer out of a
  subscription PayPal then failed to cancel.
* **INV-5 — the 402 is the paywall.** These endpoints report entitlements for
  the UI to render, but the UI is cosmetic; the gates in ``app.billing.gates``
  are what a request bypassing it hits.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import catalogue, lifecycle, metering, paypal_client
from app.billing.constants import SUBSCRIPTION_STATUSES
from app.billing.entitlements import Entitlements, get_entitlements, resolve_entitlements
from app.config import settings
from app.db.session import get_db
from app.dependencies import get_current_org, require_role
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# --- Schemas ---------------------------------------------------------------


class PlanOut(BaseModel):
    plan_code: str
    model: str
    display_name: str
    price_year_cents: int
    seats: int
    max_companies: int | None
    max_sites: int | None
    ai_credits_year: int | None
    features: dict


class UsageOut(BaseModel):
    ai_credits_used: int
    ai_credits_included: int | None
    ai_credits_overage: int
    ai_credits_allowance: int | None
    ai_credits_remaining: int | None
    active_companies: int
    max_companies: int | None


class EntitlementsOut(BaseModel):
    account_type: str
    plan_code: str
    status: str
    is_active: bool
    # None = all 17 document types.
    allowed_doc_types: list[str] | None
    seats: int
    max_companies: int | None
    max_sites: int | None
    ai_credits_year: int | None
    features: dict
    period_start: str | None
    period_end: str | None
    # False while ENTITLEMENTS_ENFORCE is off: the UI should still *show* limits
    # but must not tell the user an action is blocked when it will succeed.
    enforced: bool
    usage: UsageOut


class SubscribeIn(BaseModel):
    plan_code: str = Field(min_length=1, max_length=32)


class SubscribeOut(BaseModel):
    approval_url: str
    paypal_subscription_id: str


class CancelIn(BaseModel):
    reason: str = Field(default="Richiesta dell'utente", max_length=127)


class SetPlanIn(BaseModel):
    plan_code: str = Field(min_length=1, max_length=32)
    status: str = "active"
    months: int = Field(default=12, ge=1, le=60)


# --- MB-3.3 — what am I entitled to -----------------------------------------


async def _entitlements_out(
    org_id: uuid.UUID, ent: Entitlements, db: AsyncSession
) -> EntitlementsOut:
    usage = await metering.usage_summary(org_id, db, ent)
    return EntitlementsOut(
        account_type=ent.account_type,
        plan_code=ent.plan_code,
        status=ent.status,
        is_active=ent.is_active,
        allowed_doc_types=(
            None if ent.allowed_doc_types is None else sorted(ent.allowed_doc_types)
        ),
        seats=ent.seats,
        max_companies=ent.max_companies,
        max_sites=ent.max_sites,
        ai_credits_year=ent.ai_credits_year,
        features=ent.features,
        period_start=ent.period_start.isoformat() if ent.period_start else None,
        period_end=ent.period_end.isoformat() if ent.period_end else None,
        enforced=settings.ENTITLEMENTS_ENFORCE,
        usage=UsageOut(**usage),
    )


@router.get("/entitlements", response_model=EntitlementsOut)
async def get_my_entitlements(
    org_id: uuid.UUID = Depends(get_current_org),
    ent: Entitlements = Depends(get_entitlements),
    db: AsyncSession = Depends(get_db),
) -> EntitlementsOut:
    """The resolved plan plus current usage. Drives the whole billing UI."""
    return await _entitlements_out(org_id, ent, db)


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(
    ent: Entitlements = Depends(get_entitlements),
    db: AsyncSession = Depends(get_db),
) -> list[PlanOut]:
    """Plans this tenant can buy — its own channel only, and only checkoutable ones."""
    plans = await catalogue.list_purchasable(db, account_type=ent.account_type)
    return [
        PlanOut(
            plan_code=p.plan_code,
            model=p.model,
            display_name=p.display_name,
            price_year_cents=p.price_year_cents,
            seats=p.seats,
            max_companies=p.max_companies,
            max_sites=p.max_sites,
            ai_credits_year=p.ai_credits_year,
            features=p.features,
        )
        for p in plans
    ]


# --- MB-4.2 — start a subscription ------------------------------------------


@router.post("/subscribe", response_model=SubscribeOut)
async def subscribe(
    body: SubscribeIn,
    user: User = Depends(require_role("admin")),
    ent: Entitlements = Depends(get_entitlements),
    db: AsyncSession = Depends(get_db),
) -> SubscribeOut:
    """Create a PayPal subscription and hand back its approval URL.

    Admin-only: this commits the organization to a recurring charge.

    Nothing about our subscription row changes here. The customer has not paid
    yet — they have not even left for PayPal — so the plan moves only when the
    ``ACTIVATED`` webhook confirms it (MB-4.3).
    """
    org_id = user.organization_id

    if not paypal_client.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pagamenti non configurati su questo ambiente.",
        )

    plan = await catalogue.get_plan(body.plan_code, db)
    if plan is None:
        raise HTTPException(status_code=404, detail="Piano non trovato.")
    if not plan.is_checkoutable:
        # Either the Phase-4 setup script has not run, or this is A_FOUNDING.
        logger.error(
            "billing: plan %s is not checkoutable (paypal_plan_id=%r, price=%d)",
            plan.plan_code, plan.paypal_plan_id, plan.price_year_cents,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Questo piano non è acquistabile online. Contatta il supporto.",
        )
    if plan.model != ("A" if ent.account_type == "consultant" else "B"):
        # The channel-conflict guardrail (INV-9) applied to purchasing, not just
        # to document types: a direct company must not buy a consultant plan.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Questo piano non è disponibile per il tuo tipo di account.",
        )

    try:
        resource = await paypal_client.create_subscription(
            plan.paypal_plan_id,
            custom_id=str(org_id),
            return_url=f"{settings.FRONTEND_URL}/billing?esito=ok",
            cancel_url=f"{settings.FRONTEND_URL}/billing?esito=annullato",
            brand_name=settings.PAYPAL_BRAND_NAME,
            subscriber_email=user.email,
        )
    except paypal_client.PayPalError:
        logger.exception("billing: PayPal refused to create a subscription for org %s", org_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="PayPal non ha potuto creare l'abbonamento. Riprova più tardi.",
        )

    url = paypal_client.approval_link(resource)
    if not url:
        logger.error("billing: PayPal subscription %s has no approve link", resource.get("id"))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="PayPal non ha restituito un link di approvazione.",
        )

    logger.info(
        "billing: org %s started checkout for %s (PayPal %s)",
        org_id, plan.plan_code, resource.get("id"),
    )
    return SubscribeOut(approval_url=url, paypal_subscription_id=resource["id"])


# --- MB-4.4 — cancel / change plan ------------------------------------------


@router.post("/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel(
    body: CancelIn,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Ask PayPal to cancel. Our status changes when the webhook says so.

    202, not 200: the cancellation is accepted, not yet reflected locally. The
    customer keeps access until the webhook lands — which is correct, since they
    have paid for the period either way.
    """
    org_id = user.organization_id
    subscription_id = await lifecycle.get_paypal_subscription_id(org_id, db)

    if not subscription_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nessun abbonamento PayPal attivo da disdire.",
        )

    try:
        await paypal_client.cancel_subscription(subscription_id, body.reason)
    except paypal_client.PayPalError:
        logger.exception("billing: cancel failed for org %s (%s)", org_id, subscription_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="PayPal non ha potuto annullare l'abbonamento. Riprova più tardi.",
        )

    logger.info("billing: org %s requested cancellation of %s", org_id, subscription_id)
    return {
        "status": "accepted",
        "detail": (
            "Disdetta inviata a PayPal. L'abbonamento resta attivo fino alla fine "
            "del periodo già pagato."
        ),
    }


@router.post("/revise", response_model=SubscribeOut)
async def revise(
    body: SubscribeIn,
    user: User = Depends(require_role("admin")),
    ent: Entitlements = Depends(get_entitlements),
    db: AsyncSession = Depends(get_db),
) -> SubscribeOut:
    """Change plan on a live subscription. Returns a fresh approval link."""
    org_id = user.organization_id
    subscription_id = await lifecycle.get_paypal_subscription_id(org_id, db)

    if not subscription_id:
        # Nothing to revise — this tenant has never checked out. Sending them
        # through /subscribe is the correct path, so say so rather than 500.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nessun abbonamento PayPal da modificare: attivane uno.",
        )

    plan = await catalogue.get_plan(body.plan_code, db)
    if plan is None or not plan.is_checkoutable:
        raise HTTPException(status_code=404, detail="Piano non disponibile.")
    if plan.plan_code == ent.plan_code:
        raise HTTPException(status_code=409, detail="Sei già su questo piano.")

    try:
        resource = await paypal_client.revise_subscription(
            subscription_id,
            plan.paypal_plan_id,
            return_url=f"{settings.FRONTEND_URL}/billing?esito=ok",
            cancel_url=f"{settings.FRONTEND_URL}/billing?esito=annullato",
        )
    except paypal_client.PayPalError:
        logger.exception("billing: revise failed for org %s (%s)", org_id, subscription_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="PayPal non ha potuto modificare l'abbonamento. Riprova più tardi.",
        )

    url = paypal_client.approval_link(resource)
    if not url:
        # A revise that needs no re-approval returns no link. The plan change is
        # already in flight at PayPal and its webhook will carry it.
        return SubscribeOut(approval_url="", paypal_subscription_id=subscription_id)
    return SubscribeOut(approval_url=url, paypal_subscription_id=subscription_id)


# --- MB-4.3 — the webhook (sole writer of subscription state) ---------------

# Events we act on. Anything else is recorded and ignored — PayPal sends far
# more than this, and an unrecognised type must be a no-op, never an error that
# makes PayPal retry forever.
_SUBSCRIPTION_EVENTS = {
    "BILLING.SUBSCRIPTION.CREATED",
    "BILLING.SUBSCRIPTION.ACTIVATED",
    "BILLING.SUBSCRIPTION.UPDATED",
    "BILLING.SUBSCRIPTION.SUSPENDED",
    "BILLING.SUBSCRIPTION.CANCELLED",
    "BILLING.SUBSCRIPTION.EXPIRED",
    "BILLING.SUBSCRIPTION.PAYMENT.FAILED",
}
# Payment events carry a `billing_agreement_id` rather than a subscription id.
_PAYMENT_EVENTS = {"PAYMENT.SALE.COMPLETED", "PAYMENT.SALE.DENIED", "PAYMENT.SALE.REFUNDED"}

_CLAIM_EVENT = text(
    """
    INSERT INTO billing_webhook_events (event_id, event_type, resource_id)
    VALUES (:event_id, :event_type, :resource_id)
    ON CONFLICT (event_id) DO NOTHING
    RETURNING event_id
    """
)

_FINISH_EVENT = text(
    """
    UPDATE billing_webhook_events
       SET processed_at = now(), outcome = :outcome
     WHERE event_id = :event_id
    """
)


@router.post("/webhook", include_in_schema=False)
async def paypal_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Receive a PayPal event. Verified, idempotent, and the only status writer.

    Always answers 200 once an event is verified and claimed, including for
    events we ignore — a non-2xx makes PayPal retry, and retrying an event we
    have deliberately skipped achieves nothing but noise. Genuine failures
    (a PayPal read that errors) do raise, so the retry is useful.

    Unverified events get 401 and are not recorded: an attacker must not be able
    to fill the ledger, and PayPal will not be sending them anyway.
    """
    raw = await request.body()

    if not await paypal_client.verify_webhook_signature(dict(request.headers), raw):
        logger.error("billing webhook: signature verification failed — rejecting")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
        )

    try:
        event = json.loads(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Malformed JSON")

    event_id = event.get("id")
    event_type = event.get("event_type", "")
    resource = event.get("resource") or {}
    if not event_id:
        raise HTTPException(status_code=400, detail="Event has no id")

    # A subscription event's resource IS the subscription; a payment event's
    # resource points at one via billing_agreement_id.
    resource_id = (
        resource.get("id") if event_type in _SUBSCRIPTION_EVENTS
        else resource.get("billing_agreement_id")
    )

    claimed = (
        await db.execute(
            _CLAIM_EVENT,
            {"event_id": event_id[:64], "event_type": event_type[:64],
             "resource_id": (resource_id or None) and str(resource_id)[:64]},
        )
    ).first()
    if claimed is None:
        # Someone already handled it. PayPal retries aggressively; this is the
        # normal path for a duplicate, not an error.
        await db.commit()
        logger.info("billing webhook: %s (%s) already handled", event_id, event_type)
        return {"status": "duplicate"}
    await db.commit()

    outcome = "ignored: unhandled event type"
    try:
        if event_type in _SUBSCRIPTION_EVENTS and resource_id:
            outcome = await lifecycle.sync_from_paypal(str(resource_id), db)
        elif event_type in _PAYMENT_EVENTS and resource_id:
            # Re-reading the subscription picks up the new next_billing_time,
            # which is what rolls the usage meters into the new period.
            outcome = await lifecycle.sync_from_paypal(str(resource_id), db)
        await db.execute(_FINISH_EVENT, {"event_id": event_id[:64], "outcome": outcome[:2000]})
        await db.commit()
    except Exception:
        # Leave processed_at NULL so the row reads as "claimed but unfinished",
        # and let PayPal's retry try again — but the claim is already committed,
        # so clear it or the retry would be swallowed as a duplicate.
        logger.exception("billing webhook: handling %s (%s) failed", event_id, event_type)
        await db.rollback()
        await db.execute(
            text("DELETE FROM billing_webhook_events WHERE event_id = :e AND processed_at IS NULL"),
            {"e": event_id[:64]},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook handling failed",
        )

    logger.info("billing webhook: %s (%s) -> %s", event_id, event_type, outcome)
    return {"status": "ok", "outcome": outcome}


# --- MB-3.1 — admin: set a plan by hand -------------------------------------


@router.post("/admin/organizations/{organization_id}/plan", response_model=EntitlementsOut)
async def admin_set_plan(
    organization_id: uuid.UUID,
    body: SetPlanIn,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> EntitlementsOut:
    """Put an organization on a plan without PayPal (invoice paid off-platform).

    How the first consultant deals actually close: bank transfer, then this.
    Also the enterprise path, where the price is negotiated per deal.
    """
    if body.status not in SUBSCRIPTION_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {sorted(SUBSCRIPTION_STATUSES)}",
        )
    if not await catalogue.plan_code_exists(body.plan_code, db):
        raise HTTPException(status_code=404, detail="Piano non trovato.")

    now = datetime.now(timezone.utc)
    # Calendar-month arithmetic without a dependency: 30-day months are close
    # enough for a manually-administered term, and the exact end date is
    # whatever the admin agreed commercially anyway.
    await lifecycle.set_plan_manually(
        org_id=organization_id,
        plan_code=body.plan_code,
        status=body.status,
        period_start=now,
        period_end=now + timedelta(days=30 * body.months),
        db=db,
    )
    await db.commit()

    ent = await resolve_entitlements(organization_id, db)
    logger.info(
        "billing: admin put org %s on %s (%s) for %d months",
        organization_id, body.plan_code, body.status, body.months,
    )
    return await _entitlements_out(organization_id, ent, db)
