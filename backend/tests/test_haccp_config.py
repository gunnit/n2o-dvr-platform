"""Unit tests for US-4.3 — HACCP activity types + CCP merge + route wiring.

End-to-end DB CRUD is exercised by the frontend QA flow; these tests pin:

  * The activity-type catalog is well-formed (every entry has at least one
    CCP, every CCP has all the structured fields we render in the .docx).
  * ``get_default_ccps`` returns copies so caller mutation doesn't leak
    into the module-level constants.
  * ``merge_ccps`` preserves operator edits, adds new defaults, and keeps
    operator-added customs.
  * The FastAPI router registers the three US-4.3 endpoints the frontend
    depends on.
  * Pydantic schemas reject bad strategy values and accept the happy path.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.data.haccp_activity_types import (
    _ACTIVITY_TYPES,
    get_activity_type,
    get_default_ccps,
    list_activity_types,
    merge_ccps,
)
from app.schemas.haccp import HaccpRegenerateCcpsRequest


# ---------------------------------------------------------------------------
# Catalog shape
# ---------------------------------------------------------------------------


def test_catalog_has_at_least_eight_activity_types():
    # AC1 mentions ristorante / bar explicitly; consultants need enough
    # coverage that the first N2O clients rarely hit "Altro".
    assert len(_ACTIVITY_TYPES) >= 8


def test_every_activity_type_ships_with_ccps():
    for activity in _ACTIVITY_TYPES:
        assert activity["ccps"], f"{activity['slug']} has no CCPs"
        assert len(activity["ccps"]) >= 3, (
            f"{activity['slug']} ships too few CCPs for a realistic manual"
        )


def test_every_ccp_has_the_required_rendered_fields():
    # The haccp_manuale generator renders Codice + CCP + Limite critico; the
    # frontend CCP editor needs pericolo / monitoraggio / azione_correttiva /
    # frequenza in addition. Missing fields = half-rendered rows.
    required = {
        "codice",
        "nome",
        "fase",
        "pericolo",
        "limite_critico",
        "monitoraggio",
        "azione_correttiva",
        "frequenza",
    }
    for activity in _ACTIVITY_TYPES:
        for ccp in activity["ccps"]:
            missing = required - set(ccp.keys())
            assert not missing, (
                f"{activity['slug']}/{ccp.get('codice')} missing fields: {missing}"
            )


def test_activity_slugs_are_unique_and_stable():
    slugs = [a["slug"] for a in _ACTIVITY_TYPES]
    assert len(slugs) == len(set(slugs)), "duplicate activity slugs"


def test_list_activity_types_emits_ccp_count():
    payload = list_activity_types()
    ristorante = next(x for x in payload if x["slug"] == "ristorante_con_cucina")
    assert ristorante["ccp_count"] >= 5


# ---------------------------------------------------------------------------
# get_default_ccps
# ---------------------------------------------------------------------------


def test_get_default_ccps_returns_empty_for_unknown_slug():
    assert get_default_ccps("not_a_real_slug") == []


def test_get_default_ccps_returns_independent_copies():
    """Mutating the returned list must not mutate the module constants."""
    first = get_default_ccps("ristorante_con_cucina")
    first[0]["limite_critico"] = "MUTATED"

    second = get_default_ccps("ristorante_con_cucina")
    assert second[0]["limite_critico"] != "MUTATED"


def test_get_activity_type_lookup_roundtrip():
    at = get_activity_type("bar_caffetteria")
    assert at is not None
    assert at["nome"] == "Bar / caffetteria"


# ---------------------------------------------------------------------------
# merge_ccps (AC3 edit-then-merge flow)
# ---------------------------------------------------------------------------


def test_merge_preserves_operator_edited_row():
    defaults = get_default_ccps("ristorante_con_cucina")
    # Operator tweaked the cooking CCP temperature limit.
    edited = [dict(c) for c in defaults]
    edited[0]["limite_critico"] = "Temperatura al cuore >= 82 C (interno)"

    merged, preserved = merge_ccps(edited, defaults)

    # Edited row kept verbatim; its codice shows up in the preserved list
    # so the frontend can surface "1 CCP personalizzato mantenuto".
    assert merged[0]["limite_critico"] == "Temperatura al cuore >= 82 C (interno)"
    assert preserved == [edited[0]["codice"]]


def test_merge_appends_operator_added_customs():
    defaults = get_default_ccps("bar_caffetteria")
    custom = {
        "codice": "CUSTOM1",
        "nome": "Controllo gelati artigianali",
        "fase": "Esposizione",
        "pericolo": "Rottura catena del freddo",
        "limite_critico": "T vetrina <= -14 C",
        "monitoraggio": "Termometro vetrina, 2x/giorno",
        "azione_correttiva": "Sospendere vendita, scartare se > -10 C",
        "frequenza": "Bigiornaliera",
    }

    merged, preserved = merge_ccps([*defaults, custom], defaults)

    assert custom in merged, "operator-added CUSTOM1 must survive regeneration"
    assert "CUSTOM1" not in preserved  # customs are not in defaults, so never "preserved"


def test_merge_adds_new_defaults_when_switching_activities():
    # Simulate: operator had the Bar defaults, then switched to Ristorante.
    bar_defaults = get_default_ccps("bar_caffetteria")
    ristorante_defaults = get_default_ccps("ristorante_con_cucina")

    merged, _ = merge_ccps(bar_defaults, ristorante_defaults)

    codici = {row["codice"] for row in merged}
    # Cottura (CCP1) is in Ristorante but not in Bar — must appear after merge.
    assert "CCP1" in codici
    # And every Ristorante default must be represented.
    for default in ristorante_defaults:
        assert default["codice"] in codici


def test_merge_on_empty_existing_returns_defaults_unchanged():
    defaults = get_default_ccps("ristorante_con_cucina")
    merged, preserved = merge_ccps([], defaults)
    assert merged == defaults
    assert preserved == []


# ---------------------------------------------------------------------------
# Route + schema contract
# ---------------------------------------------------------------------------


def test_router_registers_haccp_endpoints():
    from app.api.v1.router import api_router

    paths = {
        (method, getattr(r, "path", ""))
        for r in api_router.routes
        for method in getattr(r, "methods", set()) or set()
    }
    assert ("GET", "/api/v1/haccp/_meta/activity-types") in paths
    assert ("GET", "/api/v1/aziende/{azienda_id}/haccp/config") in paths
    assert ("PUT", "/api/v1/aziende/{azienda_id}/haccp/config") in paths
    assert (
        "POST",
        "/api/v1/aziende/{azienda_id}/haccp/config/regenerate-ccps",
    ) in paths


def test_regenerate_request_defaults_to_merge_strategy():
    body = HaccpRegenerateCcpsRequest()
    assert body.strategy == "merge"


def test_regenerate_request_accepts_replace():
    assert HaccpRegenerateCcpsRequest(strategy="replace").strategy == "replace"


@pytest.mark.parametrize("bad", ["delete", "overwrite", "", "MERGE", "merge "])
def test_regenerate_request_rejects_unknown_strategies(bad: str):
    with pytest.raises(ValidationError):
        HaccpRegenerateCcpsRequest(strategy=bad)
