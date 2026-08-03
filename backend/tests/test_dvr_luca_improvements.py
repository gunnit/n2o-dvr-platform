"""Regression coverage for Luca's DVR cover corrections."""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

from docx import Document

from app.services.document_generator.branding import Branding
from app.services.document_generator.dvr_master import DVRMasterGenerator


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _new_generator() -> DVRMasterGenerator:
    return DVRMasterGenerator.__new__(DVRMasterGenerator)


def _cover_azienda():
    return SimpleNamespace(
        ragione_sociale="AZIENDA TEST SRL",
        sede_legale_via="Via Test 1",
        sede_legale_citta="Roma",
        cap_legale="00100",
        provincia_legale="RM",
        partita_iva="00000000000",
        codice_ateco="00.00.00",
    )


def _all_text(doc: Document) -> str:
    paragraph_text = [paragraph.text for paragraph in doc.paragraphs]
    table_text = [cell.text for table in doc.tables for row in table.rows for cell in row.cells]
    return "\n".join(paragraph_text + table_text)


def test_dvr_cover_embeds_vera_asset_and_omits_consultancy(tmp_path):
    """Configured organization branding must not leak into DVR covers."""
    gen = _new_generator()
    gen.branding = Branding(
        firm_name="CONSULTANCY SENTINEL",
        indirizzo="SENTINEL ADDRESS",
        logo_bytes=(BACKEND_ROOT / "assets" / "logo.png").read_bytes(),
        logo_content_type="image/png",
    )
    doc = Document()
    gen._add_cover_page(doc, _cover_azienda(), datetime(2026, 8, 3), 1)
    target = tmp_path / "cover.docx"
    doc.save(target)

    with ZipFile(target) as archive:
        media = [archive.read(name) for name in archive.namelist() if name.startswith("word/media/")]
    expected = (BACKEND_ROOT / "assets" / "n2o_vera_dvr.png").read_bytes()
    assert expected in media
    assert (BACKEND_ROOT / "assets" / "logo.png").read_bytes() not in media
    text = _all_text(doc)
    assert "DOCUMENTO DI VALUTAZIONE DEI RISCHI" in text
    assert "Documento elaborato da" not in text
    assert "CONSULTANCY SENTINEL" not in text
