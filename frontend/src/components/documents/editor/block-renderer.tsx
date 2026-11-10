"use client";

import {
  createContext,
  memo,
  useContext,
  useMemo,
  type CSSProperties,
} from "react";
import { ImageOff } from "lucide-react";

import { isPageBreakLine } from "@/components/documents/editor/doc-sheets";
import {
  DOC_CELL_PADDING,
  DOC_TABLE_BORDER,
  listMarkerStyle,
  paragraphStyle,
  resolveParagraph,
  type StylePropsTable,
} from "@/components/documents/editor/doc-typography";
import { EditableParagraph } from "@/components/documents/editor/editable-paragraph";
import { useDocumentImage } from "@/components/documents/editor/use-document-image";
import type {
  PreviewInlineImage,
  PreviewParagraph,
  PreviewParagraphBlock,
  PreviewTableBlock,
  PreviewTableCell,
} from "@/types";

// ---------------------------------------------------------------------------
// Document look: what every paragraph needs to draw itself
// ---------------------------------------------------------------------------

export interface DocumentLook {
  /** The payload's style_props; undefined on payloads from before the layout redesign. */
  styleProps: StylePropsTable | undefined;
  /** computeListMarkers() of the payload, by paragraph address. */
  listMarkers: ReadonlyMap<string, string>;
}

/** Provided once per preview, so memoized blocks never re-render for it. */
export const DocumentLookContext = createContext<DocumentLook>({
  styleProps: undefined,
  listMarkers: new Map(),
});

// ---------------------------------------------------------------------------
// Inline images
// ---------------------------------------------------------------------------

function InlineDocImage({
  documentId,
  image,
}: {
  documentId: string;
  image: PreviewInlineImage;
}) {
  const { src, failed } = useDocumentImage(documentId, image.image_id);

  if (failed) {
    return (
      <span
        title="Immagine non disponibile"
        className="my-1 inline-flex max-w-full items-center justify-center gap-1.5 overflow-hidden rounded-sm border border-[#e5edf5] bg-[#f6f9fc] px-2 py-1 font-body text-[11px] font-normal text-[#64748d] not-italic normal-case"
        style={{
          width: image.width_px ?? undefined,
          height: image.height_px ?? undefined,
        }}
      >
        <ImageOff className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
        Immagine non disponibile
      </span>
    );
  }
  if (!src) {
    return (
      <span
        aria-hidden
        className="my-1 inline-block max-w-full animate-pulse rounded-sm bg-[#eef2f7]"
        style={{
          width: image.width_px ?? 160,
          height: image.height_px ?? 90,
        }}
      />
    );
  }
  return (
    // Authenticated blob object URL — next/image adds nothing here.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt="Immagine del documento"
      width={image.width_px ?? undefined}
      height={image.height_px ?? undefined}
      className="my-1 inline-block h-auto max-w-full"
    />
  );
}

function paragraphImages(documentId: string, paragraph: PreviewParagraph) {
  if (paragraph.images.length === 0) return undefined;
  return paragraph.images.map((image) => (
    <InlineDocImage key={image.image_id} documentId={documentId} image={image} />
  ));
}

// ---------------------------------------------------------------------------
// Paragraph: the box (look, spacing, indent, list marker) around the text
// ---------------------------------------------------------------------------

interface DocParagraphProps {
  paragraph: PreviewParagraph;
  documentId: string;
  override: string | undefined;
  onOverrideChange: (addr: string, value: string | null) => void;
  id?: string;
  className?: string;
}

function DocParagraph({
  paragraph,
  documentId,
  override,
  onOverrideChange,
  id,
  className,
}: DocParagraphProps) {
  const { styleProps, listMarkers } = useContext(DocumentLookContext);
  const look = useMemo(
    () => resolveParagraph(paragraph, styleProps),
    [paragraph, styleProps],
  );
  const marker = paragraph.list ? (listMarkers.get(paragraph.addr) ?? "") : null;

  return (
    <div id={id} className={className} style={paragraphStyle(look)}>
      {marker !== null && (
        <span aria-hidden style={listMarkerStyle()}>
          {marker}
        </span>
      )}
      <EditableParagraph
        paragraph={paragraph}
        look={look}
        override={override}
        onOverrideChange={onOverrideChange}
        trailing={paragraphImages(documentId, paragraph)}
      />
    </div>
  );
}

export interface ParagraphBlockViewProps {
  block: PreviewParagraphBlock;
  documentId: string;
  override: string | undefined;
  onOverrideChange: (addr: string, value: string | null) => void;
}

export const ParagraphBlockView = memo(function ParagraphBlockView({
  block,
  documentId,
  override,
  onOverrideChange,
}: ParagraphBlockViewProps) {
  if (isPageBreakLine(block)) return null;
  return (
    <DocParagraph
      id={`block-${block.addr}`}
      className="scroll-mt-28"
      paragraph={block}
      documentId={documentId}
      override={override}
      onOverrideChange={onOverrideChange}
    />
  );
});

// ---------------------------------------------------------------------------
// Table block
// ---------------------------------------------------------------------------

/** Grid column of a cell = sum of the col_spans of the cells before it. */
function gridColumn(row: PreviewTableCell[], cellIdx: number): number {
  let col = 0;
  for (let i = 0; i < cellIdx; i++) col += row[i].col_span || 1;
  return col;
}

/**
 * A v_merge "restart" cell spans itself plus every consecutive following
 * row that carries a "continue" cell at the same grid column.
 */
function computeRowSpan(
  rows: PreviewTableCell[][],
  rowIdx: number,
  cellIdx: number,
): number {
  const col = gridColumn(rows[rowIdx], cellIdx);
  let span = 1;
  for (let r = rowIdx + 1; r < rows.length; r++) {
    let found = false;
    let acc = 0;
    for (const cell of rows[r]) {
      if (acc === col && cell.v_merge === "continue") {
        found = true;
        break;
      }
      acc += cell.col_span || 1;
      if (acc > col) break;
    }
    if (!found) break;
    span++;
  }
  return span;
}

function recordsShallowEqual(
  a: Record<string, string>,
  b: Record<string, string>,
): boolean {
  if (a === b) return true;
  const aKeys = Object.keys(a);
  if (aKeys.length !== Object.keys(b).length) return false;
  for (const key of aKeys) {
    if (a[key] !== b[key]) return false;
  }
  return true;
}

const CELL_V_ALIGN = {
  top: "top",
  center: "middle",
  bottom: "bottom",
} as const;

// Cell look reproduces the .docx (content, not chrome): Table Grid's black
// ½ pt borders, Word's cell margins, the cell's fill and vertical alignment.
function cellStyle(cell: PreviewTableCell): CSSProperties {
  return {
    border: DOC_TABLE_BORDER,
    padding: DOC_CELL_PADDING,
    verticalAlign: CELL_V_ALIGN[cell.v_align ?? "top"],
    backgroundColor: cell.shading ? `#${cell.shading}` : undefined,
  };
}

export interface TableBlockViewProps {
  block: PreviewTableBlock;
  documentId: string;
  /** Slice of the overrides map restricted to this table's addresses. */
  overrides: Record<string, string>;
  onOverrideChange: (addr: string, value: string | null) => void;
}

export const TableBlockView = memo(
  function TableBlockView({
    block,
    documentId,
    overrides,
    onOverrideChange,
  }: TableBlockViewProps) {
    const widths = block.col_widths_pct?.length ? block.col_widths_pct : null;
    return (
      <div
        id={`block-${block.addr}`}
        className="scroll-mt-28 overflow-x-auto"
        style={{ contentVisibility: "auto", containIntrinsicSize: "auto 160px" }}
      >
        <table
          className="w-full border-collapse"
          // The grid's own column widths; without them the browser sizes
          // the columns from their content.
          style={{ tableLayout: widths ? "fixed" : "auto" }}
        >
          {widths && (
            <colgroup>
              {widths.map((width, idx) => (
                <col key={idx} style={{ width: `${width}%` }} />
              ))}
            </colgroup>
          )}
          <tbody>
            {block.rows.map((row, rowIdx) => (
              <tr key={rowIdx}>
                {row.map((cell, cellIdx) => {
                  // "continue" cells are covered by their restart's rowSpan.
                  if (cell.v_merge === "continue") return null;
                  const rowSpan =
                    cell.v_merge === "restart"
                      ? computeRowSpan(block.rows, rowIdx, cellIdx)
                      : 1;
                  return (
                    <td
                      key={cell.addr}
                      colSpan={cell.col_span > 1 ? cell.col_span : undefined}
                      rowSpan={rowSpan > 1 ? rowSpan : undefined}
                      style={cellStyle(cell)}
                    >
                      {/* Flex column: paragraph spacing adds up as in Word. */}
                      <div className="flex flex-col">
                        {cell.paragraphs.map((paragraph) => (
                          <DocParagraph
                            key={paragraph.addr}
                            paragraph={paragraph}
                            documentId={documentId}
                            override={overrides[paragraph.addr]}
                            onOverrideChange={onOverrideChange}
                          />
                        ))}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  },
  (prev, next) =>
    prev.block === next.block &&
    prev.documentId === next.documentId &&
    prev.onOverrideChange === next.onOverrideChange &&
    recordsShallowEqual(prev.overrides, next.overrides),
);
