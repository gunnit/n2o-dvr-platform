"""Special worker-category risk rows — gestanti / minori / stranieri.

Client feedback 2026-08-13: the "Vedi normativa ..." markers must never
surface — not in the risk form (pericoli catalog) and not in the DVR risk
tables. Gestanti rows defer to the dedicated allegato when the azienda has
one; otherwise (and always for minori/stranieri) the operator scores the
indice (I = 2*D + P).
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from app.api.v1.pericoli import _normalize_special_catalog_row
from app.schemas.pericolo import PericoloLibreriaResponse
from app.services.document_generator.dvr_master import (
    GESTANTI_ALLEGATO_RIFERIMENTO,
    _normalize_special_riferimento,
)

CATALOG_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "data" / "pericoli_catalog.json"
)

SPECIAL_CODES = ("OR-03", "OR-04", "OR-05")


@pytest.fixture(scope="module")
def catalog_by_code():
    with CATALOG_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return {p["code"]: p for p in data["pericoli"]}


# ---------------------------------------------------------------------------
# Catalog seed contract
# ---------------------------------------------------------------------------


def test_catalog_special_rows_have_no_normativa_marker(catalog_by_code):
    for code in SPECIAL_CODES:
        row = catalog_by_code[code]
        assert row["valutazione_riferimento"] is None, code
        assert row["p_default"] == 2, code
        assert row["d_default"] == 2, code


def test_catalog_never_says_vedi_normativa(catalog_by_code):
    for code, row in catalog_by_code.items():
        rif = (row.get("valutazione_riferimento") or "").lower()
        assert "vedi normativa" not in rif, code


# ---------------------------------------------------------------------------
# API read-time normalization — deployed DBs were seeded from the old
# catalog by the 0a1b2c migration and still hold the legacy markers.
# ---------------------------------------------------------------------------


def _libreria_response(code: str, **overrides) -> PericoloLibreriaResponse:
    base = dict(
        id=uuid.uuid4(),
        code=code,
        categoria="Organizzazione del Lavoro",
        macro_categoria="Rischi Trasversali",
        pericolo="Test",
        p_default=None,
        d_default=None,
        valutazione_riferimento=None,
    )
    base.update(overrides)
    return PericoloLibreriaResponse(**base)


def test_api_normalizes_legacy_gestanti_row():
    out = _normalize_special_catalog_row(
        _libreria_response(
            "OR-03",
            valutazione_riferimento="Vedi normativa specifica (D.Lgs. 151/2001)",
        )
    )
    assert out.valutazione_riferimento is None
    assert out.p_default == 2
    assert out.d_default == 2


def test_api_normalizes_minori_and_stranieri():
    minori = _normalize_special_catalog_row(
        _libreria_response(
            "OR-04",
            valutazione_riferimento="Vedi normativa specifica (D.Lgs. 345/99)",
        )
    )
    stranieri = _normalize_special_catalog_row(
        _libreria_response(
            "OR-05",
            valutazione_riferimento=(
                "Verifica linguistica/formativa a cura del preposto"
            ),
        )
    )
    for out in (minori, stranieri):
        assert out.valutazione_riferimento is None
        assert out.p_default == 2
        assert out.d_default == 2


def test_api_keeps_operator_visible_scores_when_already_set():
    out = _normalize_special_catalog_row(
        _libreria_response("OR-05", p_default=3, d_default=4)
    )
    assert out.p_default == 3
    assert out.d_default == 4
    assert out.valutazione_riferimento is None


def test_api_leaves_other_rows_alone():
    out = _normalize_special_catalog_row(
        _libreria_response(
            "IN-01",
            categoria="Incendio-Esplosioni",
            valutazione_riferimento="Come da documenti allegati",
        )
    )
    assert out.valutazione_riferimento == "Come da documenti allegati"
    assert out.p_default is None
    assert out.d_default is None


# ---------------------------------------------------------------------------
# DVR emission — legacy markers never reach the I column.
# ---------------------------------------------------------------------------


def test_dvr_gestanti_marker_maps_to_allegato_reference():
    out = _normalize_special_riferimento(
        "Vedi normativa specifica (D.Lgs. 151/2001)",
        gestanti_allegato_presente=True,
    )
    assert out == GESTANTI_ALLEGATO_RIFERIMENTO


def test_dvr_gestanti_marker_drops_without_allegato():
    assert (
        _normalize_special_riferimento(
            "Vedi normativa specifica (D.Lgs. 151/2001)",
            gestanti_allegato_presente=False,
        )
        is None
    )


def test_dvr_minori_and_stranieri_markers_drop():
    for marker in (
        "Vedi normativa specifica (D.Lgs. 345/99)",
        "Verifica linguistica/formativa a cura del preposto",
    ):
        for presente in (True, False):
            assert (
                _normalize_special_riferimento(
                    marker, gestanti_allegato_presente=presente
                )
                is None
            ), marker


def test_dvr_any_vedi_normativa_text_drops():
    assert (
        _normalize_special_riferimento(
            "vedi normativa specifica (qualunque legge)",
            gestanti_allegato_presente=True,
        )
        is None
    )


def test_dvr_allegato_wording_and_none_pass_through():
    assert (
        _normalize_special_riferimento(
            "Come da documenti allegati", gestanti_allegato_presente=False
        )
        == "Come da documenti allegati"
    )
    assert (
        _normalize_special_riferimento(None, gestanti_allegato_presente=True)
        is None
    )
    assert (
        _normalize_special_riferimento(
            GESTANTI_ALLEGATO_RIFERIMENTO, gestanti_allegato_presente=False
        )
        == GESTANTI_ALLEGATO_RIFERIMENTO
    )
