"""In-browser preview + inline editing support for generated .docx files.

Parses a document body into a JSON-serialisable block model (consumed by the
frontend preview) and applies per-paragraph plain-text overrides back onto
the original bytes (consumed by the download and save-edited-version
endpoints). The .docx stays the source of truth — overrides only ever
replace run text, never styles, tables, images or headers/footers.

Two parsers share one walk over the body:
- :func:`parse_docx_to_blocks` is the original block model, frozen.
  Documents generated before the 2026-11 layout redesign must parse exactly
  as they always did (golden test on ``tests/fixtures/preview_legacy_dvr.*``).
- :func:`parse_docx_preview` is what the editor endpoint serves: the same
  blocks plus the document's look (spec
  docs/superpowers/specs/2026-11-10-document-layout-redesign-design.md
  §4.3.1). Art pages report a ``page_role`` and a background picture instead
  of an inline image; paragraphs carry their outline level, direct
  formatting and list glyph; tables carry column widths; the response adds
  the running header/footer (``furniture``), the page setup and each used
  paragraph style resolved through its ``basedOn`` chain (``style_props``).
  Every addition is optional in the schema, so old clients keep working.

Address scheme (shared contract with the frontend):
- Top-level block: the index over the body's direct CT_P / CT_Tbl children
  in document order, skipping everything else (sectPr, bookmarks) — "12".
- Cell paragraph: "{table}:{row}:{cell}:{para}" where row enumerates the
  table's direct ``w:tr`` elements, cell enumerates the row's actual
  ``w:tc`` XML children (NOT python-docx ``row.cells``, which repeats
  merged cells), and para enumerates the cell's direct ``w:p`` children.

Parse and apply share the same private enumeration helpers below so the
addresses always agree between the two directions.
"""

from __future__ import annotations

import io
import logging
import mimetypes
import posixpath
import re
import zipfile
from copy import deepcopy
from xml.etree import ElementTree

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn
from docx.oxml.simpletypes import ST_HpsMeasure, ST_SignedTwipsMeasure
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from app.services.document_generator.design import ART_MARKER_PREFIX, art_marker

logger = logging.getLogger(__name__)

# EMU per inch / CSS reference pixels per inch — used to convert wp:extent
# (EMU) into the px dimensions the browser preview renders images at.
_EMU_PER_INCH = 914400
_PX_PER_INCH = 96

# Heading level from the paragraph style name. Generators use python-docx's
# built-in "Heading N" styles (docx_utils.add_heading), but templates saved
# from Italian-localised Word carry "Titolo N" as the style name instead —
# accept both, levels 1-4 per the contract.
_HEADING_STYLE_RE = re.compile(r"^(?:heading|titolo)\s+([1-4])$", re.IGNORECASE)

_ALIGNMENT_MAP = {
    WD_ALIGN_PARAGRAPH.LEFT: "left",
    WD_ALIGN_PARAGRAPH.CENTER: "center",
    WD_ALIGN_PARAGRAPH.RIGHT: "right",
    WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
}


# ---------------------------------------------------------------------------
# Shared enumeration helpers — the single source of truth for addresses.
# Both parse_docx_to_blocks and apply_overrides_to_docx MUST go through
# these so an address handed out by parse always resolves the same element
# on apply.
# ---------------------------------------------------------------------------


def _iter_body_blocks(body):
    """Yield ``(index, element)`` for the body's direct CT_P/CT_Tbl children.

    The index over THIS filtered enumeration is the top-level block address.
    Everything else (w:sectPr, bookmarks, comments) is skipped and does not
    consume an index.
    """
    idx = 0
    for child in body.iterchildren():
        if isinstance(child, (CT_P, CT_Tbl)):
            yield idx, child
            idx += 1


def _row_elements(tbl_el) -> list:
    """Direct ``w:tr`` children of a table (nested tables never leak in)."""
    return tbl_el.findall(qn("w:tr"))


def _cell_elements(tr_el) -> list:
    """Direct ``w:tc`` children of a row — the ACTUAL XML cells.

    Deliberately not python-docx ``row.cells``: that API repeats merged
    cells to normalise the grid, which would make addresses ambiguous.
    """
    return tr_el.findall(qn("w:tc"))


def _cell_paragraph_elements(tc_el) -> list:
    """Direct ``w:p`` children of a cell (nested-table paragraphs excluded)."""
    return tc_el.findall(qn("w:p"))


def _paragraph_is_locked(p_el) -> bool:
    """True when the paragraph must not be text-replaced.

    Drawings/pictures live inside runs we'd delete, and fldChar/instrText
    are field machinery (TOC, page refs) that Word re-evaluates — replacing
    their runs would corrupt the field. w:hyperlink and w:fldSimple wrap
    runs the removal loop would destroy (link target and field code lost
    for good), and a run-level page/column break would silently vanish —
    so those paragraphs stay visible but read-only too. Same rule on parse
    (editable=False) and on apply (skip silently).
    """
    return bool(
        p_el.xpath(
            ".//w:drawing | .//w:pict | .//w:fldChar | .//w:instrText"
            " | .//w:hyperlink | .//w:fldSimple"
            ' | .//w:br[@w:type="page" or @w:type="column"]'
        )
    )


# ---------------------------------------------------------------------------
# Parse: .docx bytes -> block list
# ---------------------------------------------------------------------------


def _paragraph_run_elements(p_el) -> list:
    """All ``w:r`` elements of a paragraph in visual order.

    ``Paragraph.runs`` only yields direct ``w:r`` children, which makes text
    inside ``w:hyperlink`` / ``w:fldSimple`` wrappers (e.g. "www.inail.it")
    invisible in the preview. Walk the paragraph's direct children in
    document order and descend into those wrapper elements so the full text
    is shown — such paragraphs are locked (see _paragraph_is_locked), so
    visibility never turns into editability.
    """
    wrapper_tags = (qn("w:hyperlink"), qn("w:fldSimple"))
    run_tag = qn("w:r")
    runs: list = []
    for child in p_el.iterchildren():
        if child.tag == run_tag:
            runs.append(child)
        elif child.tag in wrapper_tags:
            runs.extend(child.iter(run_tag))
    return runs


def _run_payload(run, *, with_caps: bool = False) -> dict:
    """Serialise one run. color/size come from run.font — None when inherited.

    ``with_caps`` (preview contract only) adds the run's own capitals flag.
    """
    font = run.font
    color = None
    try:
        if font.color is not None and font.color.rgb is not None:
            color = str(font.color.rgb)
    except (AttributeError, ValueError):  # theme colors without an RGB value
        color = None
    payload = {
        "text": run.text,
        "bold": bool(font.bold),
        "italic": bool(font.italic),
        "underline": bool(font.underline),
        "color": color,
        "size": float(font.size.pt) if font.size is not None else None,
    }
    if with_caps:
        payload["caps"] = bool(font.all_caps)
    return payload


def _image_payloads(p_el, *, skip_art: bool = False) -> list[dict]:
    """Inline images in the paragraph's runs, as rId + px dimensions.

    ``skip_art`` (preview contract only) leaves out the full-page art
    pictures, which the paragraph reports as its page background instead.
    """
    images: list[dict] = []
    for drawing in p_el.xpath(".//w:drawing"):
        if skip_art and _is_art_drawing(drawing):
            continue
        rids = drawing.xpath(".//a:blip/@r:embed")
        if not rids:
            continue
        width_px = height_px = None
        extents = drawing.xpath(".//wp:extent")
        if extents:
            try:
                width_px = round(int(extents[0].get("cx")) / _EMU_PER_INCH * _PX_PER_INCH)
                height_px = round(int(extents[0].get("cy")) / _EMU_PER_INCH * _PX_PER_INCH)
            except (TypeError, ValueError):
                width_px = height_px = None
        images.append({"image_id": rids[0], "width_px": width_px, "height_px": height_px})
    return images


def _paragraph_payload(
    p_el,
    addr: str,
    parent,
    *,
    in_nested_table: bool = False,
    ctx: _PreviewContext | None = None,
) -> dict:
    """Common paragraph fields shared by top-level blocks and cell paragraphs.

    Without ``ctx`` this is the frozen legacy payload; with it, the preview
    contract's paragraph fields are added (see :class:`_PreviewContext`).
    """
    para = Paragraph(p_el, parent)
    style = None
    style_name = None
    try:
        style = para.style
        style_name = style.name if style is not None else None
    except Exception:  # defensive: malformed styles part must not kill preview
        style = None
        style_name = None
    heading_level = None
    if style_name:
        match = _HEADING_STYLE_RE.match(style_name)
        if match:
            heading_level = int(match.group(1))
    payload = {
        "addr": addr,
        "style": style_name,
        "heading_level": heading_level,
        "alignment": _ALIGNMENT_MAP.get(para.alignment),
        "editable": not in_nested_table and not _paragraph_is_locked(p_el),
        "runs": [
            _run_payload(Run(r_el, para), with_caps=ctx is not None)
            for r_el in _paragraph_run_elements(p_el)
        ],
        "images": _image_payloads(p_el, skip_art=ctx is not None),
    }
    if ctx is not None:
        payload.update(ctx.paragraph_fields(p_el, style_name, style))
    return payload


def _paragraph_has_page_break(p_el, para: Paragraph) -> bool:
    if para.paragraph_format.page_break_before:
        return True
    return bool(p_el.xpath('.//w:br[@w:type="page"]'))


def _cell_payload(tc_el, cell_addr: str, parent, ctx: _PreviewContext | None = None) -> dict:
    paragraphs: list[dict] = []
    para_idx = 0
    for p_el in _cell_paragraph_elements(tc_el):
        paragraphs.append(
            _paragraph_payload(p_el, f"{cell_addr}:{para_idx}", parent, ctx=ctx)
        )
        para_idx += 1

    # Graceful degradation for nested tables: no recursion — flatten their
    # text into extra read-only paragraphs appended to the cell. Addresses
    # continue the paraIdx sequence, so they can never collide with the
    # direct w:p addresses the apply side resolves, and editable=False
    # keeps them locked regardless.
    for nested_tbl in tc_el.findall(qn("w:tbl")):
        for nested_p in nested_tbl.iter(qn("w:p")):
            text = "".join(t.text or "" for t in nested_p.iter(qn("w:t")))
            run = {
                "text": text,
                "bold": False,
                "italic": False,
                "underline": False,
                "color": None,
                "size": None,
            }
            flattened = {
                "addr": f"{cell_addr}:{para_idx}",
                "style": None,
                "heading_level": None,
                "alignment": None,
                "editable": False,
                "runs": [run] if text else [],
                "images": [],
            }
            if ctx is not None:
                run["caps"] = False
                flattened.update(_PLAIN_PARAGRAPH_FIELDS)
            paragraphs.append(flattened)
            para_idx += 1

    shading = None
    col_span = 1
    v_merge = None
    tc_pr = tc_el.find(qn("w:tcPr"))
    if tc_pr is not None:
        shd = tc_pr.find(qn("w:shd"))
        if shd is not None:
            fill = shd.get(qn("w:fill"))
            if fill and fill.lower() != "auto":
                shading = fill.upper()
        grid_span = tc_pr.find(qn("w:gridSpan"))
        if grid_span is not None:
            try:
                col_span = int(grid_span.get(qn("w:val")) or 1)
            except (TypeError, ValueError):
                col_span = 1
        v_merge_el = tc_pr.find(qn("w:vMerge"))
        if v_merge_el is not None:
            # A bare <w:vMerge/> (no val) means "continue" per OOXML.
            v_merge = v_merge_el.get(qn("w:val")) or "continue"

    payload = {
        "addr": cell_addr,
        "paragraphs": paragraphs,
        "shading": shading,
        "col_span": col_span,
        "v_merge": v_merge,
    }
    if ctx is not None:
        payload["v_align"] = _cell_v_align(tc_pr)
    return payload


def _table_payload(tbl_el, addr: str, parent, ctx: _PreviewContext | None = None) -> dict:
    rows: list[list[dict]] = []
    for row_idx, tr_el in enumerate(_row_elements(tbl_el)):
        rows.append(
            [
                _cell_payload(tc_el, f"{addr}:{row_idx}:{cell_idx}", parent, ctx)
                for cell_idx, tc_el in enumerate(_cell_elements(tr_el))
            ]
        )
    payload = {"kind": "table", "addr": addr, "rows": rows}
    if ctx is not None:
        payload["col_widths_pct"] = _col_widths_pct(tbl_el)
    return payload


def _parse_blocks(document, ctx: _PreviewContext | None) -> list[dict]:
    """The body's blocks in address order; enriched when ``ctx`` is given."""
    blocks: list[dict] = []
    for idx, element in _iter_body_blocks(document.element.body):
        addr = str(idx)
        if isinstance(element, CT_P):
            payload = _paragraph_payload(element, addr, document, ctx=ctx)
            payload["kind"] = "paragraph"
            payload["page_break_before"] = _paragraph_has_page_break(
                element, Paragraph(element, document)
            )
            blocks.append(payload)
        else:  # CT_Tbl
            blocks.append(_table_payload(element, addr, document, ctx))
    return blocks


def parse_docx_to_blocks(docx_bytes: bytes) -> list[dict]:
    """Parse a .docx body into the addressed block model.

    Empty paragraphs are kept — they carry vertical spacing the preview
    must reproduce. Returns plain dicts (JSON-ready) validated by the
    DocumentPreviewResponse schema at the endpoint boundary.

    Frozen: this output never changes, for old documents or new ones (it
    still lists art pictures as inline images). The editor endpoint uses
    :func:`parse_docx_preview`.
    """
    document = Document(io.BytesIO(docx_bytes))
    return _parse_blocks(document, None)


def parse_docx_preview(docx_bytes: bytes) -> dict:
    """Parse a .docx into the editor's preview payload (spec §4.3.1).

    Returns ``{"blocks", "furniture", "page_setup", "style_props"}``:

    - ``blocks``: :func:`parse_docx_to_blocks`'s blocks plus, per paragraph,
      ``outline_level``, ``direct``, ``list``, ``page_role``,
      ``background_image_id`` and ``section_break_after``; per run ``caps``;
      per table ``col_widths_pct``; per cell ``v_align``. The one change to
      an old field: the art picture of a cover, divider or back cover is the
      paragraph's ``background_image_id``, not an entry of its ``images``
      (documents made before the art existed parse to the same old fields).
    - ``furniture``: the running header and footer of the body's final
      section, or None when it has neither.
    - ``page_setup``: page size and margins of the body's final section, in
      points, or None without one.
    - ``style_props``: each paragraph style a block uses, by name (the
      ``style`` field), resolved through ``basedOn`` down to ``docDefaults``.

    Pictures are referenced by relationship id only, never decoded. What
    cannot be read degrades to the plain value (None, no list, the defaults
    of a paragraph) with a warning, never failing a preview the legacy
    parser would have produced.
    """
    document = Document(io.BytesIO(docx_bytes))
    ctx = _PreviewContext(document)
    blocks = _parse_blocks(document, ctx)
    return {
        "blocks": blocks,
        "furniture": _or_none(_furniture, document, "header/footer"),
        "page_setup": _or_none(_page_setup, document, "page setup"),
        "style_props": ctx.style_props(),
    }


def _or_none(build, document, what: str):
    try:
        return build(document)
    except Exception:  # an odd part must not cost the reader the whole preview
        logger.warning("Preview: unreadable %s left out", what, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Preview contract (parse_docx_preview only): page roles, typography, lists,
# table geometry, furniture and page setup.
# ---------------------------------------------------------------------------

# Roles of the full-page art (spec §4.1.2): its picture's wp:docPr is named
# "vera-art:<role>:<key>". A marker with any other role is an ordinary picture.
_PAGE_ROLES = frozenset({"cover", "divider", "back_cover"})

# The resolved-style table and a paragraph's ``direct`` share these keys.
_STYLE_PROP_KEYS = (
    "font_size_pt",
    "bold",
    "italic",
    "caps",
    "color",
    "alignment",
    "space_before_pt",
    "space_after_pt",
    "indent_left_pt",
    "outline_level",
)
# On/off properties: when nothing in a style chain sets one, it is off.
_TOGGLE_KEYS = ("bold", "italic", "caps")

# The new paragraph fields for a paragraph that has none of them (the
# flattened text of a nested table).
_PLAIN_PARAGRAPH_FIELDS = {
    "outline_level": None,
    "direct": None,
    "list": None,
    "page_role": None,
    "background_image_id": None,
    "section_break_after": False,
}

# w:jc values (transitional and strict) -> the contract's four alignments.
_JC_ALIGNMENT = {
    "left": "left",
    "start": "left",
    "center": "center",
    "right": "right",
    "end": "right",
    "both": "justify",
    "distribute": "justify",
    "thaiDistribute": "justify",
    "lowKashida": "justify",
    "mediumKashida": "justify",
    "highKashida": "justify",
}

# w:vAlign of a cell; "both" (justified vertically) is drawn centred.
_V_ALIGN = {"top": "top", "center": "center", "both": "center", "bottom": "bottom"}

_HEX_COLOR_RE = re.compile(r"^[0-9A-Fa-f]{6}$")

# Word stores most bullets as a private-use code point (U+F0xx) of a symbol
# font: Symbol U+F0B7 is "•", Wingdings U+F0A7 is "▪". The browser has
# neither font, so the preview reports the glyph the font draws. Older files
# write the same glyphs as the font's 8-bit code ("§" in Wingdings).
_SYMBOL_FONT_GLYPHS = {
    "symbol": {0xA7: "♣", 0xA8: "♦", 0xA9: "♥", 0xAA: "♠", 0xAE: "→", 0xB7: "•", 0xDE: "⇒", 0xE0: "◊"},
    "wingdings": {
        0x6C: "●", 0x6E: "■", 0x6F: "□", 0x71: "❑", 0x75: "◆", 0x76: "❖",
        0xA7: "▪", 0xD8: "➢", 0xFC: "✓",
    },
}

# Sentinel: an attribute present but unreadable counts as not specified.
_UNSET = object()


def _on_off(value: str | None) -> bool:
    """ST_OnOff: a bare element is on; "0", "false" and "off" turn it off."""
    return value is None or value.strip().lower() not in ("0", "false", "off")


def _measure_pt(value: str | None, simple_type) -> float | None:
    """A twips or half-points attribute in points (universal measures such as
    "2.5cm" too), or None when absent or unreadable."""
    if value is None:
        return None
    try:
        return round(simple_type.convert_from_xml(value).pt, 2)
    except (ValueError, KeyError, TypeError, ArithmeticError):
        return None


def _twips_pt(value: str | None) -> float | None:
    return _measure_pt(value, ST_SignedTwipsMeasure)


def _val(element) -> str | None:
    """``w:val`` of an optional element. (Never ``element or ...``: an lxml
    element without children is falsy.)"""
    return element.get(qn("w:val")) if element is not None else None


def _int_val(element) -> int | None:
    """``w:val`` of an optional element as an int, or None."""
    try:
        return int(_val(element))
    except (TypeError, ValueError):
        return None


def _ppr_props(ppr) -> dict:
    """The style-prop keys a ``w:pPr`` specifies, and only those."""
    props: dict = {}
    if ppr is None:
        return props
    alignment = _JC_ALIGNMENT.get(_val(ppr.find(qn("w:jc"))) or "")
    if alignment is not None:
        props["alignment"] = alignment
    spacing = ppr.find(qn("w:spacing"))
    if spacing is not None:
        for key, attr in (("space_before_pt", "w:before"), ("space_after_pt", "w:after")):
            points = _twips_pt(spacing.get(qn(attr)))
            if points is not None:
                props[key] = points
    ind = ppr.find(qn("w:ind"))
    if ind is not None:
        left = ind.get(qn("w:left"))
        points = _twips_pt(left if left is not None else ind.get(qn("w:start")))
        if points is not None:
            props["indent_left_pt"] = points
    outline = _int_val(ppr.find(qn("w:outlineLvl")))
    if outline is not None:
        # 0-8 are outline levels 1-9; 9 is "body text" and ends the search.
        props["outline_level"] = outline + 1 if 0 <= outline <= 8 else None
    return props


def _rpr_props(rpr) -> dict:
    """The style-prop keys a ``w:rPr`` specifies, and only those."""
    props: dict = {}
    if rpr is None:
        return props
    size = _measure_pt(_val(rpr.find(qn("w:sz"))), ST_HpsMeasure)
    if size is not None:
        props["font_size_pt"] = size
    for key, tag in (("bold", "w:b"), ("italic", "w:i"), ("caps", "w:caps")):
        element = rpr.find(qn(tag))
        if element is not None:
            props[key] = _on_off(_val(element))
    color = _color_value(rpr.find(qn("w:color")))
    if color is not _UNSET:
        props["color"] = color
    return props


def _color_value(element):
    """"RRGGBB" for ``w:color``; None for "auto" (a real setting: it ends the
    search up the style chain); _UNSET when absent or unreadable."""
    if element is None:
        return _UNSET
    value = _val(element) or ""
    if value.lower() == "auto":
        return None
    return value.upper() if _HEX_COLOR_RE.match(value) else _UNSET


def _resolve(levels: list[dict]) -> dict:
    """Merge property levels, nearest first: each key takes the first level
    that specifies it. Unspecified on/off properties are off; everything
    else unspecified is None."""
    resolved = {}
    for key in _STYLE_PROP_KEYS:
        resolved[key] = next((level[key] for level in levels if key in level), None)
    for key in _TOGGLE_KEYS:
        if resolved[key] is None:
            resolved[key] = False
    return resolved


def _style_chain(style_el) -> list:
    """A ``w:style`` and its ``basedOn`` ancestors, nearest first. A cycle or
    a dangling ``basedOn`` ends the chain."""
    chain: list = []
    while style_el is not None and all(style_el is not seen for seen in chain):
        chain.append(style_el)
        try:
            style_el = style_el.base_style
        except Exception:  # e.g. a styleId XPath cannot quote
            break
    return chain


def _num_pr(ppr) -> tuple[int | None, int | None]:
    """``(numId, ilvl)`` of a ``w:pPr``'s ``w:numPr``; None where absent."""
    num_pr = ppr.find(qn("w:numPr")) if ppr is not None else None
    if num_pr is None:
        return None, None
    return _int_val(num_pr.find(qn("w:numId"))), _int_val(num_pr.find(qn("w:ilvl")))


def _art_role(name: str | None) -> str | None:
    """The page role of a ``vera-art:<role>:<key>`` picture name, else None."""
    if not name or not name.startswith(ART_MARKER_PREFIX):
        return None
    role = name[len(ART_MARKER_PREFIX):].split(":", 1)[0]
    return role if role in _PAGE_ROLES else None


def _is_art_drawing(drawing) -> bool:
    return any(_art_role(docpr.get("name")) for docpr in drawing.iter(qn("wp:docPr")))


def _art_page(p_el) -> tuple[str | None, str | None]:
    """``(page_role, background rId)`` of a paragraph holding kit art."""
    marker = art_marker(p_el)
    role = _art_role(marker)
    if role is None:
        return None, None
    for drawing in p_el.iter(qn("w:drawing")):
        if any(docpr.get("name") == marker for docpr in drawing.iter(qn("wp:docPr"))):
            for blip in drawing.iter(qn("a:blip")):
                if blip.get(qn("r:embed")):
                    return role, blip.get(qn("r:embed"))
            break
    return role, None


def _cell_v_align(tc_pr) -> str | None:
    if tc_pr is None:
        return None
    return _V_ALIGN.get(_val(tc_pr.find(qn("w:vAlign"))) or "")


def _col_widths_pct(tbl_el) -> list[float] | None:
    """The ``w:tblGrid`` column widths as percentages of the grid, or None
    without a usable grid."""
    grid = tbl_el.find(qn("w:tblGrid"))
    if grid is None:
        return None
    widths = [_twips_pt(col.get(qn("w:w"))) for col in grid.findall(qn("w:gridCol"))]
    if not widths or any(w is None or w < 0 for w in widths):
        return None
    total = sum(widths)
    if total <= 0:
        return None
    return [round(w * 100 / total, 2) for w in widths]


def _bullet_glyph(text: str, font: str) -> str:
    """The character a bullet level draws (see ``_SYMBOL_FONT_GLYPHS``)."""
    if len(text) != 1:
        return text
    code = ord(text)
    private_use = 0xF000 <= code <= 0xF0FF
    if not private_use and code > 0xFF:
        return text  # real Unicode: "▪", "•", "–"
    if font.startswith("courier") and text == "o":
        return "◦"  # Word's second-level hollow bullet
    tables = [table for name, table in _SYMBOL_FONT_GLYPHS.items() if font.startswith(name)]
    if not tables and private_use:
        tables = list(_SYMBOL_FONT_GLYPHS.values())
    for table in tables:
        glyph = table.get(code & 0xFF)
        if glyph is not None:
            return glyph
    return "•" if private_use else text


def _level_font(lvl) -> str:
    """The font a numbering level draws its text in, lower case ("" if none)."""
    fonts = lvl.find(f"{qn('w:rPr')}/{qn('w:rFonts')}")
    if fonts is None:
        return ""
    for slot in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        name = (fonts.get(qn(slot)) or "").strip()
        if name:
            return name.lower()
    return ""


def _list_glyph(lvl) -> str:
    """What a numbering level prints before the text: the bullet glyph, or
    the ``lvlText`` pattern ("%1.") of a numbered format."""
    pattern = _val(lvl.find(qn("w:lvlText"))) or ""
    if _val(lvl.find(qn("w:numFmt"))) == "bullet":
        return _bullet_glyph(pattern, _level_font(lvl))
    return pattern


class _NumberingIndex:
    """``numbering.xml`` indexed once: ``w:num`` -> ``w:abstractNum`` -> ``w:lvl``."""

    def __init__(self, numbering_el, styles_el) -> None:
        self._abstracts: dict[str, object] = {}
        for abstract in numbering_el.findall(qn("w:abstractNum")):
            self._abstracts.setdefault(abstract.get(qn("w:abstractNumId")), abstract)
        self._nums: dict[int, object] = {}
        for num in numbering_el.findall(qn("w:num")):
            try:
                self._nums.setdefault(int(num.get(qn("w:numId"))), num)
            except (TypeError, ValueError):
                continue
        # Numbering styles, for w:numStyleLink indirection.
        self._numbering_styles = {
            style.get(qn("w:styleId")): style
            for style in styles_el.findall(qn("w:style"))
            if style.get(qn("w:type")) == "numbering"
        }

    @classmethod
    def of(cls, document) -> _NumberingIndex | None:
        for rel in document.part.rels.values():
            if rel.is_external or rel.reltype != RT.NUMBERING:
                continue
            element = getattr(rel.target_part, "element", None)
            if element is not None:
                return cls(element, document.styles.element)
        return None

    def _abstract(self, num_id: int, hops: int = 0):
        num = self._nums.get(num_id)
        if num is None:
            return None
        abstract = self._abstracts.get(_val(num.find(qn("w:abstractNumId"))))
        link = abstract.find(qn("w:numStyleLink")) if abstract is not None else None
        if link is not None and hops < 3:
            # The definition lives with the numbering style the link names.
            style = self._numbering_styles.get(_val(link))
            linked_id, _ = _num_pr(style.find(qn("w:pPr")) if style is not None else None)
            if linked_id is not None and linked_id != num_id:
                linked = self._abstract(linked_id, hops + 1)
                if linked is not None:
                    return linked
        return abstract

    def list_info(self, num_id: int, ilvl: int | None, style_id: str | None) -> dict | None:
        """``{level, glyph}`` for a paragraph numbered ``num_id``/``ilvl``.

        Without an ``ilvl``, a level linked to the paragraph's style
        (``w:lvl/w:pStyle``) is used, else level 0.
        """
        num = self._nums.get(num_id)
        if num is None:
            return None
        abstract = self._abstract(num_id)
        levels = abstract.findall(qn("w:lvl")) if abstract is not None else []
        if ilvl is None:
            linked = [
                _int_lvl(lvl)
                for lvl in levels
                if style_id and _val(lvl.find(qn("w:pStyle"))) == style_id
            ]
            ilvl = linked[0] if linked and linked[0] is not None else 0
        # A w:lvlOverride carrying its own w:lvl replaces that level.
        for override in num.findall(qn("w:lvlOverride")):
            lvl = override.find(qn("w:lvl"))
            if lvl is not None and _int_lvl(override) == ilvl:
                return {"level": ilvl, "glyph": _list_glyph(lvl)}
        for lvl in levels:
            if _int_lvl(lvl) == ilvl:
                return {"level": ilvl, "glyph": _list_glyph(lvl)}
        return None


def _int_lvl(element) -> int | None:
    try:
        return int(element.get(qn("w:ilvl")))
    except (TypeError, ValueError):
        return None


class _PreviewContext:
    """Per-document state of :func:`parse_docx_preview`: resolved styles,
    the numbering index and the styles the blocks use."""

    def __init__(self, document) -> None:
        self._defaults: dict = {}
        try:
            defaults = document.styles.element.find(qn("w:docDefaults"))
            if defaults is not None:
                self._defaults = {
                    **_ppr_props(defaults.find(f"{qn('w:pPrDefault')}/{qn('w:pPr')}")),
                    **_rpr_props(defaults.find(f"{qn('w:rPrDefault')}/{qn('w:rPr')}")),
                }
        except Exception:
            logger.warning("Preview: unreadable docDefaults, left out", exc_info=True)
        try:
            self._numbering = _NumberingIndex.of(document)
        except Exception:
            logger.warning("Preview: unreadable numbering part, lists left out", exc_info=True)
            self._numbering = None
        # Keyed by the w:style element: kept alive here, so lxml hands back
        # the same proxy object on every lookup.
        self._resolved: dict = {}
        self._style_numbering: dict = {}
        self._lists: dict = {}
        self._used: dict[str, object] = {}
        self._warned = False

    def _style_props_of(self, style_el) -> dict:
        resolved = self._resolved.get(style_el)
        if resolved is None:
            levels = [
                {**_ppr_props(el.find(qn("w:pPr"))), **_rpr_props(el.find(qn("w:rPr")))}
                for el in _style_chain(style_el)
            ]
            resolved = self._resolved[style_el] = _resolve([*levels, self._defaults])
        return resolved

    def _numbering_of_style(self, style_el) -> tuple[int | None, int | None]:
        """The numPr a style chain carries, attribute by attribute."""
        found = self._style_numbering.get(style_el)
        if found is None:
            num_id = ilvl = None
            for el in _style_chain(style_el):
                level_num_id, level_ilvl = _num_pr(el.find(qn("w:pPr")))
                num_id = level_num_id if num_id is None else num_id
                ilvl = level_ilvl if ilvl is None else ilvl
            found = self._style_numbering[style_el] = (num_id, ilvl)
        return found

    def _list(self, ppr, style_el) -> dict | None:
        if self._numbering is None:
            return None
        num_id, ilvl = _num_pr(ppr)
        style_id = None
        if style_el is not None:
            style_id = style_el.get(qn("w:styleId"))
            style_num_id, style_ilvl = self._numbering_of_style(style_el)
            num_id = style_num_id if num_id is None else num_id
            ilvl = style_ilvl if ilvl is None else ilvl
        if not num_id:  # absent, or numId 0: numbering switched off
            return None
        key = (num_id, ilvl, style_id)
        if key not in self._lists:
            self._lists[key] = self._numbering.list_info(num_id, ilvl, style_id)
        info = self._lists[key]
        return dict(info) if info is not None else None

    def paragraph_fields(self, p_el, style_name: str | None, style) -> dict:
        """The preview contract's paragraph fields for one ``w:p``.

        The look is an addition: a paragraph it cannot be read for gets the
        plain defaults rather than costing the reader the preview the
        legacy parser would have shown.
        """
        try:
            return self._paragraph_fields(p_el, style_name, style)
        except Exception:
            if not self._warned:
                self._warned = True
                logger.warning("Preview: paragraph look unreadable, left plain", exc_info=True)
            return dict(_PLAIN_PARAGRAPH_FIELDS)

    def _paragraph_fields(self, p_el, style_name: str | None, style) -> dict:
        style_el = style.element if style is not None else None
        if style_name is not None and style_el is not None:
            self._used.setdefault(style_name, style_el)
        ppr = p_el.pPr
        rpr = ppr.find(qn("w:rPr")) if ppr is not None else None
        # Direct formatting: the paragraph's own pPr, plus its mark's rPr —
        # what sets the height of an empty paragraph.
        direct = {**_ppr_props(ppr), **_rpr_props(rpr)}
        if "outline_level" in direct:
            outline_level = direct["outline_level"]
        elif style_el is not None:
            outline_level = self._style_props_of(style_el)["outline_level"]
        else:
            outline_level = self._defaults.get("outline_level")
        page_role, background_image_id = _art_page(p_el)
        return {
            "outline_level": outline_level,
            # Only the keys the paragraph sets (a None value is a real
            # setting: "auto" colour, body-text outline level).
            "direct": direct or None,
            "list": self._list(ppr, style_el),
            "page_role": page_role,
            "background_image_id": background_image_id,
            "section_break_after": ppr is not None and ppr.find(qn("w:sectPr")) is not None,
        }

    def style_props(self) -> dict[str, dict]:
        """Every style a parsed paragraph used, by name, fully resolved (a
        style that cannot be resolved is left out: the editor falls back to
        its own defaults)."""
        table: dict[str, dict] = {}
        for name, style_el in self._used.items():
            try:
                table[name] = dict(self._style_props_of(style_el))
            except Exception:
                logger.warning("Preview: style %r unreadable, left out", name, exc_info=True)
        return table


# --- Furniture: the running header and footer ------------------------------

# Elements whose runs are text a reader sees. w:fldSimple wraps a field's
# result and w:del deleted text, so neither is listed.
_RUN_CONTAINERS = frozenset(
    qn(tag)
    for tag in ("w:hyperlink", "w:smartTag", "w:customXml", "w:ins", "w:sdt", "w:sdtContent", "w:dir", "w:bdo")
)
# Footer parts the image endpoint can address as "ftr:<part>:<rId>" (the
# same names _PART_IMAGE_ID_RE accepts).
_FOOTER_PART_RE = re.compile(r"^/word/(footer\d+\.xml)$")


def _furniture_paragraphs(container):
    """Paragraphs of a header/footer part in reading order, table cells and
    content controls included, text boxes not."""
    for child in container:
        if child.tag == qn("w:p"):
            yield child
        elif child.tag == qn("w:tbl"):
            for tr in child.findall(qn("w:tr")):
                for tc in tr.findall(qn("w:tc")):
                    yield from _furniture_paragraphs(tc)
        elif child.tag in (qn("w:sdt"), qn("w:sdtContent"), qn("w:customXml")):
            yield from _furniture_paragraphs(child)


def _furniture_runs(element):
    for child in element:
        if child.tag == qn("w:r"):
            yield child
        elif child.tag in _RUN_CONTAINERS:
            yield from _furniture_runs(child)


def _furniture_text(p_el) -> str:
    """The literal text of a header/footer paragraph, tabs as "\\t". Field
    codes and field results (PAGE, NUMPAGES, ...) are left out."""
    parts: list[str] = []
    open_fields = 0  # complex fields begun and not yet ended (they nest)
    for run in _furniture_runs(p_el):
        for child in run:
            tag = child.tag
            if tag == qn("w:fldChar"):
                kind = child.get(qn("w:fldCharType"))
                if kind == "begin":
                    open_fields += 1
                elif kind == "end" and open_fields:
                    open_fields -= 1
            elif open_fields:
                continue  # inside a field: its code or its result
            elif tag == qn("w:t"):
                parts.append(child.text or "")
            elif tag in (qn("w:tab"), qn("w:ptab")):
                parts.append("\t")
            elif tag in (qn("w:br"), qn("w:cr")):
                parts.append(" ")
    return "".join(parts)


def _default_furniture_part(document, sect_prs: list, reference: str):
    """The default header or footer part showing in the final section: its
    own, else the nearest previous section's (Word's "link to previous")."""
    for sect_pr in reversed(sect_prs):
        for ref in sect_pr.findall(qn(reference)):
            if (ref.get(qn("w:type")) or "default") != "default":
                continue
            try:
                return document.part.related_parts[ref.get(qn("r:id"))]
            except KeyError:
                return None
    return None


def _footer_logo_image_id(part) -> str | None:
    """``ftr:<part>:<rId>`` of the footer's first inline picture, or None."""
    match = _FOOTER_PART_RE.match(str(part.partname))
    if match is None:
        return None
    for inline in part.element.iter(qn("wp:inline")):
        for blip in inline.iter(qn("a:blip")):
            rel = part.rels.get(blip.get(qn("r:embed")) or "")
            if rel is not None and not rel.is_external and rel.reltype == RT.IMAGE:
                return f"ftr:{match.group(1)}:{rel.rId}"
    return None


def _furniture(document) -> dict | None:
    """Header sides, footer revision line and footer logo of the final section.

    The header's first paragraph with text is split at its first tab
    (title | client). The footer text is its first non-empty text before a
    tab — the revision line, without the page numbers.
    """
    body = document.element.body
    sect_prs = body.xpath("./w:p/w:pPr/w:sectPr | ./w:sectPr")
    header = _default_furniture_part(document, sect_prs, "w:headerReference")
    footer = _default_furniture_part(document, sect_prs, "w:footerReference")
    if header is None and footer is None:
        return None
    header_left = header_right = footer_text = footer_logo = None
    if header is not None:
        for p_el in _furniture_paragraphs(header.element):
            text = _furniture_text(p_el)
            if text.strip():
                left, _, right = text.partition("\t")
                header_left = left.strip() or None
                header_right = " ".join(piece.strip() for piece in right.split("\t") if piece.strip()) or None
                break
    if footer is not None:
        for p_el in _furniture_paragraphs(footer.element):
            footer_text = _furniture_text(p_el).partition("\t")[0].strip() or None
            if footer_text:
                break
        footer_logo = _footer_logo_image_id(footer)
    return {
        "header_left": header_left,
        "header_right": header_right,
        "footer_text": footer_text,
        "footer_logo_image_id": footer_logo,
    }


def _page_setup(document) -> dict | None:
    """Page size and margins (pt) of the body's final ``w:sectPr``."""
    sect_pr = document.element.body.find(qn("w:sectPr"))
    if sect_pr is None:
        return None

    def points(read) -> float | None:
        try:
            length = read()
        except (ValueError, KeyError, TypeError):
            return None
        # A negative top/bottom margin lets text run under the header; the
        # margin itself is its absolute value.
        return abs(round(length.pt, 2)) if length is not None else None

    return {
        "width_pt": points(lambda: sect_pr.page_width),
        "height_pt": points(lambda: sect_pr.page_height),
        "margin_top_pt": points(lambda: sect_pr.top_margin),
        "margin_bottom_pt": points(lambda: sect_pr.bottom_margin),
        "margin_left_pt": points(lambda: sect_pr.left_margin),
        "margin_right_pt": points(lambda: sect_pr.right_margin),
    }


# ---------------------------------------------------------------------------
# Apply: overrides -> new .docx bytes
# ---------------------------------------------------------------------------


def _resolve_paragraph_element(blocks: dict[int, object], addr: str):
    """Resolve an override address to a CT_P element, or None.

    Only 1-part (top-level paragraph) and 4-part (cell paragraph) addresses
    can name a paragraph; anything else — including addresses pointing past
    the end of the document or at a table — resolves to None.
    """
    try:
        parts = [int(piece) for piece in addr.split(":")]
    except ValueError:
        return None
    if any(part < 0 for part in parts):
        return None

    if len(parts) == 1:
        element = blocks.get(parts[0])
        return element if isinstance(element, CT_P) else None

    if len(parts) != 4:
        return None
    tbl_el = blocks.get(parts[0])
    if not isinstance(tbl_el, CT_Tbl):
        return None
    rows = _row_elements(tbl_el)
    if parts[1] >= len(rows):
        return None
    cells = _cell_elements(rows[parts[1]])
    if parts[2] >= len(cells):
        return None
    paragraphs = _cell_paragraph_elements(cells[parts[2]])
    if parts[3] >= len(paragraphs):
        return None
    return paragraphs[parts[3]]


def _replace_paragraph_text(p_el, text: str, document) -> None:
    """Replace the paragraph's runs with ``text``, preserving formatting.

    The first run's rPr is captured as the formatting template and carried
    onto every new run. "\\n" in the override becomes a <w:br/> line break
    WITHIN the paragraph — never a new paragraph, so block addresses stay
    stable across edits.
    """
    # Normalize Windows/mac line endings so "\r\n" yields ONE <w:br/>,
    # not a doubled break. The PATCH endpoint normalizes stored values
    # too — this is the safety net for values persisted before that.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    rpr_template = None
    first_run = p_el.find(qn("w:r"))
    if first_run is not None:
        rpr = first_run.find(qn("w:rPr"))
        if rpr is not None:
            rpr_template = deepcopy(rpr)

    # Remove the existing runs. Hyperlink wrappers carry runs too — drop
    # them as well so the override fully replaces the visible text.
    # (Hyperlink paragraphs are locked upstream, so this branch is
    # defensive only — a lock bypass must not leave duplicated text.)
    for child in list(p_el):
        if child.tag in (qn("w:r"), qn("w:hyperlink")):
            p_el.remove(child)

    para = Paragraph(p_el, document)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        run = para.add_run(line)
        if rpr_template is not None:
            run._r.insert(0, deepcopy(rpr_template))
        if i < len(lines) - 1:
            run.add_break(WD_BREAK.LINE)


def apply_overrides_to_docx(docx_bytes: bytes, overrides: dict[str, str]) -> bytes:
    """Apply per-paragraph text overrides and return new .docx bytes.

    Unresolvable addresses and locked (non-editable) paragraphs are skipped
    silently (debug log only) — a stale override must never break the
    download. Styles, tables, images and headers/footers are untouched.
    """
    document = Document(io.BytesIO(docx_bytes))
    blocks = dict(_iter_body_blocks(document.element.body))

    for addr, text in overrides.items():
        if not isinstance(text, str):
            logger.debug("Override %s has a non-string value — skipped", addr)
            continue
        p_el = _resolve_paragraph_element(blocks, addr)
        if p_el is None:
            logger.debug("Override address %s does not resolve — skipped", addr)
            continue
        if _paragraph_is_locked(p_el):
            logger.debug("Override address %s targets a locked paragraph — skipped", addr)
            continue
        _replace_paragraph_text(p_el, text, document)

    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Inline image extraction (preview <img> endpoint)
# ---------------------------------------------------------------------------


def extract_image(docx_bytes: bytes, image_id: str) -> tuple[bytes, str] | None:
    """Return ``(blob, content_type)`` for a relationship id, or None.

    ``image_id`` is the rId on the main document part, exactly as emitted
    in the parse output's ``images[].image_id``. Non-image parts (an rId
    pointing at styles, numbering, …) return None as well — the endpoint
    only ever serves actual pictures.
    """
    document = Document(io.BytesIO(docx_bytes))
    try:
        part = document.part.related_parts[image_id]
    except KeyError:
        return None
    content_type = getattr(part, "content_type", None)
    if not content_type or not content_type.startswith("image/"):
        return None
    return part.blob, content_type


# OPC relationships namespace (the .rels part, NOT the document r: namespace).
_RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

# Extensions mimetypes doesn't reliably know but Word embeds routinely.
_IMAGE_CT_FALLBACK = {
    ".emf": "image/x-emf",
    ".wmf": "image/x-wmf",
    ".svg": "image/svg+xml",
}


# Part-scoped id of a header or footer picture: "ftr:footer2.xml:rId1". The
# part name is matched whole — a bare file name in word/, so no path can
# escape it — and must agree with the prefix. A relationship id is an
# NCName, so it never holds a colon.
_PART_IMAGE_ID_RE = re.compile(
    r"(?:hdr:(?P<header>header\d+\.xml)|ftr:(?P<footer>footer\d+\.xml)):(?P<rid>[A-Za-z_][\w.\-]*)"
)


def extract_image_fast(docx_bytes: bytes, image_id: str) -> tuple[bytes, str] | None:
    """Zip-level equivalent of :func:`extract_image` — no python-docx parse.

    ``Document(bytes)`` parses the entire main part (~seconds on the 4.8MB
    DVR) just to serve one picture; here we only read one part's .rels to
    map the id -> Target and pull that entry out of the archive.

    ``image_id`` is a main-part rId (``rId9``) or a header/footer picture
    scoped to its part (``hdr:header1.xml:rId1``, ``ftr:footer2.xml:rId1``),
    resolved through that part's own .rels. Returns None for unknown or
    malformed ids, non-image relationships, external targets and missing
    parts — exactly like the slow path, which is kept for compatibility.
    """
    if ":" in image_id:
        match = _PART_IMAGE_ID_RE.fullmatch(image_id)
        if match is None:
            return None
        rels_name = f"word/_rels/{match['header'] or match['footer']}.rels"
        rel_id = match["rid"]
    else:
        rels_name = "word/_rels/document.xml.rels"
        rel_id = image_id
    try:
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
            return _read_related_image(zf, rels_name, rel_id)
    except zipfile.BadZipFile:
        return None


def _read_related_image(zf: zipfile.ZipFile, rels_name: str, rel_id: str) -> tuple[bytes, str] | None:
    """The image ``rel_id`` names in the ``rels_name`` part relationships of
    a word/ part (main document, header or footer), or None."""
    try:
        rels_xml = zf.read(rels_name)
    except KeyError:
        return None
    try:
        root = ElementTree.fromstring(rels_xml)
    except ElementTree.ParseError:
        return None
    for rel in root.iter(f"{{{_RELS_NS}}}Relationship"):
        if rel.get("Id") != rel_id:
            continue
        if (rel.get("TargetMode") or "").lower() == "external":
            return None
        if not (rel.get("Type") or "").endswith("/image"):
            return None
        target = rel.get("Target") or ""
        if target.startswith("/"):
            # Absolute part name ("/word/media/x.png").
            part_name = target.lstrip("/")
        else:
            # Relative to the source part's folder (word/); normpath
            # resolves "../" segments ("../media/x.png" -> "media/x.png").
            part_name = posixpath.normpath(posixpath.join("word", target))
        try:
            blob = zf.read(part_name)
        except KeyError:
            return None
        content_type, _ = mimetypes.guess_type(part_name)
        if not content_type or not content_type.startswith("image/"):
            ext = posixpath.splitext(part_name)[1].lower()
            content_type = _IMAGE_CT_FALLBACK.get(ext, "image/png")
        return blob, content_type
    return None
