"""Shared helpers for document generators.

Keeps each generator small and focused by extracting common docx
manipulation patterns (placeholder substitution, table helpers,
heading styling, color palettes, etc.).
"""

from __future__ import annotations

import math
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsmap, qn
from docx.shared import Cm, Pt, RGBColor, Twips
from docx.text.paragraph import Paragraph


# ---------------------------------------------------------------------------
# Design tokens — one look for all 17 documents: N2O's DVR model of
# 2026-10-20 (docs/superpowers/specs/2026-11-10-document-layout-redesign-design.md
# §4.1.1). The navy is the web app's --color-primary, so product and paperwork
# still read as one family; the table blue and the black grid come from the
# model.
# ---------------------------------------------------------------------------

BRAND_NAVY = RGBColor(0x00, 0x3D, 0x74)      # titles, labels, header text
BRAND_NAVY_HEX = "003D74"
BRAND_TABLE_HEADER = RGBColor(0x4F, 0x81, 0xBD)  # table header rows, white text
BRAND_TABLE_HEADER_HEX = "4F81BD"
BRAND_DEEP = RGBColor(0x06, 0x1B, 0x31)      # body ink
BRAND_SLATE = RGBColor(0x64, 0x74, 0x8D)     # footer text, captions, secondary lines
BRAND_SURFACE_HEX = "F6F9FC"                 # zebra rows, light label cells
BRAND_RULE_HEX = "C9D3DF"                    # header and footer hairlines only
NOTE_GREY = RGBColor(0x66, 0x66, 0x66)       # italic notes under tables
TABLE_BORDER_HEX = "auto"                    # tables: thin black grid, as in Word's Table Grid
TABLE_BORDER_SIZE = 4                        # eighths of a point: ½ pt

# Arial in every slot. N2O asked for a document that does not change between
# Windows and Mac (2026-07-27); the model's Avenir Next LT Pro is a Microsoft
# 365 cloud font that LibreOffice, Google Docs and Word without 365 replace.
# Liberation Sans carries Arial's metrics where Arial itself is missing.
FONT_FAMILY = "Arial"
FONT_SLOTS = ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs")
# A theme attribute wins over the explicit name in Word, so a slot left on
# "minorHAnsi" would print in the theme's Calibri whatever w:ascii says.
THEME_FONT_ATTRS = ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme")
# Fonts whose characters are pictures (lower case): Symbol and the dingbat
# faces map their glyphs to code points of their own, so a bullet or a check
# box set in one of them prints as a different character in any other font.
SYMBOL_FONTS = frozenset({"symbol", "wingdings", "wingdings 2", "wingdings 3", "webdings"})

# Type scale in points. Roles first (the model's hierarchy, with 10 pt tables:
# at 12 pt the five-column risk tables break words mid-word), then the legacy
# keys generators still read until they move to roles.
TYPE_SCALE = {
    "body": 12,
    "table": 10,
    "table_header": 10,
    "section_title": 25,
    "sub_title": 12,
    "part_label": 9,
    "front_heading": 14,
    "cover_title": 26,
    "header": 9,
    "footer": 8.5,
    "note": 10,
    # Legacy keys.
    "h1": 16,
    "h2": 13,
    "h3": 12,
    "cover_subtitle": 12,
    "cover_client": 16,
    "small": 8.5,
}

# Risk scale = the app's risk chips (--color-risk-*), so a GRAVE cell in the
# document is the same orange as the GRAVE chip on screen.
RISK_COLORS = {
    "ACCETTABILE": RGBColor(0x15, 0xBE, 0x53),
    "MODESTO": RGBColor(0xF5, 0x9E, 0x0B),
    "GRAVE": RGBColor(0xF9, 0x73, 0x16),
    "GRAVISSIMO": RGBColor(0xEF, 0x44, 0x44),
    "BASSO": RGBColor(0x15, 0xBE, 0x53),
    "MEDIO": RGBColor(0xF5, 0x9E, 0x0B),
    "ALTO": RGBColor(0xEF, 0x44, 0x44),
    "VERDE": RGBColor(0x15, 0xBE, 0x53),
    "GIALLO": RGBColor(0xF5, 0x9E, 0x0B),
    "ROSSO": RGBColor(0xEF, 0x44, 0x44),
}


# ---------------------------------------------------------------------------
# Address formatting (shared across all generators)
# ---------------------------------------------------------------------------

def format_comune(cap, citta, provincia) -> str:
    """Build the Italian comune segment ``CAP Comune (PROV)``.

    Any component may be missing; a blank comune never yields an orphan
    ``(PROV)``. Returns ``"—"`` when nothing is available.
    """
    seg = (citta or "").strip()
    cap = (cap or "").strip()
    provincia = (provincia or "").strip()
    if cap and seg:
        seg = f"{cap} {seg}"
    elif cap:
        seg = cap
    if provincia and seg:
        seg = f"{seg} ({provincia})"
    return seg or "—"


def format_sede(azienda, which: str = "legale") -> str:
    """Format a full Italian seat address as ``Via, CAP Comune (PROV)``.

    ``which`` selects the field family: ``"legale"`` reads
    ``sede_legale_via`` / ``sede_legale_citta`` / ``cap_legale`` /
    ``provincia_legale``; ``"operativa"`` the operative equivalents.
    Audit F-301 (2026-05-31): generators previously emitted only
    ``via, comune``, silently dropping the CAP and province held on the row.
    """
    via = (getattr(azienda, f"sede_{which}_via", None) or "").strip()
    seg = format_comune(
        getattr(azienda, f"cap_{which}", None),
        getattr(azienda, f"sede_{which}_citta", None),
        getattr(azienda, f"provincia_{which}", None),
    )
    parts = [p for p in [via, seg if seg != "—" else ""] if p]
    return ", ".join(parts) if parts else "—"

# Legacy names kept for the generators that import them. HEADER_BG stays navy:
# the DVR also colours its headings with it. Kit tables use
# BRAND_TABLE_HEADER_HEX through style_header_row.
HEADER_BG = BRAND_NAVY
HEADER_BG_HEX = BRAND_NAVY_HEX
HEADER_TEXT = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF6, 0xF9, 0xFC)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BACKEND_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = BACKEND_ROOT.parent


def _resolve_templates_dir() -> Path:
    # On Render the service root is `backend/`, so the sibling `templates/`
    # folder only exists if the buildCommand copied it in. Prefer that
    # in-backend copy; fall back to the repo-root location for local dev.
    for candidate in (BACKEND_ROOT / "templates", REPO_ROOT / "templates"):
        if candidate.is_dir():
            return candidate
    return REPO_ROOT / "templates"


TEMPLATES_DIR = _resolve_templates_dir()
# Artwork extracted from N2O's DVR model (scripts/extract_document_art.py);
# design.ART maps keys to the files.
DOCUMENT_ART_DIR = BACKEND_ROOT / "assets" / "document_art"
# The default document logo when an organization has not uploaded its own:
# the VERA ITALIA mark of the model's footer. assets/logo.png is retired.
LOGO_PATH = DOCUMENT_ART_DIR / "vera_italia_mark.png"


def slugify(text: str, max_length: int = 40) -> str:
    """Produce a filesystem-safe slug from free text."""
    lowered = (text or "").lower()
    replaced = re.sub(r"[^a-z0-9]+", "_", lowered)
    collapsed = re.sub(r"_+", "_", replaced).strip("_")
    if not collapsed:
        collapsed = "azienda"
    return collapsed[:max_length].rstrip("_") or "azienda"


# ---------------------------------------------------------------------------
# Cell shading (table header background)
# ---------------------------------------------------------------------------

def insert_in_order(parent, child, successors: tuple[str, ...]) -> None:
    """Insert ``child`` into ``parent`` before the first existing element
    whose tag is in ``successors`` (schema order), else append. Word
    validates child order inside property elements; appending blindly can
    make it report the file as corrupt."""
    tags = {qn(f"w:{t}") for t in successors}
    anchor = next((el for el in parent if el.tag in tags), None)
    if anchor is not None:
        anchor.addprevious(child)
    else:
        parent.append(child)


def shade_cell(cell, color_hex: str) -> None:
    """Set background shading on a table cell via raw w:shd XML.

    Replaces any shading already on the cell: zebra striping is applied by
    :func:`add_data_table` first and a generator may then colour a risk cell,
    and the last call must win deterministically (stacked ``w:shd`` elements
    render differently in Word and LibreOffice).
    """
    from docx.oxml import OxmlElement
    tc_pr = cell._tc.get_or_add_tcPr()
    for existing in tc_pr.findall(qn("w:shd")):
        tc_pr.remove(existing)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex)
    insert_in_order(tc_pr, shd, ("noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark", "headers", "cellIns", "cellDel", "cellMerge", "tcPrChange"))


def set_font_slots(rfonts, name: str = FONT_FAMILY) -> None:
    """Point every slot of a ``w:rFonts`` element at ``name``.

    Theme attributes are removed first: Word reads ``w:asciiTheme`` before
    ``w:ascii``, so a heading style that keeps "majorHAnsi" prints in the
    theme font whatever name it also carries.
    """
    for attr in THEME_FONT_ATTRS:
        rfonts.attrib.pop(qn(attr), None)
    for attr in FONT_SLOTS:
        rfonts.set(qn(attr), name)


def set_run_font(
    run,
    *,
    size: float | None = None,
    bold: bool | None = None,
    italic: bool | None = None,
    color: RGBColor | None = None,
    caps: bool | None = None,
):
    """Arial on all four slots of ``run``, plus whichever of size, weight,
    slant, colour and capitals are given. Every run the kit writes goes
    through here, so a kit table keeps its look inside a donor template whose
    own styles still name another font."""
    set_font_slots(run._r.get_or_add_rPr().get_or_add_rFonts())
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    if caps is not None:
        run.font.all_caps = caps
    return run


def style_header_row(row, bg_hex: str = BRAND_TABLE_HEADER_HEX, text_color: RGBColor = HEADER_TEXT) -> None:
    """Bold white text on the table-header blue. The row repeats on every page
    the table spans, so a long table never prints headless, and never splits."""
    from docx.oxml import OxmlElement
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:tblHeader")) is None:
        insert_in_order(tr_pr, OxmlElement("w:tblHeader"), ("tblCellSpacing", "jc", "hidden", "ins", "del", "trPrChange"))
    keep_row_together(row)
    for cell in row.cells:
        shade_cell(cell, bg_hex)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                set_run_font(run, size=TYPE_SCALE["table_header"], bold=True, color=text_color)


# ---------------------------------------------------------------------------
# Placeholder replacement — visit every paragraph in the document (including
# paragraphs in tables) and do straight string substitution across runs.
# ---------------------------------------------------------------------------

def replace_in_paragraph(paragraph, replacements: dict[str, str]) -> None:
    """Replace keys with values inside a single paragraph.

    Runs may split a placeholder across multiple parts, so first join and
    then redistribute. We rewrite the paragraph text in the first run and
    clear subsequent runs — this loses per-run formatting on replaced
    paragraphs, which is acceptable for simple placeholder fields.
    """
    text = paragraph.text
    changed = False
    for k, v in replacements.items():
        if k in text:
            text = text.replace(k, str(v))
            changed = True
    if changed:
        if paragraph.runs:
            paragraph.runs[0].text = text
            for run in paragraph.runs[1:]:
                run.text = ""
        else:
            paragraph.add_run(text)


def replace_placeholders(doc: Document, replacements: dict[str, str]) -> None:
    """Walk every paragraph (body + tables + headers/footers) and replace."""
    for p in doc.paragraphs:
        replace_in_paragraph(p, replacements)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    replace_in_paragraph(p, replacements)
    for section in doc.sections:
        for hf in (section.header, section.footer):
            for p in hf.paragraphs:
                replace_in_paragraph(p, replacements)


def scrub_body(
    doc: Document,
    replacements: dict[str, str],
    *,
    drop_paragraph_markers: Iterable[str] = (),
) -> int:
    """Body-only scrub for legacy templates built from a real completed client
    document that still carry that *origin* company's identity in the body.

    Several attachment templates (Stress, Gestanti, …) were authored by filling
    a real assessment, so the donor company's name/address/declaration print as
    the *assessed* subject. The page header/footer carries the consultancy's own
    letterhead (intentional branding) — this scrub therefore touches ONLY the
    body (``doc.paragraphs`` + table cells), never ``section.header/footer``.

    - ``drop_paragraph_markers``: body paragraphs whose text contains any of
      these substrings (case-insensitive) are removed entirely — use for donor
      free-prose (e.g. a company self-description) that can't be safely
      string-substituted to the client.
    - ``replacements``: case-insensitive literal swaps applied to surviving body
      paragraphs + table cells — use for structured donor identity → client data.

    Returns the number of paragraphs dropped (for logging/verification).
    """
    dropped = 0
    if drop_paragraph_markers:
        markers = [m.lower() for m in drop_paragraph_markers]
        for p in list(doc.paragraphs):
            low = (p.text or "").lower()
            if any(m in low for m in markers):
                p._p.getparent().remove(p._p)
                dropped += 1

    compiled = [
        (re.compile(re.escape(k), re.IGNORECASE), str(v)) for k, v in replacements.items()
    ]

    def _scrub(paragraph) -> None:
        text = paragraph.text
        if not text:
            return
        new = text
        for rx, val in compiled:
            new = rx.sub(lambda _m, _v=val: _v, new)
        if new != text:
            if paragraph.runs:
                paragraph.runs[0].text = new
                for run in paragraph.runs[1:]:
                    run.text = ""
            else:
                paragraph.add_run(new)

    for p in doc.paragraphs:
        _scrub(p)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _scrub(p)
    return dropped


def scrub_n2o_legacy_donor(
    doc: Document, azienda, *, drop_paragraph_markers: Iterable[str] = ()
) -> int:
    """Body-only scrub of the N2O origin-company identity baked into the legacy
    attachment templates (Stress, Gestanti) that were authored from a real N2O
    self-assessment. Swaps the donor's name / declarant / seat addresses for the
    client's, leaving the consultancy letterhead (header/footer) intact.

    The donor constants below are the literal strings found in those two
    templates (verified 2026-05-31). ``drop_paragraph_markers`` is forwarded to
    :func:`scrub_body` for donor free-prose that can't be string-substituted.
    """
    rs = azienda.ragione_sociale or ""
    legale = format_comune(
        getattr(azienda, "cap_legale", None),
        getattr(azienda, "sede_legale_citta", None),
        getattr(azienda, "provincia_legale", None),
    )
    oper = format_comune(
        getattr(azienda, "cap_operativa", None),
        getattr(azienda, "sede_operativa_citta", None),
        getattr(azienda, "provincia_operativa", None),
    )
    legale = "" if legale == "—" else legale
    oper = "" if oper == "—" else oper
    via_legale = getattr(azienda, "sede_legale_via", None) or ""
    via_oper = getattr(azienda, "sede_operativa_via", None) or via_legale
    return scrub_body(
        doc,
        {
            "N2O SRL": rs,
            "N2O S.R.L.": rs,
            "CIARAMITARO AMALIA": "",
            "VIA DEI CHIOSI 4": via_legale,
            "VIA MONZA 107/30": via_oper,
            "GORGONZOLA (MI)": legale,
            "GESSATE (MI)": oper,
        },
        drop_paragraph_markers=drop_paragraph_markers,
    )


# ---------------------------------------------------------------------------
# Simple heading/paragraph helpers
# ---------------------------------------------------------------------------

def add_heading(doc: Document, text: str, level: int = 1) -> Paragraph:
    """One heading paragraph in the ``Heading N`` style (``Title`` for level
    0), whether or not the document defines that style.

    Donor templates lack some levels (Gestanti and PEE azienda have no
    Heading 2). Without the style the paragraph stays Normal with bold
    text, 14 pt at level 1 and 12 pt below. python-docx's ``add_heading``
    appends the paragraph and its text *before* it looks the style up, so
    falling back after it raised printed every such heading twice.
    """
    paragraph = doc.add_paragraph(text)
    try:
        paragraph.style = "Title" if level == 0 else f"Heading {level}"
    except (KeyError, ValueError):
        # KeyError: no such style; ValueError: the name is not a paragraph style.
        for run in paragraph.runs:
            run.bold = True
            run.font.size = Pt(14 if level == 1 else 12)
    return paragraph


def add_paragraph(doc: Document, text: str, *, bold: bool = False, italic: bool = False, size: int = 11) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    return p


def add_consultancy_letterhead(doc: Document, branding, *, center: bool = True) -> None:
    """Render the consultancy's letterhead text block from ``branding``.

    Prints the firm name plus whatever optional letterhead detail is present
    (address, P.IVA / C.F., contacts, RSPP). Renders nothing beyond the firm
    name when the org hasn't filled the rest in. ``branding`` is a
    :class:`~app.services.document_generator.branding.Branding`.
    """
    align = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    gray = BRAND_SLATE

    name_p = doc.add_paragraph()
    name_p.alignment = align
    name_run = name_p.add_run((branding.firm_name or "").upper())
    name_run.bold = True
    name_run.font.size = Pt(TYPE_SCALE["body"])
    name_run.font.color.rgb = BRAND_NAVY

    lines: list[str] = []
    addr = branding.address_line()
    if addr:
        lines.append(addr)
    tax_bits = []
    if branding.partita_iva:
        tax_bits.append(f"P.IVA {branding.partita_iva}")
    if branding.codice_fiscale and branding.codice_fiscale != branding.partita_iva:
        tax_bits.append(f"C.F. {branding.codice_fiscale}")
    if tax_bits:
        lines.append(" · ".join(tax_bits))
    contact = branding.contact_line()
    if contact:
        lines.append(contact)
    if branding.rspp_nome:
        lines.append(f"RSPP: {branding.rspp_nome}")

    for text in lines:
        p = doc.add_paragraph()
        p.alignment = align
        run = p.add_run(text)
        run.font.size = Pt(8)
        run.font.color.rgb = gray


def _safe_table_style(table) -> None:
    """Apply Table Grid if available, otherwise apply manual cell borders."""
    try:
        table.style = "Table Grid"
    except KeyError:
        _apply_cell_borders_all(table)


def _apply_cell_borders_all(table) -> None:
    """Draw thin black borders on every cell (fallback when 'Table Grid' absent)."""
    from docx.oxml import OxmlElement
    for row in table.rows:
        for cell in row.cells:
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_borders = tc_pr.find(qn("w:tcBorders"))
            if tc_borders is None:
                tc_borders = OxmlElement("w:tcBorders")
                # Before any shading or alignment the cell already carries:
                # tcBorders precedes shd and vAlign in CT_TcPr.
                insert_in_order(tc_pr, tc_borders, ("shd", "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark", "headers", "cellIns", "cellDel", "cellMerge", "tcPrChange"))
            for edge in ("top", "left", "bottom", "right"):
                b = OxmlElement(f"w:{edge}")
                b.set(qn("w:val"), "single")
                b.set(qn("w:sz"), str(TABLE_BORDER_SIZE))
                b.set(qn("w:color"), TABLE_BORDER_HEX)
                tc_borders.append(b)


def set_table_borders(table, color_hex: str = TABLE_BORDER_HEX, size: int = TABLE_BORDER_SIZE) -> None:
    """Single borders on every edge, inside and out: ½ pt black by default,
    the Table Grid look of N2O's model. ``size`` is in eighths of a point.

    Written on the table itself so the grid survives a document whose
    template defines Table Grid differently (or not at all).
    """
    from docx.oxml import OxmlElement
    tbl_pr = table._tbl.tblPr
    for existing in tbl_pr.findall(qn("w:tblBorders")):
        tbl_pr.remove(existing)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), str(size))
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), color_hex)
        borders.append(b)
    # Word validates child order inside tblPr: tblBorders must precede shd,
    # tblLayout, tblCellMar, tblLook. Insert before the first of those.
    successors = [qn(f"w:{t}") for t in ("shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription")]
    anchor = next((child for child in tbl_pr if child.tag in successors), None)
    if anchor is not None:
        anchor.addprevious(borders)
    else:
        tbl_pr.append(borders)


def keep_row_together(row) -> None:
    """Forbid a row from splitting across a page break."""
    from docx.oxml import OxmlElement
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:cantSplit")) is None:
        insert_in_order(tr_pr, OxmlElement("w:cantSplit"), ("trHeight", "tblHeader", "tblCellSpacing", "jc", "hidden", "ins", "del", "trPrChange"))


# Label column of a key/value table: (fill, label text colour).
_KV_VARIANTS = {
    "blue": (BRAND_TABLE_HEADER_HEX, HEADER_TEXT),   # Anagrafica, environment identity
    "light": (BRAND_SURFACE_HEX, BRAND_NAVY),        # identity strips
}

# A row is kept on one page only while it is short. A keep-together row
# taller than a page makes LibreOffice loop forever (commit e0875fa).
_KEEP_TOGETHER_MAX_CHARS = 400
_KEEP_TOGETHER_MAX_LINES = 8

# Cells whose whole text is a number or a dash are centred (spec §4.1.3).
_NUMBER_RE = re.compile(r"^[+-]?\d+(?:[.,]\d+)*\s?%?$")
_DASHES = {"—", "–", "-"}


def _write_cell(
    cell,
    text: str,
    *,
    size: float | None = None,
    bold: bool | None = None,
    color: RGBColor | None = None,
    align=None,
) -> None:
    """Replace a cell's content with ``text`` in the kit's table type.

    Line breaks in ``text`` become ``w:br`` inside the one run. Cell
    paragraphs carry no spacing of their own, so rows stay as compact as the
    model's whatever the Normal style says.
    """
    cell.text = text
    for paragraph in cell.paragraphs:
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        if align is not None:
            paragraph.alignment = align
        for run in paragraph.runs:
            set_run_font(run, size=TYPE_SCALE["table"] if size is None else size, bold=bold, color=color)


def _is_centred_value(text: str) -> bool:
    value = (text or "").strip()
    return bool(value) and (
        value in _DASHES or bool(_NUMBER_RE.match(value)) or value.upper() in RISK_COLORS
    )


def _is_short(*texts: str) -> bool:
    joined = "\n".join(t or "" for t in texts)
    return len(joined) <= _KEEP_TOGETHER_MAX_CHARS and joined.count("\n") < _KEEP_TOGETHER_MAX_LINES


def _keep_with_next_in(row) -> None:
    for cell in row.cells:
        for paragraph in cell.paragraphs:
            paragraph.paragraph_format.keep_with_next = True


def add_kv_table(
    doc: Document,
    rows: Iterable[tuple[str, str]],
    *,
    variant: str = "blue",
    width_label_cm: float = 5.0,
    width_value_cm: float = 11.5,
):
    """Two-column key/value table: a coloured label column and plain values.

    ``variant="blue"``: white bold labels on the table-header blue (Anagrafica,
    environment identity). ``variant="light"``: navy bold labels on the light
    surface (the identity strips of the DVR's opening pages).
    """
    if variant not in _KV_VARIANTS:
        raise ValueError(f"unknown key/value table variant {variant!r}; use one of {sorted(_KV_VARIANTS)}")
    label_fill, label_colour = _KV_VARIANTS[variant]
    table = doc.add_table(rows=0, cols=2)
    style_applied = _try_set_table_style(table)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for column, width_cm in zip(table.columns, (width_label_cm, width_value_cm)):
        column.width = Cm(width_cm)
    for key, value in rows:
        label_text = str(key)
        value_text = "" if value is None else str(value)
        row = table.add_row()
        label, cell = row.cells
        _write_cell(label, label_text, bold=True, color=label_colour)
        _write_cell(cell, value_text)
        shade_cell(label, label_fill)
        if _is_short(label_text, value_text):
            keep_row_together(row)
    if not style_applied:
        _apply_cell_borders_all(table)
    set_table_borders(table)
    return table


def add_role_band(doc: Document, title: str, value: str):
    """A full-width band in the table-header blue naming a role, over a
    centred row with who holds it ("—" when nobody does). The DVR's
    Organizzazione aziendale della sicurezza is a stack of these."""
    table = doc.add_table(rows=2, cols=1)
    style_applied = _try_set_table_style(table)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    band = table.rows[0].cells[0]
    _write_cell(band, str(title or ""), bold=True, color=HEADER_TEXT, align=WD_ALIGN_PARAGRAPH.CENTER)
    shade_cell(band, BRAND_TABLE_HEADER_HEX)
    band.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    holder = (value or "").strip() or "—"
    _write_cell(table.rows[1].cells[0], holder, align=WD_ALIGN_PARAGRAPH.CENTER)
    _keep_with_next_in(table.rows[0])
    if _is_short(title, holder):
        for row in table.rows:
            keep_row_together(row)
    if not style_applied:
        _apply_cell_borders_all(table)
    set_table_borders(table)
    return table


def add_signature_grid(doc: Document, cells: list[tuple[str, str]], *, sign_height_cm: float = 2.5):
    """Signature grid, two signatories per grid row.

    Each grid row is three table rows: the roles on navy, the names ("—" when
    a role is vacant, so the grid never shrinks), and a blank row of at least
    ``sign_height_cm`` to sign in. With an odd count the last grid row's free
    half keeps the navy band and blank cells, never an unshaded half row.
    Every row is kept on one page and the first two stay with the signing
    row, so nobody signs under a page break.
    """
    pairs = list(cells)
    if not pairs:
        raise ValueError("add_signature_grid needs at least one (role, name) pair")
    table = doc.add_table(rows=0, cols=2)
    style_applied = _try_set_table_style(table)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for start in range(0, len(pairs), 2):
        chunk = pairs[start : start + 2]
        roles, names, signs = table.add_row(), table.add_row(), table.add_row()
        for index in range(2):
            if index < len(chunk):
                role, name = chunk[index]
                role_text, holder = str(role or ""), (name or "").strip() or "—"
            else:
                role_text, holder = "", ""
            role_cell = roles.cells[index]
            _write_cell(role_cell, role_text, bold=True, color=HEADER_TEXT, align=WD_ALIGN_PARAGRAPH.CENTER)
            shade_cell(role_cell, BRAND_NAVY_HEX)
            role_cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _write_cell(names.cells[index], holder, align=WD_ALIGN_PARAGRAPH.CENTER)
        # Rounded up to whole twips, the unit Word stores: 2.5 cm would
        # otherwise come back as 2.4998 cm.
        signs.height = Twips(math.ceil(Cm(sign_height_cm) / Twips(1)))
        signs.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        for row in (roles, names, signs):
            keep_row_together(row)
        _keep_with_next_in(roles)
        _keep_with_next_in(names)
    if not style_applied:
        _apply_cell_borders_all(table)
    set_table_borders(table)
    return table


def level_cell(cell, level: str) -> None:
    """Colour a risk-index or priority cell by its level (ACCETTABILE, MODESTO,
    GRAVE, GRAVISSIMO and the other ``RISK_COLORS`` keys): the level's fill
    with white bold centred text. An unknown level leaves the colours alone."""
    for paragraph in cell.paragraphs:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    colour = RISK_COLORS.get((level or "").strip().upper())
    if colour is None:
        return
    shade_cell(cell, str(colour))
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            set_run_font(run, bold=True, color=HEADER_TEXT)


def add_body_paragraph(doc: Document, text: str):
    """A justified body paragraph. Justification lives here, not on the
    Normal style, so table cells (which inherit Normal) stay left-aligned."""
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_run_font(paragraph.add_run(text or ""))
    return paragraph


_BULLET_STYLE = "List Bullet"


def _is_blank_paragraph(paragraph) -> bool:
    return not paragraph.text.strip() and not paragraph._p.xpath(
        ".//w:drawing | .//w:pict | .//w:object"
    )


def add_bullets(container, items: list[str], *, size_pt: float | None = None) -> list:
    """A bulleted list with real list numbering, in a document or a table cell.

    Each item is a ``List Bullet`` paragraph: the bullet comes from the
    style's numbering (python-docx's default template defines it), so Word,
    LibreOffice and the preview parser all see a list, never a typed "•".
    In a cell the empty paragraph every cell starts with becomes the first
    item instead of staying above the list, and cell bullets carry no
    paragraph spacing, like the rest of the kit's table text. Blank items are
    skipped; with nothing left, nothing is added. ``size_pt`` sets the item
    size (``TYPE_SCALE["table"]`` in a cell); ``None`` keeps the style's.

    A document without the style (a donor template) gets plain paragraphs
    with a typed bullet rather than an error. Returns the item paragraphs.
    """
    texts = [str(item).strip() for item in items if item is not None and str(item).strip()]
    in_cell = hasattr(container, "_tc")
    reuse = None
    if (
        texts
        and in_cell
        and len(container.paragraphs) == 1
        and _is_blank_paragraph(container.paragraphs[0])
    ):
        reuse = container.paragraphs[0]
        # Its empty runs (a table builder's blank cell text) go too.
        for run in list(reuse._p.r_lst):
            reuse._p.remove(run)
    paragraphs = []
    for index, text in enumerate(texts):
        paragraph = reuse if index == 0 and reuse is not None else container.add_paragraph()
        try:
            paragraph.style = _BULLET_STYLE
            label = text
        except KeyError:
            label = f"• {text}"
        set_run_font(paragraph.add_run(label), size=size_pt)
        if in_cell:
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
        paragraphs.append(paragraph)
    return paragraphs


def _try_set_table_style(table) -> bool:
    """Try Table Grid; return True if applied."""
    try:
        table.style = "Table Grid"
        return True
    except KeyError:
        return False


def add_data_table(
    doc: Document,
    headers: list[str],
    data_rows: list[list[str]],
    *,
    column_widths_cm: list[float] | None = None,
):
    """Table with a repeating blue header row and zebra data rows.

    10 pt text, left-aligned; numbers, levels and "—" are centred. The table
    spans the text width unless ``column_widths_cm`` says otherwise.
    """
    if column_widths_cm is not None and len(column_widths_cm) != len(headers):
        raise ValueError("column_widths_cm must contain one width per header")

    table = doc.add_table(rows=1, cols=len(headers))
    style_applied = _try_set_table_style(table)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr = table.rows[0]
    for i, h in enumerate(headers):
        _write_cell(hdr.cells[i], "" if h is None else str(h))
    style_header_row(hdr)

    # No cantSplit on data rows: a keep-together row taller than a page makes
    # LibreOffice loop forever (the DUVRI interferenze cells hit this), and
    # Word splits such rows regardless.
    for n, row_data in enumerate(data_rows):
        row = table.add_row()
        zebra = n % 2 == 1
        for i, cell_val in enumerate(row_data):
            text = "" if cell_val is None else str(cell_val)
            centred = WD_ALIGN_PARAGRAPH.CENTER if _is_centred_value(text) else None
            _write_cell(row.cells[i], text, align=centred)
            if zebra:
                shade_cell(row.cells[i], BRAND_SURFACE_HEX)

    if column_widths_cm is not None:
        table.autofit = False
        for column, width_cm in zip(table.columns, column_widths_cm):
            width = Cm(width_cm)
            column.width = width
            for cell in column.cells:
                cell.width = width

    if not style_applied:
        _apply_cell_borders_all(table)
    set_table_borders(table)
    return table


def page_break(doc: Document) -> None:
    doc.add_page_break()


# ---------------------------------------------------------------------------
# Donor-template surgery (audit 2026-09-03)
#
# Several attachments open a real completed client document and append the
# generated assessment after it. The donor half carried personal data — a
# staff roster with codici fiscali, scanned signatures, Street View photos —
# that no string substitution can remove. These helpers cut it out by
# structure, before the generator appends anything of its own.
# ---------------------------------------------------------------------------

def _body_children(doc: Document) -> list:
    return list(doc.element.body)


def _table_header_text(tbl_el, doc: Document) -> str:
    from docx.table import Table
    table = Table(tbl_el, doc)
    if not table.rows:
        return ""
    return " | ".join((c.text or "").strip() for c in table.rows[0].cells)


def _norm_text(text: str) -> str:
    """Case-, whitespace- and apostrophe-insensitive comparison key."""
    text = (text or "").replace(chr(0x2019), "'").replace(chr(0x2018), "'").replace(chr(0xA0), " ")
    return " ".join(text.split()).strip().lower()


def find_table_index(doc: Document, header_prefix: str, *, occurrence: int = 1) -> int | None:
    """Body index of the n-th table whose first row starts with ``header_prefix``."""
    seen = 0
    for i, el in enumerate(_body_children(doc)):
        if el.tag != qn("w:tbl"):
            continue
        if _norm_text(_table_header_text(el, doc)).startswith(_norm_text(header_prefix)):
            seen += 1
            if seen == occurrence:
                return i
    return None


def remove_body_after(doc: Document, index: int) -> int:
    """Delete every body element after ``index`` (the final ``sectPr`` is kept).

    Returns the number of elements removed. Use it to drop a donor document's
    tail — its results, company description, roster and signatures — while
    keeping the front matter and method chapters that are genuinely generic.
    """
    body = doc.element.body
    removed = 0
    for el in _body_children(doc)[index + 1 :]:
        if el.tag == qn("w:sectPr"):
            continue
        body.remove(el)
        removed += 1
    return removed


def remove_tables_with_header(doc: Document, needles: Iterable[str]) -> int:
    """Remove body tables whose first row contains ALL of ``needles``."""
    wanted = [n.lower() for n in needles]
    body = doc.element.body
    removed = 0
    for el in _body_children(doc):
        if el.tag != qn("w:tbl"):
            continue
        head = _table_header_text(el, doc).lower()
        if all(n in head for n in wanted):
            body.remove(el)
            removed += 1
    return removed


def strip_body_images(doc: Document) -> int:
    """Remove every inline picture from the body (headers/footers untouched).

    Donor templates embed scanned signatures, stamps and photographs of the
    donor's premises; none of them belong in another company's document.
    Text boxes and plain shapes are kept — a VML text box is also a ``w:pict``
    and in the legacy templates it holds the cover title. Returns the number
    of pictures removed.
    """
    removed = 0
    for tag in ("w:drawing", "w:pict"):
        for el in list(doc.element.body.iter(qn(tag))):
            has_textbox = el.find(".//" + qn("w:txbxContent")) is not None
            has_picture = (
                el.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip") is not None
                or el.find(".//{urn:schemas-microsoft-com:vml}imagedata") is not None
            )
            if has_textbox or not has_picture:
                continue
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
                removed += 1
    return removed


def reset_table_rows(doc: Document, header_prefix: str, rows: list[list[str]], *, occurrence: int = 1) -> bool:
    """Keep a table's header row, drop the rest, and write ``rows`` in its
    place — used to replace a donor's revision history with this emission."""
    from docx.table import Table
    idx = find_table_index(doc, header_prefix, occurrence=occurrence)
    if idx is None:
        return False
    table = Table(_body_children(doc)[idx], doc)
    body_rows = list(table.rows)[1:]
    # Write in place rather than deleting rows: donor tables merge cells
    # vertically, and deleting a row can orphan a vMerge continuation, which
    # Word tolerates but LibreOffice chokes on. Surplus rows are blanked, so
    # the template's form keeps its shape (six revision lines, five empty).
    for r_index, row in enumerate(body_rows):
        values = rows[r_index] if r_index < len(rows) else []
        cells = row.cells
        seen = []
        for c_index, cell in enumerate(cells):
            if any(cell._tc is s for s in seen):
                continue
            seen.append(cell._tc)
            value = values[c_index] if c_index < len(values) else ""
            _set_cell_text_keep_format(cell, "" if value is None else str(value))
    for values in rows[len(body_rows):]:
        cells = table.add_row().cells
        for cell, value in zip(cells, values):
            cell.text = "" if value is None else str(value)
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(TYPE_SCALE["table"])
    return True


def _set_cell_text_keep_format(cell, text: str) -> None:
    """Write ``text`` into a cell, reusing the first run's formatting."""
    paragraphs = cell.paragraphs
    if not paragraphs:
        cell.text = text
        return
    first = paragraphs[0]
    if first.runs:
        first.runs[0].text = text
        for run in first.runs[1:]:
            run.text = ""
    else:
        first.add_run(text)
    for extra in paragraphs[1:]:
        extra._p.getparent().remove(extra._p)


def fill_label_table(doc: Document, values: dict, *, tables=None) -> int:
    """Fill empty value cells next to (or under) matching labels in body tables.

    A label matches when the cell text, stripped of a trailing colon, equals a
    key (case, whitespace and apostrophe variants ignored). Two donor layouts
    are handled:

    - ``label | value`` rows: the cell to the right is written if empty. When
      the label cell is vertically merged over several rows (the "Sede Legale"
      cells that hold street and comune on two lines), each row takes the next
      item of a list value, so pass ``["Via Roma 1", "20100 Milano (MI)"]``.
    - stacked rows: a one-cell label row followed by a one-cell empty row.

    Each label is filled in the first table where it appears and skipped in
    later ones: a DUVRI carries the same "Ragione Sociale / Sede Legale" form
    for the committente and again for the appaltatore, and only the first is
    the client. Pass ``tables`` to restrict the search to specific tables —
    the anagrafica form repeats labels the cover already consumed, so it asks
    for itself by name (:func:`find_label_table`) instead. Values may be
    strings or lists of strings. Returns the number of cells filled.
    """
    wanted: dict[str, list[str]] = {}
    for k, v in values.items():
        items = [x for x in (v if isinstance(v, (list, tuple)) else [v]) if x]
        if items:
            wanted[_norm_text(k).rstrip(":").strip()] = [str(x) for x in items]
    if not wanted:
        return 0

    def norm(cell) -> str:
        return _norm_text(cell.text).rstrip(":").strip()

    filled = 0
    done: set[str] = set()

    class _Seen:
        # Vertically merged label cells return the same <w:tc> for every row
        # they span. Hold the element references so identity is stable —
        # python-docx/lxml recycle proxy objects, so id() alone lies.
        def __init__(self):
            self.entries: list[tuple[object, int]] = []

        def bump(self, el) -> int:
            for k, (seen_el, n) in enumerate(self.entries):
                if seen_el is el:
                    self.entries[k] = (seen_el, n + 1)
                    return n
            self.entries.append((el, 1))
            return 0

    for table in (doc.tables if tables is None else tables):
        rows = list(table.rows)
        used = _Seen()
        touched: set[str] = set()
        for r_index, row in enumerate(rows):
            cells = row.cells
            # stacked layout: single-cell label row, single-cell empty row below
            if len(set(id(c._tc) for c in cells)) == 1:
                label = norm(cells[0])
                if label in wanted and label not in done and r_index + 1 < len(rows):
                    below = rows[r_index + 1].cells
                    if len(set(id(c._tc) for c in below)) == 1 and not (below[0].text or "").strip():
                        _set_cell_text_keep_format(below[0], wanted[label][0])
                        filled += 1
                        touched.add(label)
                continue
            for i in range(len(cells) - 1):
                label = norm(cells[i])
                if label not in wanted or label in done:
                    continue
                target = cells[i + 1]
                if target._tc is cells[i]._tc:
                    continue
                # Position of this row within the merged label: the first
                # row takes the street, the second the comune, even when a
                # donor scrub already wrote the first line.
                n = used.bump(cells[i]._tc)
                if (target.text or "").strip():
                    touched.add(label)
                    break
                items = wanted[label]
                if n >= len(items):
                    break
                _set_cell_text_keep_format(target, items[n])
                filled += 1
                touched.add(label)
                break
        done |= touched
    return filled


def find_label_table(doc: Document, requires: Iterable[str]):
    """The first body table whose first column carries every one of ``requires``.

    Donor forms repeat labels — "Azienda" heads both the cover and the
    anagrafica — so a table is identified by a combination only it has,
    rather than by its position, which shifts whenever a template is edited.
    """
    from docx.table import Table

    wanted = [_norm_text(r).rstrip(":").strip() for r in requires]
    for el in _body_children(doc):
        if el.tag != qn("w:tbl"):
            continue
        table = Table(el, doc)
        labels = {
            _norm_text(row.cells[0].text).rstrip(":").strip()
            for row in table.rows
            if row.cells
        }
        if all(w in labels for w in wanted):
            return table
    return None


def remove_between(doc: Document, start_text: str, end_text: str) -> int:
    """Delete the body from the paragraph ``start_text`` up to ``end_text``.

    Both are matched on the whole paragraph text (case, whitespace and
    apostrophes ignored); the start paragraph goes with the block it heads
    and the end paragraph stays. Returns the number of body elements
    removed, or 0 when either anchor is missing — a template edit then shows
    up as a failing test instead of silently deleting the wrong half of a
    document.
    """
    from docx.text.paragraph import Paragraph

    body = doc.element.body
    children = _body_children(doc)
    start = end = None
    for i, el in enumerate(children):
        if el.tag != qn("w:p"):
            continue
        para = Paragraph(el, doc)
        style = (para.style.name if para.style else "") or ""
        if style.lower().startswith("toc"):
            # An index line is not the chapter it points at: matching one
            # would delete the whole body between the index and the anchor.
            continue
        text = _norm_text(para.text)
        if start is None and text == _norm_text(start_text):
            start = i
        elif start is not None and text == _norm_text(end_text):
            end = i
            break
    if start is None or end is None or end <= start:
        return 0
    for el in children[start:end]:
        body.remove(el)
    return end - start


def prune_toc_entries(doc: Document, texts: Iterable[str]) -> int:
    """Drop cached TOC lines for chapters no longer in the document.

    The donor index is a real TOC field, so Word rebuilds it on open (see
    ``design.refresh_fields_on_open``). Until it does, the reader sees the
    cached text — which would still list the chapters the generator replaced,
    with their old page numbers.
    """
    wanted = [_norm_text(t) for t in texts if t]
    removed = 0
    for para in list(doc.paragraphs):
        style = (para.style.name if para.style else "") or ""
        if not style.lower().startswith("toc"):
            continue
        line = _norm_text(para.text)
        if any(line.startswith(w) for w in wanted):
            para._p.getparent().remove(para._p)
            removed += 1
    return removed


def remove_blank_label_forms(doc: Document, *, min_rows: int = 3) -> int:
    """Remove two-column donor forms whose value column is entirely empty.

    Run it last, after every fill: what is still blank is a form the platform
    holds no data for. The donor templates ship six copies of the same
    per-ambiente sheet because a consultant used to fill them by hand, and
    printing them asks the operator to type what the document already states
    elsewhere. Returns the number of tables removed.
    """
    from docx.table import Table

    body = doc.element.body
    removed = 0
    for el in _body_children(doc):
        if el.tag != qn("w:tbl"):
            continue
        table = Table(el, doc)
        rows = list(table.rows)
        if len(rows) < min_rows or len(table.columns) != 2:
            continue
        values = []
        for row in rows:
            cells = row.cells
            if len(cells) > 1 and cells[1]._tc is not cells[0]._tc:
                values.append((cells[1].text or "").strip())
        if values and not any(values):
            body.remove(el)
            removed += 1
    return removed


def _set_paragraph_text_keep_format(paragraph, text: str) -> None:
    """Rewrite a paragraph, reusing the first run's formatting."""
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


_BLANK_RUN_RE = re.compile(r"_{3,}")


def fill_paragraph_blanks(doc: Document, starts_with: str, values: Iterable[str]) -> bool:
    """Write ``values`` into the underscore blanks of a donor paragraph.

    Donor declarations leave ruled blanks for a pen ("Il sottoscritto, ____
    in qualità di Datore di Lavoro della ____"). Each run of underscores
    takes the next value; surplus blanks are left ruled for signing.
    """
    remaining = list(values)
    for para in doc.paragraphs:
        if not _norm_text(para.text).startswith(_norm_text(starts_with)):
            continue
        _set_paragraph_text_keep_format(
            para,
            _BLANK_RUN_RE.sub(
                lambda m: remaining.pop(0) if remaining else m.group(0), para.text
            ),
        )
        return True
    return False


def replace_paragraph_text(doc: Document, contains: str, text: str) -> bool:
    """Rewrite the first paragraph containing ``contains``, keeping its style."""
    needle = _norm_text(contains)
    for para in doc.paragraphs:
        if needle and needle in _norm_text(para.text):
            _set_paragraph_text_keep_format(para, text)
            return True
    return False


def recolor_white_text(doc: Document, to: RGBColor = BRAND_NAVY) -> int:
    """Turn white runs navy. Donor covers set white type over a background
    picture that is no longer there, so the title printed white on white."""
    changed = 0
    for p in doc.paragraphs:
        for r in p.runs:
            try:
                rgb = r.font.color.rgb
            except Exception:
                rgb = None
            if rgb is not None and str(rgb).upper() == "FFFFFF":
                r.font.color.rgb = to
                changed += 1
    return changed
