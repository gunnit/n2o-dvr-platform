/**
 * The document's own look, as CSS: what a paragraph or run of the preview
 * payload looks like on paper, in points and Arial.
 *
 * Scoped to the sheet. The app around it keeps DESIGN.md; inside a sheet
 * these values reproduce the .docx (spec 2026-11-10 §4.3.2). Pure functions
 * (no React at runtime), unit-tested in tests/document-editor-look.test.mjs.
 *
 * The cascade for text is the paragraph's style (`style_props`, already
 * resolved through basedOn and docDefaults), then the run's own fields. A
 * paragraph's `direct` adds its paragraph-level keys (alignment, spacing,
 * indent). Its run-level keys describe the paragraph mark, which Word
 * prints only as the height of a paragraph without text — they never
 * colour or size the text.
 */

import type { CSSProperties } from "react";

import type {
  PreviewAlignment,
  PreviewBlock,
  PreviewParagraph,
  PreviewRun,
  PreviewStyleProps,
} from "@/types";

// With its extension: the unit tests load these modules in Node, which
// resolves no extensionless path (tsconfig allowImportingTsExtensions).
import { hasVisibleText } from "./doc-sheets.ts";

// Tokens of the design kit (backend/app/services/document_generator/design.py).
export const DOC_FONT_FAMILY = 'Arial, "Liberation Sans", Helvetica, sans-serif';
export const DOC_NAVY = "#003D74";
/** Header and footer hairlines. */
export const DOC_RULE = "#C9D3DF";
/** Footer text. */
export const DOC_SLATE = "#64748D";
/** Table Grid: single ½ pt black borders. */
export const DOC_TABLE_BORDER = "0.5pt solid #000";
/** Word's cell margins: 0.19 cm left and right, none above or below. */
export const DOC_CELL_PADDING = "0 5.4pt";
/** The kit's 1.08 line spacing over Arial's natural 1.15 em line. */
export const DOC_LINE_HEIGHT = 1.24;

// Word's own size when nothing in the style chain sets one.
const DEFAULT_SIZE_PT = 10;
// Word's default list geometry: text 18 pt further in per level, the
// marker hanging 18 pt to the left of it.
const LIST_STEP_PT = 18;

export type StylePropsTable = Record<string, PreviewStyleProps>;

// Payloads from before the layout redesign carry no style_props, and a
// style the backend could not resolve is left out of them: such paragraphs
// get the type scale of the documents generated before the redesign.
const FALLBACK_BODY: PreviewStyleProps = {
  font_size_pt: DEFAULT_SIZE_PT,
  bold: false,
  italic: false,
  caps: false,
  color: null,
  alignment: null,
  space_before_pt: 0,
  space_after_pt: 4,
  indent_left_pt: null,
  outline_level: null,
};

function fallbackHeading(
  level: number,
  sizePt: number,
  beforePt: number,
  afterPt: number,
): PreviewStyleProps {
  return {
    ...FALLBACK_BODY,
    font_size_pt: sizePt,
    bold: true,
    color: DOC_NAVY.slice(1),
    space_before_pt: beforePt,
    space_after_pt: afterPt,
    outline_level: level,
  };
}

const FALLBACK_HEADINGS: Record<number, PreviewStyleProps> = {
  1: fallbackHeading(1, 16, 18, 6),
  2: fallbackHeading(2, 13, 14, 4),
  3: fallbackHeading(3, 11, 10, 2),
  4: fallbackHeading(4, 11, 10, 2),
};

/** A paragraph's effective look, every value resolved. */
export interface ParagraphLook {
  /**
   * Font size of the paragraph box, in pt. It is the text size, except on
   * a paragraph without text, where the mark's own size sets the line
   * height (the kit's 1 pt spacers before art and section breaks).
   */
  sizePt: number;
  /** Size of text that sets none: the style's. */
  textSizePt: number;
  bold: boolean;
  italic: boolean;
  caps: boolean;
  /** "#RRGGBB"; null inherits the sheet's ink. */
  color: string | null;
  alignment: PreviewAlignment;
  spaceBeforePt: number;
  spaceAfterPt: number;
  /** Where the text starts; for a list item, right of its marker. */
  indentLeftPt: number;
  isListItem: boolean;
}

function positive(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) && value > 0
    ? value
    : null;
}

function finite(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/** "12pt", "14.15pt": two decimals at most. */
function pt(value: number): string {
  return `${Math.round(value * 100) / 100}pt`;
}

function styleOf(
  paragraph: PreviewParagraph,
  styleProps: StylePropsTable | null | undefined,
): PreviewStyleProps {
  if (styleProps && paragraph.style && Object.hasOwn(styleProps, paragraph.style)) {
    return styleProps[paragraph.style];
  }
  const level = paragraph.heading_level;
  if (level !== null && level !== undefined) {
    return FALLBACK_HEADINGS[Math.min(Math.max(level, 1), 4)];
  }
  if (styleProps && Object.hasOwn(styleProps, "Normal")) return styleProps.Normal;
  return FALLBACK_BODY;
}

/**
 * The look of a paragraph: its style's resolved properties, then its own
 * paragraph-level formatting (`direct`, or the legacy `alignment`).
 */
export function resolveParagraph(
  paragraph: PreviewParagraph,
  styleProps: StylePropsTable | null | undefined,
): ParagraphLook {
  const style = styleOf(paragraph, styleProps);
  const direct = paragraph.direct ?? {};
  const textSizePt = positive(style.font_size_pt) ?? DEFAULT_SIZE_PT;
  const markSizePt = hasVisibleText(paragraph.runs) ? null : positive(direct.font_size_pt);

  const list = paragraph.list ?? null;
  let indentLeftPt: number;
  if (list) {
    // A list's own indent lives in numbering.xml, which the payload does
    // not carry: only the paragraph's direct indent is more specific.
    const own = finite(direct.indent_left_pt);
    indentLeftPt = Math.max(own ?? LIST_STEP_PT * (list.level + 1), LIST_STEP_PT);
  } else {
    indentLeftPt = finite(direct.indent_left_pt) ?? finite(style.indent_left_pt) ?? 0;
  }

  return {
    sizePt: markSizePt ?? textSizePt,
    textSizePt,
    bold: style.bold === true,
    italic: style.italic === true,
    caps: style.caps === true,
    color: style.color ? `#${style.color}` : null,
    alignment: direct.alignment ?? paragraph.alignment ?? style.alignment ?? "left",
    spaceBeforePt: finite(direct.space_before_pt) ?? finite(style.space_before_pt) ?? 0,
    spaceAfterPt: finite(direct.space_after_pt) ?? finite(style.space_after_pt) ?? 0,
    indentLeftPt,
    isListItem: list !== null,
  };
}

/** CSS of a paragraph box: type, colour, alignment, spacing and indent. */
export function paragraphStyle(look: ParagraphLook): CSSProperties {
  const css: CSSProperties = {
    fontFamily: DOC_FONT_FAMILY,
    fontSize: pt(look.sizePt),
    lineHeight: DOC_LINE_HEIGHT,
    textAlign: look.alignment,
    marginTop: pt(look.spaceBeforePt),
    marginBottom: pt(look.spaceAfterPt),
  };
  if (look.bold) css.fontWeight = 700;
  if (look.italic) css.fontStyle = "italic";
  if (look.caps) css.textTransform = "uppercase";
  if (look.color) css.color = look.color;
  if (look.indentLeftPt !== 0) css.marginLeft = pt(look.indentLeftPt);
  // The list marker is positioned against the box.
  if (look.isListItem) css.position = "relative";
  return css;
}

/** `paragraphStyle(resolveParagraph(paragraph, styleProps))`. */
export function effectiveParagraphStyle(
  paragraph: PreviewParagraph,
  styleProps: StylePropsTable | null | undefined,
): CSSProperties {
  return paragraphStyle(resolveParagraph(paragraph, styleProps));
}

/**
 * CSS a run adds to its paragraph box: only what it sets. A run reports
 * `bold: false` both when unset and when off, so false inherits the style;
 * `size` and `color` null inherit too. Capitals are three-state: `caps:
 * false` is explicitly off and prints the text as typed even in a
 * capitalised heading; null or absent inherits.
 */
export function effectiveRunStyle(
  run: PreviewRun,
  look: ParagraphLook,
): CSSProperties {
  const css: CSSProperties = {};
  const sizePt = positive(run.size) ?? look.textSizePt;
  if (sizePt !== look.sizePt) css.fontSize = pt(sizePt);
  if (run.color) css.color = `#${run.color}`;
  if (run.bold && !look.bold) css.fontWeight = 700;
  if (run.italic && !look.italic) css.fontStyle = "italic";
  if (run.underline) css.textDecoration = "underline";
  if (run.caps === true && !look.caps) css.textTransform = "uppercase";
  if (run.caps === false && look.caps) css.textTransform = "none";
  return css;
}

const NO_RUN: PreviewRun = {
  text: "",
  bold: false,
  italic: false,
  underline: false,
  color: null,
  size: null,
};

/**
 * The look of text that replaces a paragraph's runs (an override, or the
 * live edit): the backend writes it with the first run's formatting.
 */
export function replacementRunStyle(
  paragraph: PreviewParagraph,
  look: ParagraphLook,
): CSSProperties {
  return effectiveRunStyle(paragraph.runs[0] ?? NO_RUN, look);
}

/** CSS of a list marker, hanging left of its paragraph's text. */
export function listMarkerStyle(): CSSProperties {
  return {
    position: "absolute",
    top: 0,
    left: pt(-LIST_STEP_PT),
    width: pt(LIST_STEP_PT),
    textAlign: "left",
    whiteSpace: "nowrap",
    userSelect: "none",
  };
}

// ---------------------------------------------------------------------------
// List markers
// ---------------------------------------------------------------------------

// "%1", "%2" … in a numbered level's lvlText stand for the counters of
// levels 1, 2 … (Word's 1-based level numbers).
const NUMBERED = /%[1-9]/;
const LEVEL_PLACEHOLDERS = /%([1-9])/g;

/**
 * Number one run of paragraphs. `null` interrupts the run (a table between
 * top-level paragraphs). Consecutive items of a level count up; an item
 * restarts the levels below it; anything that is not a list item restarts
 * everything — the payload has no numId to follow a list further.
 */
function markRun(
  paragraphs: Array<PreviewParagraph | null>,
  markers: Map<string, string>,
): void {
  let counters: number[] = [];
  for (const paragraph of paragraphs) {
    const list = paragraph?.list ?? null;
    if (paragraph === null || list === null) {
      counters = [];
      continue;
    }
    const level = Math.max(0, list.level);
    if (!NUMBERED.test(list.glyph)) {
      // A bullet: printed as is; numbered levels below it restart.
      counters.length = Math.min(counters.length, level + 1);
      markers.set(paragraph.addr, list.glyph);
      continue;
    }
    counters[level] = (counters[level] ?? 0) + 1;
    counters.length = level + 1;
    markers.set(
      paragraph.addr,
      list.glyph.replace(LEVEL_PLACEHOLDERS, (_, digit: string) =>
        String(counters[Number(digit) - 1] ?? 1),
      ),
    );
  }
}

/**
 * The marker each list paragraph shows, by address: a bullet's glyph as
 * is, a numbered pattern ("%1.", "%1.%2.") with its counters filled in.
 * Top-level paragraphs number as one run; each table cell as its own.
 */
export function computeListMarkers(blocks: PreviewBlock[]): Map<string, string> {
  const markers = new Map<string, string>();
  const topLevel: Array<PreviewParagraph | null> = [];
  for (const block of blocks) {
    if (block.kind === "paragraph") {
      topLevel.push(block);
      continue;
    }
    topLevel.push(null);
    for (const row of block.rows) {
      for (const cell of row) markRun(cell.paragraphs, markers);
    }
  }
  markRun(topLevel, markers);
  return markers;
}
