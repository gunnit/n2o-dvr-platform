"""VDT health-surveillance scheduling (US-3.5).

Per D.Lgs. 81/2008 art. 176, a VDT worker classified as "Esposto" must
undergo sorveglianza sanitaria oculistica at intervals set by the medico
competente. The statutory defaults — applied unless the medico sets a
shorter cadence — are:

  * 5 years for workers under 50
  * 2 years for workers aged 50 or more

A "near-due" visit is one that comes due within the next 60 days; the
dashboard surfaces those in the "Visite in scadenza" widget. Anything
past due is "Visite scadute" (red).

Kept in a dedicated module (rather than piggy-backing on
vdt_calculator.py) because the two concerns are orthogonal: the
calculator answers "is this worker esposto?", the scheduler answers
"when is the next eye exam?". Tests live in
backend/tests/test_vdt_surveillance.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


# Statutory defaults per art. 176. The medico competente can shorten
# either interval for a specific worker; in that case the app stores
# the effective cadence in VdtValutazione.periodicita_sorveglianza and
# we never recompute it here.
PERIODICITA_STANDARD_ANNI: int = 5
PERIODICITA_OVER_50_ANNI: int = 2

# Window for the "Visite in scadenza" widget. Matches the 60-day wording
# in US-3.5 AC2 ("upcoming visit due in less than 60 days").
IN_SCADENZA_WINDOW_DAYS: int = 60


class SurveillanceBucket(str, Enum):
    """Which widget a row belongs to, if any."""

    SCADUTE = "scadute"
    IN_SCADENZA = "in_scadenza"
    FUTURE = "future"  # not surfaced on the dashboard
    NONE = "none"  # no visit scheduled (not esposto, or never seen)


@dataclass(frozen=True)
class VisitSchedule:
    """Result of compute_next_visit."""

    data_prossima_visita: date
    periodicita: str  # "quinquennale" | "biennale"
    bucket: SurveillanceBucket


def periodicita_label_for(over_50: bool) -> str:
    return "biennale" if over_50 else "quinquennale"


def cadence_years_for(over_50: bool) -> int:
    return PERIODICITA_OVER_50_ANNI if over_50 else PERIODICITA_STANDARD_ANNI


def _add_years(d: date, years: int) -> date:
    """Add N years to a date, landing on Feb 28 if the source is Feb 29.

    ``date.replace(year=…)`` raises on 29 Feb → non-leap; we clamp instead
    so scheduling never throws on leap-year birthdays.
    """
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # Feb 29 in a non-leap destination year
        return d.replace(year=d.year + years, day=28)


def compute_next_visit(
    *,
    data_ultima_visita: date | None,
    over_50: bool,
    today: date,
    classification_date: date | None = None,
) -> VisitSchedule:
    """Compute when the next eye exam is due.

    Args:
        data_ultima_visita: The last performed visit, or None if the
            worker has never had one recorded. When None the next visit
            is scheduled from ``classification_date`` (or ``today`` as a
            last resort), on the assumption that ESPOSTO classification
            today implies a first visit is due within the cadence.
        over_50: True iff the worker is 50 or older. Drives 2y vs 5y.
        today: Reference date for bucketing. Passed in so unit tests and
            the API endpoint can freeze time without monkeypatching.
        classification_date: When the worker was classified esposto.
            Used only when data_ultima_visita is None.

    Returns:
        VisitSchedule with the materialised next-visit date, the Italian
        periodicita label for the DB column, and the bucket the row
        belongs to today.
    """
    cadence = cadence_years_for(over_50)
    anchor = data_ultima_visita or classification_date or today
    next_visit = _add_years(anchor, cadence)
    return VisitSchedule(
        data_prossima_visita=next_visit,
        periodicita=periodicita_label_for(over_50),
        bucket=bucket_for(next_visit, today),
    )


def bucket_for(data_prossima_visita: date | None, today: date) -> SurveillanceBucket:
    """Which dashboard widget a given next-visit date belongs to."""
    if data_prossima_visita is None:
        return SurveillanceBucket.NONE
    if data_prossima_visita < today:
        return SurveillanceBucket.SCADUTE
    if data_prossima_visita <= today + timedelta(days=IN_SCADENZA_WINDOW_DAYS):
        return SurveillanceBucket.IN_SCADENZA
    return SurveillanceBucket.FUTURE
