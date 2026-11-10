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
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
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


def _font_parts(doc) -> list[tuple[str, object]]:
    parts = [("document", doc.element), ("styles", doc.styles.element)]
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
    module.patch_generators(fixture, str(out))
    results = {}

    async def run_all():
        for tipo in (*DONOR_TEMPLATES, "HACCP_FORMS"):
            results[tipo] = await module.run_one(tipo, fixture["azienda"].id)

    asyncio.run(run_all())
    return results


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
    module.patch_generators(fixture, str(tmp_path / "out"))
    monkeypatch.setattr(haccp_forms, "HACCP_TEMPLATES_DIR", forms_dir)

    ok, path, message = asyncio.run(module.run_one("HACCP_FORMS", fixture["azienda"].id))
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
