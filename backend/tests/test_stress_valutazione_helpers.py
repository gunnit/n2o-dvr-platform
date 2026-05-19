"""Unit tests for the stress valutazione persistence endpoint helpers.

Pure-function coverage (no DB session needed) for:
  - `_split_answers_by_area`: the answers map -> JSONB column split.
  - `_serialize`: model -> response dict with calculator-derived fields.

The integration loop (HTTP -> DB -> response) is exercised by the
existing live API; these tests pin the contract so future refactors
don't regress the per-area split or the response shape.

Feedback #31 (2026-05-18).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from app.api.v1.stress_valutazione import _serialize, _split_answers_by_area
from app.services.stress_calculator import calculate_stress


def test_split_answers_by_area_buckets_correctly():
    answers = {
        "A.1": "INALTERATO",
        "A.10": "SI",
        "B1.1": "SI",
        "B6.3": "NO",
        "C1.1": "NO",
        "C4.8": "SI",
    }
    area_a, area_b, area_c = _split_answers_by_area(answers)
    assert area_a == {"A.1": "INALTERATO", "A.10": "SI"}
    assert area_b == {"B1.1": "SI", "B6.3": "NO"}
    assert area_c == {"C1.1": "NO", "C4.8": "SI"}


def test_split_answers_by_area_drops_empty_strings():
    answers = {"A.1": "", "B1.1": "SI", "C1.1": None}  # type: ignore[dict-item]
    area_a, area_b, area_c = _split_answers_by_area(answers)
    assert area_a == {}
    assert area_b == {"B1.1": "SI"}
    assert area_c == {}


def test_split_answers_by_area_ignores_unknown_prefixes():
    """A typoed indicator id shouldn't crash — just drop it."""
    answers = {"X.1": "SI", "A.1": "INALTERATO"}
    area_a, area_b, area_c = _split_answers_by_area(answers)
    assert area_a == {"A.1": "INALTERATO"}
    assert area_b == {}
    assert area_c == {}


def _make_row(**overrides):
    """SimpleNamespace mirroring StressValutazione's attribute surface."""
    base = {
        "id": uuid.uuid4(),
        "azienda_id": uuid.uuid4(),
        "gruppo_omogeneo": "Azienda intera",
        "area_a_eventi_sentinella": {"A.1": "INALTERATO"},
        "area_b_contenuto_lavoro": {"B1.1": "SI"},
        "area_c_contesto_lavoro": {"C1.1": "NO"},
        "punteggio_a": 0,
        "punteggio_b": 0,
        "punteggio_c": 0,
        "punteggio_totale": 0,
        "livello_rischio": "BASSO",
        "misure_correttive": None,
        "note": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_serialize_carries_calculator_derived_fields():
    row = _make_row()
    flat = {
        **row.area_a_eventi_sentinella,
        **row.area_b_contenuto_lavoro,
        **row.area_c_contesto_lavoro,
    }
    calc = calculate_stress(flat)
    resp = _serialize(row, calc)
    assert resp.id == row.id
    assert resp.livello_rischio == "BASSO"
    assert resp.azione is not None and "Monitoraggio" in resp.azione
    # Unanswered should list every indicator we didn't supply (we only
    # provided 3 above). Should be non-empty.
    assert len(resp.unanswered) > 0
    assert "A.2" in resp.unanswered  # one of the unanswered we expect


def test_serialize_without_calc_omits_derived_fields():
    row = _make_row()
    resp = _serialize(row)
    assert resp.azione is None
    assert resp.unanswered == []


def test_serialize_handles_null_jsonb_columns():
    """Defensive: a freshly-created row may have None instead of {}."""
    row = _make_row(
        area_a_eventi_sentinella=None,
        area_b_contenuto_lavoro=None,
        area_c_contesto_lavoro=None,
    )
    resp = _serialize(row)
    assert resp.area_a_eventi_sentinella == {}
    assert resp.area_b_contenuto_lavoro == {}
    assert resp.area_c_contesto_lavoro == {}
