"""Italian Codice Fiscale parsing utilities.

Extracts birth date, age, and sex from a 16-character Italian CF.

Format: SSS NNN YY M DD CCCC X
  - SSS: 3 letters from surname
  - NNN: 3 letters from name
  - YY:  2-digit birth year (chars 6-8)  (0-indexed: positions 6-7)
  - M:   1 letter encoding birth month   (position 8)
  - DD:  2 digits encoding birth day + sex (positions 9-10) — for women,
         day = real_day + 40
  - CCCC: 4 chars (1 letter + 3 alphanumerics) for place of birth
  - X:   single check character

These helpers return None on any malformed input — callers decide whether
that's an error or a soft-fail (e.g. UI auto-fill that just stays manual).

Reference: standard Italian CF spec (D.M. 23/12/1976 + ANPR conventions).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

# Italian month encoding in CF (uppercase letters).
_MONTH_LETTERS: dict[str, int] = {
    "A": 1,   # gennaio
    "B": 2,   # febbraio
    "C": 3,   # marzo
    "D": 4,   # aprile
    "E": 5,   # maggio
    "H": 6,   # giugno
    "L": 7,   # luglio
    "M": 8,   # agosto
    "P": 9,   # settembre
    "R": 10,  # ottobre
    "S": 11,  # novembre
    "T": 12,  # dicembre
}

# Female day offset.
_FEMALE_DAY_OFFSET = 40


def _normalize(cf: str | None) -> str | None:
    if not cf or not isinstance(cf, str):
        return None
    s = cf.strip().upper()
    if len(s) != 16:
        return None
    return s


def extract_birth_date(cf: str | None, today: date | None = None) -> date | None:
    """Return the birth date encoded in the CF, or None on invalid input.

    The 2-digit year is disambiguated against `today` (defaults to
    `date.today()`): if the 2-digit year is at most `today.year_2d + 5`,
    we interpret it as 2000+ ; otherwise as 1900+. This 5-year forward
    window matches typical CF tooling — newborns get their CF in advance,
    but no one alive today was born in (current_year + 6) yet.
    """
    s = _normalize(cf)
    if s is None:
        return None
    today = today or date.today()

    year_2d_str = s[6:8]
    month_letter = s[8]
    day_str = s[9:11]

    if not year_2d_str.isdigit() or not day_str.isdigit():
        return None
    if month_letter not in _MONTH_LETTERS:
        return None

    yy = int(year_2d_str)
    month = _MONTH_LETTERS[month_letter]
    raw_day = int(day_str)

    if raw_day > _FEMALE_DAY_OFFSET:
        day = raw_day - _FEMALE_DAY_OFFSET
    else:
        day = raw_day

    if not (1 <= day <= 31):
        return None

    # Century disambiguation. Prefer 2000+ when that interpretation
    # produces a date no more than 5 years in the future (handles
    # newborns whose CF was issued slightly before reference date);
    # otherwise fall back to 1900+. This collapses to "always pick 1900s"
    # for clearly-past two-digit years (e.g. yy=90 against today=1991).
    candidate_2000 = 2000 + yy
    if candidate_2000 <= today.year + 5:
        year = candidate_2000
    else:
        year = 1900 + yy

    try:
        return date(year, month, day)
    except ValueError:
        return None


def extract_age(cf: str | None, today: date | None = None) -> int | None:
    """Return the worker's age in completed years, or None on invalid CF."""
    today = today or date.today()
    bd = extract_birth_date(cf, today=today)
    if bd is None:
        return None
    years = today.year - bd.year
    # Subtract one if birthday hasn't happened yet this year.
    if (today.month, today.day) < (bd.month, bd.day):
        years -= 1
    if years < 0:
        return None
    return years


def extract_sex(cf: str | None) -> Literal["M", "F"] | None:
    """Return 'M' or 'F' from the CF day component, or None on invalid CF."""
    s = _normalize(cf)
    if s is None:
        return None
    day_str = s[9:11]
    if not day_str.isdigit():
        return None
    raw_day = int(day_str)
    if raw_day > _FEMALE_DAY_OFFSET:
        # Female day = real_day + 40; valid range 41-71.
        if 41 <= raw_day <= 71:
            return "F"
        return None
    if 1 <= raw_day <= 31:
        return "M"
    return None
