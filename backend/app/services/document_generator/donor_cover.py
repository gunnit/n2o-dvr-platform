"""The design kit on documents opened from a donor template.

Eight attachments (Gestanti, Incendio, Stress, DUVRI, POS, PEE azienda and
comune, HACCP manuale) open one of N2O's completed documents from
``templates/`` and fill it. They take the kit's *look* while keeping the
donor's structure (spec 2026-11-10 §4.4):

- :func:`strip_donor_cover` removes the donor's own cover page (ported from
  draft PR #82, commit af2a5d5, where it was tested on the real templates);
- :func:`insert_kit_cover_at_top` puts the kit's attachment cover in its place;
- :func:`normalize_fonts` prints the donor in Arial at its own sizes, so its
  pages do not jump.

The back cover and the running header and footer come from the kit as for
every other document (``add_back_cover``, ``finish_document``).
"""

from __future__ import annotations

from typing import Any

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from app.services.document_generator.design import (
    _crop_to_cover,
    _is_page_break_only,
    _page_size,
    add_cover,
    art_marker,
    cover_block_lead,
)
from app.services.document_generator.docx_utils import FONT_FAMILY, SYMBOL_FONTS, set_font_slots

_PARA_SECTPR = f"{qn('w:pPr')}/{qn('w:sectPr')}"


def _body_blocks(doc: Document) -> list:
    """Body children in order, minus the trailing section properties."""
    return [el for el in doc.element.body if el.tag != qn("w:sectPr")]


# ---------------------------------------------------------------------------
# Donor cover
# ---------------------------------------------------------------------------

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
        if el.find(_PARA_SECTPR) is not None:
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


def _starts_new_page(element, styles) -> bool:
    """True when ``element`` opens a page by itself: a paragraph holding only
    a page break, one with page-break-before (directly or from its style in
    ``styles``, the styles part's root), or an empty paragraph ending a
    section whose successor starts on a new page. A page break in front of
    it would leave an empty page."""
    if element is None or element.tag != qn("w:p"):
        return False
    if _is_page_break_only(element):
        return True
    if _page_break_before(element, styles):
        return True
    if element.find(_PARA_SECTPR) is None or "".join(t.text or "" for t in element.iter(qn("w:t"))).strip():
        return False
    following = element.getnext()
    while following is not None:
        sect_pr = following if following.tag == qn("w:sectPr") else following.find(_PARA_SECTPR)
        if sect_pr is not None:
            kind = sect_pr.find(qn("w:type"))
            start = kind.get(qn("w:val")) if kind is not None else "nextPage"
            return start in ("nextPage", "evenPage", "oddPage")
        following = following.getnext()
    return False


def _flag_on(element) -> bool | None:
    if element is None:
        return None
    return element.get(qn("w:val")) not in ("0", "false", "off")


def _page_break_before(paragraph, styles) -> bool:
    """Page-break-before on the paragraph, else from its style chain."""
    own = _flag_on(paragraph.find(f"{qn('w:pPr')}/{qn('w:pageBreakBefore')}"))
    if own is not None:
        return own
    style_ids = paragraph.xpath("./w:pPr/w:pStyle/@w:val")
    if not style_ids or styles is None:
        return False
    by_id = {style.get(qn("w:styleId")): style for style in styles.iter(qn("w:style"))}
    seen: set[str] = set()
    style_id = style_ids[0]
    while style_id and style_id not in seen and style_id in by_id:
        seen.add(style_id)
        style = by_id[style_id]
        flag = _flag_on(style.find(f"{qn('w:pPr')}/{qn('w:pageBreakBefore')}"))
        if flag is not None:
            return flag
        based = style.find(qn("w:basedOn"))
        style_id = based.get(qn("w:val")) if based is not None else None
    return False


def _fit_art_to_section(doc: Document, art, section) -> None:
    """Size a cover anchor to ``section``'s page and crop the picture to it."""
    anchor = art.find(f".//{qn('wp:anchor')}")
    if anchor is None:
        return
    width, height = _page_size(section)
    extent = anchor.find(qn("wp:extent"))
    if extent is not None:
        extent.set("cx", str(width))
        extent.set("cy", str(height))
    for ext in anchor.iter(qn("a:ext")):
        if ext.getparent().tag == qn("a:xfrm"):
            ext.set("cx", str(width))
            ext.set("cy", str(height))
    for rect in list(anchor.iter(qn("a:srcRect"))):
        rect.getparent().remove(rect)
    blip = anchor.find(f".//{qn('a:blip')}")
    image_part = doc.part.related_parts.get(blip.get(qn("r:embed"))) if blip is not None else None
    if image_part is not None:
        _crop_to_cover(anchor, image_part.image, width, height)


def insert_kit_cover_at_top(doc: Document, **cover: Any) -> int:
    """The kit's attachment cover (:func:`design.add_cover`, same keyword
    arguments) in front of an existing donor body.

    ``add_cover`` appends and sizes its art to the last section; here its
    blocks move to the start of the body, into the donor's first section,
    and the art and the title block's distance from the top edge are fitted
    to that section's page. The cover's closing page break is dropped when
    what follows opens a page by itself (the section break the donor cover
    ended on, or a page break of the generator's own): two in a row would
    leave an empty page.

    Call it after the donor's scrubs and picture sweeps, which would rewrite
    the letterhead or remove the art. Returns the number of body blocks the
    cover occupies.
    """
    last = doc.sections[-1]
    last_title_page = last.different_first_page_header_footer
    count = len(_body_blocks(doc))
    add_cover(doc, **cover)
    added = _body_blocks(doc)[count:]
    if not added:
        return 0

    body = doc.element.body
    for index, el in enumerate(added):
        body.remove(el)
        body.insert(index, el)

    first = doc.sections[0]
    art = added[0] if art_marker(added[0]) else None
    if len(doc.sections) > 1:
        # add_cover flagged the section it was appended to.
        last.different_first_page_header_footer = last_title_page
    if art is not None:
        _fit_art_to_section(doc, art, first)
        first.different_first_page_header_footer = True

    # The title block starts COVER_BLOCK_TOP_CM from the top edge of the
    # cover's own page (add_cover measured it on the last section).
    lead = added[1] if art is not None else added[0]
    Paragraph(lead, doc._body).paragraph_format.space_before = cover_block_lead(first)

    page_break = added[-1]
    if _is_page_break_only(page_break) and _starts_new_page(page_break.getnext(), doc.styles.element):
        body.remove(page_break)
        added = added[:-1]
    return len(added)


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

def _is_symbol_font(rfonts) -> bool:
    return any(
        (rfonts.get(qn(slot)) or "").strip().lower() in SYMBOL_FONTS
        for slot in ("w:ascii", "w:hAnsi")
    )


def _point_at(rfonts, family: str) -> bool:
    """Set the four slots to ``family``; True when anything changed."""
    before = dict(rfonts.attrib)
    set_font_slots(rfonts, family)
    return dict(rfonts.attrib) != before


def _numbering_root(doc: Document):
    """The numbering part's root element, or ``None`` when the document has
    none. (``doc.part.numbering_part`` would create an empty one.)"""
    try:
        part = doc.part.part_related_by(RT.NUMBERING)
    except KeyError:
        return None
    return getattr(part, "element", None)


def _story_roots(doc: Document) -> list:
    """The document part and every header and footer part, once each."""
    roots = [doc.element]
    seen = {id(doc.part)}
    for rel in doc.part.rels.values():
        if rel.is_external or rel.reltype not in (RT.HEADER, RT.FOOTER):
            continue
        part = rel.target_part
        if id(part) in seen:
            continue
        seen.add(id(part))
        roots.append(part.element)
    return roots


def normalize_fonts(doc: Document, family: str = FONT_FAMILY) -> int:
    """Set ``family`` (Arial) on every style, every list level and every run
    of the body, headers and footers. Returns the number of runs changed.

    All four ``w:rFonts`` slots are written (ascii, hAnsi, eastAsia, cs) and
    theme attributes dropped, which Word would otherwise read first. The
    document defaults get the family too, so a run or style that names no
    font inherits it; such runs are left as they are. Every other font
    declaration of the body, headers and footers (paragraph marks, content
    controls) is rewritten like a run's, and so are the levels of
    ``numbering.xml``, whose font prints the list labels ("a)", "1.").

    Never touched: a font declaration naming Symbol, Wingdings (1-3) or
    Webdings, and any run holding a ``w:sym``. Their characters are bullets
    and check boxes that print as other characters in Arial. Sizes are
    never changed, so the donor's pages keep their length.
    """
    styles = doc.styles.element
    defaults = styles.find(qn("w:docDefaults"))
    if defaults is None:
        defaults = OxmlElement("w:docDefaults")
        styles.insert(0, defaults)
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
    numbering = _numbering_root(doc)
    for root in (styles,) if numbering is None else (styles, numbering):
        for rfonts in root.iter(qn("w:rFonts")):
            if not _is_symbol_font(rfonts):
                set_font_slots(rfonts, family)

    changed = 0
    for root in _story_roots(doc):
        for rfonts in root.iter(qn("w:rFonts")):
            rpr = rfonts.getparent()
            owner = rpr.getparent() if rpr is not None else None
            is_run = owner is not None and owner.tag == qn("w:r")
            if is_run and owner.find(qn("w:sym")) is not None:
                continue
            if _is_symbol_font(rfonts):
                continue
            if _point_at(rfonts, family) and is_run:
                changed += 1
    return changed
