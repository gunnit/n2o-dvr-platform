"""Unit tests for the Italian Codice Fiscale parser.

These cover the parsing rules used by the MMC frontend (auto-derive age
band from CF when an operator picks a worker) and any future feature that
needs a quick birth-date / sex from the CF without round-tripping through
ANPR. See app.services.codice_fiscale for the spec.
"""

from __future__ import annotations

from datetime import date

from app.services.codice_fiscale import (
    extract_age,
    extract_birth_date,
    extract_sex,
)

# Reference fixed "today" for deterministic age computation.
_TODAY = date(2026, 5, 5)


# ---------------------------------------------------------------------------
# Valid inputs
# ---------------------------------------------------------------------------


def test_valid_male_cf_extracts_birth_date():
    # Male, born 1985-03-15. Year=85 → 1985; Month=C (March); Day=15.
    cf = "RSSMRA85C15F205Z"
    assert extract_birth_date(cf, today=_TODAY) == date(1985, 3, 15)


def test_valid_male_cf_extracts_age():
    cf = "RSSMRA85C15F205Z"
    # Birthday already passed by 2026-05-05 → age 41.
    assert extract_age(cf, today=_TODAY) == 41


def test_valid_male_cf_extracts_sex_M():
    cf = "RSSMRA85C15F205Z"
    assert extract_sex(cf) == "M"


def test_valid_female_cf_extracts_birth_date():
    # Female, born 1990-05-22. Year=90 → 1990; Month=E (May);
    # Day=62 (= 22 + 40 female offset).
    cf = "BNCMRA90E62H501W"
    assert extract_birth_date(cf, today=_TODAY) == date(1990, 5, 22)


def test_valid_female_cf_extracts_age():
    cf = "BNCMRA90E62H501W"
    # 2026-05-05: birthday May 22 not yet → age 35.
    assert extract_age(cf, today=_TODAY) == 35


def test_valid_female_cf_extracts_sex_F():
    cf = "BNCMRA90E62H501W"
    assert extract_sex(cf) == "F"


def test_2000s_birth_year_05_resolves_to_2005():
    # A CF with year=05 in 2026 should resolve to 2005, not 1905.
    cf = "RSSMRA05A10F205X"
    bd = extract_birth_date(cf, today=_TODAY)
    assert bd is not None
    assert bd.year == 2005


def test_2000s_birth_age_is_correct():
    cf = "RSSMRA05A10F205X"  # 2005-01-10, male
    # 2026-05-05: birthday already passed → age 21.
    assert extract_age(cf, today=_TODAY) == 21


def test_century_window_just_in_future():
    # 5-year forward window: year=30 in 2026 (today_2d=26, threshold=31)
    # should resolve to 2030, not 1930.
    cf = "RSSMRA30A10F205X"
    bd = extract_birth_date(cf, today=_TODAY)
    assert bd is not None
    assert bd.year == 2030


def test_century_window_outside_future_resolves_to_1900s():
    # year=40 in 2026 (threshold=31) → outside window → 1940.
    cf = "RSSMRA40A10F205X"
    bd = extract_birth_date(cf, today=_TODAY)
    assert bd is not None
    assert bd.year == 1940


def test_lowercase_input_is_accepted():
    assert extract_age("rssmra85c15f205z", today=_TODAY) == 41


def test_whitespace_is_stripped():
    assert extract_age("  RSSMRA85C15F205Z  ", today=_TODAY) == 41


# ---------------------------------------------------------------------------
# Invalid inputs return None — callers handle the soft-fail
# ---------------------------------------------------------------------------


def test_short_cf_returns_none():
    assert extract_birth_date("RSSMRA85C15F205") is None  # 15 chars
    assert extract_age("RSSMRA85C15F205") is None
    assert extract_sex("RSSMRA85C15F205") is None


def test_empty_cf_returns_none():
    assert extract_birth_date("") is None
    assert extract_age("") is None
    assert extract_sex("") is None


def test_none_input_returns_none():
    assert extract_birth_date(None) is None
    assert extract_age(None) is None
    assert extract_sex(None) is None


def test_bad_month_letter_returns_none():
    # 'Z' is not a valid month letter.
    cf = "RSSMRA85Z15F205Z"
    assert extract_birth_date(cf, today=_TODAY) is None
    assert extract_age(cf, today=_TODAY) is None


def test_non_digit_year_returns_none():
    cf = "RSSMRAXXC15F205Z"
    assert extract_birth_date(cf, today=_TODAY) is None


def test_non_digit_day_returns_none():
    cf = "RSSMRA85CXXF205Z"
    assert extract_birth_date(cf, today=_TODAY) is None
    assert extract_sex(cf) is None


def test_invalid_day_zero_returns_none():
    cf = "RSSMRA85C00F205Z"
    assert extract_birth_date(cf, today=_TODAY) is None
    assert extract_sex(cf) is None


def test_invalid_day_too_big_returns_none():
    # Day=72 is outside the female-encoded range (max 71).
    cf = "RSSMRA85C72F205Z"
    assert extract_sex(cf) is None


def test_february_30_returns_none():
    # Calendar-impossible date should fail.
    cf = "RSSMRA85B30F205Z"  # Feb 30
    assert extract_birth_date(cf, today=_TODAY) is None


# ---------------------------------------------------------------------------
# Age boundary behaviour
# ---------------------------------------------------------------------------


def test_age_birthday_not_yet_this_year():
    # Born 1990-12-31; today 1991-06-01 → age 0 (birthday not yet).
    cf = "RSSMRA90T31F205Z"
    today = date(1991, 6, 1)
    assert extract_age(cf, today=today) == 0


def test_age_birthday_today():
    # Born 1990-06-01; today 2020-06-01 → age 30.
    cf = "RSSMRA90H01F205Z"
    today = date(2020, 6, 1)
    assert extract_age(cf, today=today) == 30
