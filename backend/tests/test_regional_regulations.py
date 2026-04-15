"""Unit tests for the regione + regional regulations lookup (US-2.2 AC1).

Covers three concerns:

1. ``lookup_regione`` agrees with ``lookup_zone`` on every comune in the
   seismic_zones table — the two lookups MUST stay in lock-step or the
   DVR risks rendering a seismic zone for one regione but citing another
   regione's regulations (a compliance footgun).

2. ``get_regulations_for_regione`` / ``get_regulations_for_comune`` return
   the expected shape, fall back gracefully for unknown input, and don't
   mutate their internal tables on repeat calls.

3. Every regione the comune registry references has at least one
   regulation published. Without this a comune in that regione would
   auto-resolve a seismic zone + an empty regulation list, and the DVR
   would silently drop the "Regolamenti regionali applicabili" block.
"""

from __future__ import annotations

from app.data.regional_regulations import (
    Regulation,
    covered_regioni,
    get_regulations_for_comune,
    get_regulations_for_regione,
)
from app.data.seismic_zones import _RAW, lookup_regione, lookup_zone


# ---------------------------------------------------------------------------
# comune -> regione mapping via seismic_zones
# ---------------------------------------------------------------------------


def test_lookup_regione_returns_none_for_unknown_comune():
    assert lookup_regione("Atlantide") is None
    assert lookup_regione("") is None


def test_lookup_regione_tolerates_casing_and_apostrophes():
    canonical = lookup_regione("L'Aquila")
    assert canonical == "Abruzzo"
    # Right-single-quote + different casing (common Word typography).
    assert lookup_regione("l\u2019aquila") == "Abruzzo"
    assert lookup_regione("  VALLE D'AOSTA  ".replace("VALLE D'AOSTA", "Aosta")) == "Valle d'Aosta"


def test_every_comune_has_a_regione_and_a_zone():
    """The two lookups MUST agree on known-ness for every comune."""
    for comune in _RAW.keys():
        zone_match = lookup_zone(comune)
        regione = lookup_regione(comune)
        assert zone_match is not None, f"seismic zone missing for {comune!r}"
        assert regione is not None, f"regione missing for {comune!r}"


# ---------------------------------------------------------------------------
# regione -> regulations
# ---------------------------------------------------------------------------


def test_covered_regioni_matches_known_comuni_regioni():
    """Every regione referenced by the comune registry must have at least
    one regulation published. If someone adds a new regione to the comune
    table without the matching regulation block, this fails loudly."""
    regioni_in_comuni = {regione for (_, regione) in _RAW.values()}
    covered = covered_regioni()
    missing = regioni_in_comuni - covered
    assert missing == set(), f"Regioni without regulations: {missing}"


def test_each_regulation_has_required_shape():
    """Every Regulation entry must carry titolo + riferimento + ambito."""
    for regione in covered_regioni():
        regulations = get_regulations_for_regione(regione)
        assert len(regulations) >= 1, f"{regione}: no regulations"
        for reg in regulations:
            assert isinstance(reg, dict), f"{regione}: bad entry type"
            for key in ("titolo", "riferimento", "ambito"):
                assert (
                    key in reg and isinstance(reg[key], str) and reg[key].strip()
                ), f"{regione}: missing or empty {key!r}"


def test_get_regulations_for_regione_unknown_returns_empty_list():
    assert get_regulations_for_regione("Oltremare") == []


def test_get_regulations_for_regione_returns_independent_copies():
    """Caller mutation must not bleed into the module-level table."""
    a = get_regulations_for_regione("Lazio")
    a.append({"titolo": "x", "riferimento": "x", "ambito": "x"})  # type: ignore[arg-type]
    b = get_regulations_for_regione("Lazio")
    assert len(b) < len(a), "mutation bled into the module table"


# ---------------------------------------------------------------------------
# comune -> (regione, regulations) convenience
# ---------------------------------------------------------------------------


def test_get_regulations_for_comune_happy_path():
    regione, regs = get_regulations_for_comune("Milano")
    assert regione == "Lombardia"
    assert len(regs) >= 1
    # Spot-check the first anchor reference is the PRP per our data spec.
    assert any("Piano Regionale" in r["titolo"] for r in regs)


def test_get_regulations_for_comune_unknown_returns_none_and_empty():
    regione, regs = get_regulations_for_comune("Atlantide")
    assert regione is None
    assert regs == []


def test_get_regulations_for_comune_case_insensitive():
    left = get_regulations_for_comune("BOLOGNA")
    right = get_regulations_for_comune("bologna")
    assert left == right


def test_regulation_typeddict_round_trip():
    """Round-trip via dict(**Regulation) doesn't raise — matters because
    the API layer splats into the Pydantic Regulation model."""
    reg: Regulation = {
        "titolo": "Test",
        "riferimento": "Test 123",
        "ambito": "Test",
    }
    restored = dict(**reg)
    assert restored["titolo"] == "Test"
