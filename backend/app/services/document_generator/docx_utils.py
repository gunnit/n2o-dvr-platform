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
