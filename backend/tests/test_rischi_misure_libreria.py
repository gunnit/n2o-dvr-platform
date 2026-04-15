"""Unit tests for the per-client risk improvement-measure library (US-2.6 AC2).

Validates the Pydantic schemas + route registration. Auth'd DB-level CRUD
is exercised end-to-end by the frontend QA flow; mocking async SQLAlchemy
here would duplicate that without adding real coverage (see the comment in
tests/test_gestanti_cross_reference.py for the same rationale).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.rischio_misura import (
    RischioMisuraLibreriaCreate,
    RischioMisuraLibreriaUpdate,
)


# ---------------------------------------------------------------------------
# Create schema
# ---------------------------------------------------------------------------


def test_create_schema_happy_path():
    payload = RischioMisuraLibreriaCreate(
        categoria_rischio="Meccanici",
        titolo="Installare protezione fissa sulla macchina",
        descrizione="Installare riparo fisso sulle parti in movimento.",
        tipo="tecnica",
        priorita="alta",
        tempistica="entro 30 giorni",
        riferimento_normativo="art. 71 D.Lgs. 81/2008",
        provenance="ai-accepted",
    )
    assert payload.categoria_rischio == "Meccanici"
    assert payload.titolo.startswith("Installare")
    assert payload.provenance == "ai-accepted"


def test_create_schema_uses_sensible_defaults():
    """If the frontend omits tipo / priorita / provenance, defaults apply."""
    payload = RischioMisuraLibreriaCreate(
        categoria_rischio="Fisici",
        titolo="Pausa ogni 90 minuti",
        descrizione="Interrompere l'attivita ogni 90 minuti per 5 minuti.",
    )
    assert payload.tipo == "tecnica"
    assert payload.priorita == "media"
    assert payload.tempistica == ""
    assert payload.riferimento_normativo is None
    assert payload.provenance == "manual"


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("tipo", "non_esiste"),
        ("priorita", "catastrofica"),
        ("provenance", "something_else"),
    ],
)
def test_create_schema_rejects_bad_enum(field: str, bad_value: str):
    base = dict(
        categoria_rischio="Chimici",
        titolo="x",
        descrizione="y",
    )
    base[field] = bad_value
    with pytest.raises(ValidationError):
        RischioMisuraLibreriaCreate(**base)


@pytest.mark.parametrize("empty_field", ["categoria_rischio", "titolo", "descrizione"])
def test_create_schema_rejects_empty_required_fields(empty_field: str):
    base = dict(
        categoria_rischio="Chimici",
        titolo="x",
        descrizione="y",
    )
    base[empty_field] = ""
    with pytest.raises(ValidationError):
        RischioMisuraLibreriaCreate(**base)


# ---------------------------------------------------------------------------
# Update schema
# ---------------------------------------------------------------------------


def test_update_schema_all_fields_optional():
    """PATCH body can be empty and must not raise — caller might only want
    to touch updated_at, for instance."""
    payload = RischioMisuraLibreriaUpdate()
    assert payload.model_dump(exclude_unset=True) == {}


def test_update_schema_partial_change():
    payload = RischioMisuraLibreriaUpdate(priorita="urgente")
    # exclude_unset keeps the exact shape the frontend sent — critical for
    # the patch behavior in rischi_misure.py, which only touches sent keys.
    assert payload.model_dump(exclude_unset=True) == {"priorita": "urgente"}


def test_update_schema_rejects_bad_enum():
    with pytest.raises(ValidationError):
        RischioMisuraLibreriaUpdate(tipo="sconosciuto")


def test_update_schema_rejects_empty_titolo_when_provided():
    with pytest.raises(ValidationError):
        RischioMisuraLibreriaUpdate(titolo="")


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def test_router_registers_all_four_library_endpoints():
    """Fail loudly if someone removes an endpoint the measures-panel depends on."""
    from app.api.v1.router import api_router

    paths = {
        (method, getattr(r, "path", ""))
        for r in api_router.routes
        for method in getattr(r, "methods", set()) or set()
    }
    prefix = "/api/v1/aziende/{azienda_id}/rischi/misure-libreria"
    assert ("GET", prefix) in paths, "list endpoint missing"
    assert ("POST", prefix) in paths, "create endpoint missing"
    assert ("PATCH", f"{prefix}/{{misura_id}}") in paths, "patch endpoint missing"
    assert ("DELETE", f"{prefix}/{{misura_id}}") in paths, "delete endpoint missing"


def test_model_maps_to_expected_table():
    from app.models.rischio_misura_libreria import RischioMisuraLibreria

    assert RischioMisuraLibreria.__tablename__ == "rischi_misure_libreria"
    cols = {c.name for c in RischioMisuraLibreria.__table__.columns}
    # These are the frontend contract; breaking any of them silently breaks
    # measures-panel.tsx payload shape.
    for expected in (
        "azienda_id",
        "categoria_rischio",
        "titolo",
        "descrizione",
        "tipo",
        "priorita",
        "tempistica",
        "riferimento_normativo",
        "provenance",
        "created_at",
        "updated_at",
    ):
        assert expected in cols, f"column {expected!r} missing from model"
