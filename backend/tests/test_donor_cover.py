"""Donor-template attachments on the design kit (spec 2026-11-10 §4.4).

Eight attachments open one of N2O's completed documents from ``templates/``
and fill it: Gestanti, Incendio, Stress, DUVRI, POS, the two PEE and the
HACCP manual. They drop the donor's own cover for the kit's art cover, print
in Arial at the donor's own sizes, and close on the back cover. The HACCP
record forms are printed and filled by hand: Arial and the running header
and footer, no art pages.

``strip_donor_cover`` and its tests on the real templates come from draft
PR #82 (commit af2a5d5).
"""

from __future__ import annotations

import asyncio
import importlib.util
import io
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph

from app.services.document_generator import design
from app.services.document_generator.branding import Branding
from app.services.document_generator.docx_utils import TEMPLATES_DIR
from app.services.document_generator.donor_cover import (
    insert_kit_cover_at_top,
    normalize_fonts,
    strip_donor_cover,
)
from scripts.verify_dvr_luca_fixture import _generator_patch_objects

BACKEND_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = datetime(2026, 11, 10, 9, 30)
SLOTS = ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs")
THEME_SLOTS = ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme")
SYMBOL_FONTS = {"symbol", "wingdings", "wingdings 2", "wingdings 3", "webdings"}
SECT = f"{qn('w:pPr')}/{qn('w:sectPr')}"

DONOR_TEMPLATES = {
    "ALLEGATO_GESTANTI": "ALLEGATO GESTANTI.docx",
    "ALLEGATO_INCENDIO": "ALLEGATO RISCHIO INCENDIO.docx",
    "ALLEGATO_STRESS": "ALLEGATO STRESS DA LAVORO CORRELATO.docx",
    "DUVRI": "DUVRI.docx",
    "POS": "POS.docx",
    "PEE_AZIENDA": "PIANO GESTIONE EMERGENZE - AZIENDA.docx",
    "PEE_COMUNE": "PIANO GESTIONE EMERGENZE - COMUNE.docx",
    "HACCP": "HACCP.docx",
}

# Text found only on each donor's own cover page.
DONOR_COVER_MARKERS = {
    "ALLEGATO_GESTANTI": ("redatto ai sensi dell’art. 11",),
    "ALLEGATO_INCENDIO": ("Documento di valutazione", "Timbro e Firma"),
    "ALLEGATO_STRESS": ("(Metodo Indicatori Oggettivi)", "Timbro e Firma"),
    "DUVRI": ("ai sensi dell’art. 26 co. 3",),
    "POS": ("Documento ex artt. 17 - 96", "redatto in conformità"),
    "PEE_AZIENDA": ("Timbro e Firma",),
    "PEE_COMUNE": ("ex D.M. 10.03.1998", "Timbro e Firma"),
    "HACCP": ("AUTOCONTROLLO PER L'IGIENE DEGLI ALIMENTI",),
}


def _load_verify():
    spec = importlib.util.spec_from_file_location(
        "verify_all_generators",
        str(BACKEND_ROOT / "scripts" / "verify_all_generators.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MISSING = object()


def _harness_state() -> list[tuple[object, dict]]:
    """What every object the generator harness patches holds now."""
    return [(owner, dict(vars(owner))) for owner in _generator_patch_objects()]


def _changed_since(state) -> list[str]:
    """The attributes that are no longer the ones ``state`` recorded."""
    changed = []
    for owner, before in state:
        now = vars(owner)
        for name in before.keys() | now.keys():
            if now.get(name, _MISSING) is not before.get(name, _MISSING):
                changed.append(f"{getattr(owner, '__name__', owner)}.{name}")
    return sorted(changed)


# Taken while the module is collected, before any test can have patched.
_REAL_HARNESS = _harness_state()


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


def _cover_kwargs(**overrides) -> dict:
    kwargs = {
        "title": "Piano Operativo di Sicurezza",
        "azienda": _azienda(),
        "branding": Branding.default(),
        "version": 1,
        "generated_at": GENERATED_AT,
    }
    kwargs.update(overrides)
    return kwargs


def _blocks(doc) -> list:
    return [el for el in doc.element.body if el.tag != qn("w:sectPr")]


def _w_text(element) -> str:
    return "".join(t.text or "" for t in element.iter(qn("w:t")))


def _text(doc) -> str:
    """Every paragraph of the body, those in tables and text boxes included
    (the Gestanti and DUVRI covers are text boxes)."""
    return "\n".join(_w_text(p) for p in doc.element.body.iter(qn("w:p")))


def _numbering(doc):
    """The numbering part's root element, or None. (``doc.part.numbering_part``
    would create an empty part when there is none.)"""
    try:
        return doc.part.part_related_by(RT.NUMBERING).element
    except KeyError:
        return None


def _font_parts(doc) -> list[tuple[str, object]]:
    parts = [("document", doc.element), ("styles", doc.styles.element)]
    numbering = _numbering(doc)
    if numbering is not None:
        # List labels ("a)", "1.") print in the font their level names.
        parts.append(("numbering", numbering))
    for rel in doc.part.rels.values():
        if not rel.is_external and rel.reltype.endswith(("/header", "/footer")):
            parts.append((str(rel.target_part.partname), rel.target_part.element))
    return parts


def _is_symbol(fonts) -> bool:
    return any((fonts.get(qn(slot)) or "").strip().lower() in SYMBOL_FONTS for slot in ("w:ascii", "w:hAnsi"))


def _non_arial_fonts(doc) -> list[tuple[str, list[str], list[str]]]:
    """Every font declaration other than Arial, glyph fonts and ``w:sym``
    runs aside."""
    offenders = []
    for part, element in _font_parts(doc):
        for fonts in element.iter(qn("w:rFonts")):
            owner = fonts.getparent().getparent()
            if _is_symbol(fonts) or (owner.tag == qn("w:r") and owner.find(qn("w:sym")) is not None):
                continue
            declared = {fonts.get(qn(slot)) for slot in SLOTS} - {None}
            themed = [slot for slot in THEME_SLOTS if fonts.get(qn(slot))]
            if declared - {"Arial"} or themed:
                offenders.append((part, sorted(declared), themed))
    return offenders


def _style_sizes(doc) -> dict[str, list[str]]:
    sizes = {}
    for style in doc.styles.element.iter(qn("w:style")):
        sizes[style.get(qn("w:styleId"))] = style.xpath("./w:rPr/w:sz/@w:val | ./w:rPr/w:szCs/@w:val")
    return sizes


def _run_sizes(doc) -> list[list[str]]:
    sizes = []
    for _, element in _font_parts(doc):
        for run in element.iter(qn("w:r")):
            sizes.append(run.xpath("./w:rPr/w:sz/@w:val | ./w:rPr/w:szCs/@w:val"))
    return sizes


def _starts_new_page(element) -> bool:
    """True when ``element`` opens a page by itself, so a page break in front
    of it would leave an empty page."""
    if element is None or element.tag != qn("w:p"):
        return False
    if design._is_page_break_only(element):
        return True
    flag = element.find(f"{qn('w:pPr')}/{qn('w:pageBreakBefore')}")
    if flag is not None and flag.get(qn("w:val")) not in ("0", "false", "off"):
        return True
    if element.find(SECT) is not None and not _w_text(element).strip():
        following = element.getnext()
        while following is not None:
            sect = following if following.tag == qn("w:sectPr") else following.find(SECT)
            if sect is not None:
                kind = sect.find(qn("w:type"))
                return (kind.get(qn("w:val")) if kind is not None else "nextPage") != "continuous"
            following = following.getnext()
    return False


# ---------------------------------------------------------------------------
# strip_donor_cover (ported from PR #82, af2a5d5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("template", "kwargs", "expected", "first", "gone"),
    [
        # The cover ends at a section break; the frame round it goes too.
        pytest.param("ALLEGATO RISCHIO INCENDIO.docx", {}, 11, "section-break", "Documento di valutazione", id="incendio-section-break"),
        pytest.param("HACCP.docx", {"stop_text": "Definizioni"}, 17, "Definizioni", "MANUALE DI", id="haccp-marker"),
        pytest.param("DUVRI.docx", {"stop_before_table": True}, 1, "table", "DOCUMENTO UNICO", id="duvri-first-table"),
        # No boundary: an unexpected template keeps its cover, not lose its body.
        pytest.param("POS.docx", {}, 0, "unchanged", None, id="pos-no-boundary"),
        pytest.param("POS.docx", {"whole_body": True}, 10, "empty", "Piano Operativo di Sicurezza", id="pos-cover-only"),
    ],
)
def test_strip_donor_cover_on_real_templates(template, kwargs, expected, first, gone):
    doc = Document(str(TEMPLATES_DIR / template))
    before = _blocks(doc)
    removed = strip_donor_cover(doc, **kwargs)
    blocks = _blocks(doc)

    assert removed == expected
    assert len(blocks) == len(before) - removed
    assert blocks == before[removed:], "only the leading cover blocks are removed"
    if first == "section-break":
        assert blocks[0].find(SECT) is not None
        assert doc.sections[0]._sectPr.find(qn("w:pgBorders")) is None
    elif first == "Definizioni":
        assert doc.paragraphs[0].text == "Definizioni"
    elif first == "table":
        assert blocks[0].tag == qn("w:tbl")
    elif first == "unchanged":
        assert len(blocks) == 10
    elif first == "empty":
        assert blocks == []
    if gone is not None:
        assert gone not in _text(doc)[:400]


# ---------------------------------------------------------------------------
# normalize_fonts
# ---------------------------------------------------------------------------


def test_normalize_fonts_sets_arial_keeps_sizes():
    # A real donor (Times New Roman and Castellar runs, a Symbol glyph, a
    # theme font in its styles) plus the cases the templates do not have.
    doc = Document(str(TEMPLATES_DIR / "ALLEGATO GESTANTI.docx"))
    paragraph = doc.add_paragraph()
    sym_run = paragraph.add_run()
    sym = OxmlElement("w:sym")
    sym.set(qn("w:font"), "Wingdings")
    sym.set(qn("w:char"), "F0FC")
    sym_run._r.append(sym)
    sym_run.font.name = "Calibri"
    checkbox = paragraph.add_run("")
    checkbox.font.name = "Wingdings 2"
    themed = paragraph.add_run("Testo nel carattere del tema")
    fonts = themed._r.get_or_add_rPr().get_or_add_rFonts()
    fonts.set(qn("w:asciiTheme"), "minorHAnsi")
    fonts.set(qn("w:hAnsiTheme"), "minorHAnsi")
    themed.font.size = Pt(7)
    calibri = paragraph.add_run("Calibri a 9 punti")
    calibri.font.name = "Calibri"
    calibri.font.size = Pt(9)
    doc.styles.add_style("Spunta", WD_STYLE_TYPE.CHARACTER).font.name = "Webdings"

    def snapshot(run):
        fonts = run.find(f"{qn('w:rPr')}/{qn('w:rFonts')}")
        return None if fonts is None else dict(fonts.attrib)

    runs = [run for _, element in _font_parts(doc) for run in element.iter(qn("w:r"))]
    before = [snapshot(run) for run in runs]
    run_sizes, style_sizes = _run_sizes(doc), _style_sizes(doc)
    to_change = [
        run for run, fonts in zip(runs, before)
        if fonts is not None
        and run.find(qn("w:sym")) is None
        and not _is_symbol(run.find(f"{qn('w:rPr')}/{qn('w:rFonts')}"))
        and (
            {fonts.get(qn(slot)) for slot in SLOTS} != {"Arial"}
            or any(fonts.get(qn(slot)) for slot in THEME_SLOTS)
        )
    ]

    changed = normalize_fonts(doc)

    assert changed == len(to_change) > 2
    assert _non_arial_fonts(doc) == []
    for run, fonts in zip(runs, before):
        if run.find(qn("w:sym")) is not None or (fonts is not None and _is_symbol(run.find(f"{qn('w:rPr')}/{qn('w:rFonts')}"))):
            # Glyph fonts and w:sym runs print bullets and check boxes:
            # rewriting them would print the wrong character.
            assert snapshot(run) == fonts
        elif fonts is None:
            # A run that names no font inherits its style's, rewritten below.
            assert snapshot(run) is None
    assert checkbox._r.rPr.rFonts.get(qn("w:ascii")) == "Wingdings 2"
    assert sym_run._r.find(qn("w:sym")).get(qn("w:font")) == "Wingdings"
    assert doc.styles["Spunta"].font.name == "Webdings"
    defaults = doc.styles.element.find(qn("w:docDefaults")).find(qn("w:rPrDefault")).find(qn("w:rPr")).find(qn("w:rFonts"))
    assert {defaults.get(qn(slot)) for slot in SLOTS} == {"Arial"}
    # Sizes are the donor's: nothing moves on the page but the face.
    assert _run_sizes(doc) == run_sizes
    assert _style_sizes(doc) == style_sizes
    assert normalize_fonts(doc) == 0


def _level_fonts(numbering, abstract_id: str) -> dict[int, dict]:
    """``{ilvl: rFonts attributes}`` of one ``w:abstractNum``."""
    abstract = next(
        a for a in numbering.iter(qn("w:abstractNum")) if a.get(qn("w:abstractNumId")) == abstract_id
    )
    return {
        int(lvl.get(qn("w:ilvl"))): dict(lvl.find(f"{qn('w:rPr')}/{qn('w:rFonts')}").attrib)
        for lvl in abstract.iter(qn("w:lvl"))
    }


def test_normalize_fonts_rewrites_list_labels_but_not_glyph_fonts():
    # Gestanti's "a)" labels name Times New Roman in numbering.xml; bullet
    # levels name a glyph font whose code points are pictures.
    w = nsdecls("w")
    doc = Document()
    numbering = doc.part.numbering_part.element
    numbering.find(qn("w:num")).addprevious(parse_xml(
        f'<w:abstractNum {w} w:abstractNumId="70">'
        '<w:lvl w:ilvl="0"><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%1)"/><w:rPr>'
        '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Times New Roman"'
        ' w:cs="Times New Roman"/></w:rPr></w:lvl>'
        '<w:lvl w:ilvl="1"><w:numFmt w:val="bullet"/><w:lvlText w:val=""/><w:rPr>'
        '<w:rFonts w:ascii="Symbol" w:hAnsi="Symbol" w:hint="default"/></w:rPr></w:lvl>'
        '<w:lvl w:ilvl="2"><w:numFmt w:val="decimal"/><w:lvlText w:val="%3."/><w:rPr>'
        '<w:rFonts w:asciiTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi" w:cs="Times New Roman"/></w:rPr></w:lvl>'
        '<w:lvl w:ilvl="3"><w:numFmt w:val="bullet"/><w:lvlText w:val=""/><w:rPr>'
        '<w:rFonts w:ascii="Wingdings 2" w:hAnsi="Wingdings 2"/></w:rPr></w:lvl>'
        '<w:lvl w:ilvl="4"><w:numFmt w:val="bullet"/><w:lvlText w:val=""/><w:rPr>'
        '<w:rFonts w:ascii="Wingdings" w:hAnsi="Wingdings" w:cs="Wingdings"/></w:rPr></w:lvl>'
        "</w:abstractNum>"
    ))
    before = _level_fonts(numbering, "70")

    normalize_fonts(doc)

    after = _level_fonts(numbering, "70")
    arial = {qn(slot): "Arial" for slot in SLOTS}
    assert after[0] == arial
    # The theme attributes go: Word reads them before the explicit names.
    assert after[2] == arial
    # Symbol and Wingdings bullets keep their font, or they print as letters.
    for glyph_level in (1, 3, 4):
        assert after[glyph_level] == before[glyph_level]
    assert _non_arial_fonts(doc) == []


def test_generated_gestanti_list_labels_are_arial(generated):
    template = _numbering(Document(str(TEMPLATES_DIR / DONOR_TEMPLATES["ALLEGATO_GESTANTI"])))
    assert template.xpath(".//w:lvl/w:rPr/w:rFonts[@w:ascii='Times New Roman']"), "the donor's own labels"
    ok, path, message = generated["ALLEGATO_GESTANTI"]
    assert ok, message
    numbering = _numbering(Document(path))
    offenders = []
    for fonts in numbering.iter(qn("w:rFonts")):
        if _is_symbol(fonts):
            continue
        declared = {fonts.get(qn(slot)) for slot in SLOTS}
        themed = [slot for slot in THEME_SLOTS if fonts.get(qn(slot))]
        if declared != {"Arial"} or themed:
            offenders.append(dict(fonts.attrib))
    assert offenders == []


# ---------------------------------------------------------------------------
# insert_kit_cover_at_top
# ---------------------------------------------------------------------------


def test_insert_kit_cover_at_top_fits_the_art_to_the_first_section():
    # add_cover sizes its art to the last section; a donor's first section
    # can have another page size and margins.
    doc = Document()
    first = doc.sections[0]
    first.page_width, first.page_height = Cm(21.0), Cm(29.7)
    first.top_margin = Cm(3.0)
    doc.add_paragraph("Contenuto della prima sezione")
    last = doc.add_section(WD_SECTION.NEW_PAGE)
    last.orientation = WD_ORIENT.LANDSCAPE
    last.page_width, last.page_height = Cm(42.0), Cm(29.7)
    last.top_margin = Cm(1.0)
    doc.add_paragraph("Contenuto dell'ultima sezione")

    added = insert_kit_cover_at_top(doc, **_cover_kwargs())

    blocks = _blocks(doc)
    art = blocks[0]
    assert design.art_marker(art) == "vera-art:cover:cover_vera"
    assert design.section_first_blocks(doc)[0] is art
    anchor = art.find(f".//{qn('wp:anchor')}")
    extent = anchor.find(qn("wp:extent"))
    # Page sizes are stored in twips: compare with what the section holds.
    page = (doc.sections[0].page_width, doc.sections[0].page_height)
    assert abs(page[0] - Cm(21.0)) < Cm(0.01) and abs(page[1] - Cm(29.7)) < Cm(0.01)
    assert (int(extent.get("cx")), int(extent.get("cy"))) == page
    xfrm_ext = [el for el in anchor.iter(qn("a:ext")) if el.getparent().tag == qn("a:xfrm")]
    assert [(int(e.get("cx")), int(e.get("cy"))) for e in xfrm_ext] == [page]
    # A4 art on an A4 page: the landscape crop computed for the last section is gone.
    assert anchor.find(f".//{qn('a:srcRect')}") is None
    # The title block starts 4.5 cm from the top edge of the cover's page.
    lead = Paragraph(blocks[1], doc._body).paragraph_format.space_before
    assert abs(lead - Cm(4.5 - 3.0)) < Cm(0.01)
    assert doc.sections[0].different_first_page_header_footer
    assert not doc.sections[-1].different_first_page_header_footer
    # The cover ends with its page break, then the donor body follows.
    assert design._is_page_break_only(blocks[added - 1])
    assert _w_text(blocks[added]) == "Contenuto della prima sezione"
    assert "Piano Operativo di Sicurezza" in "".join(_w_text(el) for el in blocks[:added])


@pytest.mark.parametrize(
    ("top_cm", "header_cm", "body_top_cm"),
    [
        # PEE comune: a 0.75 cm top margin under a header 1.25 cm from the
        # edge. The body starts under the header line (~0.5 cm), not at the
        # margin, so a lead measured from the margin set the block 1 cm low.
        (0.75, 1.25, 1.75),
        # A header distance under 0.8 cm is raised to 1.0 cm by the running
        # header and footer (DUVRI's is 0): measure from where it will be.
        (1.0, 0.0, 1.5),
        # The usual case: the margin is below the header line, and wins.
        (3.0, 1.25, 3.0),
    ],
)
def test_cover_title_block_starts_below_a_low_header(top_cm, header_cm, body_top_cm):
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21.0), Cm(29.7)
    section.top_margin = Cm(top_cm)
    section.header_distance = Cm(header_cm)
    doc.add_paragraph("Corpo")
    insert_kit_cover_at_top(doc, **_cover_kwargs())
    lead = Paragraph(_blocks(doc)[1], doc._body).paragraph_format.space_before
    assert abs(lead - Cm(4.5 - body_top_cm)) < Cm(0.01)


def test_generated_pee_comune_cover_title_starts_below_its_header(generated):
    ok, path, message = generated["PEE_COMUNE"]
    assert ok, message
    doc = Document(path)
    section = doc.sections[0]
    assert section.top_margin < Cm(1.0)  # the donor's own small margin
    body_top = max(section.top_margin, section.header_distance + Cm(0.5))
    lead = Paragraph(_blocks(doc)[1], doc._body).paragraph_format.space_before
    assert abs(lead + body_top - Cm(4.5)) < Cm(0.01)


def test_insert_kit_cover_at_top_crops_the_art_to_another_paper_size():
    doc = Document()  # python-docx's own template is US Letter
    doc.add_paragraph("Corpo")
    insert_kit_cover_at_top(doc, **_cover_kwargs())
    section = doc.sections[0]
    anchor = _blocks(doc)[0].find(f".//{qn('wp:anchor')}")
    extent = anchor.find(qn("wp:extent"))
    assert (int(extent.get("cx")), int(extent.get("cy"))) == (section.page_width, section.page_height)
    rect = anchor.find(f".//{qn('a:srcRect')}")
    assert rect is not None and rect.get("t") == rect.get("b") and int(rect.get("t")) > 0


def test_insert_kit_cover_at_top_on_a_multi_section_donor():
    doc = Document(str(TEMPLATES_DIR / "ALLEGATO GESTANTI.docx"))
    sections = len(doc.sections)
    assert sections > 2
    assert strip_donor_cover(doc) == 14

    added = insert_kit_cover_at_top(doc, **_cover_kwargs(title="Valutazione del Rischio Lavoratrici Gestanti"))

    blocks = _blocks(doc)
    assert len(doc.sections) == sections
    assert design.art_marker(blocks[0]) == "vera-art:cover:cover_vera"
    # The cover fills the donor's first section, which ends at the donor's
    # own section break...
    assert blocks[added].find(SECT) is not None
    assert design.section_first_blocks(doc)[1] is blocks[added + 1]
    # ...which opens the next page: a page break of the cover's own would
    # leave an empty page between the two.
    assert not any(design._is_page_break_only(el) for el in blocks[:added])
    first = doc.sections[0]
    extent = blocks[0].find(f".//{qn('wp:anchor')}").find(qn("wp:extent"))
    assert (int(extent.get("cx")), int(extent.get("cy"))) == (first.page_width, first.page_height)


REVISION_HEADER = ["Rev.", "Motivazione", "Data"]


def _revision_tables(doc) -> list:
    """The body's Storico tables: header row "Rev. | Motivazione | Data"."""
    from docx.table import Table

    found = []
    for element in _blocks(doc):
        if element.tag == qn("w:tbl"):
            table = Table(element, doc)
            if [cell.text.strip() for cell in table.rows[0].cells][:2] == REVISION_HEADER[:2]:
                found.append(table)
    return found


def _rows(table) -> list[list[str]]:
    return [[cell.text for cell in row.cells] for row in table.rows]


def test_insert_kit_cover_at_top_puts_the_revision_table_after_the_cover():
    # Incendio, Stress, the two PEE and POS kept their Storico on the donor
    # cover strip_donor_cover removes (final review M-1). PEE azienda also
    # has no Heading 2 for the table's heading.
    doc = Document(str(TEMPLATES_DIR / "PIANO GESTIONE EMERGENZE - AZIENDA.docx"))
    assert strip_donor_cover(doc) == 11
    assert _revision_tables(doc) == []
    body_start = _blocks(doc)[0]

    added = insert_kit_cover_at_top(doc, revision_table=True, **_cover_kwargs(version=3))

    blocks = _blocks(doc)
    (table,) = _revision_tables(doc)
    index = blocks.index(table._tbl)
    # On the page after the cover, before the donor body.
    assert design._is_page_break_only(blocks[index - 2])
    assert _w_text(blocks[index - 1]) == "Storico delle revisioni"
    assert [_w_text(el) for el in blocks].count("Storico delle revisioni") == 1
    assert index < added and blocks[added] is body_start
    # This emission, as the cover prints it ("Revisione 02 · 10/11/2026").
    assert _rows(table) == [REVISION_HEADER, ["02", "Aggiornamento", "10/11/2026"]]
    assert "Revisione 02 · 10/11/2026" in [_w_text(el) for el in blocks[:index]]
    # The cover is unchanged: art first, the title block at 4.5 cm.
    assert design.art_marker(blocks[0]) == "vera-art:cover:cover_vera"
    lead = Paragraph(blocks[1], doc._body).paragraph_format.space_before
    assert abs(lead - design.cover_block_lead(doc.sections[0])) < Cm(0.01)


def test_insert_kit_cover_at_top_never_doubles_a_revision_table():
    # A donor whose own Storico is still in the body keeps it (finish_document
    # fills it); and without revision_table no Storico is added at all.
    kept = Document(str(TEMPLATES_DIR / "ALLEGATO RISCHIO INCENDIO.docx"))
    (own,) = _revision_tables(kept)
    insert_kit_cover_at_top(kept, revision_table=True, **_cover_kwargs())
    assert [table._tbl for table in _revision_tables(kept)] == [own._tbl]

    never = Document(str(TEMPLATES_DIR / "ALLEGATO GESTANTI.docx"))
    strip_donor_cover(never)
    insert_kit_cover_at_top(never, **_cover_kwargs())
    assert _revision_tables(never) == []


def test_insert_kit_cover_at_top_drops_its_break_before_a_page_break():
    # POS: the donor body is all cover. What follows the kit cover is the
    # generator's own page break; two in a row would leave an empty page.
    doc = Document(str(TEMPLATES_DIR / "POS.docx"))
    strip_donor_cover(doc, whole_body=True)
    doc.add_page_break()
    doc.add_paragraph("POS - ACME")
    added = insert_kit_cover_at_top(doc, **_cover_kwargs())
    blocks = _blocks(doc)
    assert not any(design._is_page_break_only(el) for el in blocks[:added])
    assert design._is_page_break_only(blocks[added])
    assert _w_text(blocks[added + 1]) == "POS - ACME"


# ---------------------------------------------------------------------------
# The eight donor attachments and the HACCP forms, as generated
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("donors")
    module = _load_verify()
    fixture = module.build_fixture()
    results = {}

    async def run_all():
        for tipo in (*DONOR_TEMPLATES, "HACCP_FORMS"):
            results[tipo] = await module.run_one(tipo, fixture["azienda"].id)

    # The tests read the files; the fakes go once they are written.
    with module.patched_generators(fixture, str(out)):
        asyncio.run(run_all())
    return results


def test_generating_the_donors_puts_the_real_generators_back(generated):
    """Final review L-1: the harness's fakes (load_data, _load_dvr_extras,
    the loaders, the output directory) must not outlive the generation, or
    every later test that runs a generator — a DB-backed one included —
    silently gets them."""
    assert generated  # the generation has run
    assert _changed_since(_REAL_HARNESS) == []


@pytest.mark.parametrize("tipo", list(DONOR_TEMPLATES))
def test_donor_attachments_get_kit_cover_and_back_cover(generated, tipo):
    ok, path, message = generated[tipo]
    assert ok, message
    doc = Document(path)
    blocks = _blocks(doc)

    # Cover and back cover are the kit's art pages; nothing (no donor logo)
    # comes before the cover.
    firsts = design.section_first_blocks(doc)
    assert firsts[0] is blocks[0]
    assert design.art_marker(firsts[0]) == "vera-art:cover:cover_vera"
    assert design.art_marker(firsts[-1]) == "vera-art:back_cover:back_vera"
    first = doc.sections[0]
    extent = blocks[0].find(f".//{qn('wp:anchor')}").find(qn("wp:extent"))
    assert (int(extent.get("cx")), int(extent.get("cy"))) == (first.page_width, first.page_height)
    assert first.different_first_page_header_footer
    cover_text = "\n".join(_w_text(el) for el in blocks[:30])
    assert "ACME MECCANICA COMPOSITA SRL" in cover_text
    assert "Revisione 00" in cover_text

    # The donor's own cover is gone, and the cover leaves no empty page.
    text = _text(doc)
    for marker in DONOR_COVER_MARKERS[tipo]:
        assert marker not in text, marker
    for index, element in enumerate(blocks[:60]):
        if element.find(SECT) is not None:
            break
        if design._is_page_break_only(element):
            assert not _starts_new_page(blocks[index + 1]), "empty page after the cover"
            break

    # Arial everywhere, at the donor's own sizes.
    assert _non_arial_fonts(doc) == []
    template_sizes = _style_sizes(Document(str(TEMPLATES_DIR / DONOR_TEMPLATES[tipo])))
    generated_sizes = _style_sizes(doc)
    assert {k: generated_sizes.get(k) for k in template_sizes} == template_sizes


# Donors whose styles part lacks a heading level the generator writes:
# Gestanti and PEE azienda have no Heading 2, Incendio no Heading 3, Stress
# no Heading 4.
@pytest.mark.parametrize("tipo", ["ALLEGATO_GESTANTI", "ALLEGATO_INCENDIO", "ALLEGATO_STRESS", "PEE_AZIENDA"])
def test_headings_the_donor_has_no_style_for_print_once(generated, tipo):
    ok, path, message = generated[tipo]
    assert ok, message
    texts = [_w_text(p).strip() for p in Document(path).element.body.iterchildren(qn("w:p"))]
    repeats = [text for text, following in zip(texts, texts[1:]) if text and text == following]
    assert repeats == []


# The donors whose own cover carried the Storico (Rev. | Motivazione | Data).
DONORS_WITH_A_STORICO = ("ALLEGATO_INCENDIO", "ALLEGATO_STRESS", "PEE_AZIENDA", "PEE_COMUNE", "POS")


@pytest.mark.parametrize("tipo", list(DONOR_TEMPLATES))
def test_donor_attachments_keep_one_revision_table(generated, tipo):
    """Final review M-1: the Storico left with the donor cover. The five
    donors that had one print the kit's, right after the cover, with this
    emission's row; Gestanti, DUVRI and the HACCP manual never had one."""
    ok, path, message = generated[tipo]
    assert ok, message
    doc = Document(path)
    tables = _revision_tables(doc)
    if tipo not in DONORS_WITH_A_STORICO:
        assert tables == []
        return
    (table,) = tables
    blocks = _blocks(doc)
    index = blocks.index(table._tbl)
    cover = [_w_text(el) for el in blocks[:index]]
    revision = next(re.fullmatch(r"Revisione (\d\d) · (\S+)", text) for text in cover if text.startswith("Revisione "))
    assert _rows(table) == [REVISION_HEADER, [revision[1], "Emissione", revision[2]]]
    # The first table of the document, on the page after the cover.
    assert _w_text(blocks[index - 1]) == "Storico delle revisioni"
    assert design._is_page_break_only(blocks[index - 2])
    assert not any(el.tag == qn("w:tbl") for el in blocks[:index])


def test_haccp_forms_have_no_cover_art(tmp_path, monkeypatch):
    # Two record forms come from donor templates (one in Times New Roman,
    # one in Aptos Display), the others are built from scratch.
    from app.services.document_generator import haccp_forms

    forms_dir = tmp_path / "haccp"
    forms_dir.mkdir()
    shutil.copy(TEMPLATES_DIR / "haccp" / "Procedura Sottovuoto.docx", forms_dir / "SA-01 Procedura sottovuoto.docx")
    shutil.copy(TEMPLATES_DIR / "haccp" / "Sostanze allergeniche.docx", forms_dir / "SA-14 Sostanze allergeniche.docx")
    module = _load_verify()
    fixture = module.build_fixture()
    monkeypatch.setattr(haccp_forms, "HACCP_TEMPLATES_DIR", forms_dir)
    before = _harness_state()

    with module.patched_generators(fixture, str(tmp_path / "out")):
        ok, path, message = asyncio.run(module.run_one("HACCP_FORMS", fixture["azienda"].id))
    # The harness is gone once the forms are written (final review L-1).
    assert _changed_since(before) == []
    assert ok, message
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        forms = {
            name: Document(io.BytesIO(archive.read(name)))
            for name in names
            if name != "INDICE_schede_HACCP.docx"
        }
        index = Document(io.BytesIO(archive.read("INDICE_schede_HACCP.docx")))
    assert len(forms) == 16

    for name, doc in forms.items():
        art = [d.get("name") for d in doc.element.iter(qn("wp:docPr")) if (d.get("name") or "").startswith(design.ART_MARKER_PREFIX)]
        assert art == [], name
        # One section, no back cover; the running header and footer from the
        # first page on, since the sheet is printed and filled in by hand.
        assert len(doc.sections) == 1, name
        section = doc.sections[0]
        assert not section.different_first_page_header_footer, name
        assert "ACME MECCANICA COMPOSITA SRL" in "\n".join(p.text for p in section.header.paragraphs), name
        assert "Pag." in "\n".join(p.text for p in section.footer.paragraphs), name
        assert _non_arial_fonts(doc) == [], name

    donor_form = next(doc for name, doc in forms.items() if "SA-01" in name)
    assert "sottovuoto" in _text(donor_form).lower()
    # A donor form keeps its own page and type sizes.
    template = Document(str(TEMPLATES_DIR / "haccp" / "Procedura Sottovuoto.docx"))
    sizes = _style_sizes(donor_form)
    assert {k: sizes.get(k) for k in _style_sizes(template)} == _style_sizes(template)

    # The packet's index keeps the kit cover it opens on.
    assert design.art_marker(design.section_first_blocks(index)[0]) == "vera-art:cover:cover_vera"
