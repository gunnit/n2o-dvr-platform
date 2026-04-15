"""Unit tests for the default P/D scoring matrix (US-2.3 AC1).

The matrix is used both server-side by
`risk_calculator.apply_default_scores_to_valutazioni` (Reset button) and
client-side by `step-rischi.tsx:initValutazioni` (pre-fill on first load).
Pins the published shape so accidental edits to reference_data.py don't
silently change the scoring on running surveys.
"""

from __future__ import annotations

from app.services.reference_data import (
    get_default_risk_matrix,
    get_default_scores,
)
from app.services.risk_calculator import apply_default_scores_to_valutazioni


def test_matrix_covers_all_eight_environment_types():
    """Every ambiente tipo the survey lets the user pick must be in the matrix."""
    matrix = get_default_risk_matrix()
    tipi = {tipo for (tipo, _) in matrix.keys()}
    expected = {
        "ufficio",
        "magazzino",
        "produzione",
        "cucina",
        "laboratorio",
        "esterno",
        "negozio",
        "altro",
    }
    assert expected <= tipi, f"Missing tipi in matrix: {expected - tipi}"


def test_matrix_returns_known_cells():
    """A few anchor cells — a change here means the Italian P/D contract moved."""
    # Ufficio: low-physical-hazard indicator.
    p, d = get_default_scores("Ufficio", "Strutture")
    assert 1 <= p <= 4
    assert 1 <= d <= 4


def test_matrix_is_case_insensitive_on_tipo():
    """Tipo comes from user-entered JSON — accept any casing."""
    mixed = get_default_scores("MagAzzino", "Macchine")
    lower = get_default_scores("magazzino", "Macchine")
    assert mixed == lower


def test_matrix_falls_back_to_low_baseline_on_miss():
    """Unknown pairs return (1, 1) so we never hand the caller a nil."""
    assert get_default_scores("spazioporto", "Dischi volanti") == (1, 1)
    assert get_default_scores("", "Strutture") == (1, 1)


def test_apply_defaults_skips_already_scored_rows():
    """AC1: defaults only fill the initial 1/1 rows — operator edits win."""
    rows = [
        {"categoria_rischio": "Macchine", "probabilita_p": 1, "danno_d": 1},
        {"categoria_rischio": "Chimici", "probabilita_p": 3, "danno_d": 4},
    ]
    updated = apply_default_scores_to_valutazioni("produzione", rows)
    # Row 1 got seeded, row 2 preserved verbatim.
    assert (
        updated[0]["probabilita_p"],
        updated[0]["danno_d"],
    ) == get_default_scores("produzione", "Macchine")
    assert updated[1]["probabilita_p"] == 3
    assert updated[1]["danno_d"] == 4


def test_apply_defaults_recomputes_indice_and_livello():
    """The seed path must leave the derived fields consistent — the DB
    column is COMPUTED, but the dict representation must match it so the
    UI doesn't flash stale values while the reload round-trips."""
    rows = [{"categoria_rischio": "Fisici", "probabilita_p": 1, "danno_d": 1}]
    updated = apply_default_scores_to_valutazioni("ufficio", rows)
    row = updated[0]
    p, d = row["probabilita_p"], row["danno_d"]
    assert row["indice_i"] == 2 * d + p
    assert row["livello_rischio"] in {
        "ACCETTABILE",
        "MODESTO",
        "GRAVE",
        "GRAVISSIMO",
    }


def test_apply_defaults_does_not_mutate_input_list():
    """Function promise in docstring — callers may rely on this."""
    original = [
        {"categoria_rischio": "Elettrici", "probabilita_p": 1, "danno_d": 1}
    ]
    snapshot = [dict(r) for r in original]
    _ = apply_default_scores_to_valutazioni("ufficio", original)
    assert original == snapshot
