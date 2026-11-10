"""The design kit: tokens, page types, furniture and table builders.

Spec: docs/superpowers/specs/2026-11-10-document-layout-redesign-design.md
§4.1 (the kit), §5 (degradation). Every generated document is built from
these pieces, so they are pinned here at the XML level — the level Word,
LibreOffice and the preview parser all read.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from types import SimpleNamespace

import pytest
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.oxml.ns import qn
from docx.shared import Cm

from app.services.document_generator import design, docx_utils
from app.services.document_generator.branding import Branding

GENERATED_AT = datetime(2026, 11, 10, 9, 30)
DOC_TITLE = "Documento di Valutazione dei Rischi"
SLOTS = ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs")
THEME_SLOTS = ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme")


def _azienda(**overrides):
    base = {
        "ragione_sociale": "Acme Meccanica Srl",
        "sede_legale_via": "Via Roma 1",
        "sede_legale_citta": "Milano",
        "cap_legale": "20100",
        "provincia_legale": "MI",
        "partita_iva": "01234567890",
        "codice_ateco": "25.62.00",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _finish(doc, *, branding=None, **kwargs):
    design.finish_document(
        doc,
        title=DOC_TITLE,
        azienda=_azienda(),
        branding=branding or Branding.default(),
        version=1,
        generated_at=GENERATED_AT,
        **kwargs,
    )


def _kit_doc(profile: str = "dvr") -> Document:
    doc = Document()
    design.setup_document(doc, profile=profile)
    return doc


def _text(container) -> str:
    return "\n".join(p.text for p in container.paragraphs)


def _paragraph_elements(doc) -> list:
    return [el for el in doc.element.body.iterchildren() if el.tag == qn("w:p")]


def _w_text(element) -> str:
    """Visible text of an element: its ``w:t`` nodes only (``itertext`` would
    also pick up the anchor's ``wp:posOffset`` values)."""
    return "".join(t.text or "" for t in element.iter(qn("w:t")))


def _cell_fill(cell) -> str | None:
    fills = cell._tc.xpath("./w:tcPr/w:shd/@w:fill")
    return fills[0] if fills else None


def _run_colours(cell) -> set[str]:
    return {str(r.font.color.rgb) for p in cell.paragraphs for r in p.runs if r.text}


def _docpr_names(element) -> list[str]:
    return [d.get("name") for d in element.iter(qn("wp:docPr"))]


# ---------------------------------------------------------------------------
# Tokens and styles
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile", ["dvr", "attachment"])
def test_styles_use_arial_everywhere(profile):
    doc = _kit_doc(profile)
    for name in ("Normal", "Heading 1", "Heading 2", "Heading 3"):
        fonts = doc.styles[name].element.find(qn("w:rPr")).find(qn("w:rFonts"))
        assert {slot: fonts.get(qn(slot)) for slot in SLOTS} == dict.fromkeys(SLOTS, "Arial"), name
        # A theme attribute overrides the explicit name in Word: the heading
        # would print in the theme's Calibri Light whatever w:ascii says.
        assert not any(fonts.get(qn(t)) for t in THEME_SLOTS), name

    defaults = doc.styles.element.find(qn("w:docDefaults")).find(qn("w:rPrDefault"))
    fonts = defaults.find(qn("w:rPr")).find(qn("w:rFonts"))
    assert {slot: fonts.get(qn(slot)) for slot in SLOTS} == dict.fromkeys(SLOTS, "Arial")
    assert not any(fonts.get(qn(t)) for t in THEME_SLOTS)
    themed = doc.styles.element.xpath(
        "//w:rFonts[@w:asciiTheme or @w:hAnsiTheme or @w:eastAsiaTheme or @w:cstheme]"
    )
    assert themed == []
    assert docx_utils.FONT_FAMILY == "Arial"


def test_normal_style_tokens_are_body_ink_and_not_justified():
    doc = _kit_doc("attachment")
    normal = doc.styles["Normal"]
    assert normal.font.size.pt == 12
    assert str(normal.font.color.rgb) == "061B31"
    assert normal.paragraph_format.space_after.pt == 4
    # Stored as w:line="259" (240ths of a line), so 1.08 reads back as 1.079.
    assert normal.paragraph_format.line_spacing == pytest.approx(1.08, abs=0.005)
    assert normal.element.xpath("./w:pPr/w:jc") == []


def test_dvr_profile_section_title_is_25pt_centered_caps():
    doc = _kit_doc("dvr")
    h2 = doc.styles["Heading 2"].element
    assert h2.xpath("./w:rPr/w:sz/@w:val") == ["50"]
    assert h2.xpath("./w:pPr/w:jc/@w:val") == ["center"]
    caps = h2.xpath("./w:rPr/w:caps")
    assert len(caps) == 1 and caps[0].get(qn("w:val")) in (None, "1", "true", "on")
    assert h2.xpath("./w:rPr/w:color/@w:val") == ["003D74"]
    assert h2.xpath("./w:rPr/w:b")

    h1 = doc.styles["Heading 1"]
    assert h1.font.size.pt == 14 and h1.font.bold
    assert h1.element.xpath("./w:pPr/w:jc") == []
    h3 = doc.styles["Heading 3"].element
    assert h3.xpath("./w:rPr/w:sz/@w:val") == ["24"]
    assert h3.xpath("./w:pPr/w:jc/@w:val") == ["center"]


def test_attachment_profile_headings_are_left_aligned_navy():
    doc = _kit_doc("attachment")
    for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 12)):
        style = doc.styles[name]
        assert style.font.size.pt == size, name
        assert style.font.bold and str(style.font.color.rgb) == "003D74", name
        assert style.element.xpath("./w:pPr/w:jc") == [], name
        assert style.element.xpath("./w:rPr/w:caps") == [], name


def test_type_scale_tokens():
    scale = docx_utils.TYPE_SCALE
    assert {
        k: scale[k]
        for k in (
            "body", "table", "table_header", "section_title", "sub_title", "part_label",
            "front_heading", "cover_title", "header", "footer", "note",
        )
    } == {
        "body": 12, "table": 10, "table_header": 10, "section_title": 25, "sub_title": 12,
        "part_label": 9, "front_heading": 14, "cover_title": 26, "header": 9, "footer": 8.5,
        "note": 10,
    }
    # Legacy keys still read by generators that have not moved to roles.
    assert {k: scale[k] for k in ("h1", "h2", "h3", "cover_subtitle", "cover_client", "small")} == {
        "h1": 16, "h2": 13, "h3": 12, "cover_subtitle": 12, "cover_client": 16, "small": 8.5,
    }
    assert docx_utils.BRAND_TABLE_HEADER_HEX == "4F81BD"
    assert str(docx_utils.NOTE_GREY) == "666666"
    assert docx_utils.LOGO_PATH == docx_utils.BACKEND_ROOT / "assets" / "document_art" / "vera_italia_mark.png"


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------


def test_data_table_header_fill_and_borders():
    doc = _kit_doc()
    table = docx_utils.add_data_table(
        doc,
        ["Rev.", "Motivazione", "Data"],
        [["00", "Emissione", "10/11/2026"], ["01", "Aggiornamento", "—"]],
    )
    header = table.rows[0]
    for cell in header.cells:
        assert _cell_fill(cell) == "4F81BD"
        assert _run_colours(cell) == {"FFFFFF"}
        assert all(r.font.bold for p in cell.paragraphs for r in p.runs)
    assert header._tr.xpath("./w:trPr/w:tblHeader")
    assert header._tr.xpath("./w:trPr/w:cantSplit")

    borders = table._tbl.tblPr.find(qn("w:tblBorders"))
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = borders.find(qn(f"w:{edge}"))
        assert (el.get(qn("w:val")), el.get(qn("w:sz")), el.get(qn("w:color"))) == ("single", "4", "auto"), edge

    for row in table.rows[1:]:
        # LibreOffice loops forever on a keep-together row taller than a page.
        assert not row._tr.xpath("./w:trPr/w:cantSplit")
    assert _cell_fill(table.rows[1].cells[0]) is None
    assert _cell_fill(table.rows[2].cells[0]) == "F6F9FC"  # zebra

    def jc(cell):
        return cell.paragraphs[0].alignment

    from docx.enum.text import WD_ALIGN_PARAGRAPH

    assert jc(table.rows[1].cells[0]) == WD_ALIGN_PARAGRAPH.CENTER  # a number
    assert jc(table.rows[2].cells[2]) == WD_ALIGN_PARAGRAPH.CENTER  # the dash
    assert jc(table.rows[1].cells[1]) is None  # text stays left
    sizes = {r.font.size.pt for row in table.rows for c in row.cells for p in c.paragraphs for r in p.runs}
    assert sizes == {10}


def test_kv_table_variants():
    doc = _kit_doc()
    blue = docx_utils.add_kv_table(doc, [("Ragione sociale", "Acme Srl"), ("P.IVA", None)])
    light = docx_utils.add_kv_table(doc, [("Azienda", "Acme Srl")], variant="light")

    label, value = blue.rows[0].cells
    assert _cell_fill(label) == "4F81BD" and _run_colours(label) == {"FFFFFF"}
    assert _cell_fill(value) is None
    assert blue.rows[1].cells[1].text == ""

    label, value = light.rows[0].cells
    assert _cell_fill(label) == "F6F9FC" and _run_colours(label) == {"003D74"}
    assert all(r.font.bold for p in label.paragraphs for r in p.runs)
    assert _cell_fill(value) is None

    widths = [int(w) for w in blue._tbl.xpath("./w:tblGrid/w:gridCol/@w:w")]
    assert widths == [round(Cm(5.0) / 635), round(Cm(11.5) / 635)]
    with pytest.raises(ValueError):
        docx_utils.add_kv_table(doc, [("a", "b")], variant="green")


def test_role_band_is_a_blue_band_over_a_centred_value():
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = _kit_doc()
    table = docx_utils.add_role_band(doc, "Datore di Lavoro", "")
    band, value = table.rows[0].cells[0], table.rows[1].cells[0]
    assert _cell_fill(band) == "4F81BD" and _run_colours(band) == {"FFFFFF"}
    assert band.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert value.text == "—" and value.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert len(table.columns) == 1


def test_signature_grid_pairs_roles_and_keeps_rows_together():
    doc = _kit_doc()
    table = docx_utils.add_signature_grid(
        doc,
        [
            ("Datore di Lavoro", "Mario Rossi"),
            ("Responsabile del S.P.P.", "Luca Bianchi"),
            ("Medico Competente", ""),
            ("RLS", None),
        ],
    )
    assert len(table.columns) == 2 and len(table.rows) == 6
    headers = [table.rows[0], table.rows[3]]
    for row in headers:
        for cell in row.cells:
            assert _cell_fill(cell) == "003D74" and _run_colours(cell) == {"FFFFFF"}
    assert [c.text for c in table.rows[0].cells] == ["Datore di Lavoro", "Responsabile del S.P.P."]
    assert [c.text for c in table.rows[1].cells] == ["Mario Rossi", "Luca Bianchi"]
    assert [c.text for c in table.rows[4].cells] == ["—", "—"]
    for sign_row in (table.rows[2], table.rows[5]):
        assert sign_row.height >= Cm(2.5)
        assert sign_row.height_rule == WD_ROW_HEIGHT_RULE.AT_LEAST
        assert all(not c.text for c in sign_row.cells)
    for row in table.rows:
        assert row._tr.xpath("./w:trPr/w:cantSplit")


def test_level_cell_colours_risk_and_priority():
    doc = _kit_doc()
    table = docx_utils.add_data_table(doc, ["Livello"], [["P = 2; D = 3; I = 8; GRAVE"], ["?"]])
    docx_utils.level_cell(table.rows[1].cells[0], "grave")
    cell = table.rows[1].cells[0]
    assert _cell_fill(cell) == "F97316"
    assert _run_colours(cell) == {"FFFFFF"}
    assert all(r.font.bold for p in cell.paragraphs for r in p.runs)
    docx_utils.level_cell(table.rows[2].cells[0], "sconosciuto")  # unknown: untouched, no crash
    assert _cell_fill(table.rows[2].cells[0]) == "F6F9FC"


def test_body_paragraph_is_justified():
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = _kit_doc()
    p = docx_utils.add_body_paragraph(doc, "Il presente documento rappresenta l'attuazione dell'obbligo.")
    assert p.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
    assert p.style.name == "Normal"


def test_long_cell_does_not_hang_libreoffice(tmp_path):
    soffice = shutil.which("soffice")
    if soffice is None:
        pytest.skip("LibreOffice (soffice) is not installed")
    doc = _kit_doc()
    words = " ".join(f"parola{i % 97}" for i in range(6000))
    docx_utils.add_data_table(doc, ["Descrizione"], [[words]])
    source = tmp_path / "long_cell.docx"
    doc.save(source)
    profile = tmp_path / "lo-profile"
    result = subprocess.run(
        [
            "timeout", "120", soffice, f"-env:UserInstallation=file://{profile}",
            "--headless", "--convert-to", "pdf", "--outdir", str(tmp_path), str(source),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "long_cell.pdf").exists()


# ---------------------------------------------------------------------------
# Art manifest
# ---------------------------------------------------------------------------

APPENDIX_A_KEYS = {
    "cover_dvr", "back_vera", "cover_vera",
    "div_servizi_igienici", "div_macchine", "div_sostanze", "div_fattori_pericolo",
    "div_ambienti", "div_mansioni", "div_dpi", "div_segnaletica", "div_formazione",
    "div_miglioramento", "div_leggi", "div_sorveglianza", "div_riunione", "div_infortuni",
    "div_comportamenti", "div_gestione_dpi", "div_infrastrutture", "div_sensibili",
    "div_acquisti", "div_appalti", "div_dichiarazione", "div_generico",
    "sign_divieto", "sign_avvertimento", "sign_obbligo", "sign_emergenza", "sign_antincendio",
    "vera_italia_mark",
}


def test_art_manifest_files_exist():
    assert APPENDIX_A_KEYS <= set(design.ART)
    for key, filename in design.ART.items():
        assert (design.ART_DIR / filename).is_file(), key
    # Ruling 1: aliases, not duplicate files.
    assert design.ART["cover_vera"] == design.ART["back_vera"]
    assert design.ART["div_generico"] == design.ART["div_ambienti"]


def test_art_path_falls_back_to_generico():
    assert design.art_path("div_leggi") == design.ART_DIR / "div_leggi.jpg"
    assert design.art_path("div_non_esiste") == design.ART_DIR / design.ART["div_generico"]


def test_art_path_is_none_when_even_generico_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(design, "ART_DIR", tmp_path)
    assert design.art_path("div_leggi") is None


# ---------------------------------------------------------------------------
# Page types
# ---------------------------------------------------------------------------


def test_art_anchor_shape():
    doc = _kit_doc()
    doc.add_paragraph("Contenuto precedente")
    title = design.add_divider(doc, "GESTIONE LEGGI E REGOLAMENTI", "div_leggi")

    section = doc.sections[-1]
    anchors = doc.element.body.xpath(".//wp:anchor")
    assert len(anchors) == 1
    anchor = anchors[0]
    assert anchor.get("behindDoc") == "1"
    assert anchor.xpath("./wp:wrapNone")
    for axis in ("positionH", "positionV"):
        position = anchor.find(qn(f"wp:{axis}"))
        assert position.get("relativeFrom") == "page"
        assert position.find(qn("wp:posOffset")).text == "0"
    extent = anchor.find(qn("wp:extent"))
    assert int(extent.get("cx")) == section.page_width
    assert int(extent.get("cy")) == section.page_height
    assert anchor.find(qn("wp:docPr")).get("name") == "vera-art:divider:div_leggi"
    assert anchor.xpath(".//a:blip/@r:embed")

    art_p = anchor.getparent()
    while art_p.tag != qn("w:p"):
        art_p = art_p.getparent()
    assert _w_text(art_p) == ""
    assert art_p.getnext() is title._p
    assert title.text == "GESTIONE LEGGI E REGOLAMENTI"
    assert title.style.name == "Heading 2"
    # The art paragraph is the first paragraph of the new section.
    assert design.section_first_blocks(doc)[-1] is art_p
    assert design.art_marker(art_p) == "vera-art:divider:div_leggi"


def test_divider_starts_new_section_with_clean_first_page():
    doc = _kit_doc()
    doc.add_paragraph("Prima sezione")
    design.add_divider(doc, "SERVIZI IGIENICO-ASSISTENZIALI", "div_servizi_igienici")
    doc.add_paragraph("Testo del capitolo")

    assert len(doc.sections) == 2
    assert doc.sections[1].different_first_page_header_footer
    assert doc.sections[1].start_type == WD_SECTION.NEW_PAGE

    _finish(doc)
    divider = doc.sections[1]
    assert divider.different_first_page_header_footer
    assert _text(divider.first_page_header).strip() == ""
    assert _text(divider.first_page_footer).strip() == ""
    header = _text(divider.header)
    assert "DOCUMENTO DI VALUTAZIONE DEI RISCHI" in header
    assert "ACME MECCANICA SRL" in header
    assert "Rev. 00 del 10/11/2026" in _text(divider.footer)


def test_divider_with_part_label_and_trailing_page_break():
    doc = _kit_doc()
    doc.add_paragraph("Prima sezione")
    title = design.add_divider(
        doc,
        "IDENTIFICAZIONE DELL'AMBIENTE DI LAVORO E DEGLI ADDETTI",
        "div_ambienti",
        part_label="PARTE III — VALUTAZIONE DEI RISCHI PER AMBIENTE DI LAVORO",
    )
    label = title._p.getprevious()
    assert label.xpath("./w:pPr/w:pStyle/@w:val") == ["Heading1"]
    assert _w_text(label).startswith("PARTE III")
    assert design.art_marker(label.getprevious()) == "vera-art:divider:div_ambienti"
    # The title sits mid-page; the content after it starts on a new page.
    assert title.paragraph_format.space_before >= Cm(8)
    following = title._p.getnext()
    assert following.xpath('.//w:br[@w:type="page"]')


def test_missing_art_degrades_to_title_only(tmp_path, monkeypatch):
    empty = tmp_path / "no-art"
    empty.mkdir()
    monkeypatch.setattr(design, "ART_DIR", empty)
    doc = _kit_doc()
    doc.add_paragraph("Prima sezione")
    title = design.add_divider(doc, "GESTIONE ACQUISTI", "div_acquisti")
    assert title.text == "GESTIONE ACQUISTI"
    assert doc.element.body.xpath(".//w:drawing") == []
    design.add_back_cover(doc)
    _finish(doc)  # no exception, no drawing
    assert doc.element.body.xpath(".//w:drawing") == []


def test_unreadable_art_file_degrades_to_title_only(tmp_path, monkeypatch):
    broken = tmp_path / "broken-art"
    broken.mkdir()
    for filename in set(design.ART.values()):
        (broken / filename).write_bytes(b"not an image")
    monkeypatch.setattr(design, "ART_DIR", broken)
    doc = _kit_doc()
    title = design.add_divider(doc, "GESTIONE ACQUISTI", "div_acquisti")
    assert title.text == "GESTIONE ACQUISTI"
    assert doc.element.body.xpath(".//w:drawing") == []


def test_art_cover_opens_the_first_section():
    doc = _kit_doc()
    design.add_art_cover(doc, "cover_dvr")
    doc.add_paragraph("Indice")
    _finish(doc)
    first = design.section_first_blocks(doc)[0]
    assert design.art_marker(first) == "vera-art:cover:cover_dvr"
    assert _w_text(first) == ""
    assert first.getnext().xpath('.//w:br[@w:type="page"]')
    cover = doc.sections[0]
    assert cover.different_first_page_header_footer
    assert _text(cover.first_page_header).strip() == ""
    assert _text(cover.first_page_footer).strip() == ""


def test_attachment_cover_is_vera_art_with_live_title_block():
    doc = _kit_doc("attachment")
    design.add_cover(
        doc,
        title="Valutazione del Rischio Videoterminali",
        subtitle="Allegato VDT",
        legal_basis="ai sensi del Titolo VII del D.Lgs. 81/2008",
        azienda=_azienda(),
        branding=Branding(firm_name="Studio Sentinella", indirizzo="Via Verdi 2"),
        version=2,
        generated_at=GENERATED_AT,
        logo_width_cm=7.0,
    )
    paragraphs = _paragraph_elements(doc)
    assert design.art_marker(paragraphs[0]) == "vera-art:cover:cover_vera"
    text = "\n".join(_w_text(p) for p in paragraphs)
    for expected in (
        "ALLEGATO AL DOCUMENTO DI VALUTAZIONE DEI RISCHI",
        "Valutazione del Rischio Videoterminali",
        "Allegato VDT",
        "ai sensi del Titolo VII del D.Lgs. 81/2008",
        "ACME MECCANICA SRL",
        "Via Roma 1, 20100 Milano (MI)",
        "P.IVA 01234567890 · ATECO 25.62.00",
        "Revisione 01 · 10/11/2026",
        "DOCUMENTO ELABORATO DA",
        "STUDIO SENTINELLA",
        "Via Verdi 2",
    ):
        assert expected in text, expected
    # The VERA mark is in the art: no separate logo picture on the cover.
    assert len(doc.element.body.xpath(".//w:drawing")) == 1
    assert paragraphs[-1].xpath('.//w:br[@w:type="page"]')


def test_back_cover_is_a_clean_final_art_section():
    doc = _kit_doc()
    doc.add_paragraph("Ultima pagina di contenuto")
    doc.add_page_break()
    design.add_back_cover(doc)
    _finish(doc)
    last = doc.sections[-1]
    assert design.art_marker(design.section_first_blocks(doc)[-1]) == "vera-art:back_cover:back_vera"
    assert last.different_first_page_header_footer
    assert _text(last.first_page_header).strip() == ""
    # The trailing page break was absorbed by the section break: no blank page.
    for el in _paragraph_elements(doc):
        only_break = el.xpath('.//w:br[@w:type="page"]') and not _w_text(el).strip()
        assert not only_break


def test_section_title_breaks_before_without_blank_pages():
    doc = _kit_doc()
    design.add_cover(
        doc, title="Allegato", azienda=_azienda(), branding=Branding.default(),
        version=1, generated_at=GENERATED_AT,
    )
    title = design.add_section_title(doc, "PRESENTAZIONE DELL'AZIENDA", part_label="PARTE I — DATI GENERALI DELL'AZIENDA")
    label = title._p.getprevious()
    # The cover's trailing page-break paragraph became a page-break-before.
    assert not label.getprevious().xpath('.//w:br[@w:type="page"]')
    assert label.xpath("./w:pPr/w:pageBreakBefore")
    assert not title._p.xpath("./w:pPr/w:pageBreakBefore")
    assert title.style.name == "Heading 2"
    assert label.xpath("./w:pPr/w:pStyle/@w:val") == ["Heading1"]
    runs = label.xpath("./w:r")
    assert runs and all(r.xpath("./w:rPr/w:sz/@w:val") == ["18"] for r in runs)
    assert all(r.xpath("./w:rPr/w:caps") for r in runs)

    docx_utils.add_data_table(doc, ["A"], [["1"]])
    second = design.add_section_title(doc, "ANAGRAFICA AZIENDALE")
    assert second._p.xpath("./w:pPr/w:pageBreakBefore")
    inline = design.add_section_title(doc, "AMBIENTI DI LAVORO", new_page=False)
    assert not inline._p.xpath("./w:pPr/w:pageBreakBefore")


def test_section_title_after_a_divider_does_not_leave_an_empty_page():
    doc = _kit_doc()
    doc.add_paragraph("Prima sezione")
    design.add_divider(doc, "IDENTIFICAZIONE DELL'AMBIENTE", "div_ambienti")
    env = design.add_section_title(doc, "UFFICIO AMMINISTRATIVO")
    previous = env._p.getprevious()
    assert not previous.xpath('.//w:br[@w:type="page"]')
    assert env._p.xpath("./w:pPr/w:pageBreakBefore")


def test_sub_title_in_and_out_of_the_index():
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = _kit_doc()
    indexed = design.add_sub_title(doc, "Foto e Planimetrie — UFFICIO", new_page=True)
    assert indexed.style.name == "Heading 3"
    assert indexed.alignment == WD_ALIGN_PARAGRAPH.CENTER

    caption = design.add_sub_title(doc, "STRUTTURE", in_toc=False, new_page=True)
    assert caption.style.name == "Normal"
    assert caption.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert caption._p.xpath("./w:pPr/w:outlineLvl") == []
    assert caption._p.xpath("./w:pPr/w:pageBreakBefore")
    run = caption.runs[0]
    assert run.font.size.pt == 12 and run.font.bold and str(run.font.color.rgb) == "003D74"


# ---------------------------------------------------------------------------
# Running header and footer
# ---------------------------------------------------------------------------


def test_footer_has_logo_rev_and_page_fields():
    doc = _kit_doc()
    doc.add_paragraph("Contenuto")
    _finish(doc)
    footer = doc.sections[0].footer
    paragraph = footer.paragraphs[0]
    p = paragraph._p
    inline = p.xpath(".//wp:inline")
    assert inline and inline[0].xpath(".//a:blip/@r:embed")
    extent = inline[0].find(qn("wp:extent"))
    assert int(extent.get("cx")) <= Cm(2.4) and int(extent.get("cy")) <= Cm(0.85)
    assert "Rev. 00 del 10/11/2026" in paragraph.text
    assert "Pag." in paragraph.text
    instructions = [t.text.strip() for t in p.iter(qn("w:instrText"))]
    assert instructions == ["PAGE", "NUMPAGES"]
    assert p.xpath("./w:pPr/w:pBdr/w:top/@w:color") == ["C9D3DF"]
    # Each field part in a run of its own, as Word writes them: LibreOffice
    # takes the result's look from its own run, so a field packed into one
    # run printed "4 di 15" in the body size and ink.
    for run in p.iter(qn("w:r")):
        assert not (run.find(qn("w:fldChar")) is not None and run.find(qn("w:t")) is not None)
    for run in paragraph.runs:
        if run.text.strip():
            assert run.font.size.pt == 8.5 and str(run.font.color.rgb) == "64748D", run.text
    # The default logo is the VERA mark, not the retired navy N2O logo.
    rid = inline[0].xpath(".//a:blip/@r:embed")[0]
    blob = footer.part.related_parts[rid].blob
    assert blob == docx_utils.LOGO_PATH.read_bytes()


def test_header_is_title_and_client_in_navy_capitals():
    doc = _kit_doc()
    doc.add_paragraph("Contenuto")
    _finish(doc)
    paragraph = doc.sections[0].header.paragraphs[0]
    assert paragraph.text == "DOCUMENTO DI VALUTAZIONE DEI RISCHI\tACME MECCANICA SRL"
    for run in paragraph.runs:
        if run.text.strip():
            assert run.font.size.pt == 9 and run.font.bold and str(run.font.color.rgb) == "003D74"
    assert paragraph._p.xpath("./w:pPr/w:pBdr/w:bottom/@w:color") == ["C9D3DF"]


def test_unreadable_logo_bytes_fall_back_to_firm_name():
    doc = _kit_doc()
    doc.add_paragraph("Contenuto")
    _finish(doc, branding=Branding(logo_bytes=b"not-an-image"))
    footer = doc.sections[0].footer
    assert "N2O SRL" in _text(footer)
    assert footer._element.xpath(".//w:drawing") == []


def test_non_art_sections_keep_running_furniture_on_first_page():
    doc = _kit_doc()
    design.add_cover(
        doc, title="Allegato", azienda=_azienda(), branding=Branding.default(),
        version=1, generated_at=GENERATED_AT,
    )
    doc.add_paragraph("Contenuto")
    doc.add_section(WD_SECTION.NEW_PAGE)
    doc.add_paragraph("Sezione senza arte")
    _finish(doc)
    plain = doc.sections[1]
    assert not plain.different_first_page_header_footer
    assert "DOCUMENTO DI VALUTAZIONE DEI RISCHI" in _text(plain.first_page_header)
    assert "Pag." in _text(plain.first_page_footer)


def test_legacy_cover_without_art_keeps_a_clean_first_page():
    """Donor templates keep their own cover until they adopt the kit."""
    doc = _kit_doc()
    doc.add_paragraph("Copertina di un modello")
    _finish(doc)
    assert doc.sections[0].different_first_page_header_footer
    _finish(doc, cover_is_clean=False)
    assert not doc.sections[0].different_first_page_header_footer


def test_drawing_ids_are_unique_across_body_header_and_footer():
    doc = _kit_doc()
    design.add_art_cover(doc, "cover_dvr")
    doc.add_paragraph("Contenuto")
    design.add_divider(doc, "GESTIONE DPI", "div_gestione_dpi")
    doc.add_paragraph("Contenuto")
    design.add_back_cover(doc)
    _finish(doc)
    ids = [d.get("id") for d in doc.element.body.iter(qn("wp:docPr"))]
    for rel in doc.part.rels.values():
        if rel.reltype.endswith(("/header", "/footer")):
            ids += [d.get("id") for d in rel.target_part.element.iter(qn("wp:docPr"))]
    assert len(ids) > 3
    assert len(ids) == len(set(ids))


def test_kit_runs_carry_arial_on_every_slot():
    doc = _kit_doc()
    design.add_art_cover(doc, "cover_dvr")
    design.add_divider(doc, "GESTIONE DPI", "div_gestione_dpi", part_label="PARTE IV")
    design.add_section_title(doc, "ANAGRAFICA AZIENDALE")
    design.add_sub_title(doc, "STRUTTURE", in_toc=False)
    docx_utils.add_data_table(doc, ["Nome", "Valore"], [["a", "1"]])
    docx_utils.add_kv_table(doc, [("Azienda", "Acme")], variant="light")
    docx_utils.add_role_band(doc, "RSPP", "Luca Bianchi")
    docx_utils.add_signature_grid(doc, [("Datore di Lavoro", "Mario Rossi")])
    docx_utils.add_body_paragraph(doc, "Testo")
    _finish(doc)
    elements = [doc.element.body] + [
        rel.target_part.element
        for rel in doc.part.rels.values()
        if rel.reltype.endswith(("/header", "/footer"))
    ]
    checked = 0
    for element in elements:
        for run in element.iter(qn("w:r")):
            if not "".join(t.text or "" for t in run.iter(qn("w:t"))).strip():
                continue
            fonts = run.find(qn("w:rPr")).find(qn("w:rFonts"))
            assert {slot: fonts.get(qn(slot)) for slot in SLOTS} == dict.fromkeys(SLOTS, "Arial")
            checked += 1
    assert checked > 10


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


def test_finalize_toc_entries_have_a_dot_leader_tab_at_text_width():
    doc = _kit_doc()
    anchors = design.add_toc(doc, title="INDICE")
    doc.add_heading("Premessa", level=1)
    design.add_section_title(doc, "ANAGRAFICA AZIENDALE")
    design.add_sub_title(doc, "Foto e Planimetrie — UFFICIO")
    design.add_sub_title(doc, "STRUTTURE", in_toc=False)
    design.finalize_toc(doc, *anchors)

    body = list(doc.element.body)
    start, end = body.index(anchors[0]._p), body.index(anchors[1]._p)
    entries = [el for el in body[start + 1 : end] if el.tag == qn("w:p")]
    assert ["".join(t.text for t in el.iter(qn("w:t"))) for el in entries] == [
        "Premessa", "ANAGRAFICA AZIENDALE", "Foto e Planimetrie — UFFICIO",
    ]
    section = doc.sections[0]
    text_width_twips = round((section.page_width - section.left_margin - section.right_margin) / 635)
    for el in entries:
        tabs = el.xpath("./w:pPr/w:tabs/w:tab")
        assert len(tabs) == 1
        tab = tabs[0]
        assert tab.get(qn("w:val")) == "right" and tab.get(qn("w:leader")) == "dot"
        assert abs(int(tab.get(qn("w:pos"))) - text_width_twips) <= 1
        assert el.xpath(".//w:r/w:tab")
