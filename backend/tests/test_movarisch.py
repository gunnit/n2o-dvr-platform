"""Unit tests for the MoVaRisCh chemical-risk calculator.

Ground-truth values are the real worked schede in
templates/allegato_chimico_luca_2026-05-19/ (CALAMIT + WODECAR), cross-checked
by hand against docs/context/RISCHIO_CHIMICO_MAPPING.md.

The "clean" schede (Solido / Stato gassoso / Polveri fini) are reproduced
exactly. The "Liquido" schede are NOT reproduced verbatim: the source tool
zeroed their inhalation route (D=0 artifact); this module applies the
model-correct rule (Einal = I x d > 0) — see test_correct_rule_*.
"""

import math

import pytest

from app.services.movarisch_calculator import (
    assess,
    classify_salute,
    ecute,
    einal,
    p_score,
    safety_level,
)


# ---------------------------------------------------------------------------
# P — hazard index (highest score among phrases)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "frasi, expected_p",
    [
        # CLP H-codes (all phrases visible in the schede)
        (["H302", "H315", "H317 cat.1B", "H319", "H411", "EUH205"], 4.5),   # EMAX RESINA EP 138
        (["H315", "H317 cat.1B", "H319", "H411"], 4.5),                      # ARALDITE 2012 RESIN
        (["H315", "H319"], 3.0),                                            # HYGIENIST MULTIUSO
        (["H314 cat.1B"], 5.75),                                            # GMT GENIUS
        (["H314 cat.1B", "H318"], 5.75),                                    # BRILL BOMAR
        (["H223", "H336"], 3.5),                                            # SVITOL SPRAY
        (["H222", "H315", "H319", "H336"], 3.5),                            # ROLMACRYL
        (["H315", "H317 cat.1B", "H318", "H411"], 4.5),                     # ARALDITE 2015-1
        # Legacy R-phrases (incl. combined codes)
        (["R36/38", "R43", "R51/53"], 4.0),                                 # ARALDITE DW 0133 RED
        (["R36/38", "R43"], 4.0),                                           # ARALDIT DRL
        (["R22", "R35", "R41"], 5.85),                                      # POLY CAR
        (["R34"], 4.85),                                                    # PULVO M
        (["R21", "R34", "R43"], 4.85),                                      # INDURENTE HY 956
        (["R36/38"], 2.75),                                                 # TERMOSOL-BIO
        (["R12", "R40"], 7.0),                                              # Spray SALDOIL (R40 scored, not canc.)
        # Unclassified / non-hazardous -> floor 1.0
        ([], 1.0),
        (["- Sostanze e miscele non classificate pericolose"], 1.0),       # EVA / Shell / INOX FIT / LR
    ],
)
def test_p_score_ground_truth(frasi, expected_p):
    assert p_score(frasi)["p"] == expected_p


def test_p_score_governing_code():
    res = p_score(["H302", "H315", "H317 cat.1B", "H319"])
    assert res["p"] == 4.5
    assert res["governing_code"] == "H317 cat.1B"
    assert res["unmatched"] == []


def test_p_score_bare_code_takes_highest_category():
    # Bare "H314" (no category in SDS) -> conservative max of 1A/1B/1C = 6.25
    assert p_score(["H314"])["p"] == 6.25


def test_p_score_carcinogen_flagged_not_scored():
    res = p_score(["H350"])
    assert res["is_cancerogeno"] is True
    assert res["p"] == 1.0  # no numeric phrase -> floor; carc handled under Capo II

    res2 = p_score(["H350", "H315"])
    assert res2["is_cancerogeno"] is True
    assert res2["p"] == 2.5  # H315 governs the numeric score


def test_p_score_reports_unmatched():
    res = p_score(["H999", "H315"])
    assert res["p"] == 2.5
    assert "H999" in res["unmatched"]


# ---------------------------------------------------------------------------
# Einal — 4-matrix chain (reproduces the clean schede exactly)
# ---------------------------------------------------------------------------

def test_einal_solido_eva():
    # EVA black/brown/nature: Solido, <0.1, uso controllato, contenimento, <15min, <1m
    r = einal("Solido - Nebbia", "< 0,1 Kg", "Uso controllato",
              "Contenimento completo", "< 15 minuti", "< 1 m")
    assert (r["d_ind"], r["u_ind"], r["c_ind"], r["i_ind"]) == (1, 1, 1, 1)
    assert r["d_factor"] == 1.0
    assert r["einal"] == 1.0


def test_einal_gas_svitol():
    # SVITOL: Stato gassoso -> D=2, U=2, C=1, I=1, d=1 -> Einal=1 (tool match)
    r = einal("Stato gassoso", "< 0,1 Kg", "Uso controllato",
              "Contenimento completo", "< 15 minuti", "< 1 m")
    assert (r["d_ind"], r["u_ind"], r["c_ind"], r["i_ind"]) == (2, 2, 1, 1)
    assert r["einal"] == 1.0


def test_einal_high_exposure_chain():
    # Worst-case chain: high-volatility liquid, large qty, dispersive, direct
    # manipulation, >6h, <1m -> D=4,U=3,C=3,I=10,d=1 -> Einal=10
    r = einal("Media / Alta volatilità e Polveri fini", ">= 100 Kg", "Uso dispersivo",
              "Manipolazione diretta", ">= 6 ore", "< 1 m")
    assert (r["d_ind"], r["u_ind"], r["c_ind"], r["i_ind"]) == (4, 3, 3, 10)
    assert r["einal"] == 10.0


def test_einal_distance_scaling():
    r = einal("Stato gassoso", ">= 100 Kg", "Uso dispersivo",
              "Manipolazione diretta", ">= 6 ore", ">= 10 m")
    assert r["i_ind"] == 10 and r["d_factor"] == 0.1
    assert r["einal"] == 1.0  # 10 * 0.1


# ---------------------------------------------------------------------------
# Ecute — dermal matrix
# ---------------------------------------------------------------------------

def test_ecute_matrix():
    assert ecute("Uso controllato", "Contatto accidentale")["ecute"] == 3   # Medio
    assert ecute("Sistema chiuso", "Nessun contatto")["ecute"] == 1         # Basso
    assert ecute("Uso dispersivo", "Contatto esteso")["ecute"] == 10        # Molto Alto
    assert ecute("Uso controllato", "Contatto esteso")["ecute"] == 10       # Molto Alto


# ---------------------------------------------------------------------------
# Health zone boundaries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "r, zona, livello",
    [
        (0.1, "VERDE", "Irrilevante"),
        (14.99, "VERDE", "Irrilevante"),
        (15.0, "ARANCIO", "Irrilevante"),
        (20.99, "ARANCIO", "Irrilevante"),
        (21.0, "GIALLO", "Superiore"),
        (40.0, "GIALLO", "Superiore"),
        (40.01, "ROSSA", "Superiore"),
        (80.0, "ROSSA", "Superiore"),
        (80.01, "NERA", "Superiore"),
        (100.0, "NERA", "Superiore"),
    ],
)
def test_classify_salute_boundaries(r, zona, livello):
    assert classify_salute(r) == (zona, livello)


# ---------------------------------------------------------------------------
# Safety level
# ---------------------------------------------------------------------------

def test_safety_level_h_codes():
    assert safety_level(["H319"])["livello"] == "Non Basso"   # eye damage
    assert safety_level(["H315"])["livello"] == "Basso"       # skin irritation
    assert safety_level(["H224"])["livello"] == "Non Basso"   # flammable
    assert safety_level([])["livello"] == "Basso"
    assert safety_level(["H315", "H319"])["livello"] == "Non Basso"  # worst wins


def test_safety_level_legacy_r_unresolved():
    res = safety_level(["R36/38"])
    assert "R36/38" in res["unresolved"]   # H-keyed table can't resolve R-codes


# ---------------------------------------------------------------------------
# Full scheda — reproduces the clean worked examples end-to-end
# ---------------------------------------------------------------------------

def test_assess_eva_full():
    # EVA: not classified, Solido; cutaneo uso controllato + contatto accidentale
    r = assess([], "Solido - Nebbia", "< 0,1 Kg", "Uso controllato",
               "Contenimento completo", "< 15 minuti", "< 1 m",
               via_cutanea_applicabile=True, contatto_cutaneo="Contatto accidentale")
    assert r["p"] == 1.0
    assert r["einal"] == 1.0 and r["rinal"] == 1.0
    assert r["ecute"] == 3 and r["rcute"] == 3.0
    assert r["rcum"] == pytest.approx(math.sqrt(10), abs=1e-3)
    assert r["zona"] == "VERDE" and r["livello_salute"] == "Irrilevante"
    assert r["livello_sicurezza"] == "Basso"


def test_assess_svitol_full():
    # SVITOL: P=3.5 (H336), gas; Rcute = 3.5*3 = 10.5 ; tool final = Irrilevante / Non Basso
    r = assess(["H223", "H336"], "Stato gassoso", "< 0,1 Kg", "Uso controllato",
               "Contenimento completo", "< 15 minuti", "< 1 m",
               via_cutanea_applicabile=True, contatto_cutaneo="Contatto accidentale")
    assert r["p"] == 3.5
    assert r["rinal"] == 3.5 and r["rcute"] == 10.5
    assert r["rcum"] == pytest.approx(math.sqrt(3.5**2 + 10.5**2), abs=1e-3)  # ~11.07
    assert r["zona"] == "VERDE" and r["livello_salute"] == "Irrilevante"
    assert r["livello_sicurezza"] == "Non Basso"


def test_assess_araldite_2015_full():
    # ARALDITE 2015-1: P=4.5, Solido; Rcute = 13.5 ; final Irrilevante / Non Basso
    r = assess(["H315", "H317 cat.1B", "H318", "H411"], "Solido - Nebbia", "< 0,1 Kg",
               "Uso controllato", "Contenimento completo", "< 15 minuti", "< 1 m",
               via_cutanea_applicabile=True, contatto_cutaneo="Contatto accidentale")
    assert r["p"] == 4.5
    assert r["rcute"] == 13.5
    assert r["rcum"] == pytest.approx(math.sqrt(4.5**2 + 13.5**2), abs=1e-3)  # ~14.23
    assert r["zona"] == "VERDE"


def test_assess_inhalation_only():
    # No dermal route -> R governed by Rinal, no Ecute/Rcute
    r = assess(["H336"], "Stato gassoso", "< 0,1 Kg", "Uso controllato",
               "Contenimento completo", "< 15 minuti", "< 1 m",
               via_cutanea_applicabile=False)
    assert r["ecute"] is None and r["rcute"] is None
    assert r["rcum"] == r["rinal"] == r["r_governing"]


# ---------------------------------------------------------------------------
# THE CORRECT RULE — divergence from the source tool's D=0 artifact
# ---------------------------------------------------------------------------

def test_correct_rule_liquid_inhalation_never_zero():
    """EMAX RESINA EP 138 was printed by the tool with Einal=0 (D=0 artifact,
    physical state left as generic 'Liquido'). Correctly classified as a
    low-volatility liquid, the inhalation route is non-zero."""
    r = einal("Bassa Volatilità", "< 0,1 Kg", "Uso controllato",
              "Contenimento completo", "< 15 minuti", "< 1 m")
    assert r["einal"] > 0          # the tool emitted 0 here — we do not
    assert r["einal"] == 1.0


def test_correct_rule_same_final_classification():
    """Applying the correct rule to EMAX (P=4.5) keeps the SAME final zone the
    tool reported (Irrilevante), proving the correction is safe for these
    low-exposure cases while fixing the under-report for higher exposure."""
    r = assess(["H302", "H315", "H317 cat.1B", "H319", "H411", "EUH205"],
               "Bassa Volatilità", "< 0,1 Kg", "Uso controllato",
               "Contenimento completo", "< 15 minuti", "< 1 m",
               via_cutanea_applicabile=True, contatto_cutaneo="Contatto accidentale")
    assert r["p"] == 4.5
    assert r["rinal"] == 4.5            # tool had 0
    assert r["rcum"] == pytest.approx(14.23, abs=0.05)
    assert r["zona"] == "VERDE" and r["livello_salute"] == "Irrilevante"
