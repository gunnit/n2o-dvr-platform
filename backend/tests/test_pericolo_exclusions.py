"""Excluded catalog rows are reported, not silently dropped (2026-08-19)."""

from types import SimpleNamespace

from app.services.pericolo_suggester import classify_catalog_row, exclusion_reason


def _row(**kw):
    base = dict(code="MA-01", ambiente_tipi=["officina"], attrezzatura_keywords=["tornio"])
    base.update(kw)
    return SimpleNamespace(**base)


def _att(descrizione):
    return SimpleNamespace(descrizione=descrizione)


def test_universal_row_is_never_excluded():
    info = classify_catalog_row(_row(ambiente_tipi=[], attrezzatura_keywords=[]), "ufficio", [])
    assert info["excluded"] is False
    assert info["matches_ambiente"] is True
    assert info["exclusion_reason"] is None


def test_row_kept_by_ambiente_type():
    info = classify_catalog_row(_row(), "officina", [])
    assert info["excluded"] is False and info["matches_ambiente"] is True


def test_row_kept_by_attrezzatura_keyword():
    info = classify_catalog_row(_row(), "ufficio", [_att("Tornio parallelo")])
    assert info["excluded"] is False
    assert info["matches_ambiente"] is False
    assert info["triggered_by_attrezzature"] == ["Tornio parallelo"]


def test_row_excluded_with_a_readable_reason():
    info = classify_catalog_row(_row(), "ufficio", [_att("Stampante")])
    assert info["excluded"] is True
    assert "officina" in info["exclusion_reason"]
    assert "tornio" in info["exclusion_reason"]
    assert "ufficio" in info["exclusion_reason"]


def test_reason_without_keywords_names_only_the_types():
    reason = exclusion_reason(_row(attrezzatura_keywords=[]), "cucina")
    assert reason == "Previsto per ambienti di tipo officina; questo ambiente è di tipo cucina."
