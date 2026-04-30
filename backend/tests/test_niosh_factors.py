"""Tests for the centralized NIOSH factor lookup module.

These tests pin the values in app.data.niosh_factors against the canonical
tables in REFERENCE_DATA.md so any drift between the calculator endpoint,
the persistence router, and the document generator is caught here.
"""

from app.data.niosh_factors import (
    classify_ir,
    compute_plr,
    durata_band,
    factor_a,
    factor_b,
    factor_c,
    factor_d,
    factor_e,
    factor_f,
)


# ---------------------------------------------------------------------------
# Factor A - Altezza (height of hands at lift origin)
# ---------------------------------------------------------------------------


def test_factor_a_optimal_height_is_one():
    assert factor_a(75) == 1.0


def test_factor_a_at_breakpoints():
    assert factor_a(0) == 0.78
    assert factor_a(25) == 0.85
    assert factor_a(50) == 0.93
    assert factor_a(150) == 0.78


def test_factor_a_clamps_above_175():
    assert factor_a(180) == 0.0
    assert factor_a(200) == 0.0


def test_factor_a_interpolates_between_rows():
    # Halfway between 25 (0.85) and 50 (0.93) -> 0.89
    assert abs(factor_a(37.5) - 0.89) < 0.01


# ---------------------------------------------------------------------------
# Factor B - Dislocazione verticale
# ---------------------------------------------------------------------------


def test_factor_b_minimum_displacement_is_one():
    assert factor_b(25) == 1.0


def test_factor_b_clamps_above_175():
    assert factor_b(180) == 0.0


# ---------------------------------------------------------------------------
# Factor C - Distanza orizzontale
# ---------------------------------------------------------------------------


def test_factor_c_min_distance_is_one():
    assert factor_c(25) == 1.0


def test_factor_c_drops_steeply():
    # Per REFERENCE_DATA: 40 cm -> 0.63
    assert factor_c(40) == 0.63


# ---------------------------------------------------------------------------
# Factor D - Angolo di asimmetria
# ---------------------------------------------------------------------------


def test_factor_d_zero_angle_is_one():
    assert factor_d(0) == 1.0


def test_factor_d_at_135_degrees():
    assert factor_d(135) == 0.57


# ---------------------------------------------------------------------------
# Factor E - Giudizio sulla presa
# ---------------------------------------------------------------------------


def test_factor_e_buono():
    assert factor_e("Buono") == 1.0


def test_factor_e_discreto():
    assert factor_e("Discreto") == 0.95


def test_factor_e_scarso():
    assert factor_e("Scarso") == 0.90


def test_factor_e_unknown_falls_back_to_worst_case():
    assert factor_e("nonsense") == 0.90


# ---------------------------------------------------------------------------
# Factor F - Frequenza x durata
# ---------------------------------------------------------------------------


def test_factor_f_low_freq_short_duration():
    # 0.2 atti/min, breve (<60 min) -> 1.00
    assert factor_f(0.2, 30) == 1.0


def test_factor_f_freq_2_long_duration():
    # 2 atti/min, lunga (>120 min) -> 0.65
    assert factor_f(2, 240) == 0.65


def test_factor_f_high_freq_returns_zero():
    # >15 atti/min -> 0 in every band
    assert factor_f(20, 30) == 0.0


def test_factor_f_zero_freq_returns_one():
    assert factor_f(0, 60) == 1.0


def test_durata_band_breve_media_lunga():
    assert durata_band(30) == "breve"
    assert durata_band(60) == "media"
    assert durata_band(120) == "media"
    assert durata_band(240) == "lunga"


# ---------------------------------------------------------------------------
# IR classification thresholds
# ---------------------------------------------------------------------------


def test_classify_ir_verde_at_or_below_075():
    assert classify_ir(0.5) == "VERDE"
    assert classify_ir(0.75) == "VERDE"


def test_classify_ir_giallo_between_075_and_1():
    assert classify_ir(0.8) == "GIALLO"
    assert classify_ir(1.0) == "GIALLO"


def test_classify_ir_rosso_above_1():
    assert classify_ir(1.01) == "ROSSO"
    assert classify_ir(2.0) == "ROSSO"


# ---------------------------------------------------------------------------
# Composite compute_plr
# ---------------------------------------------------------------------------


def test_compute_plr_optimal_lift_yields_cp():
    # All factors = 1.0 -> PLR = CP
    out = compute_plr(
        cp=25.0,
        altezza_cm=75,
        dislocazione_cm=25,
        distanza_cm=25,
        angolo_gradi=0,
        giudizio_presa="Buono",
        frequenza_atti_min=0.2,
        durata_min=30,
    )
    assert out["fattore_a"] == 1.0
    assert out["fattore_b"] == 1.0
    assert out["fattore_c"] == 1.0
    assert out["fattore_d"] == 1.0
    assert out["fattore_e"] == 1.0
    assert out["fattore_f"] == 1.0
    assert out["plr"] == 25.0


def test_compute_plr_acme_antonio_marrone_case():
    # Fixture values for ACME's tornitore Antonio Marrone
    out = compute_plr(
        cp=25.0,
        altezza_cm=50,
        dislocazione_cm=50,
        distanza_cm=30,
        angolo_gradi=30,
        giudizio_presa="Buono",
        frequenza_atti_min=2.0,
        durata_min=120,
    )
    assert out["fattore_a"] == 0.93
    assert out["fattore_b"] == 0.91
    assert out["fattore_c"] == 0.83
    assert out["fattore_d"] == 0.90
    assert out["fattore_e"] == 1.0
    assert out["fattore_f"] == 0.84
    # PLR = 25 * 0.93 * 0.91 * 0.83 * 0.90 * 1.0 * 0.84 = ~13.28
    assert 13.0 < out["plr"] < 13.5


def test_compute_plr_extreme_freq_collapses_plr():
    # 20 atti/min -> F=0 -> PLR=0
    out = compute_plr(
        cp=25.0,
        altezza_cm=75,
        dislocazione_cm=25,
        distanza_cm=25,
        angolo_gradi=0,
        giudizio_presa="Buono",
        frequenza_atti_min=20,
        durata_min=120,
    )
    assert out["plr"] == 0.0
