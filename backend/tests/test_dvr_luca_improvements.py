"""Regression coverage for Luca's DVR corrections and for the DVR rebuilt
on N2O's model of 2026-10-20 (spec §4.2: page map, art pages, tables)."""

import asyncio
import importlib.util
import inspect as pyinspect
import logging
import re
import subprocess
import sys
from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest
from docx import Document
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_BREAK
from docx.shared import Cm, Pt
from PIL import Image

from app.services.document_generator.branding import Branding
from app.services.document_generator import design, docx_utils, dvr_master
from app.services.document_generator.dvr_master import (
    DVRMasterGenerator,
    _employee_persons,
    _global_equipment_rows,
    _saved_order_key,
)
from app.services.ambiente_photo import normalize_document_image
from scripts import verify_dvr_luca_fixture as luca_fixture_verifier
from scripts.verify_dvr_luca_fixture import build_and_audit


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _load_verify():
    path = BACKEND_ROOT / "scripts" / "verify_all_generators.py"
    spec = importlib.util.spec_from_file_location("verify_all_generators_luca", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def full_dvr_doc(tmp_path):
    module = _load_verify()
    fixture = module.build_fixture()
    fixture["persone"].append(module.mk(
        nominativo="Dott.ssa Test Medico", mansione="Medico Competente",
        ordine=99, created_at=datetime(2026, 1, 10), is_esterno=True,
        ruolo_medico_competente=True, ruolo_datore_lavoro=False,
        ruolo_rspp=False, ruolo_rls=False, ruolo_primo_soccorso=False,
        ruolo_antincendio=False, ruolo_preposto=False, ambienti=[],
        dpi_codes=[], rischi_specifici_codes=[], attrezzature_speciali=[],
    ))
    with luca_fixture_verifier._patched_generator_fixture(fixture, tmp_path):
        ok, path, message = asyncio.run(
            module.run_one("DVR_MASTER", fixture["azienda"].id)
        )
        assert ok, message
        yield Document(path), fixture


@pytest.fixture
def empty_environment_dvr_doc(tmp_path):
    module = _load_verify()
    fixture = module.build_fixture()
    fixture["ambienti"] = []
    with luca_fixture_verifier._patched_generator_fixture(fixture, tmp_path):
        ok, path, message = asyncio.run(
            module.run_one("DVR_MASTER", fixture["azienda"].id)
        )
        assert ok, message
        yield Document(path)


def _next_paragraph_has_page_break(paragraph) -> bool:
    following = paragraph._p.getnext()
    return bool(following is not None and following.xpath('.//w:br[@w:type="page"]'))


def _document_xml_has_adjacent_page_breaks(doc: Document) -> bool:
    flags = [bool(paragraph._p.xpath('.//w:br[@w:type="page"]')) for paragraph in doc.paragraphs]
    return any(left and right for left, right in zip(flags, flags[1:]))


def test_title_after_a_table_breaks_before_instead_of_leaving_a_blank_page(full_dvr_doc):
    """A title that follows a table opens its page with page-break-before,
    never with a break paragraph that a full page would push onto an empty
    page of its own."""
    doc, _fixture = full_dvr_doc
    title = next(
        paragraph for paragraph in doc.paragraphs
        if paragraph.style.name == "Heading 2" and paragraph.text == "AMBIENTI DI LAVORO"
    )
    assert title._p.getprevious().tag.endswith("}tbl")
    assert title._p.xpath("./w:pPr/w:pageBreakBefore")
    assert luca_fixture_verifier._audit_page_boundaries(doc)


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


def _jpeg_bytes(color: str = "blue") -> bytes:
    output = BytesIO()
    Image.new("RGB", (24, 24), color).save(output, "JPEG")
    return output.getvalue()


COVER_ART =BACKEND_ROOT / "assets" / "document_art" / "cover_dvr.jpg"
VERA_MARK = BACKEND_ROOT / "assets" / "document_art" / "vera_italia_mark.png"


def _png_bytes(colour: str, size=(64, 24)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, colour).save(output, "PNG")
    return output.getvalue()


def _footer_logos(doc: Document) -> set[bytes]:
    logos = set()
    for section in doc.sections:
        footer = section.footer
        for blip in footer._element.xpath(".//a:blip/@r:embed"):
            logos.add(footer.part.related_parts[blip].blob)
    return logos


def test_dvr_cover_art_has_fixed_pixels_dimensions_and_no_metadata():
    """The DVR cover is the VERA artwork of N2O's model, pinned by hash and
    size, and it carries no metadata (author, tool or account names)."""
    content = COVER_ART.read_bytes()

    assert sha256(content).hexdigest() == luca_fixture_verifier._VERA_COVER_SHA256
    with Image.open(BytesIO(content)) as image:
        image.load()
        assert image.size == (1054, 1491)
        assert image.mode == "RGB"
        assert not image.getexif()
        assert set(image.info) <= {
            "jfif", "jfif_version", "jfif_unit", "jfif_density",
            "progressive", "progression",
        }
    lowered = content.lower()
    assert all(
        marker not in lowered
        for marker in (b"exif", b"xmp", b"canva", b"adobe", b"artist")
    )


def test_dvr_cover_is_the_vera_art_and_the_footer_shows_the_org_logo(tmp_path):
    """The cover is the VERA picture alone, whatever the organization's
    branding; the organization's own logo appears in the running footer
    (spec decision 3), and its name never reaches the cover."""
    from app.services.document_generator.dispatcher import get_generator_for

    module = _load_verify()
    fixture = module.build_fixture()
    org_logo = _png_bytes("purple")
    with luca_fixture_verifier._patched_generator_fixture(fixture, tmp_path):
        generator = get_generator_for("DVR_MASTER", fixture["azienda"].id, db=None)
        generator.branding = Branding(
            firm_name="CONSULTANCY SENTINEL",
            indirizzo="SENTINEL ADDRESS",
            logo_bytes=org_logo,
            logo_content_type="image/png",
        )
        doc = Document(asyncio.run(generator.generate()))

    cover = design.section_first_blocks(doc)[0]
    assert design.art_marker(cover) == "vera-art:cover:cover_dvr"
    blips = cover.xpath(".//a:blip/@r:embed")
    assert [doc.part.related_parts[rid].blob for rid in blips] == [COVER_ART.read_bytes()]
    text = _all_text(doc)
    for leak in ("CONSULTANCY SENTINEL", "SENTINEL ADDRESS", "Documento elaborato da"):
        assert leak not in text
    assert _footer_logos(doc) == {org_logo}


def test_dvr_footer_falls_back_to_the_vera_mark(full_dvr_doc):
    doc, _fixture = full_dvr_doc
    assert _footer_logos(doc) == {VERA_MARK.read_bytes()}


def test_vera_cover_audit_rejects_asset_and_embedding_changed_together(
    tmp_path, monkeypatch
):
    """Swapping the cover file and what the DVR embeds, together, still
    fails the audit: the cover is pinned by hash, not only compared with the
    file on disk."""
    fake_backend = tmp_path / "fake-backend"
    fake_art = fake_backend / "assets" / "document_art"
    fake_art.mkdir(parents=True)
    Image.new("RGB", (1054, 1491), "red").save(fake_art / "cover_dvr.jpg", "JPEG")
    (fake_art / "vera_italia_mark.png").write_bytes(VERA_MARK.read_bytes())
    monkeypatch.setattr(design, "ART_DIR", fake_art)
    doc = Document()
    design.setup_document(doc, profile="dvr")
    design.add_art_cover(doc, "cover_dvr")
    doc.add_paragraph("Indice")
    design.finish_document(
        doc,
        title="Documento di Valutazione dei Rischi",
        azienda=_cover_azienda(),
        branding=Branding.default(),
        version=1,
        generated_at=datetime(2026, 8, 3),
    )
    target = tmp_path / "fake-cover.docx"
    doc.save(target)
    monkeypatch.setattr(luca_fixture_verifier, "BACKEND_ROOT", fake_backend)

    reopened = Document(target)
    # The embedding matches the swapped file on disk...
    cover = design.section_first_blocks(reopened)[0]
    assert design.art_marker(cover) == "vera-art:cover:cover_dvr"
    # ...and the pinned hash still rejects it.
    assert not luca_fixture_verifier._audit_vera_cover(target, reopened)


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
    gen._add_dati_anagrafici_table(doc, employees)
    gen._add_dati_occupazionali_ambienti_table(doc, employees)
    gen._add_single_role_title_table(doc, "Responsabile del Servizio di Prevenzione e Protezione", [external])
    anagrafici, occupazionali, band = doc.tables
    assert [cell.text for cell in anagrafici.rows[0].cells] == [
        "Nominativo", "Codice Fiscale", "Tipologia contrattuale",
    ]
    assert [cell.text for cell in occupazionali.rows[0].cells] == [
        "Nominativo", "Mansione", "Ambiente di Lavoro",
    ]
    assert [row.cells[0].text for row in anagrafici.rows[1:]] == ["ZULU INTERNO"]
    assert [[cell.text for cell in row.cells] for row in occupazionali.rows[1:]] == [
        ["ZULU INTERNO", "OPERAIO", "TUTTA L'AZIENDA (RUOLO TRASVERSALE)"],
    ]
    assert band.cell(1, 0).text == "ALPHA RSPP (ESTERNO)"


def test_dati_occupazionali_lists_environments_as_real_bullets():
    """One List Bullet paragraph per environment, numbered through the
    style; the cell's own empty paragraph becomes the first bullet."""
    gen = _new_generator()
    person = SimpleNamespace(
        nominativo="Anna", mansione="Impiegata", ruolo_datore_lavoro=False,
        ruolo_rspp=False, ruolo_rls=False, ruolo_medico_competente=False,
        ambienti=[SimpleNamespace(nome="Ufficio"), SimpleNamespace(nome="Magazzino")],
    )
    doc = Document()
    gen._add_dati_occupazionali_ambienti_table(doc, [person])
    cell = doc.tables[0].rows[1].cells[2]
    assert [p.text for p in cell.paragraphs] == ["UFFICIO", "MAGAZZINO"]
    # No leftover empty run from the table builder's blank cell.
    assert [len(p.runs) for p in cell.paragraphs] == [1, 1]
    assert all(p.style.name == "List Bullet" for p in cell.paragraphs)
    assert doc.styles["List Bullet"].element.xpath("./w:pPr/w:numPr/w:numId")
    assert all(run.font.size == Pt(10) for p in cell.paragraphs for run in p.runs)


def test_add_bullets_in_a_document_skips_blanks_and_falls_back_without_the_style():
    doc = Document()
    bullets = docx_utils.add_bullets(doc, ["Uno", "", None, "  ", "Due"])
    assert [p.text for p in bullets] == ["Uno", "Due"]
    assert all(p.style.name == "List Bullet" for p in bullets)
    assert docx_utils.add_bullets(doc, []) == []

    bare = Document()
    style = bare.styles["List Bullet"].element
    style.getparent().remove(style)
    typed = docx_utils.add_bullets(bare, ["Tre"])
    assert [p.text for p in typed] == ["• Tre"]


def test_company_photo_is_fitted_framed_and_skipped_when_unreadable(caplog):
    gen = _new_generator()
    doc = Document()
    output = BytesIO()
    Image.new("RGB", (400, 300), "teal").save(output, "JPEG")
    gen._add_company_photo(doc, (output.getvalue(), "image/jpeg"))
    (shape,) = doc.inline_shapes
    # 4:3 into 16.5 × 11 cm: the height binds.
    assert abs(shape.height - Cm(11)) < Cm(0.01)
    assert abs(shape.width / shape.height - 4 / 3) < 0.01
    assert shape._inline.xpath(".//pic:spPr/a:ln")

    with caplog.at_level(logging.WARNING):
        gen._add_company_photo(doc, (b"not an image", "image/jpeg"))
        gen._add_company_photo(doc, None)
    assert len(doc.inline_shapes) == 1
    assert "could not be embedded" in caplog.text


def test_sign_panels_without_artwork_are_left_out(tmp_path, monkeypatch):
    empty = tmp_path / "no-art"
    empty.mkdir()
    monkeypatch.setattr(design, "ART_DIR", empty)
    doc = Document()
    _new_generator()._add_sign_panels(doc)
    assert len(doc.inline_shapes) == 0
    assert "CARTELLI DI DIVIETO" not in _all_text(doc)


def test_dvr_writes_table_cells_with_the_kit_helper():
    """The DVR kept a copy of the kit's cell writer (same body, plus an
    ``italic`` flag no caller passed); it uses the kit's own now."""
    assert dvr_master.write_cell is docx_utils.write_cell


def test_signage_colour_table_aligns_each_column_alike():
    """Final review M-3: CODIFICA CROMATICA DELLA SEGNALETICA centred
    "Rosso" and "Verde" (they spell RISK_COLORS keys) and left "Azzurro"
    and "Giallo o giallo-arancio". Every column has one alignment."""
    doc = Document()
    _new_generator()._add_segnaletica_section(doc)
    table = next(t for t in doc.tables if t.rows[0].cells[0].text == "Colore")
    colours = [row.cells[0].text for row in table.rows[1:]]
    assert {"Rosso", "Verde", "Azzurro", "Giallo o giallo-arancio"} <= set(colours)
    for index, column in enumerate(table.columns):
        alignments = {cell.paragraphs[0].alignment for cell in column.cells[1:]}
        assert alignments == {None}, (table.rows[0].cells[index].text, alignments)


def test_sign_panels_are_judged_by_manifest_key_not_file_name(tmp_path, monkeypatch):
    """A panel prints when the art resolver used the panel's own manifest
    key, whatever its file is called (here, kept in a sub-folder), and a
    missing panel never borrows the generic divider that stands in for it."""
    art = tmp_path / "art"
    (art / "signs").mkdir(parents=True)
    for key, _title in dvr_master._SIGN_PANELS:
        monkeypatch.setitem(design.ART, key, f"signs/{key}.jpg")
        Image.new("RGB", (40, 30), "red").save(art / "signs" / f"{key}.jpg", "JPEG")
    Image.new("RGB", (40, 56), "blue").save(
        art / design.ART[design._FALLBACK_ART_KEY], "JPEG"
    )
    (art / "signs" / "sign_obbligo.jpg").unlink()
    monkeypatch.setattr(design, "ART_DIR", art)

    doc = Document()
    _new_generator()._add_sign_panels(doc)

    text = _all_text(doc)
    assert len(doc.inline_shapes) == 4
    assert "CARTELLI DI DIVIETO" in text
    assert "CARTELLI DI OBBLIGO" not in text


def test_photo_image_sources_put_database_bytes_before_local_path(tmp_path):
    local = tmp_path / "legacy.jpg"
    local.write_bytes(_jpeg_bytes("green"))
    photo = SimpleNamespace(
        document_image_bytes=_jpeg_bytes("blue"), file_path=str(local)
    )

    sources = dvr_master._photo_image_sources(photo)

    assert len(sources) == 2
    assert isinstance(sources[0], BytesIO)
    assert sources[0].read() == photo.document_image_bytes
    assert sources[1] == str(local)


def test_dvr_embeds_all_ten_database_photos():
    photos = [
        SimpleNamespace(
            id=uuid.uuid4(),
            filename=f"foto-{index}.jpg",
            document_image_bytes=_jpeg_bytes(),
            file_path=None,
        )
        for index in range(10)
    ]
    doc = Document()

    _new_generator()._add_env_foto_block(doc, "REPARTO", photos)

    assert len(doc.inline_shapes) == 10
    # N2O's model dropped the "Fig. N — filename" captions.
    assert "Fig." not in _all_text(doc)
    for shape in doc.inline_shapes:
        assert shape.width <= Cm(12) and shape.height <= Cm(9)


def test_dvr_embeds_normalized_heic_photo_derivative():
    import pillow_heif

    source = BytesIO()
    pillow_heif.from_pillow(Image.new("RGB", (24, 24), "orange")).save(source)
    derivative = normalize_document_image(source.getvalue())
    photo = SimpleNamespace(
        id=uuid.UUID(int=10),
        filename="sopralluogo.heic",
        document_image_bytes=derivative.content,
        file_path=None,
    )
    doc = Document()

    _new_generator()._add_env_foto_block(doc, "REPARTO", [photo])

    assert len(doc.inline_shapes) == 1
    assert "sopralluogo.heic" not in _all_text(doc)


def test_dvr_renders_one_filename_specific_marker_per_unavailable_photo(caplog):
    photos = [
        SimpleNamespace(
            id=uuid.UUID(int=1),
            filename="folder/assente-a.heic",
            document_image_bytes=None,
            file_path="/private/missing-a.heic",
        ),
        SimpleNamespace(
            id=uuid.UUID(int=2),
            filename="assente-b.jpg",
            document_image_bytes=None,
            file_path="/private/missing-b.jpg",
        ),
    ]
    doc = Document()

    with caplog.at_level(logging.WARNING):
        _new_generator()._add_env_foto_block(doc, "REPARTO", photos)

    text = _all_text(doc)
    assert "[Foto non disponibile: assente-a.heic]" in text
    assert "[Foto non disponibile: assente-b.jpg]" in text
    warnings = [record for record in caplog.records if record.levelno >= logging.WARNING]
    assert {
        (record.photo_id, record.photo_filename) for record in warnings
    } == {
        (str(uuid.UUID(int=1)), "assente-a.heic"),
        (str(uuid.UUID(int=2)), "assente-b.jpg"),
    }
    assert all("/private/" not in record.getMessage() for record in warnings)
    assert all("folder/" not in record.getMessage() for record in warnings)


def test_corrupt_database_derivative_falls_back_to_valid_local_file(tmp_path, caplog):
    local = tmp_path / "legacy.jpg"
    local.write_bytes(_jpeg_bytes("green"))
    photo = SimpleNamespace(
        id=uuid.UUID(int=3),
        filename="folder/legacy.jpg",
        document_image_bytes=b"corrupt",
        file_path=str(local),
    )
    doc = Document()

    with caplog.at_level(logging.WARNING):
        _new_generator()._add_env_foto_block(doc, "REPARTO", [photo])

    assert len(doc.inline_shapes) == 1
    assert "[Foto non disponibile" not in _all_text(doc)
    warnings = [record for record in caplog.records if record.levelno >= logging.WARNING]
    assert [(record.photo_id, record.photo_filename) for record in warnings] == [
        (str(uuid.UUID(int=3)), "legacy.jpg")
    ]
    assert all(str(tmp_path) not in record.getMessage() for record in warnings)


def test_parent_false_applicable_children_are_effective_in_relationship_order():
    parent = SimpleNamespace(
        applicabile=False,
        pericoli=[
            SimpleNamespace(pericolo="A", applicabile=True),
            SimpleNamespace(pericolo="B", applicabile=False),
            SimpleNamespace(pericolo="C", applicabile=True),
        ],
    )
    assert [
        row.pericolo for row in dvr_master._effective_risk_sources(parent)
    ] == ["A", "C"]


def test_all_disabled_children_do_not_resurrect_parent():
    parent = SimpleNamespace(
        applicabile=True,
        pericoli=[SimpleNamespace(pericolo="A", applicabile=False)],
    )
    assert dvr_master._effective_risk_sources(parent) == []


def test_childless_applicable_parent_remains_effective():
    parent = SimpleNamespace(applicabile=True, pericoli=[])
    assert dvr_master._effective_risk_sources(parent) == [parent]


def test_parent_false_applicable_children_render_once_and_mark_checklist_yes():
    applicable = SimpleNamespace(
        pericolo="CHILD APPLICABLE SENTINEL",
        applicabile=True,
        condizioni_esposizione="COND",
        rischio="RISK",
        misure_prevenzione="MEASURE",
        probabilita_p=2,
        danno_d=3,
        livello_rischio="GRAVE",
    )
    disabled = SimpleNamespace(
        pericolo="CHILD DISABLED SENTINEL", applicabile=False
    )
    parent = SimpleNamespace(
        categoria_rischio="Macchine",
        applicabile=False,
        pericoli=[applicable, disabled],
    )
    ambiente = SimpleNamespace(valutazioni_rischio=[parent])
    doc = Document()
    gen = _new_generator()
    gen._add_env_risk_checklist(doc, ambiente)
    gen._add_env_risk_tables(doc, ambiente)
    text = _all_text(doc)
    assert text.count("CHILD APPLICABLE SENTINEL") == 1
    assert "CHILD DISABLED SENTINEL" not in text
    assert any(
        "SI" in cell.text
        for table in doc.tables
        for row in table.rows
        for cell in row.cells
    )


def test_level_two_headings_follow_the_page_map_with_clean_page_boundaries(full_dvr_doc):
    """Heading 2 is the page map of N2O's model: in-page titles (rows 4–10,
    15–18), the 23 divider titles, one title per environment in saved order;
    unnumbered and in capitals. Every one opens its page without leaving an
    empty page behind."""
    doc, fixture = full_dvr_doc
    headings = [p.text for p in doc.paragraphs if p.style.name == "Heading 2"]
    assert headings == luca_fixture_verifier._expected_heading2(fixture)
    assert not any(re.match(r"^\s*\d+(\.\d+)*\.?\s", text) for text in headings)
    assert luca_fixture_verifier._audit_page_boundaries(doc)
    assert not _document_xml_has_adjacent_page_breaks(doc)


def _drop_page_break_before(doc, title_text):
    title = next(
        p for p in doc.paragraphs
        if p.style.name == "Heading 2" and p.text == title_text
    )
    title.paragraph_format.page_break_before = False


def _insert_blank_page_before(doc, title_text):
    title = next(
        p for p in doc.paragraphs
        if p.style.name == "Heading 2" and p.text == title_text
    )
    breaker = doc.add_paragraph()
    breaker.add_run().add_break(WD_BREAK.PAGE)
    title._p.addprevious(breaker._p)


@pytest.mark.parametrize(
    "mutate",
    [_drop_page_break_before, _insert_blank_page_before],
    ids=["title-without-break", "blank-page-before-title"],
)
def test_page_boundary_audit_rejects_a_broken_title_start(full_dvr_doc, mutate):
    doc, fixture = full_dvr_doc
    assert luca_fixture_verifier._audit_topic_separators(doc, fixture)

    mutate(doc, "AMBIENTI DI LAVORO")

    assert not luca_fixture_verifier._audit_topic_separators(doc, fixture)


def test_each_part_label_occurs_once_over_the_first_title_of_its_part(full_dvr_doc):
    doc, _fixture = full_dvr_doc
    paragraphs = doc.paragraphs
    h1 = [p for p in paragraphs if p.style.name == "Heading 1"]
    first_titles = {
        "PARTE I — DATI GENERALI DELL'AZIENDA": "PRESENTAZIONE DELL'AZIENDA",
        "PARTE II — METODOLOGIA DI VALUTAZIONE": "DEFINIZIONI",
        "PARTE III — VALUTAZIONE DEI RISCHI PER AMBIENTE DI LAVORO":
            "IDENTIFICAZIONE DELL'AMBIENTE DI LAVORO E DEGLI ADDETTI",
        "PARTE IV — PROGRAMMA DI MIGLIORAMENTO":
            "PROGRAMMA E PROCEDURE DI ATTUAZIONE DELLE MISURE DI MIGLIORAMENTO",
    }
    assert [p.text for p in h1 if p.text.startswith("PARTE ")] == list(first_titles)
    for label_text, first_title in first_titles.items():
        label = next(p for p in h1 if p.text == label_text)
        assert all(run.font.size == Pt(9) for run in label.runs)
        following = paragraphs[paragraphs.index(label) + 1]
        assert following.style.name == "Heading 2"
        assert following.text == first_title
    # Parts I and II open on in-page titles, Parts III and IV on dividers.
    for label_text in list(first_titles)[:2]:
        label = next(p for p in h1 if p.text == label_text)
        assert label._p.xpath("./w:pPr/w:pageBreakBefore")
    for label_text in list(first_titles)[2:]:
        label = next(p for p in h1 if p.text == label_text)
        assert design.art_marker(label._p.getprevious()).startswith("vera-art:divider:")


def test_empty_environment_part_keeps_its_divider_and_says_so(empty_environment_dvr_doc):
    doc = empty_environment_dvr_doc
    headings = [p.text for p in doc.paragraphs if p.style.name == "Heading 2"]
    start = headings.index("IDENTIFICAZIONE DELL'AMBIENTE DI LAVORO E DEGLI ADDETTI")
    # No environment titles: the next title is the MANSIONI divider.
    assert headings[start + 1] == "MANSIONI CHE ESPONGONO I LAVORATORI A RISCHI SPECIFICI"
    dividers = [title for _key, title in luca_fixture_verifier._divider_entries(doc)]
    assert dividers == list(luca_fixture_verifier._DIVIDER_TITLES)
    notice = next(
        p for p in doc.paragraphs if p.text == "Nessun ambiente di lavoro registrato."
    )
    title = next(
        p for p in doc.paragraphs
        if p.text == "IDENTIFICAZIONE DELL'AMBIENTE DI LAVORO E DEGLI ADDETTI"
    )
    # The notice is the content of the divider's next page.
    assert title._p.getnext().getnext() is notice._p


def _measure(ordine, priorita, misura, misura_miglioramento, letter):
    return SimpleNamespace(
        id=uuid.UUID(int=ordine), created_at=datetime(2026, 1, ordine), ordine=ordine,
        priorita=priorita, misura=misura, misura_miglioramento=misura_miglioramento,
        procedura=f"P{letter}", risorse=f"S{letter}", responsabile=f"A{letter}",
        scadenza=f"D{letter}",
    )


def test_improvement_table_has_four_portrait_columns_in_saved_order():
    rows = [
        _measure(2, "MODESTO", "R2", "M2", "2"),
        _measure(1, "GRAVE", "R1", "M1", "1"),
        _measure(3, "MEDIA", "Riduzione del rischio — Macchine", None, "3"),
    ]
    doc = Document()
    _new_generator()._add_improvement_program_table(doc, rows)
    table = doc.tables[-1]
    assert [c.text for c in table.rows[0].cells] == [
        "Misura di Miglioramento", "Risorse", "Responsabile", "Priorità",
    ]
    assert [[c.text for c in row.cells] for row in table.rows[1:]] == [
        ["M1", "S1", "A1", "GRAVE"],
        ["M2", "S2", "A2", "MODESTO"],
        # No concrete measure yet: its drafted activity, never the risk text
        # (``misura`` is the "Rischio" column of the app's grid).
        ["P3", "S3", "A3", "MEDIA"],
    ]
    fills = [row.cells[3]._tc.xpath("./w:tcPr/w:shd/@w:fill") for row in table.rows[1:]]
    assert fills == [["F97316"], ["F59E0B"], ["F59E0B"]]
    # Portrait: no landscape section is opened for the table.
    assert len(doc.sections) == 1


def test_improvement_measure_falls_back_to_activity_then_risk_then_dash():
    rows = [
        _measure(1, "ALTA", "R1", None, "1"),
        _measure(2, "ALTA", "R2", "  ", "2"),
        _measure(3, "ALTA", "R3", None, "3"),
        _measure(4, "ALTA", "  ", None, "4"),
    ]
    rows[1].procedura = None
    rows[2].procedura = "   "
    rows[3].procedura = ""
    doc = Document()
    _new_generator()._add_improvement_program_table(doc, rows)
    table = doc.tables[-1]
    assert [row.cells[0].text for row in table.rows[1:]] == ["P1", "R2", "R3", "—"]


def test_auto_seeded_measure_prints_its_drafted_actions_not_the_risk():
    """A seeded row keeps the risk summary in ``misura`` and the drafted
    actions, flagged for the RSPP, in ``procedura``; the printed Misura
    column carries the actions (final review I-2)."""
    from unittest.mock import AsyncMock, Mock

    machine_risk = SimpleNamespace(
        id=uuid.uuid4(), pericolo="Contatto con organi in movimento",
        indice_i=7, applicabile=True, livello_rischio="GRAVE",
    )
    officina = SimpleNamespace(
        nome="Officina", preposto_id=None, persone=[],
        valutazioni_rischio=[
            SimpleNamespace(categoria_rischio="Macchine", pericoli=[machine_risk]),
        ],
    )
    generator = _new_generator()
    generator.azienda_id = uuid.uuid4()
    generator.db = AsyncMock()
    generator.db.add = Mock()

    seeded = asyncio.run(
        generator._auto_seed_misure({"ambienti": [officina], "persone": []})
    )
    (measure,) = seeded
    assert measure.misura.startswith("Riduzione del rischio — Macchine")
    assert not measure.misura_miglioramento

    doc = Document()
    generator._add_improvement_program_table(doc, seeded)
    printed = doc.tables[-1].rows[1].cells[0].text
    assert printed == measure.procedura
    assert printed.startswith("[DA COMPILARE — RSPP] Verifica della marcatura CE")
    assert "Riduzione del rischio" not in printed


def test_declaration_page_and_signature_grid(full_dvr_doc):
    doc, fixture = full_dvr_doc
    declaration = next(
        paragraph for paragraph in doc.paragraphs
        if paragraph.text == "DICHIARAZIONE DEL DATORE DI LAVORO"
        and paragraph.style.name == "Heading 2"
    )
    assert _next_paragraph_has_page_break(declaration)
    grid = luca_fixture_verifier._signature_grid(doc)
    assert [[cell.text for cell in row.cells] for row in grid.rows] == [
        ["Datore di Lavoro", "Responsabile del S.P.P."],
        ["MARIO ROSSI", "LUCA BIANCHI"],
        ["", ""],
        ["Medico Competente", "RLS"],
        ["DOTT.SSA TEST MEDICO", "GIULIA VERDI"],
        ["", ""],
    ]
    for row in (grid.rows[2], grid.rows[5]):
        assert row.height >= Cm(2.5)
        assert row.height_rule == WD_ROW_HEIGHT_RULE.AT_LEAST
    for row in grid.rows:
        assert row._tr.xpath("./w:trPr/w:cantSplit")
    final_clause = next(paragraph for paragraph in doc.paragraphs if paragraph.text.startswith("di impegnarsi a rielaborare"))
    place_date = next(paragraph for paragraph in doc.paragraphs if ", lì " in paragraph.text)
    # The place line is dated like the footer's revision.
    assert place_date.text.endswith(fixture["generated_at"].strftime("%d/%m/%Y"))
    assert final_clause._p.xpath("./w:pPr/w:keepNext")
    assert place_date._p.xpath("./w:pPr/w:keepNext")
    assert final_clause._p.getnext() is place_date._p
    assert place_date._p.getnext() is grid._tbl


def test_luca_fixture_auditor_reports_all_acceptance_checks(tmp_path):
    report = build_and_audit(tmp_path)
    assert report == {key: True for key in luca_fixture_verifier._REPORT_KEYS}
    assert len(report) == 25


def _all_paragraph_texts(doc: Document) -> list[str]:
    """Every paragraph's text: body, table cells, headers and footers."""
    texts = [paragraph.text for paragraph in doc.paragraphs]
    texts += [
        paragraph.text
        for table in doc.tables
        for row in table.rows
        for cell in row.cells
        for paragraph in cell.paragraphs
    ]
    for section in doc.sections:
        for part in (
            section.header, section.footer,
            section.first_page_header, section.first_page_footer,
        ):
            texts += [paragraph.text for paragraph in part.paragraphs]
    return texts


def test_dvr_sparse_azienda_generates(tmp_path):
    """Review Focus 2: no environments, people, photos, allegati or misure.

    The document still opens on the VERA cover and closes on the back cover,
    the signature grid keeps its four roles with "—" for nobody, and no
    missing value leaks into the text as ``None``.
    """
    module = _load_verify()
    fixture = module.build_fixture()
    for key in ("ambienti", "persone", "attrezzature", "sostanze_chimiche"):
        fixture[key] = []

    async def no_extras(self, data):
        return {
            "foto_by_ambiente": {},
            "vdt_esposti_persona_ids": set(),
            "allegati_presenti": [],
            "misure_miglioramento": [],
            "protocolli_sanitari": [],
            "foto_presentazione": None,
        }

    with luca_fixture_verifier._patched_generator_fixture(fixture, tmp_path):
        DVRMasterGenerator._load_dvr_extras = no_extras
        ok, path, message = asyncio.run(
            module.run_one("DVR_MASTER", fixture["azienda"].id)
        )
    assert ok, message
    doc = Document(path)

    firsts = design.section_first_blocks(doc)
    assert design.art_marker(firsts[0]) == "vera-art:cover:cover_dvr"
    assert design.art_marker(firsts[-1]) == "vera-art:back_cover:back_vera"

    grid = luca_fixture_verifier._signature_grid(doc)
    assert grid is not None
    assert [cell.text for cell in grid.rows[0].cells + grid.rows[3].cells] == [
        "Datore di Lavoro", "Responsabile del S.P.P.", "Medico Competente", "RLS",
    ]
    assert [cell.text for cell in grid.rows[1].cells + grid.rows[4].cells] == [
        "—", "—", "—", "—",
    ]
    leaks = [text for text in _all_paragraph_texts(doc) if "None" in text]
    assert leaks == []


def test_luca_fixture_cli_is_directly_runnable_outside_backend(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(BACKEND_ROOT / "scripts" / "verify_dvr_luca_fixture.py"),
            "--help",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def _generator_patch_surface():
    from app.services.document_generator import (
        _biologico_common,
        allegato_gestanti,
        allegato_incendio,
        allegato_microclima,
        allegato_microclima_severo,
        allegato_mmc,
        allegato_stress,
        allegato_vdt,
        base,
        data_loader,
        duvri,
        haccp_forms,
        haccp_manuale,
        pee_azienda,
        pee_comune,
        pos,
    )

    version_classes = [
        allegato_mmc.AllegatoMmcGenerator,
        allegato_vdt.AllegatoVdtGenerator,
        allegato_stress.AllegatoStressGenerator,
        allegato_gestanti.AllegatoGestantiGenerator,
        allegato_incendio.AllegatoIncendioGenerator,
        allegato_microclima.AllegatoMicroclimaGenerator,
        allegato_microclima_severo.AllegatoMicroclimaSeveroGenerator,
        pee_azienda.PeeAziendaGenerator,
        pee_comune.PeeComuneGenerator,
        duvri.DuvriGenerator,
        pos.PosGenerator,
        haccp_manuale.HaccpManualeGenerator,
        haccp_forms.HaccpFormsGenerator,
    ]
    loader_modules = [
        (allegato_mmc, "load_mmc"),
        (allegato_vdt, "load_vdt"),
        (allegato_stress, "load_stress_all"),
        (allegato_incendio, "load_incendio"),
        (allegato_microclima, "load_microclima"),
        (allegato_microclima_severo, "load_microclima"),
        (allegato_gestanti, "load_gestanti"),
        (duvri, "load_duvri"),
        (pos, "load_pos"),
        (haccp_manuale, "load_haccp"),
        (haccp_forms, "load_haccp"),
        (pee_azienda, "load_pee"),
        (pee_comune, "load_pee"),
    ]
    data_loaders = [
        "load_mmc",
        "load_vdt",
        "load_stress",
        "load_stress_all",
        "load_incendio",
        "load_microclima",
        "load_gestanti",
        "load_biologico",
        "load_haccp",
        "load_pee",
        "load_duvri",
        "load_pos",
    ]
    return [
        (base.BaseDocumentGenerator, "load_data"),
        (base.BaseDocumentGenerator, "_get_output_dir"),
        (DVRMasterGenerator, "_load_dvr_extras"),
        (DVRMasterGenerator, "_get_next_version"),
        *[(generator, "_next_version") for generator in version_classes],
        (_biologico_common, "_next_version"),
        *[(data_loader, name) for name in data_loaders],
        *loader_modules,
        (_biologico_common, "load_biologico"),
    ]


def _snapshot_patch_surface():
    return [
        (owner, name, getattr(owner, name))
        for owner, name in _generator_patch_surface()
    ]


def _assert_patch_surface_restored(snapshot):
    assert [
        (owner, name)
        for owner, name, original in snapshot
        if getattr(owner, name) is not original
    ] == []


def _exercise_document_fixture_and_collect_patch_leaks(
    fixture_factory, tmp_path, *, raise_inside
):
    snapshots = [
        (owner, dict(vars(owner)))
        for owner in luca_fixture_verifier._generator_patch_objects()
    ]
    yielded = fixture_factory.__wrapped__(tmp_path)
    try:
        if not pyinspect.isgenerator(yielded):
            return False, luca_fixture_verifier._changed_attributes(snapshots)
        next(yielded)
        if raise_inside:
            with pytest.raises(RuntimeError, match="fixture consumer failed"):
                yielded.throw(RuntimeError("fixture consumer failed"))
        else:
            yielded.close()
        return True, luca_fixture_verifier._changed_attributes(snapshots)
    finally:
        luca_fixture_verifier._restore_attributes(
            luca_fixture_verifier._changed_attributes(snapshots)
        )


@pytest.mark.parametrize(
    "fixture_factory",
    [full_dvr_doc, empty_environment_dvr_doc],
    ids=["full", "empty-environment"],
)
@pytest.mark.parametrize("raise_inside", [False, True], ids=["success", "exception"])
def test_document_fixtures_restore_complete_generator_patch_surface(
    fixture_factory, tmp_path, raise_inside
):
    was_yield_fixture, leaks = _exercise_document_fixture_and_collect_patch_leaks(
        fixture_factory, tmp_path, raise_inside=raise_inside
    )

    assert was_yield_fixture, "fixture must yield inside the restoration context"
    assert [(getattr(owner, "__name__", repr(owner)), name) for owner, name, _ in leaks] == []


def _ordered_acme_doc_content(path: Path):
    doc = Document(path)
    roster = luca_fixture_verifier._people_table(doc, "DATI OCCUPAZIONALI")
    return (
        [row.cells[0].text.strip() for row in roster.rows[1:]],
        luca_fixture_verifier._environment_titles(doc),
    )


def test_repeat_builds_keep_exact_acme_roster_and_environment_order(tmp_path):
    expected = (
        [
            "MARIO ROSSI",
            "LUCA BIANCHI",
            "GIULIA VERDI",
            "ANTONIO MARRONE",
            "VALENTINA RINALDI",
        ],
        [
            "UFFICI AMMINISTRATIVI E TECNICI",
            "OFFICINA MECCANICA",
            "MAGAZZINO",
            "MENSA AZIENDALE CON CUCINA",
            "DEPOSITO CHIMICI",
            "AREA ESTERNA",
        ],
    )
    first = tmp_path / "first"
    second = tmp_path / "second"

    build_and_audit(first)
    build_and_audit(second)

    assert _ordered_acme_doc_content(first / "DVR_Acme_Regression.docx") == expected
    assert _ordered_acme_doc_content(second / "DVR_Acme_Regression.docx") == expected


def test_build_and_audit_restores_every_generator_patch_on_success(tmp_path):
    before = _snapshot_patch_surface()

    build_and_audit(tmp_path)

    _assert_patch_surface_restored(before)


def test_build_and_audit_restores_every_generator_patch_on_exception(
    tmp_path, monkeypatch
):
    before = _snapshot_patch_surface()

    def fail_audit(path, fixture):
        raise RuntimeError("forced audit failure")

    monkeypatch.setattr(luca_fixture_verifier, "audit_luca_docx", fail_audit)
    with pytest.raises(RuntimeError, match="forced audit failure"):
        build_and_audit(tmp_path)

    _assert_patch_surface_restored(before)


def _photo_block_doc(*, captions: bool) -> tuple[Document, list[bytes]]:
    doc = Document()
    doc.add_heading("Foto e Planimetrie — ZULU REPARTO", level=3)
    blobs = []
    for index in range(10):
        content = _jpeg_bytes(f"#{index * 20:02x}5080")
        blobs.append(content)
        doc.add_paragraph().add_run().add_picture(BytesIO(content), width=Cm(6))
        if captions:
            doc.add_paragraph(f"Fig. {index + 1} — foto-{index}.jpg")
    return doc, blobs


def test_photo_audit_accepts_ten_pictures_and_rejects_captions():
    doc, blobs = _photo_block_doc(captions=False)
    assert luca_fixture_verifier._audit_all_ten_photos(doc, {"expected_photo_blobs": blobs})

    captioned, blobs = _photo_block_doc(captions=True)
    assert not luca_fixture_verifier._audit_all_ten_photos(
        captioned, {"expected_photo_blobs": blobs}
    )
    assert not luca_fixture_verifier._audit_no_photo_captions(captioned)


def test_effective_risk_audit_rejects_sentinel_text_without_risk_tables():
    doc = Document()
    doc.add_paragraph("RISK APPLICABLE SENTINEL")

    assert not luca_fixture_verifier._audit_effective_risks(doc, {})


def test_acme_audit_rejects_wrong_roster_order(tmp_path):
    build_and_audit(tmp_path)
    fixture = luca_fixture_verifier.build_acme_fixture()
    path = tmp_path / "DVR_Acme_Regression.docx"
    doc = Document(path)
    roster = next(
        table
        for table in doc.tables
        if table.rows
        and table.rows[0].cells[0].text.strip() == "Nominativo"
    )
    first = roster.rows[1].cells[0].text
    second = roster.rows[2].cells[0].text
    roster.rows[1].cells[0].text = second
    roster.rows[2].cells[0].text = first
    doc.save(path)

    assert not luca_fixture_verifier._audit_acme_regression(path, fixture)


def test_declaration_audit_rejects_swapped_rspp_and_medico_cells():
    fixture = luca_fixture_verifier.build_luca_fixture()
    persone = sorted(fixture["persone"], key=_saved_order_key)
    doc = Document()
    design.setup_document(doc, profile="dvr")
    doc.add_paragraph("Contenuto precedente")
    gen = _new_generator()
    gen._add_dichiarazione_ddl(doc, fixture["azienda"], persone, fixture["generated_at"])
    gen._add_signature_table(doc, persone)
    assert luca_fixture_verifier._audit_declaration_signatures(doc, fixture)

    grid = luca_fixture_verifier._signature_grid(doc)
    rspp = grid.cell(1, 1).text
    medico = grid.cell(4, 0).text
    grid.cell(1, 1).text = medico
    grid.cell(4, 0).text = rspp

    assert not luca_fixture_verifier._audit_declaration_signatures(
        doc, fixture
    )
