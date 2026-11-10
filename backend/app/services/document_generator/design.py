"""The design kit: page types and page furniture for every generated document.

Document audit 2026-09-03 found three visual families shipping under one
product; this module has been the single place the cover, running
header/footer, revision table, table of contents and file properties are
drawn ever since. The 2026-11-10 redesign
(docs/superpowers/specs/2026-11-10-document-layout-redesign-design.md, §4.1)
brings it to the look of N2O's DVR model of 2026-10-20:

- **Page types.** :func:`add_art_cover` (the DVR's picture-only cover),
  :func:`add_cover` (attachments: VERA art plus a live title block),
  :func:`add_divider` (a new section opening on a full-page photo with the
  title mid-page), :func:`add_section_title` (the in-page 25 pt title),
  :func:`add_sub_title` and :func:`add_back_cover`.
- **Art.** Each picture is anchored to the page origin behind the text, sized
  to its section's page, alone in an empty paragraph whose ``wp:docPr`` is
  named ``vera-art:<role>:<key>``. That marker is how
  :func:`add_running_header_footer` (and the preview parser) know the page is
  art: those sections get an empty first-page header and footer.
- **Furniture.** Header: title | client in navy capitals over a hairline.
  Footer: the organization's logo (else the VERA mark), the revision, and
  "Pag. X di Y".

Palette, type scale and the table builders live in :mod:`docx_utils`
(``BRAND_*``, ``TYPE_SCALE``, ``add_*_table``) because generators that never
draw a page type use them too.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.image.image import Image as DocxImage
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Emu, Pt, RGBColor
from docx.text.paragraph import Paragraph

from app.services.document_generator.branding import Branding, resolve_logo_source
from app.services.document_generator.docx_utils import (
    BRAND_DEEP,
    BRAND_NAVY,
    BRAND_NAVY_HEX,
    BRAND_RULE_HEX,
    BRAND_SLATE,
    DOCUMENT_ART_DIR,
    FONT_FAMILY,
    TYPE_SCALE,
    add_data_table,
    fill_label_table,
    format_sede,
    insert_in_order,
    reset_table_rows,
    set_font_slots,
    set_run_font,
)

logger = logging.getLogger(__name__)

# A4 with a binding-side margin; text width is 16.5 cm.
PAGE_W_CM = 21.0
PAGE_H_CM = 29.7
MARGIN_TOP_CM = 2.0
MARGIN_BOTTOM_CM = 2.0
MARGIN_LEFT_CM = 2.5
MARGIN_RIGHT_CM = 2.0
TEXT_WIDTH_CM = PAGE_W_CM - MARGIN_LEFT_CM - MARGIN_RIGHT_CM

# Footer logo box (the model's VERA mark is 2.4 × 0.85 cm).
FOOTER_LOGO_MAX_W_CM = 2.4
FOOTER_LOGO_MAX_H_CM = 0.85

# Where a divider's title starts, from the top edge of the page. The model's
# one-line titles have their capitals at 12.8 cm and two-line titles start
# at 11.9 cm: 12 cm sits between the two.
DIVIDER_TITLE_TOP_CM = 12.0
# Where an attachment cover's title block starts (eyebrow top edge).
COVER_BLOCK_TOP_CM = 4.5

_BACKSLASH = chr(92)

# CT_PPr child sequence (ECMA-376 17.3.1.26); used to insert in schema order.
_PPR_ORDER = [
    "pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
    "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
    "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
    "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc",
    "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr",
    "sectPr", "pPrChange",
]

_PARA_SECTPR = f"{qn('w:pPr')}/{qn('w:sectPr')}"
_BLOCK_TAGS = frozenset(qn(t) for t in ("w:p", "w:tbl", "w:sdt", "w:customXml", "w:altChunk"))


# ---------------------------------------------------------------------------
# Art manifest (spec Appendix A)
# ---------------------------------------------------------------------------

ART_DIR: Path = DOCUMENT_ART_DIR
ART_MARKER_PREFIX = "vera-art:"
_FALLBACK_ART_KEY = "div_generico"

# key -> file in ART_DIR. Two keys are aliases, not files (Ruling 1 of the
# plan): the attachment cover uses the back-cover artwork, and the fallback
# divider reuses the Part III photo, exactly as in N2O's model.
ART: dict[str, str] = {
    "cover_dvr": "cover_dvr.jpg",
    "back_vera": "back_vera.jpg",
    "cover_vera": "back_vera.jpg",
    "div_servizi_igienici": "div_servizi_igienici.jpg",
    "div_macchine": "div_macchine.jpg",
    "div_sostanze": "div_sostanze.jpg",
    "div_fattori_pericolo": "div_fattori_pericolo.jpg",
    "div_ambienti": "div_ambienti.jpg",
    "div_mansioni": "div_mansioni.jpg",
    "div_dpi": "div_dpi.jpg",
    "div_segnaletica": "div_segnaletica.jpg",
    "div_formazione": "div_formazione.jpg",
    "div_miglioramento": "div_miglioramento.jpg",
    "div_leggi": "div_leggi.jpg",
    "div_sorveglianza": "div_sorveglianza.jpg",
    "div_riunione": "div_riunione.jpg",
    "div_infortuni": "div_infortuni.jpg",
    "div_comportamenti": "div_comportamenti.jpg",
    "div_gestione_dpi": "div_gestione_dpi.jpg",
    "div_infrastrutture": "div_infrastrutture.jpg",
    "div_sensibili": "div_sensibili.jpg",
    "div_acquisti": "div_acquisti.jpg",
    "div_appalti": "div_appalti.jpg",
    "div_dichiarazione": "div_dichiarazione.jpg",
    _FALLBACK_ART_KEY: "div_ambienti.jpg",
    "sign_divieto": "sign_divieto.jpg",
    "sign_avvertimento": "sign_avvertimento.jpg",
    "sign_obbligo": "sign_obbligo.jpg",
    "sign_emergenza": "sign_emergenza.jpg",
    "sign_antincendio": "sign_antincendio.jpg",
    "vera_italia_mark": "vera_italia_mark.png",
}


def _resolve_art(key: str) -> tuple[str, Path] | None:
    """``(key actually used, file)`` for ``key``: its own file when present,
    else the generic divider, else ``None``. Every fallback is logged."""
    candidates = [key] if key in ART else []
    if not candidates:
        logger.warning("Unknown document art key %r; using %r", key, _FALLBACK_ART_KEY)
    if _FALLBACK_ART_KEY not in candidates:
        candidates.append(_FALLBACK_ART_KEY)
    for candidate in candidates:
        path = ART_DIR / ART[candidate]
        if path.is_file():
            if candidate != key and key in ART:
                logger.warning("Document art %r is missing in %s; using %r", key, ART_DIR, candidate)
            return candidate, path
    logger.warning("No document art for %r in %s; the page is left white", key, ART_DIR)
    return None


def art_path(key: str) -> Path | None:
    """The file for art ``key``; an unknown key or a missing file falls back to
    ``div_generico``, and ``None`` means even that is missing."""
    resolved = _resolve_art(key)
    return resolved[1] if resolved else None


def _usable_art(key: str) -> tuple[str, Path] | None:
    """Like :func:`_resolve_art`, but only an image python-docx can read."""
    resolved = _resolve_art(key)
    if resolved is None:
        return None
    try:
        DocxImage.from_file(str(resolved[1]))
    except Exception:
        logger.warning("Document art %s is not a readable image; the page is left white", resolved[1])
        return None
    return resolved


def art_marker(paragraph) -> str | None:
    """The ``vera-art:<role>:<key>`` name of the art picture anchored in a
    paragraph (a python-docx ``Paragraph`` or its ``w:p``), else ``None``."""
    element = getattr(paragraph, "_p", paragraph)
    if element is None or element.tag != qn("w:p"):
        return None
    for docpr in element.iter(qn("wp:docPr")):
        name = docpr.get("name") or ""
        if name.startswith(ART_MARKER_PREFIX):
            return name
    return None


# ---------------------------------------------------------------------------
# Revision numbering — one source for all documents
# ---------------------------------------------------------------------------

def revision_label(version: int | None) -> str:
    """``DocumentoGenerato.versione`` (1-based) -> the printed revision ("00").

    The database counts emissions from 1; Italian safety documents number them
    from 0 because revision zero *is* the first issue. Before the audit the DVR
    used this rule and MMC/VDT printed ``Revisione 01`` for the same first
    issue; every generator now goes through here.
    """
    try:
        n = int(version or 0)
    except (TypeError, ValueError):
        n = 0
    return f"{max(n - 1, 0):02d}"


def revision_motivation(version: int | None) -> str:
    """Storico-revisioni wording for the current emission."""
    try:
        n = int(version or 0)
    except (TypeError, ValueError):
        n = 0
    return "Emissione" if n <= 1 else "Aggiornamento"


# ---------------------------------------------------------------------------
# Page setup and base styles
# ---------------------------------------------------------------------------

def _set_style_font(style, name: str) -> None:
    """Set the font on a style in all four slots (ASCII, high ANSI,
    East-Asian, complex script) and drop any theme font, which Word would
    otherwise use instead (Calibri Light or Cambria on headings)."""
    style.font.name = name
    set_font_slots(style.element.get_or_add_rPr().get_or_add_rFonts(), name)


def _set_document_fonts(doc: Document, name: str = FONT_FAMILY) -> None:
    """The document default font and every style's font become ``name``.

    The default covers text that names no font at all (a table cell written
    without a run style); the sweep covers styles such as Heading 4 or Title
    that the python-docx template ties to the theme fonts.
    """
    styles_el = doc.styles.element
    defaults = styles_el.find(qn("w:docDefaults"))
    if defaults is None:
        defaults = OxmlElement("w:docDefaults")
        styles_el.insert(0, defaults)
    rpr_default = defaults.find(qn("w:rPrDefault"))
    if rpr_default is None:
        rpr_default = OxmlElement("w:rPrDefault")
        defaults.insert(0, rpr_default)
    rpr = rpr_default.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        rpr_default.append(rpr)
    if rpr.find(qn("w:rFonts")) is None:
        rpr.insert(0, OxmlElement("w:rFonts"))
    for fonts in styles_el.iter(qn("w:rFonts")):
        set_font_slots(fonts, name)


def _keep_with_next(style) -> None:
    ppr = style.element.get_or_add_pPr()
    for tag in ("w:keepNext", "w:keepLines"):
        for existing in ppr.findall(qn(tag)):
            ppr.remove(existing)
    after_keep_next = _PPR_ORDER[_PPR_ORDER.index("keepLines"):]
    insert_in_order(ppr, OxmlElement("w:keepNext"), tuple(after_keep_next))
    insert_in_order(ppr, OxmlElement("w:keepLines"), tuple(_PPR_ORDER[_PPR_ORDER.index("pageBreakBefore"):]))


# Heading roles per profile (spec §4.1.4): size, alignment, capitals, space
# before and after in points. All bold navy.
_HEADING_PROFILES: dict[str, dict[int, tuple[float, object, bool, float, float]]] = {
    # DVR: Heading 1 is the front-matter heading (INDICE, Premessa; part
    # labels add direct formatting), Heading 2 the 25 pt section title,
    # Heading 3 the centred sub-title.
    "dvr": {
        1: (TYPE_SCALE["front_heading"], None, False, 6, 6),
        2: (TYPE_SCALE["section_title"], WD_ALIGN_PARAGRAPH.CENTER, True, 6, 18),
        3: (TYPE_SCALE["sub_title"], WD_ALIGN_PARAGRAPH.CENTER, False, 12, 6),
    },
    "attachment": {
        1: (TYPE_SCALE["h1"], None, False, 18, 6),
        2: (TYPE_SCALE["h2"], None, False, 14, 4),
        3: (TYPE_SCALE["h3"], None, False, 10, 2),
    },
}


def setup_document(doc: Document, *, landscape: bool = False, profile: str = "attachment") -> None:
    """A4, binding margins, Arial everywhere, navy headings that never orphan.

    ``profile`` picks the heading roles: ``"dvr"`` (front heading, 25 pt
    section title, centred sub-title) or ``"attachment"`` (16/13/12 pt
    chapter headings). Normal is Arial 12 in body ink, not justified: body
    paragraphs are justified by :func:`docx_utils.add_body_paragraph`, so
    table cells stay left-aligned.

    Idempotent: safe to call on a document opened from a template too — it
    rewrites page geometry, the font of every style, and the ``Normal`` and
    ``Heading 1-3`` styles.
    """
    if profile not in _HEADING_PROFILES:
        raise ValueError(f"unknown document profile {profile!r}; use one of {sorted(_HEADING_PROFILES)}")
    for section in doc.sections:
        if landscape:
            section.orientation = WD_ORIENT.LANDSCAPE
            section.page_width = Cm(PAGE_H_CM)
            section.page_height = Cm(PAGE_W_CM)
        else:
            section.orientation = WD_ORIENT.PORTRAIT
            section.page_width = Cm(PAGE_W_CM)
            section.page_height = Cm(PAGE_H_CM)
        section.top_margin = Cm(MARGIN_TOP_CM)
        section.bottom_margin = Cm(MARGIN_BOTTOM_CM)
        section.left_margin = Cm(MARGIN_LEFT_CM)
        section.right_margin = Cm(MARGIN_RIGHT_CM)
        section.header_distance = Cm(1.0)
        section.footer_distance = Cm(1.0)

    _set_document_fonts(doc, FONT_FAMILY)

    normal = doc.styles["Normal"]
    _set_style_font(normal, FONT_FAMILY)
    normal.font.size = Pt(TYPE_SCALE["body"])
    normal.font.color.rgb = BRAND_DEEP
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.08
    normal.paragraph_format.alignment = None

    for level, (size, alignment, caps, before, after) in _HEADING_PROFILES[profile].items():
        try:
            style = doc.styles[f"Heading {level}"]
        except KeyError:
            continue
        _set_style_font(style, FONT_FAMILY)
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.italic = False
        style.font.color.rgb = BRAND_NAVY
        style.font.all_caps = True if caps else None
        style.paragraph_format.alignment = alignment
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        _keep_with_next(style)


# ---------------------------------------------------------------------------
# Small drawing primitives
# ---------------------------------------------------------------------------

def _paragraph_border(paragraph, edge: str, color_hex: str = BRAND_RULE_HEX, size: int = 6, space: int = 4) -> None:
    """Hairline on one edge of a paragraph (``top`` or ``bottom``)."""
    ppr = paragraph._p.get_or_add_pPr()
    pbdr = ppr.find(qn("w:pBdr"))
    if pbdr is None:
        pbdr = OxmlElement("w:pBdr")
        insert_in_order(ppr, pbdr, tuple(_PPR_ORDER[_PPR_ORDER.index("shd"):]))
    el = OxmlElement(f"w:{edge}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(size))
    el.set(qn("w:space"), str(space))
    el.set(qn("w:color"), color_hex)
    pbdr.append(el)


def _add_field(paragraph, instruction: str, cached: str, look: dict) -> None:
    """Append a Word field (PAGE, NUMPAGES, ...) with a cached result, so the
    unrefreshed view is still sensible.

    Written the way Word writes it: one run per part (begin, instruction,
    separator, result, end), each carrying ``look``. LibreOffice formats the
    result from its own run; a field packed into a single run printed at the
    paragraph's default size and colour.
    """
    def field_char(kind: str) -> None:
        run = set_run_font(paragraph.add_run(), **look)
        char = OxmlElement("w:fldChar")
        char.set(qn("w:fldCharType"), kind)
        run._r.append(char)

    field_char("begin")
    run = set_run_font(paragraph.add_run(), **look)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    run._r.append(instr)
    field_char("separate")
    set_run_font(paragraph.add_run(cached), **look)
    field_char("end")


def _centered(
    doc: Document,
    text: str,
    *,
    size: float,
    bold: bool = False,
    italic: bool = False,
    colour: RGBColor | None = None,
    caps: bool = False,
    spacing: float | None = None,
    space_after: float | None = None,
    space_before: Cm | Pt | None = None,
):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text.upper() if caps else text)
    set_run_font(run, size=size, bold=bold, italic=italic, color=colour)
    if spacing is not None:
        rpr = run._r.get_or_add_rPr()
        sp = OxmlElement("w:spacing")
        sp.set(qn("w:val"), str(int(spacing * 20)))
        insert_in_order(rpr, sp, ("w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath"))
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    if space_before is not None:
        p.paragraph_format.space_before = space_before
    return p


def _add_heading(doc: Document, text: str, level: int):
    """``doc.add_heading`` with the kit's font on the run."""
    paragraph = doc.add_heading(text, level=level)
    for run in paragraph.runs:
        set_run_font(run)
    return paragraph


def insert_logo_at_top(doc: Document, branding: Branding, *, width_cm: float = 4.5) -> bool:
    """Put the consultancy mark as the very first body element.

    For donor templates whose cover is a text box we cannot restyle: the
    donor's own logo is stripped with the other body pictures and the
    organization's mark takes its place above the title.
    """
    logo_src = resolve_logo_source(branding)
    if logo_src is None:
        return False
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    try:
        p.add_run().add_picture(logo_src, width=Cm(width_cm))
    except Exception:
        p._p.getparent().remove(p._p)
        return False
    body = doc.element.body
    body.remove(p._p)
    body.insert(0, p._p)
    return True


# ---------------------------------------------------------------------------
# Page boundaries
#
# A page break written as its own paragraph can end up alone at the top of a
# page when the content before it fills the previous one, and then breaks
# again: an empty page. The kit therefore starts pages with
# page-break-before on the first paragraph of the new page (the idea of
# DVRMasterGenerator._ensure_page_boundary) and absorbs a trailing
# page-break paragraph into the next page start or section break.
# ---------------------------------------------------------------------------

def _last_block(doc: Document):
    """The last body element before the document-level ``w:sectPr``."""
    for element in reversed(doc.element.body):
        if element.tag != qn("w:sectPr"):
            return element
    return None


def _is_empty_paragraph(p) -> bool:
    return not "".join(t.text or "" for t in p.iter(qn("w:t"))).strip() and not p.xpath(
        ".//w:drawing | .//w:pict | .//w:object"
    )


def _is_page_break_only(p) -> bool:
    """A paragraph that holds nothing but page breaks (``doc.add_page_break``)."""
    if p.tag != qn("w:p") or p.find(_PARA_SECTPR) is not None:
        return False
    found = False
    for child in p:
        if child.tag == qn("w:pPr"):
            continue
        if child.tag != qn("w:r"):
            return False
        for item in child:
            if item.tag == qn("w:rPr"):
                continue
            if item.tag == qn("w:br") and item.get(qn("w:type")) == "page":
                found = True
                continue
            return False
    return found


def _drop_trailing_page_break(doc: Document) -> bool:
    last = _last_block(doc)
    if last is None or not _is_page_break_only(last):
        return False
    last.getparent().remove(last)
    return True


def _starts_new_page_already(doc: Document) -> bool:
    """True when the next paragraph appended will open a page anyway."""
    last = _last_block(doc)
    if last is None:
        return True
    if last.tag != qn("w:p"):
        return False
    if last.find(_PARA_SECTPR) is not None:
        return doc.sections[-1].start_type in (WD_SECTION.NEW_PAGE, WD_SECTION.EVEN_PAGE, WD_SECTION.ODD_PAGE)
    flag = last.find(f"{qn('w:pPr')}/{qn('w:pageBreakBefore')}")
    if flag is not None and flag.get(qn("w:val")) in (None, "1", "true", "on") and _is_empty_paragraph(last):
        return True
    return False


def _page_break_needed(doc: Document, new_page: bool) -> bool:
    """Prepare a page start: absorb a trailing page-break paragraph and say
    whether the next paragraph needs page-break-before."""
    if not new_page:
        return False
    _drop_trailing_page_break(doc)
    return not _starts_new_page_already(doc)


def _set_mark_size(p, half_points: int) -> None:
    """Size of a paragraph's mark: it sets the height of an empty paragraph."""
    ppr = p.get_or_add_pPr()
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        insert_in_order(ppr, rpr, ("sectPr", "pPrChange"))
    for tag in ("w:sz", "w:szCs"):
        el = rpr.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            rpr.append(el)
        el.set(qn("w:val"), str(half_points))


def _shrink(paragraph) -> None:
    """Make an empty paragraph 1 pt tall, with no spacing."""
    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.line_spacing = Pt(1)
    _set_mark_size(paragraph._p, 2)


def _start_art_section(doc: Document):
    """A new section on a new page for a divider or the back cover.

    python-docx ends the previous section with an empty paragraph carrying
    its ``w:sectPr``; it is shrunk to 1 pt so a previous page filled to the
    last line does not spill it onto a page of its own. An empty document
    has nothing to end: its first section is used.
    """
    _drop_trailing_page_break(doc)
    if _last_block(doc) is None:
        return doc.sections[-1]
    section = doc.add_section(WD_SECTION.NEW_PAGE)
    breaks = doc.element.body.xpath("./w:p[w:pPr/w:sectPr]")
    if breaks:
        _shrink(Paragraph(breaks[-1], doc._body))
    return section


# ---------------------------------------------------------------------------
# Full-page art
# ---------------------------------------------------------------------------

_ART_Z_ORDER = 251658240  # Word's base for objects behind the text

_ANCHOR_XML = (
    '<wp:anchor %s distT="0" distB="0" distL="0" distR="0" simplePos="0" '
    'relativeHeight="%d" behindDoc="1" locked="0" layoutInCell="1" allowOverlap="1">'
    '<wp:simplePos x="0" y="0"/>'
    '<wp:positionH relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionH>'
    '<wp:positionV relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionV>'
    '<wp:extent cx="%d" cy="%d"/>'
    '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
    "<wp:wrapNone/>"
    "</wp:anchor>"
)


def _page_size(section) -> tuple[int, int]:
    width = section.page_width or Cm(PAGE_W_CM)
    height = section.page_height or Cm(PAGE_H_CM)
    return int(width), int(height)


def _crop_to_cover(inline, image, width: int, height: int) -> None:
    """Crop the picture's long side so it fills the page undistorted
    (``object-fit: cover``). Art is cut to A4, so on A4 this does nothing;
    a donor template on another paper size keeps its own page setup."""
    if not image.px_width or not image.px_height:
        return
    image_ratio = image.px_width / image.px_height
    page_ratio = width / height
    if abs(image_ratio - page_ratio) / page_ratio < 0.005:
        return
    rect = OxmlElement("a:srcRect")
    if image_ratio > page_ratio:
        side = int(round((1 - page_ratio / image_ratio) / 2 * 100000))
        rect.set("l", str(side))
        rect.set("r", str(side))
    else:
        side = int(round((1 - image_ratio / page_ratio) / 2 * 100000))
        rect.set("t", str(side))
        rect.set("b", str(side))
    blip = inline.find(".//" + qn("a:blip"))
    if blip is not None:
        blip.addnext(rect)


def _anchor_behind_page(inline, name: str) -> None:
    """Turn python-docx's ``wp:inline`` into a page-anchored picture behind
    the text, keeping its ``a:graphic`` and its document-unique ``docPr`` id."""
    extent = inline.find(qn("wp:extent"))
    anchor = parse_xml(
        _ANCHOR_XML % (nsdecls("wp"), _ART_Z_ORDER, int(extent.get("cx")), int(extent.get("cy")))
    )
    for tag in ("wp:docPr", "wp:cNvGraphicFramePr", "a:graphic"):
        child = inline.find(qn(tag))
        if child is not None:
            anchor.append(child)
    anchor.find(qn("wp:docPr")).set("name", name)
    inline.getparent().replace(inline, anchor)


def _add_art_paragraph(doc: Document, key: str, path: Path, *, role: str, section):
    """Append the empty 1 pt paragraph holding the full-page picture for
    ``section``. Returns it, or ``None`` (with nothing appended) on failure."""
    width, height = _page_size(section)
    paragraph = doc.add_paragraph()
    _shrink(paragraph)
    run = paragraph.add_run()
    set_run_font(run, size=1)
    try:
        inline = run.add_picture(str(path), width=Emu(width), height=Emu(height))._inline
    except Exception:
        logger.warning("Document art %s could not be embedded; the page is left white", path, exc_info=True)
        paragraph._p.getparent().remove(paragraph._p)
        return None
    blip = inline.find(".//" + qn("a:blip"))
    image_part = run.part.related_parts.get(blip.get(qn("r:embed"))) if blip is not None else None
    if image_part is not None:
        _crop_to_cover(inline, image_part.image, width, height)
    _anchor_behind_page(inline, f"{ART_MARKER_PREFIX}{role}:{key}")
    return paragraph


# ---------------------------------------------------------------------------
# Page types
# ---------------------------------------------------------------------------

def add_art_cover(doc: Document, art_key: str) -> None:
    """A picture-only cover opening the document's first section (the DVR's:
    title, "D.LGS. 81/08" and the VERA mark are in the art).

    Call it first. If the body already has content, the cover is moved in
    front of it. Without usable art nothing is added, and a warning is logged.
    """
    resolved = _usable_art(art_key)
    if resolved is None:
        return
    first_section = doc.sections[0]
    had_content = _last_block(doc) is not None
    art = _add_art_paragraph(doc, *resolved, role="cover", section=first_section)
    if art is None:
        return
    doc.add_page_break()
    if had_content:
        body = doc.element.body
        page_break = art._p.getnext()
        body.insert(0, page_break)
        body.insert(0, art._p)
    first_section.different_first_page_header_footer = True


def add_cover(
    doc: Document,
    *,
    title: str,
    azienda,
    branding: Branding,
    version: int | None,
    generated_at: datetime,
    subtitle: str | None = None,
    legal_basis: str | None = None,
    eyebrow: str | None = "Allegato al Documento di Valutazione dei Rischi",
    logo_width_cm: float = 5.0,
    show_consultancy: bool = True,
) -> None:
    """The cover every attachment shares: the VERA artwork (``cover_vera``)
    behind a live title block in the upper part of the page.

    Top to bottom: eyebrow, title, subtitle, legal basis, a short rule, the
    assessed company's identity (name, seat, P.IVA, ATECO), revision and date
    and — when ``show_consultancy`` — the "elaborato da" letterhead. Ends
    with a page break. Every field degrades to nothing when the data is
    missing; the cover never prints a placeholder. Without the artwork the
    title block stands on a white page.

    ``logo_width_cm`` is accepted for compatibility and ignored: the VERA
    mark is part of the artwork, so the cover carries no separate logo.
    """
    del logo_width_cm
    section = doc.sections[-1]
    top_cm = (section.top_margin or Cm(MARGIN_TOP_CM)) / Cm(1)
    resolved = _usable_art("cover_vera")
    if resolved is not None and _add_art_paragraph(doc, *resolved, role="cover", section=section) is not None:
        section.different_first_page_header_footer = True
    lead = Cm(max(COVER_BLOCK_TOP_CM - top_cm, 0))

    if eyebrow:
        _centered(doc, eyebrow, size=TYPE_SCALE["small"], colour=BRAND_SLATE, caps=True, spacing=1.2, space_after=8, space_before=lead)
        lead = None
    _centered(doc, title, size=TYPE_SCALE["cover_title"], bold=True, colour=BRAND_NAVY, space_after=6, space_before=lead)
    if subtitle:
        _centered(doc, subtitle, size=TYPE_SCALE["cover_subtitle"], colour=BRAND_SLATE, space_after=2)
    if legal_basis:
        _centered(doc, legal_basis, size=TYPE_SCALE["body"], italic=True, colour=BRAND_SLATE, space_after=10)

    rule = doc.add_paragraph()
    rule.paragraph_format.left_indent = Cm(5.0)
    rule.paragraph_format.right_indent = Cm(5.0)
    rule.paragraph_format.space_after = Pt(0)
    _paragraph_border(rule, "bottom", BRAND_NAVY_HEX, size=8, space=1)

    ragione = (getattr(azienda, "ragione_sociale", None) or "").strip()
    _centered(
        doc,
        ragione.upper() if ragione else "—",
        size=TYPE_SCALE["cover_client"],
        bold=True,
        colour=BRAND_DEEP,
        space_after=4,
        space_before=Cm(1.2),
    )
    sede = format_sede(azienda, "legale")
    if sede and sede != "—":
        _centered(doc, sede, size=TYPE_SCALE["body"], colour=BRAND_SLATE, space_after=2)
    bits = []
    piva = getattr(azienda, "partita_iva", None)
    ateco = getattr(azienda, "codice_ateco", None)
    if piva:
        bits.append(f"P.IVA {piva}")
    if ateco:
        bits.append(f"ATECO {ateco}")
    if bits:
        _centered(doc, " · ".join(bits), size=TYPE_SCALE["body"], colour=BRAND_SLATE)

    _centered(
        doc,
        f"Revisione {revision_label(version)} · {generated_at.strftime('%d/%m/%Y')}",
        size=TYPE_SCALE["body"],
        bold=True,
        colour=BRAND_DEEP,
        space_after=14,
        space_before=Cm(1.2),
    )

    if show_consultancy:
        _centered(
            doc,
            "Documento elaborato da",
            size=TYPE_SCALE["small"],
            colour=BRAND_SLATE,
            caps=True,
            spacing=1.0,
            space_after=2,
        )
        _centered(
            doc,
            (branding.firm_name or "").upper(),
            size=TYPE_SCALE["body"],
            bold=True,
            colour=BRAND_NAVY,
            space_after=1,
        )
        for line in _letterhead_lines(branding):
            _centered(doc, line, size=TYPE_SCALE["small"], colour=BRAND_SLATE, space_after=0)

    doc.add_page_break()


def _letterhead_lines(branding: Branding) -> list[str]:
    lines: list[str] = []
    addr = branding.address_line()
    if addr:
        lines.append(addr)
    tax = []
    if branding.partita_iva:
        tax.append(f"P.IVA {branding.partita_iva}")
    if branding.codice_fiscale and branding.codice_fiscale != branding.partita_iva:
        tax.append(f"C.F. {branding.codice_fiscale}")
    if tax:
        lines.append(" · ".join(tax))
    contact = branding.contact_line()
    if contact:
        lines.append(contact)
    if branding.rspp_nome:
        lines.append(f"RSPP: {branding.rspp_nome}")
    return lines


# Heights used to keep a divider's title at the same place with or without a
# part label: the 1 pt art paragraph, and a 9 pt label line plus 6 pt after.
_ART_PARAGRAPH_CM = Pt(1) / Cm(1)
_PART_LABEL_BLOCK_CM = 0.6


def _add_part_label(doc: Document, text: str):
    """The small "PARTE I — …" line: Heading 1 (so it is in the index) with
    the part-label look applied directly (9 pt bold navy capitals, centred)."""
    paragraph = doc.add_heading(text, level=1)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(6)
    for run in paragraph.runs:
        set_run_font(run, size=TYPE_SCALE["part_label"], bold=True, color=BRAND_NAVY, caps=True)
    return paragraph


def add_divider(doc: Document, title: str, art_key: str, *, part_label: str | None = None):
    """A divider page: a new section on a new page with a full-page photo,
    an optional part label at the top and the title (Heading 2) mid-page.

    The section shows no header or footer on this first page and the running
    ones after it; the content that follows starts on the next page. The art
    sits in its own empty paragraph, so the title stays an ordinary editable
    heading. Without usable art the page is white with the title. Returns the
    title paragraph.
    """
    resolved = _usable_art(art_key)
    section = _start_art_section(doc)
    used_cm = (section.top_margin or Cm(MARGIN_TOP_CM)) / Cm(1)
    if resolved is not None and _add_art_paragraph(doc, *resolved, role="divider", section=section) is not None:
        section.different_first_page_header_footer = True
        used_cm += _ART_PARAGRAPH_CM
    if part_label:
        _add_part_label(doc, part_label)
        used_cm += _PART_LABEL_BLOCK_CM
    heading = _add_heading(doc, title, level=2)
    heading.paragraph_format.space_before = Cm(max(DIVIDER_TITLE_TOP_CM - used_cm, 0))
    doc.add_page_break()
    return heading


def add_section_title(doc: Document, title: str, *, part_label: str | None = None, new_page: bool = True):
    """The in-page title (Heading 2), optionally under a part label.

    With ``new_page`` the first paragraph emitted (the label, else the title)
    gets page-break-before rather than a break paragraph of its own, so a
    table that filled the previous page never leaves an empty one behind.
    Returns the title paragraph.
    """
    break_before = _page_break_needed(doc, new_page)
    label = _add_part_label(doc, part_label) if part_label else None
    heading = _add_heading(doc, title, level=2)
    if label is not None:
        # The model leaves ~1.7 cm between a part label and its title.
        heading.paragraph_format.space_before = Pt(18)
    if break_before:
        (label or heading).paragraph_format.page_break_before = True
    return heading


def add_sub_title(doc: Document, text: str, *, in_toc: bool = True, new_page: bool = False):
    """A sub-title: 12 pt bold navy, centred.

    ``in_toc``: Heading 3, so it is in the index. Otherwise a Normal
    paragraph with the same look and no outline level (the risk-category
    captions the index leaves out). ``new_page`` starts it on a new page.
    """
    break_before = _page_break_needed(doc, new_page)
    if in_toc:
        paragraph = _add_heading(doc, text, level=3)
    else:
        paragraph = doc.add_paragraph()
        fmt = paragraph.paragraph_format
        fmt.space_before = Pt(12)
        fmt.space_after = Pt(6)
        fmt.keep_with_next = True
        set_run_font(
            paragraph.add_run(text),
            size=TYPE_SCALE["sub_title"],
            bold=True,
            color=BRAND_NAVY,
        )
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if break_before:
        paragraph.paragraph_format.page_break_before = True
    return paragraph


def add_back_cover(doc: Document, art_key: str = "back_vera") -> None:
    """The closing page: a new one-page section that is all art, with no
    header or footer. Without usable art it is left out entirely: a white
    last page would serve nobody."""
    resolved = _usable_art(art_key)
    if resolved is None:
        logger.warning("Back cover %r left out: no usable artwork", art_key)
        return
    section = _start_art_section(doc)
    if _add_art_paragraph(doc, *resolved, role="back_cover", section=section) is not None:
        section.different_first_page_header_footer = True


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def section_first_blocks(doc: Document) -> list:
    """The first body block (``w:p``, ``w:tbl``, ...) of each section, in the
    order of ``doc.sections``; ``None`` for a section with no block.

    python-docx stores a section break on the last paragraph *before* it, so
    a section's first block is the first one after the previous
    ``w:sectPr``-carrying paragraph.
    """
    firsts: list = []
    first = None
    for element in doc.element.body.iterchildren():
        if element.tag == qn("w:sectPr"):
            firsts.append(first)
            first = None
            continue
        if element.tag not in _BLOCK_TAGS:
            continue
        if first is None:
            first = element
        if element.tag == qn("w:p") and element.find(_PARA_SECTPR) is not None:
            firsts.append(first)
            first = None
    return firsts


def _section_index_of(doc: Document, target) -> int:
    index = 0
    for element in doc.element.body.iterchildren():
        if element is target:
            return index
        if element.tag == qn("w:p") and element.find(_PARA_SECTPR) is not None:
            index += 1
    return len(doc.sections) - 1


def _text_width(section) -> int:
    width = (section.page_width or Cm(PAGE_W_CM)) - (section.left_margin or 0) - (section.right_margin or 0)
    return int(width) if width > 0 else int(Cm(TEXT_WIDTH_CM))


# ---------------------------------------------------------------------------
# Running header / footer
# ---------------------------------------------------------------------------

def _clear(container) -> None:
    """Empty a header/footer container so re-application is idempotent."""
    for p in list(container.paragraphs):
        p._p.getparent().remove(p._p)
    for t in list(container.tables):
        t._tbl.getparent().remove(t._tbl)


def _emit(paragraph, parts: list[tuple[str, dict]]) -> None:
    for text, fmt in parts:
        look = {
            "size": fmt.get("size", TYPE_SCALE["footer"]),
            "bold": fmt.get("bold", False),
            "color": fmt.get("colour", BRAND_SLATE),
        }
        field = fmt.get("field")
        if field:
            _add_field(paragraph, field, fmt.get("cached", "1"), look)
        else:
            set_run_font(paragraph.add_run(text), **look)


def _two_sided(container, left: list[tuple[str, dict]], right: list[tuple[str, dict]], *, width_cm: float):
    """One paragraph with left text and a right-aligned tab: the classic
    running-head layout without a table."""
    p = container.paragraphs[0] if container.paragraphs else container.add_paragraph()
    p.paragraph_format.tab_stops.add_tab_stop(Cm(width_cm), WD_TAB_ALIGNMENT.RIGHT)
    p.paragraph_format.space_after = Pt(0)
    _emit(p, left)
    _emit(p, [("\t", left[-1][1] if left else {})])
    _emit(p, right)
    return p


def _footer_logo_box(branding: Branding) -> tuple[int, int] | None:
    """Width and height (EMU) that fit the logo in 2.4 × 0.85 cm without
    distortion, or ``None`` when there is no readable logo."""
    source = resolve_logo_source(branding)
    if source is None:
        return None
    try:
        image = DocxImage.from_file(source)
    except Exception:
        logger.warning("Organization logo is not a readable image; the footer prints the firm name")
        return None
    if not image.px_width or not image.px_height:
        return None
    scale = min(Cm(FOOTER_LOGO_MAX_W_CM) / image.px_width, Cm(FOOTER_LOGO_MAX_H_CM) / image.px_height)
    return max(int(image.px_width * scale), 1), max(int(image.px_height * scale), 1)


def _write_header(header, *, title: str, ragione: str, width_cm: float) -> None:
    look = {"size": TYPE_SCALE["header"], "bold": True, "colour": BRAND_NAVY}
    paragraph = _two_sided(header, [(title.upper(), look)], [(ragione.upper(), look)], width_cm=width_cm)
    _paragraph_border(paragraph, "bottom", BRAND_RULE_HEX, size=6, space=3)


def _write_footer(footer, *, branding: Branding, logo_box, firm: str, rev: str, width_cm: float) -> None:
    """Logo, two spaces, the revision; at the right margin "Pag. X di Y".
    An unreadable logo gives way to the firm name in bold navy."""
    paragraph = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(width_cm), WD_TAB_ALIGNMENT.RIGHT)
    paragraph.paragraph_format.space_after = Pt(0)
    placed = False
    if logo_box is not None:
        run = paragraph.add_run()
        try:
            run.add_picture(resolve_logo_source(branding), width=Emu(logo_box[0]), height=Emu(logo_box[1]))
            placed = True
        except Exception:
            logger.warning("Organization logo could not be embedded; the footer prints the firm name", exc_info=True)
            run._r.getparent().remove(run._r)
    lead = "  "
    if not placed:
        if firm:
            _emit(paragraph, [(firm, {"bold": True, "colour": BRAND_NAVY})])
        else:
            lead = ""
    slate: dict = {}
    _emit(
        paragraph,
        [
            (f"{lead}{rev}", slate),
            ("\t", slate),
            ("Pag. ", slate),
            ("", {"field": "PAGE"}),
            (" di ", slate),
            ("", {"field": "NUMPAGES"}),
        ],
    )
    _paragraph_border(paragraph, "top", BRAND_RULE_HEX, size=6, space=3)


def _write_running(header, footer, *, title: str, ragione: str, branding: Branding, logo_box, firm: str, rev: str, width_cm: float) -> None:
    _write_header(header, title=title, ragione=ragione, width_cm=width_cm)
    _write_footer(footer, branding=branding, logo_box=logo_box, firm=firm, rev=rev, width_cm=width_cm)


def _dedupe_drawing_ids(doc: Document) -> None:
    """Give every ``wp:docPr`` in the body, headers and footers its own id.

    python-docx numbers pictures per part, so each footer's logo would be
    picture 1 like the first picture of the body; Word expects the ids to be
    unique across the document.
    """
    roots = [doc.element]
    for rel in doc.part.rels.values():
        if not rel.is_external and rel.reltype in (RT.HEADER, RT.FOOTER):
            roots.append(rel.target_part.element)
    docprs = [docpr for root in roots for docpr in root.iter(qn("wp:docPr"))]
    next_id = max((int(d.get("id")) for d in docprs if (d.get("id") or "").isdigit()), default=0) + 1
    seen: set[str] = set()
    for docpr in docprs:
        value = docpr.get("id") or ""
        if not value.isdigit() or value in seen:
            value = str(next_id)
            next_id += 1
            docpr.set("id", value)
        seen.add(value)


def add_running_header_footer(
    doc: Document,
    *,
    title: str,
    azienda,
    branding: Branding,
    version: int | None,
    generated_at: datetime,
    cover_is_clean: bool = True,
) -> None:
    """Header: TITLE | CLIENT. Footer: logo · Rev. NN del gg/mm/aaaa | Pag. X di Y.

    Applied to every section. A section whose first paragraph carries an art
    marker (cover, divider, back cover) gets an empty first-page header and
    footer, and the running ones on its following pages; every other section
    carries them on all its pages. ``cover_is_clean`` keeps the first page of
    the first section clean even without art — the covers of the donor
    templates, which keep their own until they adopt the kit.

    Content is written fresh into the default, first-page and even-page
    parts, replacing whatever a donor template carried there — this is how
    the legacy N2O letterhead leaves the template family.
    """
    ragione = (getattr(azienda, "ragione_sociale", None) or "").strip()
    firm = (branding.firm_name or "").strip()
    rev = f"Rev. {revision_label(version)} del {generated_at.strftime('%d/%m/%Y')}"
    logo_box = _footer_logo_box(branding)
    firsts = section_first_blocks(doc)
    for index, section in enumerate(doc.sections):
        first = firsts[index] if index < len(firsts) else None
        clean = art_marker(first) is not None or (cover_is_clean and index == 0)
        width_cm = _text_width(section) / Cm(1)
        section.different_first_page_header_footer = clean
        # Donor templates set the footer distance to 0 (DUVRI) so their
        # letterhead sat on the page edge; the running header/footer needs
        # room, and a 0 distance is also where renderers start to struggle.
        for attr in ("header_distance", "footer_distance"):
            current = getattr(section, attr, None)
            if current is None or current < Cm(0.8):
                setattr(section, attr, Cm(1.0))
        parts = (
            section.header, section.footer,
            section.first_page_header, section.first_page_footer,
            section.even_page_header, section.even_page_footer,
        )
        for container in parts:
            container.is_linked_to_previous = False
            _clear(container)

        running = dict(title=title, ragione=ragione, branding=branding, logo_box=logo_box, firm=firm, rev=rev, width_cm=width_cm)
        _write_running(section.header, section.footer, **running)
        # Even pages only matter when the document asks for odd/even headers;
        # writing them keeps a donor's evenAndOddHeaders setting harmless.
        _write_running(section.even_page_header, section.even_page_footer, **running)

        if clean:
            # An empty paragraph is required so Word does not fall back to
            # the default header on the art page.
            section.first_page_header.add_paragraph("")
            section.first_page_footer.add_paragraph("")
        else:
            _write_running(section.first_page_header, section.first_page_footer, **running)
    _dedupe_drawing_ids(doc)


# ---------------------------------------------------------------------------
# Revision history, table of contents, file properties
# ---------------------------------------------------------------------------

def add_revision_table(
    doc: Document,
    version: int | None,
    generated_at: datetime,
    *,
    heading: str | None = "Storico delle revisioni",
    level: int = 2,
):
    """The single-row Storico for this emission, numbered like the cover."""
    if heading:
        _add_heading(doc, heading, level)
    table = add_data_table(
        doc,
        ["Rev.", "Motivazione", "Data"],
        [[revision_label(version), revision_motivation(version), generated_at.strftime("%d/%m/%Y")]],
        column_widths_cm=[2.0, 10.5, 4.0],
    )
    doc.add_paragraph("")
    return table


def add_toc(doc: Document, *, title: str = "Indice"):
    """A real TOC field with a cached outline the reader sees before any F9.

    Returns ``(field_start_p, end_p)`` for :func:`finalize_toc`, which fills
    the cached body with the headings actually emitted. Word is told to
    refresh fields on open, which restores page numbers.
    """
    _add_heading(doc, title, 1)
    field_start_p = doc.add_paragraph()
    run = field_start_p.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    run._r.append(begin)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " TOC " + _BACKSLASH + 'o "1-3" ' + _BACKSLASH + "h " + _BACKSLASH + "z " + _BACKSLASH + "u "
    run._r.append(instr)
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    run._r.append(sep)

    placeholder = doc.add_paragraph()
    set_run_font(placeholder.add_run("Indice in fase di aggiornamento."), size=TYPE_SCALE["body"], italic=True, color=BRAND_SLATE)

    end_p = doc.add_paragraph()
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_p.add_run()._r.append(end)

    refresh_fields_on_open(doc)
    doc.add_page_break()
    return field_start_p, end_p


def refresh_fields_on_open(doc: Document) -> None:
    """Ask Word to update every field when the document is opened.

    Page numbers, NUMPAGES and — on the donor templates — the index. Their
    TOC is a real field whose cached lines were written by the consultant who
    last saved the template, so without this the reader sees that outline
    instead of the one this generation produced.
    """
    try:
        settings_root = doc.settings.element
        if settings_root.find(qn("w:updateFields")) is None:
            uf = OxmlElement("w:updateFields")
            uf.set(qn("w:val"), "true")
            settings_root.append(uf)
    except Exception:
        pass


def finalize_toc(doc: Document, field_start_p, end_p) -> None:
    """Rewrite the TOC's cached body from the Heading 1-3 paragraphs that
    follow it, so the document is navigable even before Word refreshes.

    Each entry ends in a tab to a right-aligned stop with a dot leader at the
    text width, the index's look; Word writes the page numbers when it
    refreshes the field on open.
    """
    body = doc.element.body
    children = list(body)
    try:
        start_idx = children.index(field_start_p._p)
        end_idx = children.index(end_p._p)
    except ValueError:
        return

    entries: list[tuple[int, str]] = []
    for para in doc.paragraphs:
        name = (para.style.name if para.style else "") or ""
        if not name.startswith("Heading "):
            continue
        try:
            level = int(name.split(" ")[1])
        except (IndexError, ValueError):
            continue
        if level not in (1, 2, 3):
            continue
        try:
            idx = children.index(para._p)
        except ValueError:
            continue
        if idx <= end_idx:
            continue
        text = (para.text or "").strip()
        if text:
            entries.append((level, text))
    if not entries:
        return

    leader_at = Emu(_text_width(doc.sections[_section_index_of(doc, field_start_p._p)]))
    for el in children[start_idx + 1 : end_idx]:
        body.remove(el)
    for level, text in entries:
        new_p = doc.add_paragraph()
        indent = (level - 1) * 0.5
        if indent:
            new_p.paragraph_format.left_indent = Cm(indent)
        new_p.paragraph_format.space_after = Pt(2)
        new_p.paragraph_format.tab_stops.add_tab_stop(leader_at, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        size = TYPE_SCALE["body"] if level == 1 else TYPE_SCALE["table"]
        set_run_font(
            new_p.add_run(text),
            size=size,
            bold=level == 1,
            color=BRAND_NAVY if level == 1 else BRAND_DEEP,
        )
        set_run_font(new_p.add_run("\t"), size=size)
        body.remove(new_p._p)
        body.insert(list(body).index(end_p._p), new_p._p)


def _xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def set_core_properties(
    doc: Document,
    *,
    title: str,
    azienda,
    branding: Branding,
    generated_at: datetime,
    version: int | None,
) -> None:
    """Make File > Properties tell the truth.

    Donor templates arrived with their authors' names, a hardware vendor as
    Company and, in one case, "Ethan Frome" as the title. Everything a client
    could read in the properties pane is rewritten from this generation.
    """
    ragione = (getattr(azienda, "ragione_sociale", None) or "").strip()
    firm = (branding.firm_name or "").strip()
    cp = doc.core_properties
    cp.title = title
    cp.subject = ragione
    cp.author = firm
    cp.last_modified_by = firm
    cp.category = "Sicurezza sul lavoro"
    cp.keywords = ""
    cp.comments = ""
    cp.identifier = ""
    cp.content_status = ""
    cp.created = generated_at
    cp.modified = generated_at
    try:
        cp.revision = max(int(version or 1), 1)
    except (TypeError, ValueError):
        cp.revision = 1
    # app.xml (Company, Application, TotalTime...) has no python-docx API.
    try:
        for part in doc.part.package.iter_parts():
            if str(part.partname) != "/docProps/app.xml":
                continue
            blob = part.blob.decode("utf8", "replace")
            blob = re.sub(r"<Company>.*?</Company>", f"<Company>{_xml_escape(firm)}</Company>", blob, flags=re.S)
            blob = re.sub(r"<Manager>.*?</Manager>", "<Manager></Manager>", blob, flags=re.S)
            blob = re.sub(r"<Application>.*?</Application>", "<Application>Microsoft Office Word</Application>", blob, flags=re.S)
            blob = re.sub(r"<TotalTime>.*?</TotalTime>", "<TotalTime>0</TotalTime>", blob, flags=re.S)
            part._blob = blob.encode("utf8")
    except Exception:
        pass


def fill_cover_tables(
    doc: Document,
    *,
    azienda,
    version: int | None,
    generated_at: datetime,
    extra: dict[str, str] | None = None,
) -> None:
    """Fill a donor template's cover forms from the client's data.

    The template covers are label | value tables whose value cells are empty
    — there is no token to substitute, which is why ``replace_placeholders``
    never did anything on them (audit 2026-09-03). Only empty value cells are
    written, so a template that already carries a value is left alone. The
    revision history is reset to this emission.
    """
    ragione = (getattr(azienda, "ragione_sociale", None) or "").strip()

    def seat_lines(which: str) -> list[str]:
        # Donor covers keep street and comune on two merged rows; hand them
        # over as two items so each row gets its own line.
        from app.services.document_generator.docx_utils import format_comune
        via = (getattr(azienda, f"sede_{which}_via", None) or "").strip()
        comune = format_comune(
            getattr(azienda, f"cap_{which}", None),
            getattr(azienda, f"sede_{which}_citta", None),
            getattr(azienda, f"provincia_{which}", None),
        )
        return [x for x in (via, comune if comune != "—" else "") if x]

    legale_lines = seat_lines("legale")
    operativa_lines = seat_lines("operativa") or legale_lines
    values: dict = {
        "Azienda": ragione,
        "Ragione sociale": ragione,
        "Sede Legale": legale_lines,
        "Sede Operativa": operativa_lines,
        "Sede": legale_lines,
        "Data": generated_at.strftime("%d/%m/%Y"),
    }
    piva = getattr(azienda, "partita_iva", None)
    if piva:
        values["P.IVA"] = piva
        values["Partita IVA"] = piva
    if extra:
        values.update({k: v for k, v in extra.items() if v})
    fill_label_table(doc, values)
    reset_table_rows(
        doc,
        "Rev. | Motivazione",
        [[revision_label(version), revision_motivation(version), generated_at.strftime("%d/%m/%Y")]],
    )


def _referenced_ids(element) -> set[str]:
    ids: set[str] = set()
    for el in element.iter():
        for attr in (qn("r:embed"), qn("r:id"), qn("r:link")):
            value = el.get(attr)
            if value:
                ids.add(value)
    return ids


def _remove_external_links(part, root) -> int:
    """Delete pictures linked to the internet and unwrap web hyperlinks.

    The DUVRI donor template pulls its status icons from www.secofor.it and
    links a Google search: offline Word shows red boxes, LibreOffice hangs
    on the fetch, and a third party's site has no place in a client's file.
    """
    removed = 0
    for rId, rel in list(part.rels.items()):
        if not rel.is_external:
            continue
        kind = rel.reltype.rsplit("/", 1)[-1]
        if kind == "image":
            for el in list(root.iter()):
                if el.get(qn("r:link")) == rId or el.get(qn("r:id")) == rId:
                    holder = el
                    while holder is not None and holder.tag not in (qn("w:drawing"), qn("w:pict"), qn("w:r")):
                        holder = holder.getparent()
                    target = holder if holder is not None else el
                    parent = target.getparent()
                    if parent is not None:
                        parent.remove(target)
                        removed += 1
            part.rels.pop(rId, None)
        elif kind == "hyperlink":
            for link in list(root.iter(qn("w:hyperlink"))):
                if link.get(qn("r:id")) != rId:
                    continue
                parent = link.getparent()
                index = parent.index(link)
                for child in list(link):
                    parent.insert(index, child)
                    index += 1
                parent.remove(link)
                removed += 1
            part.rels.pop(rId, None)
    return removed


def prune_orphan_parts(doc: Document) -> int:
    """Drop header/footer/image relationships nothing points to any more,
    and everything that points outside the file.

    Removing a donor picture from the body, or rewriting a section's
    headers, leaves the old part in the package: not rendered, but still in
    the file a client receives (a stripped Street View photo travelled that
    way). Returns the number of relationships dropped.
    """
    dropped = _remove_external_links(doc.part, doc.element.body)
    used = _referenced_ids(doc.element.body)
    for rId, rel in list(doc.part.rels.items()):
        if rel.is_external:
            continue
        kind = rel.reltype.rsplit("/", 1)[-1]
        if kind in ("header", "footer", "image") and rId not in used:
            doc.part.drop_rel(rId)
            dropped += 1
    # Images inside the header/footer parts we kept (their paragraphs were
    # cleared, their picture relationships were not).
    for rel in list(doc.part.rels.values()):
        kind = rel.reltype.rsplit("/", 1)[-1]
        if rel.is_external or kind not in ("header", "footer"):
            continue
        part = rel.target_part
        element = getattr(part, "element", None)
        if element is None:
            continue
        inner_used = _referenced_ids(element)
        for rId, sub in list(part.rels.items()):
            kind = sub.reltype.rsplit("/", 1)[-1]
            if rId in inner_used or kind not in ("image", "hyperlink"):
                continue
            # A cleared donor footer keeps its mailto: relationship even
            # though no run points at it any more; drop it with the images.
            if sub.is_external:
                part.rels.pop(rId, None)
            else:
                part.drop_rel(rId)
            dropped += 1
    return dropped


def finish_document(
    doc: Document,
    *,
    title: str,
    azienda,
    branding: Branding,
    version: int | None,
    generated_at: datetime,
    cover_is_clean: bool = True,
    fill_cover: bool = False,
    cover_values: dict[str, str] | None = None,
) -> None:
    """Everything a generator must do before ``doc.save``: running header and
    footer on every section, honest file properties, no orphaned donor parts
    and — for documents opened from a donor template — the cover forms
    filled in."""
    if fill_cover:
        fill_cover_tables(doc, azienda=azienda, version=version, generated_at=generated_at, extra=cover_values)
    add_running_header_footer(
        doc,
        title=title,
        azienda=azienda,
        branding=branding,
        version=version,
        generated_at=generated_at,
        cover_is_clean=cover_is_clean,
    )
    set_core_properties(
        doc,
        title=title,
        azienda=azienda,
        branding=branding,
        generated_at=generated_at,
        version=version,
    )
    refresh_fields_on_open(doc)
    try:
        prune_orphan_parts(doc)
    except Exception:
        # Pruning is hygiene, never a reason to fail a generation.
        pass
