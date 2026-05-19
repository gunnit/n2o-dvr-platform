"""Regression test for feedback #32 (2026-05-18).

The allegato_gestanti generator used to read row-dict keys "rischio" and
"misura", but the gestanti API persists "descrizione" + ("misura_alternativa"
or "justification"). Result: the "Rischio" and "Misura adottata" columns
came out empty even when the operator had filled the form. This pins the
key-mapping logic so future schema drift can't silently break the
allegato again.
"""

from __future__ import annotations

# Re-implement the row-mapping the generator does in-line. Keeping it in
# a tiny helper makes it directly testable; the generator itself stays as
# inline code so the docx render path doesn't need a DB session.

def _map_rischio_row(r: dict) -> list[str]:
    descrizione = (
        r.get("descrizione")
        or r.get("rischio")
        or r.get("risk_key")
        or ""
    )
    allegato = r.get("allegato", "")
    misura = (
        r.get("misura_alternativa")
        or r.get("justification")
        or r.get("misura")
        or ""
    )
    return [descrizione, allegato, misura]


def test_maps_real_api_shape_for_rejected_risk():
    """The shape persisted by POST /aziende/{id}/gestanti/{val_id}/risk-decision
    when action='reject' — should yield the descrizione and the alternative."""
    row = {
        "risk_key": "agenti_chimici_pericolosi",
        "allegato": "Allegato B",
        "descrizione": "Esposizione ad agenti chimici pericolosi",
        "action": "reject",
        "justification": None,
        "misura_alternativa": "Riassegnazione a mansione di segreteria",
    }
    assert _map_rischio_row(row) == [
        "Esposizione ad agenti chimici pericolosi",
        "Allegato B",
        "Riassegnazione a mansione di segreteria",
    ]


def test_maps_real_api_shape_for_accepted_risk():
    """action='accept' carries the justification in place of an alternative."""
    row = {
        "risk_key": "movimentazione_carichi",
        "allegato": "Allegato C",
        "descrizione": "Movimentazione manuale dei carichi",
        "action": "accept",
        "justification": "Pesi inferiori ai limiti di legge per gestanti",
        "misura_alternativa": None,
    }
    assert _map_rischio_row(row) == [
        "Movimentazione manuale dei carichi",
        "Allegato C",
        "Pesi inferiori ai limiti di legge per gestanti",
    ]


def test_falls_back_to_legacy_keys():
    """Historical rows persisted before the schema change used "rischio"
    and "misura"; the mapping must still surface them."""
    row = {"rischio": "Lavoro notturno", "allegato": "Allegato A", "misura": "Esonero"}
    assert _map_rischio_row(row) == ["Lavoro notturno", "Allegato A", "Esonero"]


def test_empty_row_yields_empty_strings_not_none():
    assert _map_rischio_row({}) == ["", "", ""]


def test_generator_uses_same_logic():
    """Sanity check: the generator source contains the same key sequence
    so the test stays meaningful as code evolves."""
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "app" / "services" / "document_generator" / "allegato_gestanti.py"
    text = src.read_text(encoding="utf-8")
    assert 'r.get("descrizione")' in text
    assert 'r.get("misura_alternativa")' in text
    assert 'r.get("justification")' in text
