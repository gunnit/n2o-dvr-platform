"""Unit tests for VDT health-surveillance cadence + bucketing (US-3.5)."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.vdt_surveillance import (
    IN_SCADENZA_WINDOW_DAYS,
    PERIODICITA_OVER_50_ANNI,
    PERIODICITA_STANDARD_ANNI,
    SurveillanceBucket,
    _add_years,
    bucket_for,
    cadence_years_for,
    compute_next_visit,
    periodicita_label_for,
)


def test_cadence_years_under_50_is_five():
    assert cadence_years_for(over_50=False) == PERIODICITA_STANDARD_ANNI == 5


def test_cadence_years_over_50_is_two():
    assert cadence_years_for(over_50=True) == PERIODICITA_OVER_50_ANNI == 2


def test_periodicita_labels():
    assert periodicita_label_for(False) == "quinquennale"
    assert periodicita_label_for(True) == "biennale"


def test_add_years_handles_leap_day_rollover():
    """Feb 29 → Feb 28 in the destination year when non-leap."""
    assert _add_years(date(2024, 2, 29), 1) == date(2025, 2, 28)
    # Back into a leap year it should stay on Feb 29.
    assert _add_years(date(2024, 2, 29), 4) == date(2028, 2, 29)


def test_compute_next_visit_with_last_visit_under_50():
    today = date(2026, 4, 15)
    result = compute_next_visit(
        data_ultima_visita=date(2024, 4, 15),
        over_50=False,
        today=today,
    )
    assert result.data_prossima_visita == date(2029, 4, 15)
    assert result.periodicita == "quinquennale"
    assert result.bucket == SurveillanceBucket.FUTURE


def test_compute_next_visit_with_last_visit_over_50_biennial():
    today = date(2026, 4, 15)
    result = compute_next_visit(
        data_ultima_visita=date(2025, 4, 15),
        over_50=True,
        today=today,
    )
    assert result.data_prossima_visita == date(2027, 4, 15)
    assert result.periodicita == "biennale"
    assert result.bucket == SurveillanceBucket.FUTURE


def test_compute_next_visit_falls_back_to_classification_date():
    today = date(2026, 4, 15)
    classified = date(2026, 1, 10)
    result = compute_next_visit(
        data_ultima_visita=None,
        over_50=False,
        today=today,
        classification_date=classified,
    )
    # First visit anchored to classification_date, +5y.
    assert result.data_prossima_visita == date(2031, 1, 10)


def test_compute_next_visit_uses_today_when_no_anchors():
    today = date(2026, 4, 15)
    result = compute_next_visit(
        data_ultima_visita=None,
        over_50=True,
        today=today,
    )
    assert result.data_prossima_visita == date(2028, 4, 15)


# --- bucket_for ---------------------------------------------------------


@pytest.mark.parametrize(
    "next_visit_offset_days,expected",
    [
        (-30, SurveillanceBucket.SCADUTE),  # 30 days ago
        (-1, SurveillanceBucket.SCADUTE),   # yesterday
        (0, SurveillanceBucket.IN_SCADENZA),  # today counts as in-scadenza
        (IN_SCADENZA_WINDOW_DAYS - 1, SurveillanceBucket.IN_SCADENZA),
        (IN_SCADENZA_WINDOW_DAYS, SurveillanceBucket.IN_SCADENZA),  # edge inclusive
        (IN_SCADENZA_WINDOW_DAYS + 1, SurveillanceBucket.FUTURE),
        (365, SurveillanceBucket.FUTURE),
    ],
)
def test_bucket_for_boundaries(next_visit_offset_days, expected):
    from datetime import timedelta

    today = date(2026, 4, 15)
    nv = today + timedelta(days=next_visit_offset_days)
    assert bucket_for(nv, today) == expected


def test_bucket_for_none_is_none():
    assert bucket_for(None, date(2026, 4, 15)) == SurveillanceBucket.NONE
