"""``POST /aziende/visura/estrai`` — visura camerale at the start of the censimento.

Client call 2026-09-04: upload the visura next to the P.IVA autofill so the
operator reviews prefilled fields instead of typing them. These tests pin:

* the pure mapping from visura plaintext to ``AziendaCreate`` fields, with
  the provenance every field carries;
* the privacy contract — a natural person's codice fiscale on the visura
  never surfaces for a company, and the endpoint calls no AI and meters
  nothing, exactly like the post-creation upload it mirrors;
* the upload guards (PDF only, non-empty, <= 10 MB, readable text) and the
  route staying declared ahead of the ``/{azienda_id}`` routes.

Unit style, no DB / HTTP — the endpoint is awaited directly with a
``starlette.UploadFile``, the pattern ``test_ambiente_photo.py`` uses.
"""

from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.api.v1.aziende import estrai_visura
from app.core.exceptions import BadRequestError
from app.schemas.azienda import AziendaAutofillResponse, AziendaCreate
from app.services.visura_parser import SOURCE_LABEL, build_visura_autofill, parse_visura

BACKEND = Path(__file__).resolve().parents[1]
AZIENDE_PY = BACKEND / "app" / "api" / "v1" / "aziende.py"
PARSER_PY = BACKEND / "app" / "services" / "visura_parser.py"


# Infocamere "Visura ordinaria" layout as pypdf flattens it: one "Label value"
# row per line, the impresa's codice fiscale label wrapped over two lines, the
# amministratore's personal code further down under the cariche.
INFOCAMERE = """CAMERA DI COMMERCIO INDUSTRIA ARTIGIANATO E AGRICOLTURA DI MILANO
Registro Imprese - Archivio ufficiale della CCIAA
VISURA ORDINARIA SOCIETA' DI CAPITALE
ACME MECCANICA S.R.L.
DATI ANAGRAFICI
Indirizzo Sede legale MILANO (MI) VIA ROMA 1 CAP 20100
Domicilio digitale/PEC Acme@PEC.it
Numero REA MI - 1234567
Codice fiscale e n.iscr. al
Registro Imprese 01234567890
Partita IVA 01234567890
Forma giuridica societa' a responsabilita' limitata
Data atto di costituzione 12/03/2005
Data iscrizione 20/03/2005
Capitale sociale in Euro deliberato 20.000,00 sottoscritto 10.000,00 versato 10.000,00
Stato attivita' attiva
Data inizio attivita' 01/04/2005
Attivita'
Attivita' prevalente esercitata dall'impresa LAVORI DI MECCANICA GENERALE
Codice ATECO 2025 25.62.00 - Lavori di meccanica generale
Importanza prevalente
Addetti al 30/06/2025: 12
UNITA' LOCALI
Unita' locale n. 1
Indirizzo ROMA (RM) VIA VERDI 5 CAP 00100
Tipologia magazzino
Unita' locale n. 2
Indirizzo VIA GARIBALDI 9 - 10100 TORINO (TO)
Tipologia deposito
INFORMAZIONI DA STATUTO/ATTO COSTITUTIVO
Denominazione ACME MECCANICA S.R.L.
Durata 31/12/2050
AMMINISTRATORI
ROSSI MARIO
Codice fiscale RSSMRA80A01H501U
Carica amministratore unico
"""

PERSON_CF = "RSSMRA80A01H501U"


# ---------------------------------------------------------------------------
# Pure mapping
# ---------------------------------------------------------------------------


def test_infocamere_layout_maps_every_supported_field():
    parsed = parse_visura(INFOCAMERE)

    assert parsed.values == {
        "ragione_sociale": "ACME MECCANICA S.R.L.",
        "forma_giuridica": "SRL",
        "codice_fiscale": "01234567890",
        "partita_iva": "01234567890",
        "rea": "MI-1234567",
        "pec": "acme@pec.it",
        "sede_legale_via": "VIA ROMA 1",
        "sede_legale_citta": "MILANO",
        "cap_legale": "20100",
        "provincia_legale": "MI",
        "codice_ateco": "25.62.00",
        "attivita": "Lavori di meccanica generale",
        "data_costituzione": "2005-03-12",
        "capitale_sociale": 10000.0,
        "numero_dipendenti_dichiarati": 12,
        "sede_operativa_via": "VIA VERDI 5",
        "sede_operativa_citta": "ROMA",
        "cap_operativa": "00100",
        "provincia_operativa": "RM",
        "sedi_operative_extra": [
            {
                "via": "VIA GARIBALDI 9",
                "citta": "TORINO",
                "comune": "TORINO",
                "provincia": "TO",
                "cap": "10100",
            }
        ],
    }
    assert parsed.warnings == []


def test_label_anchored_fields_are_high_and_heuristic_ones_medium():
    parsed = parse_visura(INFOCAMERE)
    heuristic = {"attivita", "numero_dipendenti_dichiarati"}
    for name, confidence in parsed.confidence.items():
        expected = "medium" if name in heuristic else "high"
        assert confidence == expected, f"{name}: {confidence} != {expected}"


def test_values_are_a_valid_create_payload():
    """Whatever the parser emits must survive ``AziendaCreate`` validation —
    the page posts these values back unchanged when the operator saves."""
    parsed = parse_visura(INFOCAMERE)
    azienda = AziendaCreate(**parsed.values)
    assert azienda.codice_ateco == "25.62.00"
    assert azienda.data_costituzione.isoformat() == "2005-03-12"
    assert azienda.provincia_legale == "MI"


def test_capitale_falls_back_to_first_amount_without_sottoscritto():
    parsed = parse_visura("Capitale sociale 25.500,50 Euro i.v.\nStato attivita' attiva")
    assert parsed.values["capitale_sociale"] == 25500.5


def test_data_iscrizione_is_a_medium_fallback_for_data_costituzione():
    parsed = parse_visura("Data iscrizione 20/03/2005\n")
    assert parsed.values["data_costituzione"] == "2005-03-20"
    assert parsed.confidence["data_costituzione"] == "medium"


def test_heading_name_and_inline_form_are_medium_when_no_label_exists():
    parsed = parse_visura("VISURA ORDINARIA SOCIETA' DI PERSONE\nFRATELLI BIANCHI S.N.C.\nPartita IVA 01234567890\n")
    assert parsed.values["ragione_sociale"] == "FRATELLI BIANCHI S.N.C."
    assert parsed.confidence["ragione_sociale"] == "medium"
    assert parsed.values["forma_giuridica"] == "SNC"
    assert parsed.confidence["forma_giuridica"] == "medium"


def test_street_first_address_layout_is_decomposed():
    parsed = parse_visura("Sede legale: VIA GARIBALDI 9 - 10100 TORINO (TO)\n")
    assert parsed.values["sede_legale_via"] == "VIA GARIBALDI 9"
    assert parsed.values["sede_legale_citta"] == "TORINO"
    assert parsed.values["cap_legale"] == "10100"
    assert parsed.values["provincia_legale"] == "TO"


def test_address_without_cap_is_medium_confidence():
    parsed = parse_visura("Indirizzo Sede legale MILANO (MI) VIA ROMA 1\n")
    assert parsed.values["sede_legale_via"] == "VIA ROMA 1"
    assert "cap_legale" not in parsed.values
    assert parsed.confidence["sede_legale_via"] == "medium"


def test_wrapped_address_line_is_joined():
    parsed = parse_visura("Indirizzo Sede legale MILANO (MI) VIA ROMA 1\nCAP 20100\nDomicilio digitale/PEC a@b.it\n")
    assert parsed.values["cap_legale"] == "20100"
    assert parsed.values["pec"] == "a@b.it"


def test_unita_locale_matching_the_sede_legale_is_not_a_sede_operativa():
    text = (
        "Indirizzo Sede legale MILANO (MI) VIA ROMA 1 CAP 20100\n"
        "Unita' locale n. 1\nIndirizzo MILANO (MI) VIA ROMA 1 CAP 20100\n"
    )
    parsed = parse_visura(text)
    assert "sede_operativa_via" not in parsed.values
    assert "sedi_operative_extra" not in parsed.values


def test_unrecognised_text_yields_no_values_and_says_what_is_missing():
    parsed = parse_visura("Relazione tecnica sul microclima. Nessun dato societario.")
    assert parsed.values == {}
    assert len(parsed.warnings) == 3
    assert all(w.endswith("inseriscila a mano.") for w in parsed.warnings)


# ---------------------------------------------------------------------------
# Privacy — only the impresa's own codice fiscale
# ---------------------------------------------------------------------------


def test_company_visura_never_surfaces_a_persons_codice_fiscale():
    parsed = parse_visura(INFOCAMERE)
    assert PERSON_CF not in str(parsed.values)
    assert parsed.values["codice_fiscale"] == "01234567890"


def test_company_without_header_code_does_not_fall_through_to_the_amministratore():
    text = (
        "Forma giuridica societa' a responsabilita' limitata\n"
        "AMMINISTRATORI\nROSSI MARIO\nCodice fiscale RSSMRA80A01H501U\n"
    )
    parsed = parse_visura(text)
    assert "codice_fiscale" not in parsed.values


def test_ditta_individuale_keeps_the_titolare_code_because_it_is_the_impresa():
    text = (
        "Codice fiscale e n.iscr. al Registro Imprese RSSMRA80A01H501U\n"
        "Forma giuridica impresa individuale\n"
    )
    parsed = parse_visura(text)
    assert parsed.values["codice_fiscale"] == PERSON_CF
    assert parsed.values["forma_giuridica"] == "Ditta Individuale"


def test_build_response_matches_the_piva_autofill_envelope():
    response = build_visura_autofill(INFOCAMERE)
    assert isinstance(response, AziendaAutofillResponse)
    assert response.partita_iva == "01234567890"
    assert set(response.meta) == set(response.values)
    for meta in response.meta.values():
        assert meta.source == SOURCE_LABEL
        assert meta.confidence in ("high", "medium")
        assert meta.source_url is None
    assert response.warnings == []


# ---------------------------------------------------------------------------
# Endpoint guards
# ---------------------------------------------------------------------------


def _upload(content: bytes, filename: str = "visura.pdf", content_type: str = "application/pdf") -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content), headers={"content-type": content_type})


def _make_pdf(lines: list[str]) -> bytes:
    """One text-showing operator per line so pypdf hands back real newlines.

    ``test_description_revisions._make_pdf`` puts everything in one string;
    the parser is line-oriented, so this variant moves the text cursor
    (``T*``) between lines the way a real visura renderer does.
    """
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    parts = [b"BT\n/F1 10 Tf\n12 TL\n40 800 Td\n"]
    for line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        parts.append(b"(" + safe.encode("latin-1", errors="replace") + b") Tj T*\n")
    parts.append(b"ET\n")
    content = DecodedStreamObject()
    content.set_data(b"".join(parts))
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    page[NameObject("/Contents")] = content
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_endpoint_rejects_non_pdf_with_400():
    with pytest.raises(BadRequestError, match="Solo file PDF ammessi"):
        await estrai_visura(file=_upload(b"hello", filename="visura.docx", content_type="application/octet-stream"))


@pytest.mark.asyncio
async def test_endpoint_rejects_empty_file_with_400():
    with pytest.raises(BadRequestError, match="File vuoto"):
        await estrai_visura(file=_upload(b""))


@pytest.mark.asyncio
async def test_endpoint_rejects_oversize_file_with_400():
    with pytest.raises(BadRequestError, match=r"troppo grande \(max 10 MB\)"):
        await estrai_visura(file=_upload(b"%PDF-1.4\n" + b"0" * (10 * 1024 * 1024)))


@pytest.mark.asyncio
async def test_endpoint_rejects_scanned_pdf_without_text_with_400():
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    with pytest.raises(BadRequestError, match="illeggibile"):
        await estrai_visura(file=_upload(buf.getvalue()))


@pytest.mark.asyncio
async def test_endpoint_rejects_pdf_that_is_not_a_visura_with_400():
    pdf = _make_pdf(["Relazione tecnica", "Nessun dato societario in questo documento"])
    with pytest.raises(BadRequestError, match="Nessun dato riconosciuto"):
        await estrai_visura(file=_upload(pdf))


@pytest.mark.asyncio
async def test_endpoint_parses_a_real_pdf_end_to_end(tmp_path):
    """Through pypdf, from memory: nothing is written under FILE_STORAGE_PATH."""
    from app.config import settings

    original = settings.FILE_STORAGE_PATH
    settings.FILE_STORAGE_PATH = str(tmp_path)
    try:
        response = await estrai_visura(file=_upload(_make_pdf(INFOCAMERE.splitlines())))
    finally:
        settings.FILE_STORAGE_PATH = original

    assert response.values["ragione_sociale"] == "ACME MECCANICA S.R.L."
    assert response.values["partita_iva"] == "01234567890"
    assert response.values["rea"] == "MI-1234567"
    assert response.values["sedi_operative_extra"][0]["citta"] == "TORINO"
    assert response.meta["ragione_sociale"].source == SOURCE_LABEL
    assert PERSON_CF not in str(response.values)
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Wiring — route order, capability, no AI, no metering
# ---------------------------------------------------------------------------


def _endpoint_node(name: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(AZIENDE_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in aziende.py")


def _called_names(node: ast.AST) -> set[str]:
    return {
        n.func.id for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }


def test_route_is_registered_and_declared_before_the_azienda_id_routes():
    from tests.conftest import route_pairs

    from app.api.v1.router import api_router

    assert ("POST", "/api/v1/aziende/visura/estrai") in route_pairs(api_router)
    # Source order is the routing order: a literal segment declared after
    # `/{azienda_id}` would be parsed as a UUID and 422.
    assert _endpoint_node("estrai_visura").lineno < _endpoint_node("get_azienda").lineno


def test_endpoint_is_gated_on_the_same_capability_as_the_upload():
    for name in ("estrai_visura", "upload_visura"):
        node = _endpoint_node(name)
        guards = {
            arg.id
            for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "require_capability"
            for arg in n.args
            if isinstance(arg, ast.Name)
        }
        assert guards == {"SURVEY_WRITE"}, f"{name}: {guards}"


def test_both_visura_endpoints_share_the_upload_guards():
    for name in ("estrai_visura", "upload_visura"):
        assert "_read_visura_upload" in _called_names(_endpoint_node(name)), name


def test_endpoint_calls_no_ai_and_meters_nothing_like_the_upload_it_mirrors():
    """The existing visura upload is local pypdf + redaction with no AI call and
    no credit charge; the pre-creation parse keeps exactly that posture."""
    for name in ("estrai_visura", "upload_visura"):
        called = _called_names(_endpoint_node(name))
        assert not called & {"metered", "generate_company_description", "autofill_from_piva", "consolidate"}, (
            f"{name} reaches AI or the meter: {sorted(called)}"
        )


def test_parser_module_never_touches_the_ai_layer():
    source = PARSER_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    } | {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not any(m.startswith(("app.services.ai", "openai", "httpx")) for m in imports), imports
