/**
 * How the editor cuts a document into sheets, and how big a sheet is.
 *
 * Pure functions (no React) so they are unit-tested on their own:
 * tests/document-editor-look.test.mjs. A sheet is where Word starts a page
 * on purpose — a page break, a section break or an art page — not a printed
 * page: a browser cannot reproduce Word's pagination, so a long section
 * simply makes a longer sheet and the editor shows no page numbers
 * (spec 2026-11-10 §3 decision 4, §4.3.2).
 */

import type {
  PreviewBlock,
  PreviewPageRole,
  PreviewPageSetup,
  PreviewParagraph,
  PreviewParagraphBlock,
  PreviewRun,
} from "@/types";

export type SheetRole = PreviewPageRole | "content";

export interface Sheet {
  /** "cover", "divider" and "back_cover" are art sheets; the rest are content. */
  role: SheetRole;
  /** An art sheet's full-page picture (main-part image id); null otherwise. */
  backgroundImageId: string | null;
  blocks: PreviewBlock[];
}

/**
 * Whether some run shows text: anything but whitespace. The preview contract
 * judges a paragraph so (the backend's `has_text`): spaces, tabs or line
 * breaks print nothing, and the paragraph mark sets the line's height. The
 * one predicate behind blank lines, page-break lines and the mark's size.
 */
export function hasVisibleText(runs: readonly PreviewRun[]): boolean {
  return runs.some((run) => run.text.trim() !== "");
}

/** No text and no picture: a line that only holds a break or spacing. */
function isBlankParagraph(block: PreviewBlock): boolean {
  return (
    block.kind === "paragraph" &&
    block.images.length === 0 &&
    !hasVisibleText(block.runs)
  );
}

/**
 * A paragraph that only carries a page break (`w:br w:type="page"`): it
 * opens its sheet, and Word prints nothing for it at the top of the page.
 */
export function isPageBreakLine(block: PreviewParagraphBlock): boolean {
  return (
    block.page_break_before &&
    !block.editable &&
    block.images.length === 0 &&
    !hasVisibleText(block.runs)
  );
}

/**
 * Split the block stream into sheets. A sheet starts at a paragraph with
 * `page_break_before`, after a paragraph with `section_break_after`, and at
 * a paragraph with a `page_role` (the art of a cover, divider or back
 * cover), which makes it an art sheet. A section break followed by art
 * opens one sheet, not two. Art that follows nothing but blank lines (a
 * lone page break) takes that sheet over instead of leaving a blank page:
 * Word anchors the picture to the page those lines are on.
 */
export function groupIntoSheets(blocks: PreviewBlock[]): Sheet[] {
  const sheets: Sheet[] = [];
  let current: Sheet | null = null;
  let afterSectionBreak = false;

  for (const block of blocks) {
    const paragraph: PreviewParagraph | null =
      block.kind === "paragraph" ? block : null;
    const role = paragraph?.page_role ?? null;
    const backgroundImageId = paragraph?.background_image_id ?? null;
    const pageBreakBefore = block.kind === "paragraph" && block.page_break_before;

    const takesOverBlankSheet =
      current !== null &&
      role !== null &&
      !afterSectionBreak &&
      !pageBreakBefore &&
      current.role === "content" &&
      current.blocks.every(isBlankParagraph);

    if (takesOverBlankSheet && current !== null) {
      current.role = role;
      current.backgroundImageId = backgroundImageId;
    } else if (
      current === null ||
      afterSectionBreak ||
      pageBreakBefore ||
      role !== null
    ) {
      current = { role: role ?? "content", backgroundImageId, blocks: [] };
      sheets.push(current);
    }

    current.blocks.push(block);
    afterSectionBreak = paragraph?.section_break_after === true;
  }
  return sheets;
}

// ---------------------------------------------------------------------------
// Geometry
// ---------------------------------------------------------------------------

export interface SheetGeometry {
  widthPx: number;
  /** The sheet's minimum height: it grows with a long section. */
  heightPx: number;
  /** The page margins. */
  paddingTopPx: number;
  paddingBottomPx: number;
  paddingLeftPx: number;
  paddingRightPx: number;
  /**
   * The page inside its margins: the placeholder (contain-intrinsic-size)
   * of a sheet skipped off screen, to which content-visibility adds the
   * padding back — so a skipped sheet is exactly one page high.
   */
  contentWidthPx: number;
  contentHeightPx: number;
}

// CSS pixels are 1/96 in, points 1/72 in.
const PX_PER_PT = 96 / 72;
const PT_PER_CM = 72 / 2.54;

// A4 with the design kit's margins (top, bottom, left, right: 2.0 / 2.0 /
// 2.5 / 2.0 cm), for payloads without a page setup — cached from before the
// layout redesign, or a body without section properties.
const FALLBACK_PT = {
  width: 21 * PT_PER_CM,
  height: 29.7 * PT_PER_CM,
  top: 2.0 * PT_PER_CM,
  bottom: 2.0 * PT_PER_CM,
  left: 2.5 * PT_PER_CM,
  right: 2.0 * PT_PER_CM,
};

const round2 = (px: number): number => Math.round(px * 100) / 100;

function toPx(
  points: number | null | undefined,
  fallbackPt: number,
  allowZero: boolean,
): number {
  const usable =
    typeof points === "number" &&
    Number.isFinite(points) &&
    (allowZero ? points >= 0 : points > 0);
  return round2((usable ? points : fallbackPt) * PX_PER_PT);
}

/**
 * Sheet size and margins from the document's page setup (points) at 96 dpi:
 * A4 is about 794 × 1123 px. Each missing or unusable value falls back on
 * its own; donor-template documents keep their own geometry this way.
 */
export function sheetGeometry(
  pageSetup: PreviewPageSetup | null | undefined,
): SheetGeometry {
  const widthPx = toPx(pageSetup?.width_pt, FALLBACK_PT.width, false);
  const heightPx = toPx(pageSetup?.height_pt, FALLBACK_PT.height, false);
  const paddingTopPx = toPx(pageSetup?.margin_top_pt, FALLBACK_PT.top, true);
  const paddingBottomPx = toPx(pageSetup?.margin_bottom_pt, FALLBACK_PT.bottom, true);
  const paddingLeftPx = toPx(pageSetup?.margin_left_pt, FALLBACK_PT.left, true);
  const paddingRightPx = toPx(pageSetup?.margin_right_pt, FALLBACK_PT.right, true);
  return {
    widthPx,
    heightPx,
    paddingTopPx,
    paddingBottomPx,
    paddingLeftPx,
    paddingRightPx,
    contentWidthPx: round2(Math.max(0, widthPx - paddingLeftPx - paddingRightPx)),
    contentHeightPx: round2(Math.max(0, heightPx - paddingTopPx - paddingBottomPx)),
  };
}
