"""Tests for the Phase 3 pericolo suggester (filter logic only — pure func)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from app.services.pericolo_suggester import (
    CANONICAL_TIPI,
    normalize_ambiente_tipo,
)


CATALOG_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "data" / "pericoli_catalog.json"
)


# ---------------------------------------------------------------------------
# normalize_ambiente_tipo
# ---------------------------------------------------------------------------


def test_canonical_tipi_pass_through():
    for t in CANONICAL_TIPI:
        assert normalize_ambiente_tipo(t) == t
        assert normalize_ambiente_tipo(t.upper()) == t


def test_free_text_tipi_bucket_correctly():
    cases = {
        "Ufficio direzionale": "ufficio",
        "Open space": "ufficio",
        "Sala riunioni": "ufficio",
        "Cucina industriale": "cucina",
        "Sala mensa / Refettorio": "cucina",
        "Bar / Caffetteria": "cucina",
        "Magazzino centrale": "magazzino",
        "Deposito merci": "magazzino",
        "Laboratorio chimico": "laboratorio",
        "Laboratorio analisi": "laboratorio",
        "Officina meccanica": "officina",
        "Officina elettrica": "officina",
        "Capannone produttivo": "produzione",
        "Reparto produzione": "produzione",
        "Linea di assemblaggio": "produzione",
        "Showroom / Sala esposizione": "negozio",
        "Negozio / Punto vendita": "negozio",
        "Area esterna / Cortile": "esterno",
        "Cantiere": "esterno",
        "Bagno / Servizi igienici": "altro",
        "Locale tecnico": "altro",
    }
    for raw, expected in cases.items():
        assert normalize_ambiente_tipo(raw) == expected, raw


def test_unknown_tipo_falls_back_to_altro():
    assert normalize_ambiente_tipo("teleporter bay") == "altro"
    assert normalize_ambiente_tipo("") == "altro"
    assert normalize_ambiente_tipo(None) == "altro"


# ---------------------------------------------------------------------------
# Catalog integrity — pins the seed contract.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def catalog():
    with CATALOG_PATH.open() as f:
        return json.load(f)


def test_catalog_has_107_pericoli(catalog):
    """The migration seeds this list. Hard pin so accidental edits show
    up as a test failure rather than a silent DB drift."""
    assert len(catalog["pericoli"]) == 107


def test_every_pericolo_has_required_fields(catalog):
    required = {"code", "categoria", "macro_categoria", "pericolo"}
    for p in catalog["pericoli"]:
        assert required <= set(p.keys()), p["code"]
        assert isinstance(p["ambiente_tipi"], list)
        assert isinstance(p["attrezzatura_keywords"], list)


def test_codes_are_unique(catalog):
    codes = [p["code"] for p in catalog["pericoli"]]
    assert len(codes) == len(set(codes))


def test_categoria_counts_match_meta(catalog):
    expected = catalog["_meta"]["counts_by_categoria"]
    actual: dict[str, int] = {}
    for p in catalog["pericoli"]:
        actual[p["categoria"]] = actual.get(p["categoria"], 0) + 1
    assert actual == expected


def test_ambiente_tipi_use_canonical_buckets_only(catalog):
    """Tagging script must keep the keys in the canonical bucket vocabulary
    — anything else means the suggester won't match."""
    allowed = CANONICAL_TIPI
    for p in catalog["pericoli"]:
        for t in p["ambiente_tipi"]:
            assert t in allowed, f"{p['code']} has stray bucket: {t}"


def test_p_d_defaults_only_present_when_not_delegated(catalog):
    """Rows that delegate to allegato or normativa shouldn't carry inline
    P/D; rows that don't delegate should."""
    for p in catalog["pericoli"]:
        if p.get("valutazione_riferimento"):
            assert p["p_default"] is None, p["code"]
            assert p["d_default"] is None, p["code"]
        else:
            assert p["p_default"] is not None, p["code"]
            assert p["d_default"] is not None, p["code"]


# ---------------------------------------------------------------------------
# suggest_pericoli filter logic — emulated DB rows.
# ---------------------------------------------------------------------------


@dataclass
class _FakePericolo:
    id: str = "fake-id"
    code: str = "FK-01"
    categoria: str = "Macchine"
    macro_categoria: str = "Rischi per la Sicurezza"
    pericolo: str = "Test hazard"
    condizioni_esposizione: str | None = None
    rischio: str | None = None
    misure_prevenzione: str | None = None
    p_default: int | None = 2
    d_default: int | None = 2
    valutazione_riferimento: str | None = None
    ambiente_tipi: list[str] = field(default_factory=list)
    attrezzatura_keywords: list[str] = field(default_factory=list)


@dataclass
class _FakeAmbiente:
    tipo: str | None = "Ufficio"


@dataclass
class _FakeAttrezzatura:
    descrizione: str = ""


def _filter_pericoli(rows, ambiente, attrezzature):
    """Mimic the in-loop filter from suggest_pericoli without the DB roundtrip.
    Mirrors the filter contract in the service so we can test it as a unit."""
    bucket = normalize_ambiente_tipo(ambiente.tipo)
    out = []
    for row in rows:
        ambiente_match = not row.ambiente_tipi or bucket in row.ambiente_tipi
        att_hits = []
        if row.attrezzatura_keywords:
            for att in attrezzature:
                desc = (att.descrizione or "").lower()
                if any(kw.lower() in desc for kw in row.attrezzatura_keywords):
                    if att.descrizione not in att_hits:
                        att_hits.append(att.descrizione)
        if not ambiente_match and not att_hits:
            continue
        out.append(
            {
                "pericolo": row,
                "matches_ambiente": ambiente_match,
                "triggered_by_attrezzature": att_hits,
            }
        )
    return out


def test_universal_pericolo_matches_every_ambiente():
    row = _FakePericolo(ambiente_tipi=[])  # empty == universal
    for tipo in CANONICAL_TIPI:
        result = _filter_pericoli([row], _FakeAmbiente(tipo=tipo), [])
        assert len(result) == 1
        assert result[0]["matches_ambiente"] is True


def test_specific_pericolo_filtered_to_listed_tipi():
    row = _FakePericolo(ambiente_tipi=["produzione", "officina"])
    assert _filter_pericoli([row], _FakeAmbiente("Ufficio"), []) == []
    assert _filter_pericoli([row], _FakeAmbiente("Produzione"), []) != []
    assert _filter_pericoli([row], _FakeAmbiente("Officina meccanica"), []) != []


def test_attrezzatura_keyword_overrides_ambiente_filter():
    """Saldatrice in ufficio → MA-01 shouldn't be hidden just because the
    ambiente filter excludes ufficio. Keyword override wins."""
    row = _FakePericolo(
        ambiente_tipi=["produzione", "officina"],
        attrezzatura_keywords=["saldatrice"],
    )
    result = _filter_pericoli(
        [row],
        _FakeAmbiente("Ufficio"),
        [_FakeAttrezzatura("Saldatrice MIG 220A")],
    )
    assert len(result) == 1
    assert result[0]["matches_ambiente"] is False
    assert result[0]["triggered_by_attrezzature"] == ["Saldatrice MIG 220A"]


def test_keyword_match_is_case_insensitive_substring():
    row = _FakePericolo(
        ambiente_tipi=["produzione"], attrezzatura_keywords=["forno"]
    )
    result = _filter_pericoli(
        [row],
        _FakeAmbiente("Cucina"),
        [_FakeAttrezzatura("FORNO ELETTRICO da 50L")],
    )
    assert result[0]["triggered_by_attrezzature"] == ["FORNO ELETTRICO da 50L"]


def test_multiple_keywords_dedupe_attrezzature():
    """Same attrezzatura matching two keywords surfaces the row once with
    one entry in triggered_by — not twice."""
    row = _FakePericolo(
        ambiente_tipi=[],
        attrezzatura_keywords=["forno", "elettrico"],
    )
    result = _filter_pericoli(
        [row],
        _FakeAmbiente("Cucina"),
        [_FakeAttrezzatura("Forno elettrico da 50L")],
    )
    assert len(result) == 1
    assert result[0]["triggered_by_attrezzature"] == ["Forno elettrico da 50L"]
