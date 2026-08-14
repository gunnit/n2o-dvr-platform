"""Unit tests for the VDT API derivation helpers (US-3.4 / US-3.5).

The HTTP layer is thin — its non-trivial logic is `_apply_derived` (single
row: esposto, periodicita_sorveglianza, data_prossima_visita) plus the
person-level hour summing (client feedback 2026-08: one worker on multiple
devices is classified on the SUM of their weekly hours) and the age-based
periodicità (art. 176 c.3).

Testing this directly (instead of round-tripping through TestClient) keeps
the test surface small and stays consistent with the rest of the suite,
which exercises pure functions over models.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.api.v1.vdt import _apply_derived
from app.services.document_generator.allegato_vdt import group_rows_by_person
from app.services.vdt_calculator import (
    VDT_EXPOSURE_THRESHOLD_HOURS,
    classify_total_exposure,
    total_weekly_hours,
)
from app.services.vdt_surveillance import age_on, surveillance_periodicita


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


# ---------------------------------------------------------------------------
# Person-level hour summing (client feedback 2026-08): one worker on several
# devices is classified on the TOTAL weekly hours across all postazioni.
# ---------------------------------------------------------------------------


def _row(persona_id, postazione, ore, **extra):
    defaults = dict(
        persona_id=persona_id,
        postazione=postazione,
        ore_settimanali=ore,
        data_nascita=None,
        eta_50_plus=False,
        idoneita_visiva=None,
        note=None,
    )
    defaults.update(extra)
    return SimpleNamespace(**defaults)


def test_two_postazioni_sum_over_threshold_is_esposto():
    """12 h + 10 h = 22 h => esposto even though neither row crosses 20 h."""
    assert classify_total_exposure([12, 10]) == "ESPOSTO"


def test_two_postazioni_sum_under_threshold_is_non_esposto():
    """8 h + 6 h = 14 h => non esposto."""
    assert classify_total_exposure([8, 6]) == "NON_ESPOSTO"


def test_total_weekly_hours_treats_none_as_zero():
    assert total_weekly_hours([12, None, 10]) == 22.0


def test_sum_exactly_at_threshold_is_esposto():
    """Inclusive threshold survives the summing (12 + 8 = 20)."""
    assert classify_total_exposure([12, 8]) == "ESPOSTO"


def test_group_rows_by_person_merges_same_persona():
    p1, p2 = uuid.uuid4(), uuid.uuid4()
    rows = [
        _row(p1, "PC fisso", 12),
        _row(p2, "PC reception", 8),
        _row(p1, "Laptop", 10),
    ]
    groups = group_rows_by_person(rows)
    assert [pid for pid, _ in groups] == [p1, p2]
    by_pid = dict(groups)
    assert [r.postazione for r in by_pid[p1]] == ["PC fisso", "Laptop"]
    # The person-level classification runs on the group's summed hours.
    assert (
        classify_total_exposure(r.ore_settimanali for r in by_pid[p1])
        == "ESPOSTO"
    )
    assert (
        classify_total_exposure(r.ore_settimanali for r in by_pid[p2])
        == "NON_ESPOSTO"
    )


def test_group_rows_by_person_keeps_generic_rows_separate():
    """Anonymous workstations can't be assumed to share a worker: each
    persona_id=None row is its own group, never summed with the others."""
    rows = [_row(None, "Reception", 15), _row(None, "Magazzino", 15)]
    groups = group_rows_by_person(rows)
    assert len(groups) == 2
    for pid, group_rows in groups:
        assert pid is None
        assert len(group_rows) == 1
        assert (
            classify_total_exposure(r.ore_settimanali for r in group_rows)
            == "NON_ESPOSTO"
        )


# ---------------------------------------------------------------------------
# Age-based periodicità (art. 176 c.3, client feedback 2026-08): biennale
# for 50+ (or con prescrizioni), quinquennale otherwise — computed from
# data_nascita, with the legacy eta_50_plus flag as fallback only.
# ---------------------------------------------------------------------------


def test_apply_derived_periodicita_from_birth_date_over_50():
    born = date(_today().year - 60, 1, 1)
    out = _apply_derived({"ore_settimanali": 30, "data_nascita": born})
    assert out["esposto"] is True
    assert out["periodicita_sorveglianza"] == "biennale"


def test_apply_derived_birth_date_wins_over_stale_flag():
    """data_nascita is authoritative: a 30-year-old with a stale
    eta_50_plus=True flag still gets the quinquennale cadence."""
    born = date(_today().year - 30, 1, 1)
    out = _apply_derived(
        {"ore_settimanali": 30, "data_nascita": born, "eta_50_plus": True}
    )
    assert out["periodicita_sorveglianza"] == "quinquennale"


def test_apply_derived_con_prescrizioni_forces_biennale():
    born = date(_today().year - 30, 1, 1)
    out = _apply_derived(
        {
            "ore_settimanali": 30,
            "data_nascita": born,
            "idoneita_visiva": "con prescrizioni",
        }
    )
    assert out["periodicita_sorveglianza"] == "biennale"


def test_age_on_counts_whole_years():
    born = date(1975, 6, 15)
    assert age_on(born, date(2025, 6, 14)) == 49
    assert age_on(born, date(2025, 6, 15)) == 50


def test_surveillance_periodicita_flips_on_50th_birthday():
    born = date(1976, 8, 1)
    common = dict(data_nascita=born, eta_50_plus=False, idoneita_visiva=None)
    assert (
        surveillance_periodicita(on=date(2026, 7, 31), **common)
        == "quinquennale"
    )
    assert (
        surveillance_periodicita(on=date(2026, 8, 1), **common) == "biennale"
    )
