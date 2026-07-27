"""The plan catalogue, as data.

This is the *only* place prices, seats and limits are written down. Model A
(consultants) and Model B (direct companies) differ solely as rows here —
never as forked code (INV-4).

Rows land in the ``plans`` table two ways:

* the Phase-1 migration seeds them once, so a deploy is self-sufficient;
* ``backend/scripts/seed_plans.py`` re-applies this module whenever the
  catalogue changes (a price rise, a new tier, ``paypal_plan_id`` backfill).

``tests/test_plan_catalogue.py`` asserts the migration's literals still match
this module, so the two can't drift apart.

Prices are **annual, in euro cents, excluding IVA 22%**. First-year setup fees
(Base €690 / Plus €1,290 / Multi-sede €2,900; Studio +€1,500 onboarding;
Network +€3,500) are one-time Checkout line items, not plan fields.

``None`` means "unlimited / not metered" in every limit field, and
``allowed_doc_types=None`` means all 17 document types.
"""

from typing import Any

from app.billing.constants import normalize_doc_type

# --- Model B document sets (plan §6 — the channel-conflict contract) --------
# These are the INV-9 guardrail: a direct tenant may only generate what its
# plan lists. Written in the canonical lowercase wire form.

_B_BASE_DOCS = [
    "dvr_master",
    "allegato_mmc",
    "allegato_vdt",
    "allegato_stress",
    "allegato_gestanti",
    "allegato_incendio",
]

_B_PLUS_DOCS = _B_BASE_DOCS + [
    "allegato_microclima",
    "allegato_microclima_severo",
    "allegato_biologico_alimentare",
    "allegato_biologico_asilo",
    "allegato_biologico_dentisti",
    "pee_azienda",
    "duvri",
]

# ⚠️ OPEN-DECISION-1. The pricing deck gives Multi-sede "all 17 incl. POS +
# HACCP", which contradicts both the POS/construction → partner guardrail and
# the <50-worker ceiling for direct plans. Until a human resolves it, POS,
# HACCP and HACCP_FORMS are excluded from *every* Model B plan. Do not add them
# here without that decision — shipping POS to a direct tenant is the
# channel-conflict scenario the whole guardrail exists to prevent.
_B_MULTISEDE_DOCS = _B_PLUS_DOCS + ["pee_comune"]


# --- The catalogue ---------------------------------------------------------

PLAN_CATALOGUE: list[dict[str, Any]] = [
    # --- Model A: consultants and studios. All 17 doc types, always. -------
    {
        "plan_code": "A_SOLO",
        "model": "A",
        "display_name": "Solo",
        "price_year_cents": 149_000,
        "seats": 1,
        "max_companies": 15,
        "max_sites": None,
        "ai_credits_year": 2_500,
        "allowed_doc_types": None,
        "features": {
            "white_label_domain": False,
            "sub_tenants": 0,
            "api": "none",
            "data_certa": False,
            "rspp_reviews_included": 0,
        },
        "active": True,
    },
    {
        "plan_code": "A_STUDIO",
        "model": "A",
        "display_name": "Studio",
        "price_year_cents": 390_000,
        "seats": 5,
        "max_companies": 60,
        "max_sites": None,
        "ai_credits_year": 9_000,
        "allowed_doc_types": None,
        "features": {
            "white_label_domain": False,
            "sub_tenants": 0,
            "api": "read",
            "data_certa": False,
            "rspp_reviews_included": 0,
            "template_migrations": 1,
        },
        "active": True,
    },
    {
        "plan_code": "A_NETWORK",
        "model": "A",
        "display_name": "Network",
        "price_year_cents": 890_000,
        "seats": 15,
        "max_companies": 200,
        "max_sites": None,
        "ai_credits_year": 30_000,
        "allowed_doc_types": None,
        "features": {
            "white_label_domain": True,
            "sub_tenants": 10,
            "api": "full",
            "data_certa": True,
            "rspp_reviews_included": 0,
        },
        "active": True,
    },
    {
        "plan_code": "A_ENTERPRISE",
        "model": "A",
        "display_name": "Enterprise",
        # "18,000+" in the deck — the floor. Enterprise is quoted, so the row
        # is a starting point the admin endpoint (MB-3.1) overrides per deal.
        "price_year_cents": 1_800_000,
        "seats": 40,
        "max_companies": None,   # unlimited
        "max_sites": None,
        "ai_credits_year": None,  # pooled / unmetered
        "allowed_doc_types": None,
        "features": {
            "white_label_domain": True,
            "sub_tenants": None,
            "api": "full",
            "webhooks": True,
            "data_certa": True,
            "rspp_reviews_included": 0,
        },
        "active": True,
    },
    {
        # The grandfather row. Every organization that existed before billing
        # is put on this (MB-1.3). €0, 3-year term — deliberately not
        # renegotiated annually. See OPEN-DECISION-2.
        "plan_code": "A_FOUNDING",
        "model": "A",
        "display_name": "Founding Partner",
        "price_year_cents": 0,
        "seats": 5,
        "max_companies": 60,
        "max_sites": None,
        "ai_credits_year": 9_000,
        "allowed_doc_types": None,
        "features": {
            "white_label_domain": True,
            "sub_tenants": 0,
            "api": "read",
            "data_certa": True,
            "rspp_reviews_included": 0,
            "founding": True,
        },
        "active": True,
    },
    # --- Model B: direct companies. -----------------------------------------
    # Seeded inactive: not sellable until Phase 5 (MB-5.1) flips them on, after
    # the eligibility gate, the DdL consent copy and legal review exist.
    {
        "plan_code": "B_BASE",
        "model": "B",
        "display_name": "Base",
        "price_year_cents": 49_000,
        "seats": 2,
        "max_companies": None,
        "max_sites": 1,
        "ai_credits_year": 500,
        "allowed_doc_types": _B_BASE_DOCS,
        "features": {
            "white_label_domain": False,
            "sub_tenants": 0,
            "api": "none",
            "data_certa": False,  # available as an add-on
            "rspp_reviews_included": 0,
        },
        "active": False,
    },
    {
        "plan_code": "B_PLUS",
        "model": "B",
        "display_name": "Plus",
        "price_year_cents": 99_000,
        "seats": 5,
        "max_companies": None,
        "max_sites": 3,
        "ai_credits_year": 1_000,
        "allowed_doc_types": _B_PLUS_DOCS,
        "features": {
            "white_label_domain": False,
            "sub_tenants": 0,
            "api": "none",
            "data_certa": True,
            "rspp_reviews_included": 1,
        },
        "active": False,
    },
    {
        "plan_code": "B_MULTISEDE",
        "model": "B",
        "display_name": "Multi-sede",
        "price_year_cents": 240_000,
        "seats": 15,
        "max_companies": None,
        "max_sites": 10,
        "ai_credits_year": 2_500,
        "allowed_doc_types": _B_MULTISEDE_DOCS,
        "features": {
            "white_label_domain": False,
            "sub_tenants": 0,
            "api": "none",
            "data_certa": True,
            "rspp_reviews_included": 2,
        },
        # Blocked on OPEN-DECISION-1 — whether Multi-sede belongs in the direct
        # channel at all. Stays inactive even after Phase 5 until that lands.
        "active": False,
    },
]

PLANS_BY_CODE: dict[str, dict[str, Any]] = {p["plan_code"]: p for p in PLAN_CATALOGUE}


def validate_catalogue() -> None:
    """Fail loudly on a catalogue that would misbehave in production.

    Called by the seed script and the tests. Cheap insurance against a typo in
    a doc-type string silently withholding a document a customer paid for.
    """
    from app.billing.constants import ALL_DOC_TYPES, PLAN_CODES

    seen: set[str] = set()
    for plan in PLAN_CATALOGUE:
        code = plan["plan_code"]
        if code in seen:
            raise ValueError(f"duplicate plan_code in catalogue: {code}")
        seen.add(code)

        if code not in PLAN_CODES:
            raise ValueError(f"{code} is not in billing.constants.PLAN_CODES")
        if plan["model"] not in {"A", "B"}:
            raise ValueError(f"{code}: model must be 'A' or 'B', got {plan['model']!r}")
        if plan["seats"] < 1:
            raise ValueError(f"{code}: seats must be >= 1")
        if plan["price_year_cents"] < 0:
            raise ValueError(f"{code}: price cannot be negative")

        docs = plan["allowed_doc_types"]
        if docs is not None:
            unknown = {d for d in docs if normalize_doc_type(d) not in ALL_DOC_TYPES}
            if unknown:
                raise ValueError(
                    f"{code}: unknown document types {sorted(unknown)} — "
                    "they will never match a real generation request"
                )
            if len(set(docs)) != len(docs):
                raise ValueError(f"{code}: duplicate entries in allowed_doc_types")

    missing = PLAN_CODES - seen
    if missing:
        raise ValueError(f"catalogue is missing plan codes: {sorted(missing)}")
