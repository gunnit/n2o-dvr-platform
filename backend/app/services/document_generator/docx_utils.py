"""Shared helpers for document generators.

Keeps each generator small and focused by extracting common docx
manipulation patterns (placeholder substitution, table helpers,
heading styling, color palettes, etc.).
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsmap, qn
from docx.shared import Cm, Pt, RGBColor


# ---------------------------------------------------------------------------
# Colors shared with DVR Master palette
# ---------------------------------------------------------------------------

RISK_COLORS = {
    "ACCETTABILE": RGBColor(0x4C, 0xAF, 0x50),
    "MODESTO": RGBColor(0xFF, 0xC1, 0x07),
    "GRAVE": RGBColor(0xFF, 0x98, 0x00),
    "GRAVISSIMO": RGBColor(0xF4, 0x43, 0x36),
    "BASSO": RGBColor(0x4C, 0xAF, 0x50),
    "MEDIO": RGBColor(0xFF, 0xC1, 0x07),
    "ALTO": RGBColor(0xF4, 0x43, 0x36),
    "VERDE": RGBColor(0x4C, 0xAF, 0x50),
    "GIALLO": RGBColor(0xFF, 0xC1, 0x07),
    "ROSSO": RGBColor(0xF4, 0x43, 0x36),
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

HEADER_BG = RGBColor(0x1A, 0x23, 0x7E)
HEADER_TEXT = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF5, 0xF5, 0xF5)


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
LOGO_PATH = BACKEND_ROOT / "assets" / "logo.png"


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

def shade_cell(cell, color_hex: str) -> None:
    """Set background shading on a table cell via raw w:shd XML."""
    from docx.oxml import OxmlElement
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex)
    tc_pr.append(shd)


def style_header_row(row, bg_hex: str = "1A237E", text_color: RGBColor = HEADER_TEXT) -> None:
    """Bold white text on dark header background."""
    for cell in row.cells:
        shade_cell(cell, bg_hex)
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True
                run.font.color.rgb = text_color
                run.font.size = Pt(10)


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

def add_heading(doc: Document, text: str, level: int = 1) -> None:
    """Add a heading; fall back to Normal style if custom heading missing."""
    try:
        h = doc.add_heading(text, level=level)
    except Exception:
        h = doc.add_paragraph(text)
        for r in h.runs:
            r.bold = True
            r.font.size = Pt(14 if level == 1 else 12)
    return h


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
    gray = RGBColor(0x66, 0x66, 0x66)

    name_p = doc.add_paragraph()
    name_p.alignment = align
    name_run = name_p.add_run((branding.firm_name or "").upper())
    name_run.bold = True
    name_run.font.size = Pt(11)
    name_run.font.color.rgb = HEADER_BG

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
                tc_pr.append(tc_borders)
            for edge in ("top", "left", "bottom", "right"):
                b = OxmlElement(f"w:{edge}")
                b.set(qn("w:val"), "single")
                b.set(qn("w:sz"), "4")
                b.set(qn("w:color"), "808080")
                tc_borders.append(b)


def add_kv_table(doc: Document, rows: Iterable[tuple[str, str]], *, width_label_cm: float = 5.0, width_value_cm: float = 11.0) -> None:
    """2-column key/value table."""
    table = doc.add_table(rows=0, cols=2)
    style_applied = _try_set_table_style(table)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in rows:
        row = table.add_row().cells
        row[0].text = str(k)
        row[1].text = str(v) if v is not None else ""
        for p in row[0].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.size = Pt(10)
        for p in row[1].paragraphs:
            for r in p.runs:
                r.font.size = Pt(10)
        shade_cell(row[0], "F5F5F5")
    if not style_applied:
        _apply_cell_borders_all(table)
    return table


def _try_set_table_style(table) -> bool:
    """Try Table Grid; return True if applied."""
    try:
        table.style = "Table Grid"
        return True
    except KeyError:
        return False


def add_data_table(doc: Document, headers: list[str], data_rows: list[list[str]]) -> None:
    """Table with styled header + rows."""
    table = doc.add_table(rows=1, cols=len(headers))
    style_applied = _try_set_table_style(table)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr = table.rows[0]
    for i, h in enumerate(headers):
        hdr.cells[i].text = h
    style_header_row(hdr)

    for row_data in data_rows:
        row = table.add_row()
        for i, cell_val in enumerate(row_data):
            row.cells[i].text = "" if cell_val is None else str(cell_val)
            for p in row.cells[i].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    if not style_applied:
        _apply_cell_borders_all(table)
    return table


def page_break(doc: Document) -> None:
    doc.add_page_break()
