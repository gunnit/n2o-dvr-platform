"""The plan catalogue, and its agreement with the migration that seeds it.

The catalogue lives in two places by design: `app/billing/plan_catalogue.py`
(editable, used by the seed script) and literal SQL in migration
`de3f4a5b6c7d` (frozen, so a deploy is self-sufficient and a refactor of the
module can never break an old migration). This module is what stops those two
drifting — a price changed in one place and not the other would mean a
freshly-migrated database disagrees with a re-seeded one.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from app.billing.constants import ALL_DOC_TYPES, PLAN_CODES
from app.billing.plan_catalogue import (
    PLAN_CATALOGUE,
    PLANS_BY_CODE,
    validate_catalogue,
)

_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic" / "versions" / "de3f4a5b6c7d_grandfather_existing_orgs.py"
)

# Column order of the PLANS tuples in the migration.
_FIELDS = [
    "plan_code", "model", "display_name", "price_year_cents", "seats",
    "max_companies", "max_sites", "ai_credits_year", "allowed_doc_types",
    "features", "active",
]


def _migration_plans() -> dict[str, dict]:
    """Read the migration's PLANS literal without importing the migration.

    Parsed with `ast` rather than imported because alembic modules expect a
    migration context; the literal is all we need.
    """
    tree = ast.parse(_MIGRATION.read_text(encoding="utf-8"))
    consts: dict[str, str] = {}
    plans_node = None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if target.id == "PLANS":
            plans_node = node.value
        elif isinstance(node.value, (ast.Constant, ast.BinOp, ast.JoinedStr)):
            try:
                consts[target.id] = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                pass

    assert plans_node is not None, "PLANS literal not found in the migration"

    out: dict[str, dict] = {}
    for row in plans_node.elts:
        values = []
        for elt in row.elts:
            if isinstance(elt, ast.Name):          # the _B_* doc-type strings
                values.append(consts[elt.id])
            else:
                values.append(ast.literal_eval(elt))
        plan = dict(zip(_FIELDS, values))
        # The migration stores JSON as text; decode to compare like for like.
        plan["allowed_doc_types"] = (
            None if plan["allowed_doc_types"] is None
            else json.loads(plan["allowed_doc_types"])
        )
        plan["features"] = json.loads(plan["features"])
        out[plan["plan_code"]] = plan
    return out


def test_catalogue_is_internally_valid():
    validate_catalogue()  # raises on unknown doc types, dupes, bad models


def test_catalogue_covers_every_declared_plan_code():
    assert set(PLANS_BY_CODE) == PLAN_CODES


@pytest.mark.parametrize("code", sorted(PLAN_CODES))
def test_migration_and_catalogue_agree(code):
    migration = _migration_plans()
    assert code in migration, f"{code} is in the catalogue but not seeded by the migration"
    for field in _FIELDS:
        assert migration[code][field] == PLANS_BY_CODE[code][field], (
            f"{code}.{field} differs: migration={migration[code][field]!r} "
            f"catalogue={PLANS_BY_CODE[code][field]!r}"
        )


def test_migration_seeds_nothing_extra():
    assert set(_migration_plans()) == PLAN_CODES


# --- the commercial contract ----------------------------------------------


def test_model_a_plans_grant_all_seventeen_doc_types():
    for plan in PLAN_CATALOGUE:
        if plan["model"] == "A":
            assert plan["allowed_doc_types"] is None, plan["plan_code"]


def test_no_model_b_plan_includes_pos_or_haccp():
    """OPEN-DECISION-1, and the reason the guardrail exists: POS means a
    construction site, which routes to a consultant partner. Shipping it to a
    direct tenant is the channel-conflict scenario. Do not relax this test
    without a recorded human decision."""
    for plan in PLAN_CATALOGUE:
        if plan["model"] != "B":
            continue
        docs = set(plan["allowed_doc_types"] or ())
        assert not docs & {"pos", "haccp", "haccp_forms"}, plan["plan_code"]


def test_model_b_plans_are_a_strict_progression():
    base = set(PLANS_BY_CODE["B_BASE"]["allowed_doc_types"])
    plus = set(PLANS_BY_CODE["B_PLUS"]["allowed_doc_types"])
    multi = set(PLANS_BY_CODE["B_MULTISEDE"]["allowed_doc_types"])
    # A more expensive plan must never take a document away.
    assert base < plus < multi
    assert multi <= ALL_DOC_TYPES


def test_model_b_plans_ship_inactive():
    """Not sellable until Phase 5 wires eligibility, consent and legal review."""
    for plan in PLAN_CATALOGUE:
        if plan["model"] == "B":
            assert plan["active"] is False, plan["plan_code"]


def test_prices_increase_with_capability():
    order = ["A_SOLO", "A_STUDIO", "A_NETWORK", "A_ENTERPRISE"]
    prices = [PLANS_BY_CODE[c]["price_year_cents"] for c in order]
    assert prices == sorted(prices)
    seats = [PLANS_BY_CODE[c]["seats"] for c in order]
    assert seats == sorted(seats)


def test_founding_plan_is_free_and_generous_enough_for_the_live_tenant():
    founding = PLANS_BY_CODE["A_FOUNDING"]
    assert founding["price_year_cents"] == 0
    assert founding["allowed_doc_types"] is None
    # Matches Studio's limits — the grandfathered tenant must not be worse off
    # than a paying customer.
    studio = PLANS_BY_CODE["A_STUDIO"]
    assert founding["max_companies"] >= studio["max_companies"]
    assert founding["ai_credits_year"] >= studio["ai_credits_year"]
