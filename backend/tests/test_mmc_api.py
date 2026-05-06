"""Regression tests for the MMC PATCH save bug (admin feedback 2026-05-04 #1).

The original PATCH handler always re-ran NIOSH math from a merged "current
row + updates" dict and wrote back only the enriched NIOSH-derived fields,
plus whatever happened to land via dict expansion. Two issues:

  1. Non-NIOSH fields (compito, note, misure_proposte) were prone to
     getting dropped on partial updates because the merge order made them
     easy to forget.
  2. When the client sent only a non-NIOSH field (e.g. just
     `misure_proposte`), the multipliers were still recomputed — and if the
     row hadn't been created with all 7 NIOSH inputs, the calc reverted
     them to default 1.0, silently corrupting the saved assessment.

The fix splits the merge into a pure helper (`_build_patch_assignments`)
that only recomputes multipliers when a NIOSH input actually changed, and
otherwise persists exactly what the client sent. These tests pin that
contract so future refactors don't regress it.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.api.v1.mmc import _apply_niosh, _build_patch_assignments


def _make_row(**overrides) -> SimpleNamespace:
    """Build a row-like stand-in mirroring MmcValutazione's attribute surface.

    `_build_patch_assignments` only reads attributes from `row`, so a
    SimpleNamespace is enough — keeps the test pure (no DB session needed).
    """
    base = {
        "id": uuid.uuid4(),
        "azienda_id": uuid.uuid4(),
        "persona_id": None,
        "ambiente_id": None,
        "compito": "Sollevamento cassette",
        "peso_kg": 12.0,
        "sesso": "M",
        "fascia_eta": ">18",
        "altezza_cm": 75,
        "dislocazione_cm": 25,
        "distanza_cm": 30,
        "angolo_gradi": 0,
        "giudizio_presa": "Buono",
        "frequenza_atti_min": 4.0,
        "durata_min": 90,
        "cp": 25.0,
        "fattore_a": 1.0,
        "fattore_b": 1.0,
        "fattore_c": 1.0,
        "fattore_d": 1.0,
        "fattore_e": 1.0,
        "fattore_f": 1.0,
        "plr": 25.0,
        "indice_ir": 0.48,
        "livello_rischio": "VERDE",
        "area_classificazione": "Verde",
        "note": None,
        "misure_proposte": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _seed_with_niosh() -> SimpleNamespace:
    """Build a row whose multipliers match its NIOSH inputs (consistent state)."""
    inputs = {
        "sesso": "M",
        "fascia_eta": ">18",
        "peso_kg": 12.0,
        "altezza_cm": 75,
        "dislocazione_cm": 25,
        "distanza_cm": 30,
        "angolo_gradi": 0,
        "giudizio_presa": "Buono",
        "frequenza_atti_min": 4.0,
        "durata_min": 90,
        "cp": 25.0,
    }
    enriched = _apply_niosh(inputs)
    return _make_row(**enriched)


# ---------------------------------------------------------------------------
# Bug repro: non-NIOSH PATCH must not drop user-sent fields
# ---------------------------------------------------------------------------


def test_patch_misure_proposte_persists():
    row = _seed_with_niosh()
    updates = {"misure_proposte": "Ridurre la frequenza di sollevamento"}

    out = _build_patch_assignments(row, updates)

    assert out.get("misure_proposte") == "Ridurre la frequenza di sollevamento"


def test_patch_non_niosh_fields_do_not_recompute_multipliers():
    """If only non-NIOSH fields change, derived multipliers must NOT be touched.

    This is the silent-corruption case: previously, recomputing from a
    `current` dict that omitted some NIOSH inputs would default missing
    multipliers to 1.0 and overwrite valid persisted values.
    """
    row = _seed_with_niosh()
    updates = {"misure_proposte": "Ridurre la frequenza"}

    out = _build_patch_assignments(row, updates)

    # None of the NIOSH-derived fields should appear in the assignments,
    # because nothing in the input space changed.
    for k in (
        "cp",
        "fattore_a",
        "fattore_b",
        "fattore_c",
        "fattore_d",
        "fattore_e",
        "fattore_f",
        "plr",
        "indice_ir",
        "livello_rischio",
        "area_classificazione",
    ):
        assert k not in out, f"{k} should not be reassigned for a non-NIOSH PATCH"


def test_patch_compito_only_persists_and_does_not_touch_niosh():
    row = _seed_with_niosh()
    updates = {"compito": "Carico pallet su scaffale alto"}

    out = _build_patch_assignments(row, updates)

    assert out["compito"] == "Carico pallet su scaffale alto"
    assert "fattore_a" not in out
    assert "plr" not in out


def test_patch_note_persists():
    row = _seed_with_niosh()
    updates = {"note": "Operazione svolta solo nei turni mattutini"}

    out = _build_patch_assignments(row, updates)

    assert out["note"] == "Operazione svolta solo nei turni mattutini"
    assert "indice_ir" not in out


# ---------------------------------------------------------------------------
# When a NIOSH input changes, multipliers MUST be recomputed
# ---------------------------------------------------------------------------


def test_patch_frequenza_recomputes_multipliers():
    """Bumping frequency from 4 to 8 atti/min must move factor_f down."""
    row = _seed_with_niosh()
    f_before = row.fattore_f
    plr_before = row.plr

    updates = {"frequenza_atti_min": 8.0}

    out = _build_patch_assignments(row, updates)

    assert "fattore_f" in out
    assert "plr" in out
    assert "indice_ir" in out
    # Higher frequency → lower factor_f → lower PLR.
    assert out["fattore_f"] < f_before
    assert out["plr"] < plr_before
    # The frequency value the client sent must also pass through.
    assert out["frequenza_atti_min"] == 8.0


def test_patch_peso_recomputes_indice_ir_only_when_meaningful():
    """peso_kg is a NIOSH input (drives IR = peso/PLR). PATCH must update IR."""
    row = _seed_with_niosh()
    ir_before = row.indice_ir

    updates = {"peso_kg": 24.0}  # double the load

    out = _build_patch_assignments(row, updates)

    assert "indice_ir" in out
    # Doubling the peso roughly doubles IR (PLR unchanged at the same
    # multipliers + cp). Use a strict inequality rather than an exact
    # match — we only care that the recompute fired.
    assert out["indice_ir"] > ir_before
    assert out["peso_kg"] == 24.0


def test_patch_combined_niosh_and_note_persists_both():
    """Mixed PATCH: persist user fields AND recompute NIOSH from merged state."""
    row = _seed_with_niosh()

    updates = {
        "frequenza_atti_min": 10.0,
        "misure_proposte": "Introdurre pause ogni 30 minuti",
    }

    out = _build_patch_assignments(row, updates)

    assert out["frequenza_atti_min"] == 10.0
    assert out["misure_proposte"] == "Introdurre pause ogni 30 minuti"
    assert "fattore_f" in out
    assert "plr" in out


def test_patch_no_changes_returns_empty_assignments():
    row = _seed_with_niosh()
    out = _build_patch_assignments(row, {})
    assert out == {}
