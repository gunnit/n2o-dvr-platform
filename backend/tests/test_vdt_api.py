"""Unit tests for the VDT API derivation helper (US-3.4 / US-3.5).

The HTTP layer is thin — its only non-trivial logic is `_apply_derived`
which takes the user input (postazione, ore_settimanali, eta_50_plus,
data_ultima_visita) and fills in the server-derived fields (esposto,
periodicita_sorveglianza, data_prossima_visita).

Testing this directly (instead of round-tripping through TestClient) keeps
the test surface small and stays consistent with the rest of the suite,
which exercises pure functions over models.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.api.v1.vdt import _apply_derived
from app.services.vdt_calculator import VDT_EXPOSURE_THRESHOLD_HOURS


def _today() -> date:
    return datetime.now(timezone.utc).date()


def test_below_threshold_is_not_esposto():
    out = _apply_derived({"ore_settimanali": 19.5})
    assert out["esposto"] is False
    assert out["periodicita_sorveglianza"] is None
    assert out["data_prossima_visita"] is None


def test_at_threshold_is_esposto():
    """20 h/week is inclusive per art. 173."""
    out = _apply_derived({"ore_settimanali": VDT_EXPOSURE_THRESHOLD_HOURS})
    assert out["esposto"] is True
    assert out["periodicita_sorveglianza"] == "quinquennale"
    assert out["data_prossima_visita"] is not None


def test_above_threshold_under_50_is_quinquennale():
    out = _apply_derived(
        {"ore_settimanali": 35, "eta_50_plus": False},
    )
    assert out["esposto"] is True
    assert out["periodicita_sorveglianza"] == "quinquennale"
    # Default anchor is today -> next visit ~5 years out.
    assert out["data_prossima_visita"].year >= _today().year + 4


def test_above_threshold_over_50_is_biennale():
    out = _apply_derived(
        {"ore_settimanali": 35, "eta_50_plus": True},
    )
    assert out["periodicita_sorveglianza"] == "biennale"
    # 2 years from anchor (today by default).
    assert out["data_prossima_visita"].year <= _today().year + 2


def test_anchor_uses_data_ultima_visita_when_provided():
    last = date(2024, 6, 1)
    out = _apply_derived(
        {
            "ore_settimanali": 30,
            "eta_50_plus": False,
            "data_ultima_visita": last,
        },
    )
    # Quinquennale → anchor + 5y, regardless of today.
    assert out["data_prossima_visita"] == date(2029, 6, 1)


def test_zero_hours_is_not_esposto():
    out = _apply_derived({"ore_settimanali": 0})
    assert out["esposto"] is False


def test_apply_derived_does_not_mutate_input():
    payload = {"ore_settimanali": 25, "eta_50_plus": True}
    snapshot = dict(payload)
    _apply_derived(payload)
    assert payload == snapshot


def test_missing_ore_treated_as_zero():
    """Caller might omit ore_settimanali; helper must not blow up."""
    out = _apply_derived({})
    assert out["esposto"] is False
    assert out["periodicita_sorveglianza"] is None


@pytest.mark.parametrize(
    "ore,expected",
    [
        (0, False),
        (10.5, False),
        (19.99, False),
        (20.0, True),
        (40.0, True),
    ],
)
def test_threshold_boundary(ore, expected):
    out = _apply_derived({"ore_settimanali": ore})
    assert out["esposto"] is expected
