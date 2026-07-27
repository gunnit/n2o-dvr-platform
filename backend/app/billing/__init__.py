"""Monetization: plan catalogue, entitlements, and usage metering.

This package is the *only* seam between the product and commercial concerns.
Two rules keep it that way (see docs/build/MONETIZATION-BUILD-PLAN.md §2):

* **INV-8** — ``services/document_generator/*`` must never import this package.
  Regulatory content stays single-sourced and billing-agnostic. Enforced by
  ``.importlinter``.
* **INV-4** — Model A (consultants) and Model B (direct companies) differ only
  as rows in the ``plans`` catalogue. No ``if account_type == "direct"``
  business logic anywhere.

Nothing here is wired into a request path during Phase 0; the resolver is
additive and every enforcement gate lands later behind
``settings.ENTITLEMENTS_ENFORCE``.
"""

from app.billing.constants import (
    ALL_DOC_TYPES,
    CREDIT_WEIGHTS,
    FOUNDING_PLAN_CODE,
    PLAN_CODES,
    normalize_doc_type,
)
from app.billing.entitlements import (
    Entitlements,
    get_entitlements,
    resolve_entitlements,
)
from app.billing.gates import (
    ensure_company_slot,
    ensure_doc_type_allowed,
    ensure_seat_available,
    ensure_site_slot,
    ensure_subscription_active,
)
from app.billing.metering import (
    count_active_companies,
    is_company_active,
    record_active_company,
    refund_credits,
    spend_credits,
)

__all__ = [
    "ALL_DOC_TYPES",
    "CREDIT_WEIGHTS",
    "FOUNDING_PLAN_CODE",
    "PLAN_CODES",
    "normalize_doc_type",
    "Entitlements",
    "get_entitlements",
    "resolve_entitlements",
    "ensure_company_slot",
    "ensure_doc_type_allowed",
    "ensure_seat_available",
    "ensure_site_slot",
    "ensure_subscription_active",
    "count_active_companies",
    "is_company_active",
    "record_active_company",
    "refund_credits",
    "spend_credits",
]
