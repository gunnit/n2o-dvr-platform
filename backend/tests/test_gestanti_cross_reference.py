"""Unit tests for the Gestanti cross-reference engine (US-3.9 / US-3.10).

Two layers:
 1. Pure-function tests on the catalog (no DB) — exercise the keyword
    matching, allegato coverage, alternative-mansione picker.
 2. Schema validation tests on the Pydantic decision payload — enforce the
    justification / misura_alternativa min-length rule without spinning up
    the full FastAPI + Postgres stack (which the smoke suite in
    test_calculators.py already covers).

The HTTP endpoint itself is exercised end-to-end by the frontend QA step
(screenshots in docs/qa/gestanti/); mocking async SQLAlchemy + async session
here would duplicate that without adding real coverage.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.data.dlgs_151_2001 import (
    INCOMPATIBLE_RISKS,
    find_matches_for_mansione,
    has_any_incompatible_risk,
)
from app.schemas.gestanti import DecisionRequest


# ---------------------------------------------------------------------------
# Catalog shape
# ---------------------------------------------------------------------------


def test_catalog_has_minimum_entries():
    """Spec: 12-15 entries covering the most common Allegati A/B/C risks."""
    assert 12 <= len(INCOMPATIBLE_RISKS) <= 20


def test_catalog_covers_all_three_allegati():
    """Each Allegato (A, B, C) must be represented at least twice."""
    from collections import Counter

    counts = Counter(info["allegato"] for info in INCOMPATIBLE_RISKS.values())
    assert counts["A"] >= 2, f"Allegato A under-represented: {counts}"
    assert counts["B"] >= 2, f"Allegato B under-represented: {counts}"
    assert counts["C"] >= 2, f"Allegato C under-represented: {counts}"


def test_catalog_entries_have_required_fields():
    for key, info in INCOMPATIBLE_RISKS.items():
        assert info["allegato"] in {"A", "B", "C"}, key
        assert isinstance(info["descrizione"], str) and info["descrizione"], key
        keywords = info["incompatible_mansione_keywords"]
        assert isinstance(keywords, list) and len(keywords) >= 1, key
        for kw in keywords:
            assert kw == kw.lower(), (
                f"{key}: keyword {kw!r} must be lowercase for the matcher"
            )


# ---------------------------------------------------------------------------
# Keyword matching
# ---------------------------------------------------------------------------


def test_empty_mansione_returns_no_matches():
    assert find_matches_for_mansione("") == []
    assert find_matches_for_mansione("   ") == []


def test_office_mansione_is_cleared():
    """An administrative / office job should not match anything."""
    assert find_matches_for_mansione("Impiegata amministrativa back-office") == []
    assert find_matches_for_mansione("Addetta segreteria") == []
    assert has_any_incompatible_risk("Impiegata amministrativa") is False


def test_warehouse_worker_matches_manual_handling():
    matches = find_matches_for_mansione("Magazziniera")
    keys = {k for k, _ in matches}
    assert "manual_handling_heavy" in keys


def test_welder_matches_chemicals_and_vibrations_and_noise():
    matches = find_matches_for_mansione("Operaia saldatrice")
    keys = {k for k, _ in matches}
    # saldator* should hit at least CMR chemicals AND noise AND hand-arm vibrations
    assert "chemical_exposure_cmr" in keys
    assert "noise_exposure" in keys
    assert "hand_arm_vibrations" in keys


def test_nurse_matches_biological_agents_and_night_shift():
    matches = find_matches_for_mansione("Infermiera di reparto")
    keys = {k for k, _ in matches}
    assert "biological_agents" in keys
    assert "night_shift" in keys


def test_forklift_driver_matches_vibrations_and_handling():
    matches = find_matches_for_mansione("Carrellista magazzino")
    keys = {k for k, _ in matches}
    assert "driving_heavy_vehicles" in keys
    assert "whole_body_vibrations" in keys


def test_match_is_deduplicated_per_risk_key():
    """A mansione hitting multiple keywords of the same risk must appear once."""
    # "Saldatrice in cantiere edile" could hit two keywords of
    # hand_arm_vibrations ("saldator" and "edil") — the matcher must still
    # return a single (risk_key, info) pair for that risk.
    matches = find_matches_for_mansione("Saldatrice in cantiere edile")
    keys = [k for k, _ in matches]
    assert len(keys) == len(set(keys)), f"Duplicate risk_keys: {keys}"


def test_matching_is_case_insensitive():
    low = {k for k, _ in find_matches_for_mansione("saldatore")}
    mixed = {k for k, _ in find_matches_for_mansione("Saldatore")}
    upper = {k for k, _ in find_matches_for_mansione("SALDATORE")}
    assert low == mixed == upper and len(low) > 0


# ---------------------------------------------------------------------------
# Decision payload validation (US-3.10)
# ---------------------------------------------------------------------------


def test_accept_requires_justification_10_chars():
    # Too short -> rejected by validator
    with pytest.raises(ValidationError):
        DecisionRequest(
            risk_key="manual_handling_heavy",
            action="accept",
            justification="troppo",
        )
    # Exactly 10 non-whitespace chars -> OK
    ok = DecisionRequest(
        risk_key="manual_handling_heavy",
        action="accept",
        justification="sufficient",
    )
    assert ok.justification == "sufficient"


def test_reject_requires_misura_10_chars():
    with pytest.raises(ValidationError):
        DecisionRequest(
            risk_key="night_shift",
            action="reject",
            misura_alternativa="corto",
        )
    ok = DecisionRequest(
        risk_key="night_shift",
        action="reject",
        misura_alternativa="Riallocata a turno diurno 8-17",
    )
    assert ok.misura_alternativa.startswith("Riallocata")


def test_whitespace_only_values_are_rejected():
    with pytest.raises(ValidationError):
        DecisionRequest(
            risk_key="manual_handling_heavy",
            action="accept",
            justification="          ",  # only spaces
        )


def test_invalid_action_value_rejected():
    with pytest.raises(ValidationError):
        DecisionRequest(
            risk_key="manual_handling_heavy",
            action="maybe",  # type: ignore[arg-type]
            justification="sufficient",
        )
