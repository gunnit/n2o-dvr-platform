"""Billing constants: doc-type registry, credit weights, plan codes.

Nothing here encodes prices or per-plan limits — those are **data** in the
``plans`` table (INV-4), seeded by MB-1.2/MB-5.1. This module only holds the
vocabulary both sides agree on.
"""

from app.services.document_generator.dispatcher import ALL_DOCUMENT_TYPES

# --- Document types -------------------------------------------------------
# Single source of truth is the dispatcher registry (INV-8): billing may *read*
# the doc-type registry but must never be imported by the generators.
#
# Casing note (drift found 2026-07-27, plan §6 corrected): the dispatcher
# constant is UPPERCASE (``DVR_MASTER``) and `get_generator_for` normalizes its
# argument with `.upper()`, so dispatch is case-insensitive. But the value that
# actually travels the wire and lands in `documenti_generati.tipo_documento` is
# **lowercase** — the frontend catalogue (`components/documents/document-types.ts`)
# emits `dvr_master`, and `api/v1/documents.py` compares against the lowercase
# literal. Lowercase is therefore the canonical form for entitlement checks, and
# every comparison must go through `normalize_doc_type` rather than trusting the
# caller's casing.


def normalize_doc_type(tipo: str | None) -> str:
    """Canonicalize a ``tipo_documento`` for entitlement comparison.

    Mirrors the dispatcher's own normalization (`.replace("-", "_")`) but folds
    to lowercase, the form used on the wire and in the database.
    """
    return (tipo or "").strip().lower().replace("-", "_")


ALL_DOC_TYPES: frozenset[str] = frozenset(normalize_doc_type(t) for t in ALL_DOCUMENT_TYPES)

# Canary: if a generator is added or removed, the plan catalogue's per-plan
# doc-type maps (plan §6) need revisiting. Fail loudly at import rather than
# silently entitling/withholding a new document type.
assert len(ALL_DOC_TYPES) == 17, (
    f"Expected 17 document types from the dispatcher registry, got {len(ALL_DOC_TYPES)}. "
    "A generator was added or removed — review the per-plan allowed_doc_types maps "
    "(docs/build/MONETIZATION-BUILD-PLAN.md §6) before shipping."
)

# --- AI credit weights ----------------------------------------------------
# Cost proxy per AI action, charged at the API endpoint (one layer above
# `services/ai/client.py`, which stays OpenAI/privacy-only — INV-8).
CREDIT_WEIGHTS: dict[str, int] = {
    "reasoning": 1,   # suggesters: rischi, DPI, misure, HACCP CCP, POS phases, stress
    "vision": 4,      # equipment recognized from a photo
    "sds": 8,         # Safety Data Sheet PDF extraction (gpt-5.5 vision)
    "visura": 15,     # Registro Imprese / openapi.com lookup (billed per call upstream)
}

# --- Plan codes -----------------------------------------------------------
# Rows in `plans`. Model A = consultants/studios, Model B = direct companies.
# Prices, seats, limits and allowed_doc_types are columns, not code (INV-4).
# The per-plan doc-type maps are plan §6; B_MULTISEDE is blocked on
# OPEN-DECISION-1 (POS/HACCP stay excluded from every B plan until resolved).
PLAN_CODES: frozenset[str] = frozenset(
    {
        "A_SOLO",
        "A_STUDIO",
        "A_NETWORK",
        "A_ENTERPRISE",
        "A_FOUNDING",
        "B_BASE",
        "B_PLUS",
        "B_MULTISEDE",
    }
)

# The grandfather plan. Used as the INV-1 soft-fail when an org somehow has no
# subscription row: never lock anyone out of the live tenant over a data gap.
FOUNDING_PLAN_CODE = "A_FOUNDING"

# `Organization.account_type` values.
ACCOUNT_TYPE_CONSULTANT = "consultant"
ACCOUNT_TYPE_DIRECT = "direct"
ACCOUNT_TYPES: frozenset[str] = frozenset({ACCOUNT_TYPE_CONSULTANT, ACCOUNT_TYPE_DIRECT})

# `subscriptions.status` values. Our own vocabulary, not PayPal's: the Phase-4
# webhook maps PayPal's subscription states onto these (APPROVAL_PENDING /
# APPROVED -> trialing, ACTIVE -> active, SUSPENDED -> past_due,
# CANCELLED / EXPIRED -> canceled). Webhooks are the only writer (INV-2).
SUBSCRIPTION_STATUSES: frozenset[str] = frozenset(
    {"trialing", "active", "past_due", "canceled"}
)
# Statuses that still grant generation rights. `past_due` keeps full access
# while PayPal retries a failed payment (a plan's `payment_failure_threshold`
# allows several attempts before it gives up); the read-only downgrade is
# MB-4.5.
ACTIVE_STATUSES: frozenset[str] = frozenset({"trialing", "active", "past_due"})
