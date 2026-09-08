"""Shared page furniture for every generated document.

Document audit 2026-09-03 found three visual families shipping under one
product: code-built documents on US Letter with no header, footer or page
numbers; donor-template documents carrying a 2000s-era N2O letterhead in
their header/footer XML; and one-page stubs with no cover at all. This module
is the single place the cover, running header/footer, revision table, table
of contents and file properties are drawn, so every document looks like the
same consultancy produced it — and so an organization that uploads its own
logo gets it on every page of every document.

Palette and type scale live in :mod:`docx_utils` (``BRAND_*``, ``TYPE_SCALE``)
because the table helpers there need them too.

Cover redesign 2026-09-07: one layout for all documents — a consultancy
letterhead strip, a navy title band, the assessed company's identity and
revision tables and the stamp/signature boxes — with a running header (mark,
title | client) and a two-line footer (letterhead | Pagina X di Y, revision).
Documents opened from a donor template drop the donor's own cover first
(:func:`strip_donor_cover`) and take this one. The DVR Master uses the same
layout with the VERA mark as its hero and no consultancy identity anywhere
(a client requirement, see
docs/superpowers/plans/2026-08-03-dvr-master-luca-improvements.md).
"""

from __future__ import annotations

import copy
import re
from datetime import datetime

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from app.services.document_generator.branding import Branding, resolve_logo_source
from app.services.document_generator.docx_utils import (
    BRAND_DEEP,
    BRAND_LABEL,
    BRAND_LIGHT,
    BRAND_NAVY,
    BRAND_NAVY_HEX,
    BRAND_ON_NAVY,
    BRAND_RULE_HEX,
    BRAND_SLATE,
    BRAND_SURFACE_HEX,
    BRAND_WHITE,
    FONT_FAMILY,
    TRICOLORE_HEX,
    TYPE_SCALE,
    add_data_table,
    fill_label_table,
    format_sede,
    insert_in_order,
    reset_table_rows,
    set_table_borders,
    shade_cell,
)

# A4 with a binding-side margin; text width is 16.5 cm. The top margin holds
# the running header (mark + title line + hairline) and the bottom one the
# two-line footer, each 1 cm from the page edge.
PAGE_W_CM = 21.0
PAGE_H_CM = 29.7
MARGIN_TOP_CM = 2.3
MARGIN_BOTTOM_CM = 2.4
MARGIN_LEFT_CM = 2.5
MARGIN_RIGHT_CM = 2.0
TEXT_WIDTH_CM = PAGE_W_CM - MARGIN_LEFT_CM - MARGIN_RIGHT_CM

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
    """Set the font on a style including the East-Asian/complex-script slots,
    otherwise Word can fall back to Cambria/Times for headings."""
    style.font.name = name
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attr), name)


def _keep_with_next(style) -> None:
    ppr = style.element.get_or_add_pPr()
    for tag in ("w:keepNext", "w:keepLines"):
        for existing in ppr.findall(qn(tag)):
            ppr.remove(existing)
    after_keep_next = _PPR_ORDER[_PPR_ORDER.index("keepLines"):]
    insert_in_order(ppr, OxmlElement("w:keepNext"), tuple(after_keep_next))
    insert_in_order(ppr, OxmlElement("w:keepLines"), tuple(_PPR_ORDER[_PPR_ORDER.index("pageBreakBefore"):]))


def setup_document(doc: Document, *, landscape: bool = False) -> None:
    """A4, binding margins, Calibri body, navy headings that never orphan.

    Idempotent: safe to call on a document opened from a template too — it
    only rewrites page geometry and the ``Normal``/``Heading 1-3`` styles.
    """
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

    normal = doc.styles["Normal"]
    _set_style_font(normal, FONT_FAMILY)
    normal.font.size = Pt(TYPE_SCALE["body"])
    normal.font.color.rgb = BRAND_DEEP
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.08

    specs = {
        1: (TYPE_SCALE["h1"], BRAND_NAVY, 18, 6),
        2: (TYPE_SCALE["h2"], BRAND_NAVY, 14, 4),
        3: (TYPE_SCALE["h3"], BRAND_DEEP, 10, 2),
    }
    for level, (size, colour, before, after) in specs.items():
        try:
            style = doc.styles[f"Heading {level}"]
        except KeyError:
            continue
        _set_style_font(style, FONT_FAMILY)
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.italic = False
        style.font.color.rgb = colour
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


def _add_field(run, instruction: str, cached: str = "1") -> None:
    """Emit a Word field (PAGE, NUMPAGES, ...) with a cached result so the
    unrefreshed view is still sensible.

    The field is spread over five runs — begin, instruction, separate, result,
    end — each carrying ``run``'s formatting. That is the layout Word writes
    itself, and the one LibreOffice honours when it draws the result: with
    everything in one run it fell back to the paragraph's font for the number.
    """
    rpr = run._r.get_or_add_rPr()
    last = run._r

    def next_run():
        nonlocal last
        r = OxmlElement("w:r")
        r.append(copy.deepcopy(rpr))
        last.addnext(r)
        last = r
        return r

    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    run._r.append(begin)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    next_run().append(instr)
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    next_run().append(sep)
    text = OxmlElement("w:t")
    text.text = cached
    next_run().append(text)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    next_run().append(end)


# ---------------------------------------------------------------------------
# Table primitives — the cover is built from tables, because a shaded cell is
# the one block-colour device python-docx, Word and LibreOffice all agree on
# ---------------------------------------------------------------------------

_TBLPR_AFTER_BORDERS = ("shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription", "tblPrChange")
_TBLPR_AFTER_CELLMAR = ("tblLook", "tblCaption", "tblDescription", "tblPrChange")
_TBLPR_AFTER_WIDTH = ("jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription", "tblPrChange")
_TCPR_AFTER_BORDERS = ("shd", "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark", "headers", "cellIns", "cellDel", "cellMerge", "tcPrChange")
_RPR_AFTER_SPACING = ("w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath")


def _twips(cm: float) -> str:
    return str(int(round(cm * 567)))


def _body_blocks(doc: Document) -> list:
    """Body children in order, minus the trailing section properties."""
    return [el for el in doc.element.body if el.tag != qn("w:sectPr")]


def _text_width_cm(doc: Document) -> float:
    """Text width of the first section, or the A4 default when a bare
    document has no geometry yet."""
    try:
        section = doc.sections[0]
        width = section.page_width - section.left_margin - section.right_margin
        return width / 360000
    except (IndexError, TypeError):
        return TEXT_WIDTH_CM


def _gap(doc: Document, before_pt: float):
    """A one-point paragraph carrying vertical space. Tables have no spacing
    of their own, so the room between the cover's blocks lives here."""
    p = doc.add_paragraph()
    fmt = p.paragraph_format
    fmt.space_before = Pt(before_pt)
    fmt.space_after = Pt(0)
    fmt.line_spacing = Pt(1)
    p.add_run("").font.size = Pt(1)
    return p


def _set_run_font(run) -> None:
    """Pin the run to the brand face on every script slot. Documents opened
    from a donor template inherit that template's Normal (Times, mostly), and
    the cover and running furniture must not."""
    run.font.name = FONT_FAMILY
    rpr = run._r.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attr), FONT_FAMILY)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if fonts.get(qn(attr)) is not None:
            del fonts.attrib[qn(attr)]


def _run_spacing(run, pt: float) -> None:
    """Letter-spacing on one run (``w:spacing`` counts twentieths of a point)."""
    rpr = run._r.get_or_add_rPr()
    sp = OxmlElement("w:spacing")
    sp.set(qn("w:val"), str(int(pt * 20)))
    insert_in_order(rpr, sp, _RPR_AFTER_SPACING)


def _text_paragraph(
    container,
    text: str,
    *,
    size: float,
    bold: bool = False,
    italic: bool = False,
    colour: RGBColor | None = None,
    caps: bool = False,
    spacing: float | None = None,
    align=None,
    space_before: float = 0,
    space_after: float = 0,
    first: bool = False,
):
    """One run in one paragraph. ``first`` reuses the paragraph a new table
    cell is born with instead of adding a second one."""
    p = container.paragraphs[0] if first else container.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text.upper() if caps else text)
    _set_run_font(run)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if colour is not None:
        run.font.color.rgb = colour
    if spacing is not None:
        _run_spacing(run, spacing)
    return p


def _table_no_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    for existing in tbl_pr.findall(qn("w:tblBorders")):
        tbl_pr.remove(existing)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    insert_in_order(tbl_pr, borders, _TBLPR_AFTER_BORDERS)


def _table_width(table, cm: float) -> None:
    tbl_pr = table._tbl.tblPr
    width = tbl_pr.find(qn("w:tblW"))
    if width is None:
        width = OxmlElement("w:tblW")
        insert_in_order(tbl_pr, width, _TBLPR_AFTER_WIDTH)
    width.set(qn("w:w"), _twips(cm))
    width.set(qn("w:type"), "dxa")


def _table_cell_margins(table, *, top_cm: float = 0.0, bottom_cm: float = 0.0, left_cm: float = 0.0, right_cm: float = 0.0) -> None:
    tbl_pr = table._tbl.tblPr
    for existing in tbl_pr.findall(qn("w:tblCellMar")):
        tbl_pr.remove(existing)
    margins = OxmlElement("w:tblCellMar")
    for edge, cm in (("top", top_cm), ("left", left_cm), ("bottom", bottom_cm), ("right", right_cm)):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:w"), _twips(cm))
        el.set(qn("w:type"), "dxa")
        margins.append(el)
    insert_in_order(tbl_pr, margins, _TBLPR_AFTER_CELLMAR)


def _cell_borders(cell, edges: dict[str, tuple[str, int]]) -> None:
    """Borders on one cell: ``edges`` maps top/left/bottom/right to
    ``(colour_hex, size)`` with the size in eighths of a point; the edges not
    named are switched off."""
    tc_pr = cell._tc.get_or_add_tcPr()
    for existing in tc_pr.findall(qn("w:tcBorders")):
        tc_pr.remove(existing)
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        spec = edges.get(edge)
        if spec is None:
            el.set(qn("w:val"), "nil")
        else:
            colour, size = spec
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), str(size))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), colour)
        borders.append(el)
    insert_in_order(tc_pr, borders, _TCPR_AFTER_BORDERS)


def _row_height(row, cm: float, *, exact: bool) -> None:
    row.height = Cm(cm)
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY if exact else WD_ROW_HEIGHT_RULE.AT_LEAST


def _fixed_table(container, widths_cm: list[float], *, rows: int = 1):
    """A borderless fixed-layout table, centred, with no cell padding.
    ``container`` is the document or a cell (for the nested tricolore bar)."""
    table = container.add_table(rows=rows, cols=len(widths_cm))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for column, width_cm in zip(table.columns, widths_cm):
        column.width = Cm(width_cm)
        for cell in column.cells:
            cell.width = Cm(width_cm)
    _table_width(table, sum(widths_cm))
    _table_no_borders(table)
    _table_cell_margins(table)
    return table


def _move_to_top(doc: Document, count: int) -> None:
    """Move the last ``count`` body blocks to the front, order preserved."""
    body = doc.element.body
    blocks = _body_blocks(doc)
    for index, el in enumerate(blocks[len(blocks) - count:]):
        body.remove(el)
        body.insert(index, el)


def strip_donor_cover(
    doc: Document,
    *,
    stop_text: str | None = None,
    stop_before_table: bool = False,
    whole_body: bool = False,
    max_scan: int = 60,
) -> int:
    """Remove a donor template's own cover page.

    Deletes every leading body block up to — not including — the first one
    that ends the cover: a paragraph carrying a section break, a paragraph
    whose text is ``stop_text``, or (with ``stop_before_table``) the first
    table. ``whole_body`` says the donor body is nothing but its cover (the
    POS template) and clears it entirely. Otherwise nothing is removed when
    no boundary appears within ``max_scan`` blocks, so an unexpected
    template keeps its cover rather than losing its body. The donor's page
    frame around the cover section goes with it. Returns the number of
    blocks removed.
    """
    blocks = _body_blocks(doc)
    boundary = len(blocks) if whole_body else None
    for index, el in enumerate(blocks[:max_scan] if boundary is None else []):
        if el.tag == qn("w:tbl"):
            if stop_before_table:
                boundary = index
                break
            continue
        if el.find(f"{qn('w:pPr')}/{qn('w:sectPr')}") is not None:
            boundary = index
            break
        if stop_text is not None:
            text = "".join(t.text or "" for t in el.iter(qn("w:t")))
            if " ".join(text.split()).lower() == " ".join(stop_text.split()).lower():
                boundary = index
                break
    if boundary is None:
        return 0
    body = doc.element.body
    for el in blocks[:boundary]:
        body.remove(el)
    try:
        sect_pr = doc.sections[0]._sectPr
    except IndexError:
        sect_pr = None
    if sect_pr is not None:
        for frame in sect_pr.findall(qn("w:pgBorders")):
            sect_pr.remove(frame)
    return boundary


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------

def _letterhead_strip(doc: Document, branding: Branding, *, logo_width_cm: float, width_cm: float) -> None:
    """Consultancy mark on the left, firm name and letterhead lines ranged
    right, on a shared hairline."""
    table = _fixed_table(doc, [7.5, width_cm - 7.5])
    _table_cell_margins(table, bottom_cm=0.22)
    left, right = table.rows[0].cells
    for cell in (left, right):
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
        _cell_borders(cell, {"bottom": (BRAND_RULE_HEX, 6)})
    logo_src = resolve_logo_source(branding)
    logo_p = left.paragraphs[0]
    logo_p.paragraph_format.space_after = Pt(0)
    if logo_src is not None:
        try:
            logo_p.add_run().add_picture(logo_src, width=Cm(logo_width_cm))
        except Exception:
            # An unreadable upload must not break generation; the firm name
            # on the right still identifies the consultancy.
            pass
    _text_paragraph(
        right,
        (branding.firm_name or "").strip().upper(),
        size=9,
        bold=True,
        colour=BRAND_NAVY,
        align=WD_ALIGN_PARAGRAPH.RIGHT,
        first=True,
    )
    for line in _letterhead_lines(branding):
        _text_paragraph(right, line, size=TYPE_SCALE["small"], colour=BRAND_SLATE, align=WD_ALIGN_PARAGRAPH.RIGHT)


def _tiny(paragraph) -> None:
    """Collapse a paragraph Word insists on (after a nested table) to a point."""
    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.line_spacing = Pt(1)
    paragraph.add_run("").font.size = Pt(1)


def _title_band(doc: Document, *, eyebrow: str | None, title: str, subtitle: str | None, legal_basis: str | None, width_cm: float) -> None:
    """Navy band: eyebrow, title, subtitle, legal basis and the tricolore bar
    that sits under the N2O wordmark."""
    table = _fixed_table(doc, [width_cm])
    _table_cell_margins(table, top_cm=0.6, bottom_cm=0.5, left_cm=0.85, right_cm=0.85)
    cell = table.rows[0].cells[0]
    shade_cell(cell, BRAND_NAVY_HEX)
    first = True
    if eyebrow:
        _text_paragraph(cell, eyebrow, size=TYPE_SCALE["small"], colour=BRAND_LIGHT, caps=True, spacing=1.2, space_after=6, first=True)
        first = False
    last = _text_paragraph(cell, title, size=TYPE_SCALE["cover_title"], bold=True, colour=BRAND_WHITE, space_after=4, first=first)
    if subtitle:
        last = _text_paragraph(cell, subtitle, size=TYPE_SCALE["cover_subtitle"], colour=BRAND_ON_NAVY, space_after=2)
    if legal_basis:
        last = _text_paragraph(cell, legal_basis, size=TYPE_SCALE["h3"], italic=True, colour=BRAND_ON_NAVY)
    last.paragraph_format.space_after = Pt(9)
    bar = _fixed_table(cell, [0.85, 0.85, 0.85])
    bar.alignment = WD_TABLE_ALIGNMENT.LEFT
    _row_height(bar.rows[0], 0.12, exact=True)
    for segment, colour in zip(bar.rows[0].cells, TRICOLORE_HEX):
        shade_cell(segment, colour)
        _tiny(segment.paragraphs[0])
    _tiny(cell.paragraphs[-1])


def _identity_rows(azienda) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    legale = format_sede(azienda, "legale")
    if legale != "—":
        rows.append(("Sede legale", legale))
    operativa = format_sede(azienda, "operativa")
    if operativa not in ("—", legale):
        rows.append(("Sede operativa", operativa))
    piva = str(getattr(azienda, "partita_iva", None) or "").strip()
    if piva:
        rows.append(("Partita IVA", piva))
    ateco = str(getattr(azienda, "codice_ateco", None) or "").strip()
    if ateco:
        rows.append(("Codice ATECO", ateco))
    return rows


def _label_table(doc: Document, rows: list[tuple[str, str]], *, width_cm: float):
    label_cm = 4.2
    table = _fixed_table(doc, [label_cm, width_cm - label_cm], rows=len(rows))
    _table_cell_margins(table, top_cm=0.09, bottom_cm=0.09, left_cm=0.2, right_cm=0.2)
    set_table_borders(table)
    for row, (label, value) in zip(table.rows, rows):
        _row_height(row, 0.62, exact=False)
        label_cell, value_cell = row.cells
        _text_paragraph(label_cell, label, size=TYPE_SCALE["table"], bold=True, colour=BRAND_LABEL, first=True)
        _text_paragraph(value_cell, value, size=TYPE_SCALE["table"], colour=BRAND_DEEP, first=True)
        shade_cell(label_cell, BRAND_SURFACE_HEX)
    return table


def _signature_boxes(doc: Document, *, width_cm: float):
    """Two labelled boxes: the employer's stamp and signature, the RSPP's
    signature — the cover is where the paper copy gets signed."""
    box_cm = (width_cm - 0.7) / 2
    table = _fixed_table(doc, [box_cm, 0.7, box_cm], rows=2)
    _table_cell_margins(table, top_cm=0.05, bottom_cm=0.12)
    labels = ("Timbro e firma del Datore di Lavoro", "Firma dell'RSPP")
    for cell, label in zip((table.rows[0].cells[0], table.rows[0].cells[2]), labels):
        _text_paragraph(cell, label, size=TYPE_SCALE["small"], colour=BRAND_SLATE, caps=True, spacing=1.2, first=True)
    _row_height(table.rows[1], 1.9, exact=True)
    edges = {edge: (BRAND_RULE_HEX, 6) for edge in ("top", "left", "bottom", "right")}
    for cell in (table.rows[1].cells[0], table.rows[1].cells[2]):
        _cell_borders(cell, edges)
    return table


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
    logo_width_cm: float = 4.0,
    show_letterhead: bool = True,
    hero_image=None,
    hero_width_cm: float = 8.0,
    hero_fallback_text: str | None = None,
    show_signatures: bool = True,
    at_top: bool = False,
    page_break: bool = True,
) -> int:
    """The cover every document shares.

    Top to bottom: the consultancy letterhead strip (the organization's
    uploaded logo, else the bundled N2O mark, with the firm's letterhead
    lines ranged right); an optional hero image (the DVR's VERA mark); the
    navy title band with eyebrow, title, subtitle and legal basis; the
    assessed company's name and identity table (seats, P.IVA, ATECO); the
    revision table numbered like the Storico; and the stamp/signature boxes.

    Every field degrades to nothing when the data is missing; the cover never
    prints a placeholder. ``show_letterhead=False`` leaves the consultancy off
    the page entirely (the DVR Master, by client requirement). With
    ``at_top`` the cover is moved in front of everything already in the body
    — how a document opened from a donor template gets it — and
    ``page_break`` says whether to end it with a page break (not when a
    section break already follows). Returns the number of body blocks added.
    """
    width_cm = _text_width_cm(doc)
    before = len(_body_blocks(doc))

    if show_letterhead:
        _letterhead_strip(doc, branding, logo_width_cm=logo_width_cm, width_cm=width_cm)

    if hero_image is not None:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(22 if show_letterhead else 6)
        p.paragraph_format.space_after = Pt(18)
        run = p.add_run()
        try:
            run.add_picture(hero_image, width=Cm(hero_width_cm))
        except Exception:
            if hero_fallback_text:
                run.text = hero_fallback_text
                run.font.size = Pt(14)
                run.font.italic = True
                run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    else:
        _gap(doc, 78 if show_letterhead else 24)

    _title_band(doc, eyebrow=eyebrow, title=title, subtitle=subtitle, legal_basis=legal_basis, width_cm=width_cm)

    ragione = (getattr(azienda, "ragione_sociale", None) or "").strip()
    _text_paragraph(doc, "Azienda", size=TYPE_SCALE["small"], colour=BRAND_SLATE, caps=True, spacing=1.2, space_before=24, space_after=3)
    _text_paragraph(doc, ragione.upper() if ragione else "—", size=TYPE_SCALE["cover_client"], bold=True, colour=BRAND_DEEP, space_after=6)
    rows = _identity_rows(azienda)
    if rows:
        _label_table(doc, rows, width_cm=width_cm)

    _gap(doc, 18)
    revisions = add_data_table(
        doc,
        ["Rev.", "Motivazione", "Data"],
        [[revision_label(version), revision_motivation(version), generated_at.strftime("%d/%m/%Y")]],
        column_widths_cm=[2.0, width_cm - 6.0, 4.0],
    )
    for row in revisions.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    _set_run_font(run)

    if show_signatures:
        _gap(doc, 34)
        _signature_boxes(doc, width_cm=width_cm)

    if page_break:
        doc.add_page_break()

    added = len(_body_blocks(doc)) - before
    if at_top:
        _move_to_top(doc, added)
    return added


def _tax_line(branding: Branding) -> str | None:
    """``P.IVA … · C.F. …`` from the parts present, or None."""
    tax = []
    if branding.partita_iva:
        tax.append(f"P.IVA {branding.partita_iva}")
    if branding.codice_fiscale and branding.codice_fiscale != branding.partita_iva:
        tax.append(f"C.F. {branding.codice_fiscale}")
    return " · ".join(tax) or None


def _letterhead_lines(branding: Branding) -> list[str]:
    lines: list[str] = []
    addr = branding.address_line()
    if addr:
        lines.append(addr)
    tax = _tax_line(branding)
    if tax:
        lines.append(tax)
    contact = branding.contact_line()
    if contact:
        lines.append(contact)
    if branding.rspp_nome:
        lines.append(f"RSPP: {branding.rspp_nome}")
    return lines


# ---------------------------------------------------------------------------
# Running header / footer
# ---------------------------------------------------------------------------

def _clear(container) -> None:
    """Empty a header/footer container so re-application is idempotent."""
    for p in list(container.paragraphs):
        p._p.getparent().remove(p._p)
    for t in list(container.tables):
        t._tbl.getparent().remove(t._tbl)


def _two_sided(container, left: list[tuple[str, dict]], right: list[tuple[str, dict]], *, width_cm: float, new_paragraph: bool = False):
    """One paragraph with left content and a right-aligned tab: the classic
    running-head layout without a table. A part is ``(text, fmt)``; ``fmt``
    may carry ``field`` (PAGE, NUMPAGES) or ``picture`` (a path or stream
    embedded at ``height_cm``) instead of text."""
    if new_paragraph or not container.paragraphs:
        p = container.add_paragraph()
    else:
        p = container.paragraphs[0]
    p.paragraph_format.tab_stops.add_tab_stop(Cm(width_cm), WD_TAB_ALIGNMENT.RIGHT)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)

    def emit(parts):
        for text, fmt in parts:
            run = p.add_run()
            picture = fmt.get("picture")
            if picture is not None:
                try:
                    run.add_picture(picture, height=Cm(fmt.get("height_cm", 0.55)))
                except Exception:
                    # An unreadable logo upload leaves the header text-only.
                    pass
                continue
            _set_run_font(run)
            run.font.size = Pt(fmt.get("size", TYPE_SCALE["small"]))
            run.bold = fmt.get("bold", False)
            run.font.color.rgb = fmt.get("colour", BRAND_SLATE)
            field = fmt.get("field")
            if field:
                _add_field(run, field, fmt.get("cached", "1"))
            else:
                run.text = text

    emit(left)
    tab = p.add_run()
    tab.text = chr(9)
    emit(right)
    return p


def _write_running(header, footer, *, title: str, ragione: str, branding: Branding, rev: str, width_cm: float, header_logo: bool) -> None:
    """Header: mark + title | client. Footer: firm · address · P.IVA | Pagina
    X di Y, then contacts | Rev. NN del date."""
    left: list[tuple[str, dict]] = []
    logo_src = resolve_logo_source(branding) if header_logo else None
    if logo_src is not None:
        left.append(("", {"picture": logo_src, "height_cm": 0.55}))
        left.append(("   ", {"size": 9}))
    left.append((title, {"bold": True, "colour": BRAND_NAVY, "size": 9}))
    hp = _two_sided(header, left, [(ragione, {"colour": BRAND_SLATE, "size": 9})], width_cm=width_cm)
    _paragraph_border(hp, "bottom", BRAND_RULE_HEX, size=6, space=4)

    first_left: list[tuple[str, dict]] = [((branding.firm_name or "").strip().upper(), {"bold": True, "colour": BRAND_NAVY})]
    for bit in (branding.address_line(), _tax_line(branding)):
        if bit:
            first_left += [(" · ", {}), (bit, {})]
    page = {"bold": True, "colour": BRAND_DEEP}
    first_right = [
        ("Pagina ", page),
        ("", {"field": "PAGE", **page}),
        (" di ", page),
        ("", {"field": "NUMPAGES", **page}),
    ]
    fp = _two_sided(footer, first_left, first_right, width_cm=width_cm)
    _paragraph_border(fp, "top", BRAND_RULE_HEX, size=6, space=4)
    contact = branding.contact_line()
    _two_sided(footer, [(contact, {})] if contact else [], [(rev, {})], width_cm=width_cm, new_paragraph=True)


def add_running_header_footer(
    doc: Document,
    *,
    title: str,
    azienda,
    branding: Branding,
    version: int | None,
    generated_at: datetime,
    cover_is_clean: bool = True,
    header_logo: bool = True,
) -> None:
    """Header: consultancy mark, document title | client. Footer: letterhead
    line | Pagina X di Y, then contacts | Rev. NN del date.

    Applied to every section; with ``cover_is_clean`` the first page of the
    first section (the cover) gets no header/footer. Content is written fresh
    into the default, first-page and even-page header/footer parts, replacing
    whatever a donor template carried there — this is how the legacy N2O
    letterhead leaves the template family. ``header_logo=False`` keeps the
    mark out of the header (the DVR Master embeds only the VERA asset).
    """
    ragione = (getattr(azienda, "ragione_sociale", None) or "").strip()
    rev = f"Rev. {revision_label(version)} del {generated_at.strftime('%d/%m/%Y')}"
    for index, section in enumerate(doc.sections):
        width_cm = (section.page_width - section.left_margin - section.right_margin) / 360000
        section.different_first_page_header_footer = bool(cover_is_clean and index == 0)
        # Donor templates set the footer distance to 0 (DUVRI) so their
        # letterhead sat on the page edge; the running header/footer needs
        # room, and a 0 distance is also where renderers start to struggle.
        for attr in ("header_distance", "footer_distance"):
            current = getattr(section, attr, None)
            if current is None or current < Cm(0.8):
                setattr(section, attr, Cm(1.0))
        # Room for the mark in the header and the two footer lines: donor
        # sections arrive with margins as tight as 0.75 cm.
        for attr, minimum in (("top_margin", MARGIN_TOP_CM), ("bottom_margin", MARGIN_BOTTOM_CM)):
            current = getattr(section, attr, None)
            if current is None or current < Cm(minimum):
                setattr(section, attr, Cm(minimum))
        parts = (
            section.header, section.footer,
            section.first_page_header, section.first_page_footer,
            section.even_page_header, section.even_page_footer,
        )
        for container in parts:
            container.is_linked_to_previous = False
            _clear(container)

        running = dict(title=title, ragione=ragione, branding=branding, rev=rev, width_cm=width_cm, header_logo=header_logo)
        _write_running(section.header, section.footer, **running)
        # Even pages only matter when the document asks for odd/even headers;
        # writing them keeps a donor's evenAndOddHeaders setting harmless.
        _write_running(section.even_page_header, section.even_page_footer, **running)

        if section.different_first_page_header_footer:
            # Leave the cover clean: an empty paragraph is required so Word does
            # not fall back to the default header on page one.
            section.first_page_header.add_paragraph("")
            section.first_page_footer.add_paragraph("")
        else:
            _write_running(section.first_page_header, section.first_page_footer, **running)


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
        doc.add_heading(heading, level=level)
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
    doc.add_heading(title, level=1)
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
    r = placeholder.add_run("Indice in fase di aggiornamento.")
    r.font.size = Pt(TYPE_SCALE["body"])
    r.italic = True
    r.font.color.rgb = BRAND_SLATE

    end_p = doc.add_paragraph()
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_p.add_run()._r.append(end)

    try:
        settings_root = doc.settings.element
        if settings_root.find(qn("w:updateFields")) is None:
            uf = OxmlElement("w:updateFields")
            uf.set(qn("w:val"), "true")
            settings_root.append(uf)
    except Exception:
        pass

    doc.add_page_break()
    return field_start_p, end_p


def finalize_toc(doc: Document, field_start_p, end_p) -> None:
    """Rewrite the TOC's cached body from the Heading 1-3 paragraphs that
    follow it, so the document is navigable even before Word refreshes."""
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

    for el in children[start_idx + 1 : end_idx]:
        body.remove(el)
    for level, text in entries:
        new_p = doc.add_paragraph()
        indent = (level - 1) * 0.5
        if indent:
            new_p.paragraph_format.left_indent = Cm(indent)
        new_p.paragraph_format.space_after = Pt(2)
        run = new_p.add_run(text)
        run.font.size = Pt(TYPE_SCALE["body"] if level == 1 else TYPE_SCALE["table"])
        run.bold = level == 1
        run.font.color.rgb = BRAND_NAVY if level == 1 else BRAND_DEEP
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
    header_logo: bool = True,
) -> None:
    """Everything a generator must do before ``doc.save``: running header and
    footer on every section, honest file properties, no orphaned donor parts
    and — for documents opened from a donor template — the cover forms
    filled in. ``header_logo=False`` keeps the consultancy mark out of the
    running header (the DVR Master carries only the VERA asset)."""
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
        header_logo=header_logo,
    )
    set_core_properties(
        doc,
        title=title,
        azienda=azienda,
        branding=branding,
        generated_at=generated_at,
        version=version,
    )
    try:
        prune_orphan_parts(doc)
    except Exception:
        # Pruning is hygiene, never a reason to fail a generation.
        pass
