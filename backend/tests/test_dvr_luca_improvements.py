"""Regression coverage for Luca's DVR cover corrections."""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import uuid
from zipfile import ZipFile

from docx import Document

from app.services.document_generator.branding import Branding
from app.services.document_generator.dvr_master import (
    DVRMasterGenerator,
    _employee_persons,
    _global_equipment_rows,
    _saved_order_key,
)


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


def test_saved_order_places_null_after_explicit_order_and_uses_stable_ties():
    rows = [
        SimpleNamespace(nome="Zulu", ordine=2, created_at=datetime(2026, 1, 3), id=uuid.UUID(int=3)),
        SimpleNamespace(nome="Alpha", ordine=1, created_at=datetime(2026, 1, 2), id=uuid.UUID(int=2)),
        SimpleNamespace(nome="Beta", ordine=None, created_at=datetime(2026, 1, 1), id=uuid.UUID(int=1)),
    ]
    assert [row.nome for row in sorted(rows, key=_saved_order_key)] == ["Alpha", "Zulu", "Beta"]


def test_external_rspp_and_medico_are_not_employees_but_remain_role_holders():
    internal_rspp = SimpleNamespace(nominativo="Interno", is_esterno=False, ruolo_rspp=True, ruolo_medico_competente=False)
    external_rspp = SimpleNamespace(nominativo="RSPP Esterno", is_esterno=True, ruolo_rspp=True, ruolo_medico_competente=False)
    external_medico = SimpleNamespace(nominativo="Medico Esterno", is_esterno=True, ruolo_rspp=False, ruolo_medico_competente=True)
    employees = _employee_persons([external_medico, internal_rspp, external_rspp])
    assert employees == [internal_rspp]


def test_global_equipment_groups_description_and_orders_environment_names():
    ambienti = [
        SimpleNamespace(id=uuid.UUID(int=1), nome="Reparto B"),
        SimpleNamespace(id=uuid.UUID(int=2), nome="Reparto A"),
    ]
    rows = _global_equipment_rows(
        [
            SimpleNamespace(descrizione=" Trapano   a colonna ", ambiente_id=ambienti[1].id, marcatura_ce=True, verifiche_periodiche=False),
            SimpleNamespace(descrizione="TRAPANO A COLONNA", ambiente_id=ambienti[0].id, marcatura_ce=False, verifiche_periodiche=False),
        ],
        ambienti,
    )
    assert rows == [["TRAPANO A COLONNA", "REPARTO B, REPARTO A", "MISTO", "NO"]]


def test_employee_tables_keep_saved_order_and_external_consultants_keep_roles():
    gen = DVRMasterGenerator.__new__(DVRMasterGenerator)
    internal = SimpleNamespace(
        nominativo="Zulu Interno", mansione="Operaio", is_esterno=False,
        ruolo_datore_lavoro=True, ruolo_rspp=False, ruolo_rls=False,
        ruolo_medico_competente=False, ruolo_primo_soccorso=False,
        ruolo_antincendio=False, ambienti=[], codice_fiscale=None,
        tipologia_contrattuale=None,
    )
    external = SimpleNamespace(
        nominativo="Alpha RSPP", mansione="RSPP", is_esterno=True,
        ruolo_datore_lavoro=False, ruolo_rspp=True, ruolo_rls=False,
        ruolo_medico_competente=False, ruolo_primo_soccorso=False,
        ruolo_antincendio=False, ambienti=[], codice_fiscale=None,
        tipologia_contrattuale=None,
    )
    employees = _employee_persons([internal, external])
    doc = Document()
    gen._add_dati_occupazionali_table(doc, employees)
    gen._add_single_role_title_table(doc, "Responsabile del Servizio di Prevenzione e Protezione", [external])
    assert [row.cells[0].text for row in doc.tables[0].rows[1:]] == ["ZULU INTERNO"]
    assert "ALPHA RSPP (ESTERNO)" in doc.tables[1].cell(1, 0).text
