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

from app.billing import (
    catalogue,
    credit_packs,
    credits as credits_ledger,
    lifecycle,
    metering,
    paypal_client,
)
from app.billing.constants import SUBSCRIPTION_STATUSES
from app.billing.entitlements import Entitlements, get_entitlements, resolve_entitlements
from app.config import settings
from app.db.session import get_db
from app.core.permissions import BILLING_MANAGE, BILLING_READ
from app.dependencies import get_current_org, require_capability
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


class UsageKindOut(BaseModel):
    """One row of "where did the credits go" for the current period."""

    kind: str
    actions: int
    credits: int


class UsageOut(BaseModel):
    ai_credits_used: int
    ai_credits_included: int | None
    ai_credits_overage: int
    ai_credits_allowance: int | None
    ai_credits_remaining: int | None
    active_companies: int
    max_companies: int | None
    # Empty until the tenant spends something. Ordered by credits descending, so
    # the UI can render it as a breakdown without sorting client-side.
    by_kind: list[UsageKindOut] = Field(default_factory=list)


class EntitlementsOut(BaseModel):
    account_type: str
    # None = the org has never bought a plan. The UI must render a call to
    # action, not a plan code the customer does not hold (MB-6.1).
    plan_code: str | None
    status: str
    is_active: bool
    # False = never purchased. Distinct from `is_active`, which is also false
    # for a lapsed subscription — "attiva un piano" vs "rinnova".
    subscribed: bool
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
    usage["by_kind"] = await metering.usage_by_kind(org_id, db, ent)
    return EntitlementsOut(
        account_type=ent.account_type,
        plan_code=ent.plan_code,
        status=ent.status,
        is_active=ent.is_active,
        subscribed=ent.subscribed,
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


# --- Credit packs (D-14) ----------------------------------------------------
#
# Top-ups are a one-time PayPal *order*, not a subscription: the customer picks a
# pack, approves once, and the credits land on the current period's counter. The
# grant is guarded by `credit_purchases.status`, so the browser return and the
# webhook can both report the same payment without crediting it twice.


class CreditPackOut(BaseModel):
    pack_code: str
    display_name: str
    credits: int
    price_cents: int
    description: str
    #: Cents per credit — lets the UI show the bulk discount without arithmetic.
    price_per_credit_cents: float
    recommended: bool = False


class CreditCheckoutIn(BaseModel):
    pack_code: str = Field(min_length=1, max_length=32)


class CreditCheckoutOut(BaseModel):
    approval_url: str
    paypal_order_id: str
    purchase_id: uuid.UUID


class CreditCaptureIn(BaseModel):
    paypal_order_id: str = Field(min_length=1, max_length=64)


class CreditPurchaseOut(BaseModel):
    id: uuid.UUID
    pack_code: str
    display_name: str
    credits: int
    amount_cents: int
    currency: str
    status: str
    period_start: str
    created_at: str
    completed_at: str | None


class CreditCaptureOut(BaseModel):
    # False when the order was already settled by the other path. Not an error:
    # the credits are on the account either way, which is what the customer
    # asked about.
    granted: bool
    credits: int
    purchase: CreditPurchaseOut | None
    usage: UsageOut


def _pack_out(pack: dict) -> CreditPackOut:
    return CreditPackOut(
        pack_code=pack["pack_code"],
        display_name=pack["display_name"],
        credits=pack["credits"],
        price_cents=pack["price_cents"],
        description=pack["description"],
        price_per_credit_cents=round(credit_packs.price_per_credit_cents(pack), 3),
        recommended=bool(pack.get("recommended")),
    )


def _purchase_out(record: credits_ledger.PurchaseRecord) -> CreditPurchaseOut:
    pack = credit_packs.get_pack(record.pack_code)
    return CreditPurchaseOut(
        id=record.id,
        pack_code=record.pack_code,
        # Retired packs keep their receipts readable: fall back to the credit
        # count rather than printing an internal code at the customer.
        display_name=(pack or {}).get("display_name") or f"{record.credits} crediti",
        credits=record.credits,
        amount_cents=record.amount_cents,
        currency=record.currency,
        status=record.status,
        period_start=record.period_start.isoformat(),
        created_at=record.created_at.isoformat(),
        completed_at=record.completed_at.isoformat() if record.completed_at else None,
    )


@router.get("/credits/packs", response_model=list[CreditPackOut])
async def list_credit_packs(
    _user: User = Depends(require_capability(BILLING_READ)),
) -> list[CreditPackOut]:
    """The top-up catalogue. Same packs for both channels (INV-4)."""
    return [_pack_out(p) for p in credit_packs.CREDIT_PACKS]


@router.get("/credits/purchases", response_model=list[CreditPurchaseOut])
async def list_credit_purchases(
    _user: User = Depends(require_capability(BILLING_READ)),
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[CreditPurchaseOut]:
    """Recent top-up receipts, newest first."""
    return [_purchase_out(r) for r in await credits_ledger.list_purchases(org_id, db)]


@router.post("/credits/checkout", response_model=CreditCheckoutOut)
async def checkout_credits(
    body: CreditCheckoutIn,
    user: User = Depends(require_capability(BILLING_MANAGE)),
    ent: Entitlements = Depends(get_entitlements),
    db: AsyncSession = Depends(get_db),
) -> CreditCheckoutOut:
    """Open a PayPal order for one credit pack and hand back its approval URL.

    Requires a live subscription. Packs *extend* an allowance — they are not a
    way to buy AI without a plan, and selling one to an unsubscribed tenant
    would hand them credits that ``ensure_subscription_active`` still refuses to
    let them use for generation. Pooled/unmetered tenants are refused for the
    opposite reason: there is no ceiling to raise.
    """
    org_id = user.organization_id

    pack = credit_packs.get_pack(body.pack_code)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pacchetto crediti non trovato.")

    if not ent.subscribed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Attiva prima un abbonamento: i pacchetti di crediti si aggiungono "
                "a un piano esistente."
            ),
        )
    if not ent.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Il tuo abbonamento non è attivo. Rinnovalo per poter acquistare "
                "crediti aggiuntivi."
            ),
        )
    if ent.credits_unmetered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Il tuo piano include crediti AI illimitati: non servono pacchetti aggiuntivi.",
        )
    if not paypal_client.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pagamenti non configurati su questo ambiente.",
        )

    # Written before PayPal is called so the order can carry our row id: a paid
    # order we cannot map back to a purchase is the one failure mode with no
    # recovery that doesn't involve reading PayPal's dashboard by hand.
    purchase = await credits_ledger.start_purchase(
        org_id=org_id,
        user_id=user.id,
        pack=pack,
        period_start=ent.meter_period_start,
        db=db,
    )
    purchase_id = purchase.id
    await db.commit()

    try:
        resource = await paypal_client.create_order(
            amount_cents=pack["price_cents"],
            currency="EUR",
            description=f"N2O DVR — {pack['display_name']} AI",
            custom_id=str(org_id),
            reference_id=str(purchase_id),
            return_url=f"{settings.FRONTEND_URL}/billing?crediti=ok",
            cancel_url=f"{settings.FRONTEND_URL}/billing?crediti=annullato",
            brand_name=settings.PAYPAL_BRAND_NAME,
            request_id=str(purchase_id),
        )
    except paypal_client.PayPalError:
        logger.exception("billing: PayPal refused a credit order for org %s", org_id)
        await credits_ledger.abandon(purchase_id, db)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="PayPal non ha potuto avviare il pagamento. Riprova più tardi.",
        )

    order_id = resource.get("id")
    url = paypal_client.approval_link(resource)
    if not order_id or not url:
        logger.error("billing: PayPal credit order for org %s has no id/approve link", org_id)
        await credits_ledger.abandon(purchase_id, db)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="PayPal non ha restituito un link di pagamento.",
        )

    await credits_ledger.attach_order(purchase_id, str(order_id), db)
    await db.commit()

    logger.info(
        "billing: org %s started a credit checkout for %s (PayPal order %s)",
        org_id, pack["pack_code"], order_id,
    )
    return CreditCheckoutOut(
        approval_url=url, paypal_order_id=str(order_id), purchase_id=purchase_id
    )


@router.post("/credits/capture", response_model=CreditCaptureOut)
async def capture_credits(
    body: CreditCaptureIn,
    user: User = Depends(require_capability(BILLING_MANAGE)),
    ent: Entitlements = Depends(get_entitlements),
    db: AsyncSession = Depends(get_db),
) -> CreditCaptureOut:
    """Take the money for an approved order and credit the account.

    Called by the browser on its way back from PayPal. The webhook is the
    backstop for the customer who closes the tab mid-redirect, so both paths run
    the same :func:`credits_ledger.complete_purchase` and the row status decides
    which one actually grants.

    Reports the resulting balance so the UI can update the tracker without a
    second round trip — the number the customer just paid to change is the one
    thing they are looking at.
    """
    org_id = user.organization_id
    order_id = body.paypal_order_id.strip()

    purchase = await credits_ledger.find_by_order(order_id, db)
    if purchase is None or purchase.organization_id != org_id:
        # Never confirm the existence of another tenant's order.
        raise HTTPException(status_code=404, detail="Ordine non trovato.")

    if purchase.status != "completed":
        try:
            resource = await paypal_client.capture_order(order_id)
        except paypal_client.PayPalOrderNotApproved:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Il pagamento non è stato approvato su PayPal. Nessun addebito effettuato.",
            )
        except paypal_client.PayPalError:
            logger.exception("billing: capture failed for order %s (org %s)", order_id, org_id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="PayPal non ha potuto completare il pagamento. Riprova più tardi.",
            )

        if not paypal_client.order_is_paid(resource):
            # Approved but not captured is a PayPal state we must not treat as
            # paid: granting credits here would be giving away product.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Il pagamento risulta non completato. Nessun credito è stato aggiunto.",
            )

    record = await credits_ledger.complete_purchase(order_id, db)
    await db.commit()

    # Re-read after the grant: `ent` was resolved before the credits landed.
    fresh = await resolve_entitlements(org_id, db)
    usage = await metering.usage_summary(org_id, db, fresh)
    usage["by_kind"] = await metering.usage_by_kind(org_id, db, fresh)

    return CreditCaptureOut(
        granted=record is not None,
        credits=record.credits if record else purchase.credits,
        purchase=_purchase_out(record) if record else None,
        usage=UsageOut(**usage),
    )


@router.post("/credits/abandon", status_code=status.HTTP_204_NO_CONTENT)
async def abandon_credits(
    body: CreditCaptureIn,
    user: User = Depends(require_capability(BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark a checkout the customer cancelled, so the history reads honestly.

    Best-effort housekeeping, not a money path: `abandon` only ever moves a
    *pending* row, so a cancel callback that arrives after the webhook has
    already banked the payment cannot undo it.
    """
    purchase = await credits_ledger.find_by_order(body.paypal_order_id.strip(), db)
    if purchase is None or purchase.organization_id != user.organization_id:
        return
    await credits_ledger.abandon(purchase.id, db)
    await db.commit()


# --- MB-4.2 — start a subscription ------------------------------------------


@router.post("/subscribe", response_model=SubscribeOut)
async def subscribe(
    body: SubscribeIn,
    user: User = Depends(require_capability(BILLING_MANAGE)),
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

    # Business rules before environment ones. A direct tenant POSTing a Model A
    # plan code must be told it is not available to them (403) regardless of
    # whether PayPal happens to be configured on this deploy — answering 503
    # describes our infrastructure when the request was never permissible in the
    # first place, and made `test_a_direct_tenant_cannot_buy_a_consultant_plan`
    # fail on any environment without credentials.
    plan = await catalogue.get_plan(body.plan_code, db)
    if plan is None:
        raise HTTPException(status_code=404, detail="Piano non trovato.")
    if plan.model != ("A" if ent.account_type == "consultant" else "B"):
        # The channel-conflict guardrail (INV-9) applied to purchasing, not just
        # to document types: a direct company must not buy a consultant plan.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Questo piano non è disponibile per il tuo tipo di account.",
        )
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

    if not paypal_client.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pagamenti non configurati su questo ambiente.",
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
    user: User = Depends(require_capability(BILLING_MANAGE)),
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
    user: User = Depends(require_capability(BILLING_MANAGE)),
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
# One-time credit-pack orders. `CHECKOUT.ORDER.APPROVED` fires before the money
# moves, so only the capture counts — approving and then abandoning must never
# grant credits. This is the backstop for the customer who closes the tab during
# the redirect; the browser's `/credits/capture` normally gets there first, and
# the row-status guard makes whichever loses a no-op.
_ORDER_CAPTURE_EVENTS = {"PAYMENT.CAPTURE.COMPLETED"}

def _order_id_of_capture(resource: dict) -> str | None:
    """The order id behind a ``PAYMENT.CAPTURE.COMPLETED`` resource.

    The event's own ``id`` is the *capture* id, which matches nothing on our
    side. PayPal puts the order id under ``supplementary_data.related_ids``;
    ``links`` carries it too, as the ``up`` relation, which is the fallback for
    the accounts where the supplementary block comes back empty.
    """
    related = (resource.get("supplementary_data") or {}).get("related_ids") or {}
    order_id = related.get("order_id")
    if order_id:
        return str(order_id)
    for link in resource.get("links") or []:
        if link.get("rel") == "up":
            href = link.get("href") or ""
            tail = href.rstrip("/").rsplit("/", 1)[-1]
            if tail and "checkout/orders" in href:
                return tail
    return None


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
    # resource points at one via billing_agreement_id; a capture's resource is
    # the capture, whose order id hides in supplementary_data.
    if event_type in _SUBSCRIPTION_EVENTS:
        resource_id = resource.get("id")
    elif event_type in _ORDER_CAPTURE_EVENTS:
        resource_id = _order_id_of_capture(resource)
    else:
        resource_id = resource.get("billing_agreement_id")

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
        elif event_type in _ORDER_CAPTURE_EVENTS and resource_id:
            # A subscription renewal can also arrive as a capture. Only an order
            # we opened for a credit pack has a `credit_purchases` row, so an
            # unknown order id is a legitimate no-op rather than an error.
            record = await credits_ledger.complete_purchase(str(resource_id), db)
            outcome = (
                f"credit pack granted: +{record.credits} ({record.pack_code})"
                if record
                else "ignored: no pending credit purchase for this order"
            )
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
    _admin: User = Depends(require_capability(BILLING_MANAGE)),
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
