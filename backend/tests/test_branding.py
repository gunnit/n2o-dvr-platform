"""Unit tests for the document branding resolver (per-organization letterhead).

Pure logic — no DB. Guards the fallback behaviour that keeps document
generation working for a sparse org and keeps the committed N2O logo as the
default so existing output never regresses.
"""

from __future__ import annotations

import types
from pathlib import Path

from app.services.document_generator.branding import (
    DEFAULT_LOGO_PATH,
    Branding,
    resolve_logo_path,
)


def _fake_org(**overrides):
    """A duck-typed Organization-like object."""
    base = {
        "name": "Acme Safety SRL",
        "logo_path": None,
        "indirizzo": None,
        "cap": None,
        "citta": None,
        "provincia": None,
        "partita_iva": None,
        "codice_fiscale": None,
        "telefono": None,
        "email": None,
        "sito_web": None,
        "rspp_nome": None,
    }
    base.update(overrides)
    return types.SimpleNamespace(**base)


def test_default_uses_n2o_firm_name():
    b = Branding.default()
    assert b.firm_name == "N2O SRL"
    assert b.logo_path is None


def test_from_organization_reads_fields():
    org = _fake_org(
        name="Acme Safety SRL",
        indirizzo="Via Roma 1",
        partita_iva="01234567890",
        rspp_nome="Mario Rossi",
    )
    b = Branding.from_organization(org)
    assert b.firm_name == "Acme Safety SRL"
    assert b.indirizzo == "Via Roma 1"
    assert b.partita_iva == "01234567890"
    assert b.rspp_nome == "Mario Rossi"


def test_from_organization_blank_name_falls_back_to_default_firm_name():
    org = _fake_org(name="   ")
    b = Branding.from_organization(org)
    assert b.firm_name == "N2O SRL"


def test_from_organization_handles_none_org():
    b = Branding.from_organization(None)
    assert b.firm_name == "N2O SRL"


def test_resolve_logo_path_falls_back_to_default_when_no_custom():
    b = Branding.default()
    assert resolve_logo_path(b) == DEFAULT_LOGO_PATH


def test_resolve_logo_path_falls_back_when_custom_missing_on_disk():
    b = Branding.default()
    b.logo_path = "/data/org_logos/does-not-exist/nope.png"
    assert resolve_logo_path(b) == DEFAULT_LOGO_PATH


def test_resolve_logo_path_uses_custom_when_present(tmp_path: Path):
    logo = tmp_path / "custom.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n")  # minimal PNG magic
    b = Branding.default()
    b.logo_path = str(logo)
    assert resolve_logo_path(b) == logo


def test_has_letterhead_detail_true_when_address_present():
    b = Branding.default()
    assert b.has_letterhead_detail() is False
    b.indirizzo = "Via Roma 1"
    assert b.has_letterhead_detail() is True
