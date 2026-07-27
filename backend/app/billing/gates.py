"""Entitlement gates — the decisions, and whether they bite yet.

Every gate has the same two-mode shape (MB-1.5):

* ``settings.ENTITLEMENTS_ENFORCE`` **false** (default) — compute the decision,
  log what *would* have happened, and allow. This is shadow mode: it is how we
  learn, against real traffic, whether the rules would block legitimate work
  before they can actually do it (INV-1).
* **true** — the same decision, but a denial raises ``402 Payment Required``.

The 402 is the real paywall (INV-5). Frontend gating is cosmetic; these
functions run inside FastAPI and are what a request bypassing the UI hits.

Shadow lines are greppable on purpose::

    WOULD_BLOCK reason=doc_type org=… plan=B_BASE detail=pos
    WOULD_402   reason=credits  org=… plan=A_SOLO detail=need 8, 3 left

Denial messages are Italian: they surface directly in the operator's UI.
"""

import logging
import uuid

from fastapi import HTTPException, status

from app.billing.entitlements import Entitlements
from app.config import settings

logger = logging.getLogger(__name__)

# 402 rather than 403: this is "your plan doesn't cover it, pay to proceed",
# not "you lack permission". The frontend keys the upgrade prompt off it.
_PAYMENT_REQUIRED = status.HTTP_402_PAYMENT_REQUIRED


def _deny(
    *,
    reason: str,
    org_id: uuid.UUID | None,
    ent: Entitlements,
    detail_log: str,
    detail_user: str,
) -> None:
    """Raise when enforcing, otherwise record what would have happened.

    Never raises while ``ENTITLEMENTS_ENFORCE`` is false — that is the whole
    point of the shadow period.
    """
    if settings.ENTITLEMENTS_ENFORCE:
        raise HTTPException(status_code=_PAYMENT_REQUIRED, detail=detail_user)
    logger.info(
        "WOULD_402 reason=%s org=%s plan=%s account_type=%s detail=%s",
        reason, org_id, ent.plan_code, ent.account_type, detail_log,
    )


def ensure_doc_type_allowed(
    ent: Entitlements, tipo: str | None, org_id: uuid.UUID | None = None
) -> None:
    """Gate a document type against the plan (MB-2.1, INV-9).

    Model A plans carry ``allowed_doc_types = NULL`` and pass everything. The
    explicit subsets on Model B plans are the channel-conflict contract — this
    is what stops POS reaching a direct tenant.
    """
    if ent.allows_doc_type(tipo):
        return
    _deny(
        reason="doc_type",
        org_id=org_id,
        ent=ent,
        detail_log=str(tipo),
        detail_user=(
            "Questo documento non è incluso nel tuo piano. "
            "Effettua l'upgrade per generarlo."
        ),
    )


def ensure_seat_available(
    ent: Entitlements, current_seats: int, org_id: uuid.UUID | None = None
) -> None:
    """Gate adding a user beyond the plan's seat count (MB-2.5).

    ``current_seats`` is the count *before* adding, so the check is whether one
    more still fits.
    """
    if current_seats + 1 <= ent.seats:
        return
    _deny(
        reason="seats",
        org_id=org_id,
        ent=ent,
        detail_log=f"{current_seats + 1} > {ent.seats}",
        detail_user=(
            f"Il tuo piano include {ent.seats} utenti. "
            "Effettua l'upgrade per aggiungerne altri."
        ),
    )


def ensure_company_slot(
    ent: Entitlements,
    active_companies: int,
    already_active: bool,
    org_id: uuid.UUID | None = None,
) -> None:
    """Gate activating one more client company this period (MB-2.3, Model A).

    Only a company's **first** activation in the period consumes a slot — a
    company already counted this period is free to keep generating, which is
    why ``already_active`` short-circuits before the ceiling is consulted.
    ``max_companies = None`` means unlimited.
    """
    if already_active or ent.max_companies is None:
        return
    if active_companies + 1 <= ent.max_companies:
        return
    _deny(
        reason="companies",
        org_id=org_id,
        ent=ent,
        detail_log=f"{active_companies + 1} > {ent.max_companies} in period {ent.meter_period_start}",
        detail_user=(
            f"Hai raggiunto il limite di {ent.max_companies} aziende attive per il periodo. "
            "Effettua l'upgrade per aggiungerne altre."
        ),
    )


def ensure_site_slot(
    ent: Entitlements, current_sites: int, org_id: uuid.UUID | None = None
) -> None:
    """Gate adding a sede / unità locale beyond the plan (Model B)."""
    if ent.max_sites is None:
        return
    if current_sites + 1 <= ent.max_sites:
        return
    _deny(
        reason="sites",
        org_id=org_id,
        ent=ent,
        detail_log=f"{current_sites + 1} > {ent.max_sites}",
        detail_user=(
            f"Il tuo piano include {ent.max_sites} sedi. "
            "Effettua l'upgrade per aggiungerne altre."
        ),
    )


def ensure_subscription_active(ent: Entitlements, org_id: uuid.UUID | None = None) -> None:
    """Gate write operations for a lapsed subscription (MB-4.5).

    ``past_due`` deliberately still passes: Stripe Smart Retries run for days
    and a customer must not lose their DVR mid-dunning. Read and download paths
    must never call this — a canceled tenant keeps access to documents it
    already generated, which D.Lgs. 81/2008 retention requires.
    """
    if ent.is_active:
        return
    _deny(
        reason="subscription",
        org_id=org_id,
        ent=ent,
        detail_log=ent.status,
        detail_user=(
            "Il tuo abbonamento non è attivo. "
            "Puoi consultare e scaricare i documenti esistenti, ma non generarne di nuovi."
        ),
    )
