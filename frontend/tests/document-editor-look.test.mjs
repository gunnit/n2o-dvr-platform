import assert from "node:assert/strict";
import test from "node:test";

import {
  groupIntoSheets,
  hasVisibleText,
  isPageBreakLine,
  sheetGeometry,
} from "../src/components/documents/editor/doc-sheets.ts";
import {
  computeListMarkers,
  effectiveParagraphStyle,
  effectiveRunStyle,
  listMarkerStyle,
  replacementRunStyle,
  resolveParagraph,
} from "../src/components/documents/editor/doc-typography.ts";

// The editor draws a document the way it prints (spec 2026-11-10 §4.3.2):
// sheets that start where Word starts a page, Arial in points from the
// resolved styles, list markers and the page geometry of the .docx. The
// fixtures mirror GET /documenti/{id}/preview field for field.

function run(fields = {}) {
  return {
    text: "Testo",
    bold: false,
    italic: false,
    underline: false,
    color: null,
    size: null,
    // Unset: null. false is "explicitly off" (see the caps test).
    caps: null,
    ...fields,
  };
}

function para(addr, fields = {}) {
  return {
    kind: "paragraph",
    addr,
    style: "Normal",
    heading_level: null,
    alignment: null,
    editable: true,
    runs: [run({ text: `Paragrafo ${addr}` })],
    images: [],
    outline_level: null,
    direct: null,
    list: null,
    page_role: null,
    background_image_id: null,
    section_break_after: false,
    page_break_before: false,
    ...fields,
  };
}

/** A paragraph that holds only a page break (`w:br w:type="page"`). */
function pageBreak(addr, fields = {}) {
  return para(addr, {
    editable: false,
    runs: [run({ text: "" })],
    page_break_before: true,
    ...fields,
  });
}

/** The paragraph of a kit art page: a 1 pt line carrying the picture. */
function art(addr, role, imageId) {
  return para(addr, {
    editable: false,
    runs: [run({ text: "", size: 1.0 })],
    direct: { font_size_pt: 1.0, space_before_pt: 0.0, space_after_pt: 0.0 },
    page_role: role,
    background_image_id: imageId,
  });
}

function cell(addr, paragraphs) {
  return {
    addr,
    paragraphs,
    shading: null,
    col_span: 1,
    v_merge: null,
    v_align: null,
  };
}

function table(addr, rows = [[cell(`${addr}:0:0`, [])]]) {
  return { kind: "table", addr, rows, col_widths_pct: [100] };
}

const sheetsOf = (sheets) =>
  sheets.map((sheet) => [
    sheet.role,
    sheet.backgroundImageId,
    sheet.blocks.map((block) => block.addr),
  ]);

// ---------------------------------------------------------------------------
// Sheets
// ---------------------------------------------------------------------------

test("a page break starts a sheet, but the first block never leaves an empty one", () => {
  const sheets = groupIntoSheets([
    para("0", { page_break_before: true }),
    para("1"),
    pageBreak("2"),
    para("3"),
  ]);
  assert.deepEqual(sheetsOf(sheets), [
    ["content", null, ["0", "1"]],
    ["content", null, ["2", "3"]],
  ]);
});

test("whatever follows a section break starts a sheet, a table too", () => {
  const sheets = groupIntoSheets([
    para("0"),
    para("1", { section_break_after: true }),
    table("2"),
    para("3"),
  ]);
  assert.deepEqual(sheetsOf(sheets), [
    ["content", null, ["0", "1"]],
    ["content", null, ["2", "3"]],
  ]);
});

test("an art paragraph opens one sheet with its role and picture, also right after a section break", () => {
  const sheets = groupIntoSheets([
    art("0", "cover", "rId9"),
    pageBreak("1"),
    para("2", { section_break_after: true }),
    art("3", "divider", "rId11"),
    para("4", { style: "Heading 2", heading_level: 2 }),
    pageBreak("5"),
    para("6", { section_break_after: true }),
    art("7", "back_cover", "rId12"),
  ]);
  assert.deepEqual(sheetsOf(sheets), [
    ["cover", "rId9", ["0"]],
    ["content", null, ["1", "2"]],
    ["divider", "rId11", ["3", "4"]],
    ["content", null, ["5", "6"]],
    ["back_cover", "rId12", ["7"]],
  ]);
});

test("art right after a page-break line takes over that sheet instead of leaving it blank", () => {
  const sheets = groupIntoSheets([
    para("0"),
    pageBreak("1"),
    art("2", "divider", "rId11"),
    para("3"),
  ]);
  assert.deepEqual(sheetsOf(sheets), [
    ["content", null, ["0"]],
    ["divider", "rId11", ["1", "2", "3"]],
  ]);
});

test("whitespace is not text: one predicate, the backend's (a run shows text if it is more than whitespace)", () => {
  assert.equal(hasVisibleText([]), false);
  assert.equal(hasVisibleText([run({ text: "" }), run({ text: " \t\n " })]), false);
  assert.equal(hasVisibleText([run({ text: "  " }), run({ text: "x" })]), true);
});

test("a page-break line is a locked paragraph that carries the break and nothing visible", () => {
  assert.equal(isPageBreakLine(pageBreak("2")), true);
  assert.equal(
    isPageBreakLine(pageBreak("3", { runs: [run({ text: "  " }), run({ text: "\t" })] })),
    true,
  );
  assert.equal(isPageBreakLine(pageBreak("4", { runs: [run({ text: "Indice" })] })), false);
  assert.equal(isPageBreakLine(pageBreak("5", { editable: true })), false);
  assert.equal(
    isPageBreakLine(
      pageBreak("6", { images: [{ image_id: "rId7", width_px: 100, height_px: 80 }] }),
    ),
    false,
  );
  assert.equal(isPageBreakLine(pageBreak("7", { page_break_before: false })), false);
});

test("lines of whitespace before art count as blank: the art takes their sheet over", () => {
  const sheets = groupIntoSheets([
    para("0"),
    pageBreak("1", { runs: [run({ text: " " })] }),
    para("2", { editable: false, runs: [run({ text: "\t" })] }),
    art("3", "divider", "rId11"),
  ]);
  assert.deepEqual(sheetsOf(sheets), [
    ["content", null, ["0"]],
    ["divider", "rId11", ["1", "2", "3"]],
  ]);
});

test("a payload from before the layout redesign is grouped by its page breaks", () => {
  const legacy = (addr, pageBreakBefore) => ({
    kind: "paragraph",
    addr,
    style: "Normal",
    heading_level: null,
    alignment: null,
    editable: true,
    runs: [{ text: "Testo", bold: false, italic: false, underline: false, color: null, size: null }],
    images: [],
    page_break_before: pageBreakBefore,
  });
  const legacyTable = { kind: "table", addr: "1", rows: [] };
  const sheets = groupIntoSheets([
    legacy("0", false),
    legacyTable,
    legacy("2", true),
    legacy("3", false),
  ]);
  assert.deepEqual(sheetsOf(sheets), [
    ["content", null, ["0", "1"]],
    ["content", null, ["2", "3"]],
  ]);
});

test("the sheet takes the page setup, converted from points to CSS pixels at 96 dpi", () => {
  const geometry = sheetGeometry({
    width_pt: 595.3,
    height_pt: 841.9,
    margin_top_pt: 56.7,
    margin_bottom_pt: 56.7,
    margin_left_pt: 70.85,
    margin_right_pt: 56.7,
  });
  assert.deepEqual(geometry, {
    widthPx: 793.73,
    heightPx: 1122.53,
    paddingTopPx: 75.6,
    paddingBottomPx: 75.6,
    paddingLeftPx: 94.47,
    paddingRightPx: 75.6,
    contentWidthPx: 623.66,
    contentHeightPx: 971.33,
  });
});

// A4, margins 2.0 (top) / 2.0 (bottom) / 2.5 (left) / 2.0 (right) cm.
const A4_KIT = {
  widthPx: 793.7,
  heightPx: 1122.52,
  paddingTopPx: 75.59,
  paddingBottomPx: 75.59,
  paddingLeftPx: 94.49,
  paddingRightPx: 75.59,
  contentWidthPx: 623.62,
  contentHeightPx: 971.34,
};

test("without a page setup the sheet is A4 with the kit's margins", () => {
  assert.deepEqual(sheetGeometry(null), A4_KIT);
  assert.deepEqual(sheetGeometry(undefined), A4_KIT);
});

test("a sheet skipped off screen keeps one page's height: its placeholder is the page's content box", () => {
  // content-visibility adds the padding (the margins) to contain-intrinsic-size;
  // a placeholder of the full page made every skipped sheet a margin too tall,
  // and a jump from the index overshot its heading by that much per sheet.
  const geometry = sheetGeometry({
    width_pt: 595.3,
    height_pt: 841.9,
    margin_top_pt: 56.7,
    margin_bottom_pt: 56.7,
    margin_left_pt: 70.85,
    margin_right_pt: 56.7,
  });
  assert.equal(geometry.contentWidthPx, 623.66);
  assert.equal(geometry.contentHeightPx, 971.33);
  assert.equal(
    Math.round((geometry.contentHeightPx + geometry.paddingTopPx + geometry.paddingBottomPx) * 100) / 100,
    geometry.heightPx,
  );
});

test("each missing or unusable page-setup value falls back on its own", () => {
  const geometry = sheetGeometry({
    width_pt: 841.9,
    height_pt: null,
    margin_top_pt: 28.35,
    margin_bottom_pt: 0,
    margin_left_pt: -3,
    margin_right_pt: null,
  });
  assert.deepEqual(geometry, {
    widthPx: 1122.53,
    heightPx: 1122.52,
    paddingTopPx: 37.8,
    paddingBottomPx: 0,
    paddingLeftPx: 94.49,
    paddingRightPx: 75.59,
    contentWidthPx: 952.45,
    contentHeightPx: 1084.72,
  });
});

// ---------------------------------------------------------------------------
// Typography
// ---------------------------------------------------------------------------

const ARIAL = 'Arial, "Liberation Sans", Helvetica, sans-serif';

// style_props of a kit document, as the endpoint resolves them.
const NORMAL = {
  font_size_pt: 12.0,
  bold: false,
  italic: false,
  caps: false,
  color: "061B31",
  alignment: null,
  space_before_pt: null,
  space_after_pt: 4.0,
  indent_left_pt: null,
  outline_level: null,
};
const KIT_STYLES = {
  Normal: NORMAL,
  "Heading 2": {
    font_size_pt: 25.0,
    bold: true,
    italic: false,
    caps: true,
    color: "003D74",
    alignment: "center",
    space_before_pt: 6.0,
    space_after_pt: 18.0,
    indent_left_pt: null,
    outline_level: 2,
  },
  "List Bullet": NORMAL,
};

const LOOK_KEYS = [
  "fontFamily",
  "fontSize",
  "fontWeight",
  "fontStyle",
  "textTransform",
  "color",
  "textAlign",
  "marginTop",
  "marginBottom",
  "marginLeft",
];
const lookOf = (css) =>
  Object.fromEntries(
    LOOK_KEYS.filter((key) => css[key] !== undefined).map((key) => [key, css[key]]),
  );

test("a paragraph takes its style's resolved look in points and Arial, direct paragraph keys on top", () => {
  const title = para("10", {
    style: "Heading 2",
    heading_level: 2,
    outline_level: 2,
    direct: { space_before_pt: 18.0 },
  });
  assert.deepEqual(lookOf(effectiveParagraphStyle(title, KIT_STYLES)), {
    fontFamily: ARIAL,
    fontSize: "25pt",
    fontWeight: 700,
    textTransform: "uppercase",
    color: "#003D74",
    textAlign: "center",
    marginTop: "18pt",
    marginBottom: "18pt",
  });

  const indented = para("5", {
    direct: { alignment: "justify", space_after_pt: 2.0, indent_left_pt: 14.15 },
  });
  assert.deepEqual(lookOf(effectiveParagraphStyle(indented, KIT_STYLES)), {
    fontFamily: ARIAL,
    fontSize: "12pt",
    color: "#061B31",
    textAlign: "justify",
    marginTop: "0pt",
    marginBottom: "2pt",
    marginLeft: "14.15pt",
  });
});

test("the paragraph mark's keys in direct size an empty paragraph and never its text", () => {
  // Payloads from before the contract fix still send them on text paragraphs.
  const text = para("14", {
    direct: { alignment: "justify", font_size_pt: 1.0, bold: true, color: "FF0000" },
  });
  const textLook = lookOf(effectiveParagraphStyle(text, KIT_STYLES));
  assert.equal(textLook.fontSize, "12pt");
  assert.equal(textLook.fontWeight, undefined);
  assert.equal(textLook.color, "#061B31");
  assert.equal(textLook.textAlign, "justify");

  const spacer = para("18", {
    runs: [],
    direct: { font_size_pt: 1.0, space_before_pt: 0.0, space_after_pt: 0.0 },
  });
  const spacerLook = lookOf(effectiveParagraphStyle(spacer, KIT_STYLES));
  assert.equal(spacerLook.fontSize, "1pt");
  assert.equal(spacerLook.marginTop, "0pt");
  assert.equal(spacerLook.marginBottom, "0pt");
});

test("a run adds only what it sets: unset bold, size and colour inherit the style", () => {
  const title = resolveParagraph(para("10", { style: "Heading 2" }), KIT_STYLES);
  // bold false is "unset or off": it never un-bolds a bold style.
  assert.deepEqual(effectiveRunStyle(run(), title), {});

  const body = resolveParagraph(para("11"), KIT_STYLES);
  assert.deepEqual(
    effectiveRunStyle(
      run({ size: 10.0, color: "FFFFFF", bold: true, italic: true, underline: true, caps: true }),
      body,
    ),
    {
      fontSize: "10pt",
      color: "#FFFFFF",
      fontWeight: 700,
      fontStyle: "italic",
      textDecoration: "underline",
      textTransform: "uppercase",
    },
  );
  assert.deepEqual(effectiveRunStyle(run({ size: 12.0 }), body), {});
});

test("a run's capitals: explicitly off prints as typed in a capitalised title, unset inherits", () => {
  const title = resolveParagraph(para("10", { style: "Heading 2" }), KIT_STYLES);
  const body = resolveParagraph(para("11"), KIT_STYLES);
  // "(Riferimento)" under ELENCO FATTORI DI PERICOLO: Word prints it as typed.
  assert.deepEqual(effectiveRunStyle(run({ caps: false }), title), { textTransform: "none" });
  // Unset inherits the paragraph's capitals: null, or no caps key at all as
  // in a payload from before the layout redesign.
  assert.deepEqual(effectiveRunStyle(run({ caps: null }), title), {});
  const legacy = run();
  delete legacy.caps;
  assert.deepEqual(effectiveRunStyle(legacy, title), {});
  // On adds capitals; off has nothing to undo in a paragraph without them.
  assert.deepEqual(effectiveRunStyle(run({ caps: true }), body), { textTransform: "uppercase" });
  assert.deepEqual(effectiveRunStyle(run({ caps: false }), body), {});
});

test("text typed into an empty paragraph shows at its style's size, not at its mark's", () => {
  const spacer = resolveParagraph(
    para("18", { runs: [], direct: { font_size_pt: 1.0 } }),
    KIT_STYLES,
  );
  assert.deepEqual(effectiveRunStyle(run(), spacer), { fontSize: "12pt" });
});

test("a whitespace-only spacer is sized by its paragraph mark, like an empty one", () => {
  // The backend sends the mark's keys for it (no run shows text) and Word
  // prints it at the mark's height: 1 pt, not the style's 12 pt.
  const spacer = para("19", {
    editable: false,
    runs: [run({ text: " " }), run({ text: "\t" })],
    direct: { font_size_pt: 1.0, space_before_pt: 0.0, space_after_pt: 0.0 },
  });
  const look = lookOf(effectiveParagraphStyle(spacer, KIT_STYLES));
  assert.equal(look.fontSize, "1pt");
  assert.equal(look.marginTop, "0pt");
  assert.equal(look.marginBottom, "0pt");
});

test("replacement text takes the first run's look, and the style's when there is no run", () => {
  const body = para("20", {
    runs: [
      run({ text: "Primo", bold: true, color: "C00000", size: 10.0 }),
      run({ text: " secondo", italic: true, underline: true, size: 14.0 }),
    ],
  });
  assert.deepEqual(replacementRunStyle(body, resolveParagraph(body, KIT_STYLES)), {
    fontSize: "10pt",
    color: "#C00000",
    fontWeight: 700,
  });

  const title = para("21", { style: "Heading 2", heading_level: 2 });
  assert.deepEqual(replacementRunStyle(title, resolveParagraph(title, KIT_STYLES)), {});

  const empty = para("22", { runs: [], direct: { font_size_pt: 1.0 } });
  assert.deepEqual(replacementRunStyle(empty, resolveParagraph(empty, KIT_STYLES)), {
    fontSize: "12pt",
  });
});

test("without style_props a heading falls back to a navy bold scale, and the legacy alignment still applies", () => {
  const legacy = (fields) => ({
    addr: "17",
    style: "Normal",
    heading_level: null,
    alignment: null,
    editable: true,
    runs: [{ text: "Testo", bold: false, italic: false, underline: false, color: null, size: null }],
    images: [],
    ...fields,
  });
  assert.deepEqual(
    lookOf(
      effectiveParagraphStyle(
        legacy({ style: "Heading 1", heading_level: 1, alignment: "center" }),
        undefined,
      ),
    ),
    {
      fontFamily: ARIAL,
      fontSize: "16pt",
      fontWeight: 700,
      color: "#003D74",
      textAlign: "center",
      marginTop: "18pt",
      marginBottom: "6pt",
    },
  );
  const body = lookOf(effectiveParagraphStyle(legacy({}), undefined));
  assert.equal(body.fontSize, "10pt");
  assert.equal(body.fontWeight, undefined);
  assert.equal(body.textAlign, "left");
});

// ---------------------------------------------------------------------------
// Lists
// ---------------------------------------------------------------------------

test("list markers: bullets keep their glyph, numbers count consecutive items per level", () => {
  const item = (addr, level, glyph) =>
    para(addr, { style: "List Number", list: { level, glyph } });
  const markers = computeListMarkers([
    item("0", 0, "%1."),
    item("1", 0, "%1."),
    item("2", 1, "%1.%2."),
    item("3", 1, "%1.%2."),
    item("4", 0, "%1."),
    item("5", 1, "%1.%2."),
    item("6", 0, "•"),
    para("7"),
    item("8", 0, "%1."),
  ]);
  assert.deepEqual(Object.fromEntries(markers), {
    0: "1.",
    1: "2.",
    2: "2.1.",
    3: "2.2.",
    4: "3.",
    5: "3.1.",
    6: "•",
    8: "1.",
  });
});

test("lists inside table cells are numbered cell by cell", () => {
  // Cell paragraphs carry every paragraph field but kind and page_break_before.
  const item = (addr) => {
    const cellParagraph = para(addr, { list: { level: 0, glyph: "%1)" } });
    delete cellParagraph.kind;
    delete cellParagraph.page_break_before;
    return cellParagraph;
  };
  const markers = computeListMarkers([
    para("2", { list: { level: 0, glyph: "%1)" } }),
    table("3", [
      [
        cell("3:0:0", [item("3:0:0:0"), item("3:0:0:1")]),
        cell("3:0:1", [item("3:0:1:0")]),
      ],
    ]),
    para("4", { list: { level: 0, glyph: "%1)" } }),
  ]);
  assert.deepEqual(Object.fromEntries(markers), {
    2: "1)",
    "3:0:0:0": "1)",
    "3:0:0:1": "2)",
    "3:0:1:0": "1)",
    4: "1)",
  });
});

test("a list item's text starts 18 pt in per level, or at its own indent, with the marker hanging 18 pt to its left", () => {
  const bullet = (addr, level, direct = null) =>
    para(addr, { style: "List Bullet", list: { level, glyph: "•" }, direct });
  assert.equal(effectiveParagraphStyle(bullet("15", 0), KIT_STYLES).marginLeft, "18pt");
  assert.equal(effectiveParagraphStyle(bullet("16", 1), KIT_STYLES).marginLeft, "36pt");
  assert.equal(
    effectiveParagraphStyle(bullet("17", 0, { indent_left_pt: 28.35 }), KIT_STYLES).marginLeft,
    "28.35pt",
  );
  const marker = listMarkerStyle();
  assert.equal(marker.position, "absolute");
  assert.equal(marker.left, "-18pt");
  assert.equal(marker.width, "18pt");
});
