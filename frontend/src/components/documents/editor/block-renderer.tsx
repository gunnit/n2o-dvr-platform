"use client";

import { memo, useEffect, useState } from "react";
import { ImageOff } from "lucide-react";

import { EditableParagraph } from "@/components/documents/editor/editable-paragraph";
import { fetchImageBlobUrl } from "@/lib/api-client";
import type {
  PreviewBlock,
  PreviewInlineImage,
  PreviewParagraph,
  PreviewParagraphBlock,
  PreviewTableBlock,
  PreviewTableCell,
} from "@/types";

/**
 * Split the block stream into A4-like "sheets": a paragraph flagged with
 * page_break_before starts a new sheet (unless it would be the very first
 * block, which already sits at the top of sheet 1).
 */
export function groupIntoSheets(blocks: PreviewBlock[]): PreviewBlock[][] {
  const sheets: PreviewBlock[][] = [];
  let current: PreviewBlock[] = [];
  for (const block of blocks) {
    if (
      block.kind === "paragraph" &&
      block.page_break_before &&
      current.length > 0
    ) {
      sheets.push(current);
      current = [];
    }
    current.push(block);
  }
  if (current.length > 0) sheets.push(current);
  return sheets;
}

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
  // No reset-on-prop-change needed: the component is keyed by image_id in
  // paragraphImages(), so a different image remounts with fresh state.
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    fetchImageBlobUrl(
      `/api/v1/documenti/${documentId}/preview/images/${image.image_id}`,
    )
      .then((url) => {
        if (cancelled) {
          if (url) URL.revokeObjectURL(url);
          return;
        }
        if (url) {
          objectUrl = url;
          setSrc(url);
        } else {
          setFailed(true);
        }
      })
      .catch(() => {
        // Network/auth failure — settle into the placeholder instead of
        // pulsing forever (and leaking an unhandled promise rejection).
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId, image.image_id]);

  if (failed) {
    return (
      <span
        title="Immagine non disponibile"
        className="my-1 inline-flex max-w-full items-center justify-center gap-1.5 overflow-hidden rounded-sm border border-[#e5edf5] bg-[#f6f9fc] px-2 py-1 text-[11px] text-[#64748d]"
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
// Paragraph block
// ---------------------------------------------------------------------------

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
  return (
    <div id={`block-${block.addr}`} className="scroll-mt-28">
      <EditableParagraph
        paragraph={block}
        override={override}
        onOverrideChange={onOverrideChange}
        trailing={paragraphImages(documentId, block)}
      />
    </div>
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
    return (
      <div
        id={`block-${block.addr}`}
        className="my-3 scroll-mt-28 overflow-x-auto"
        style={{ contentVisibility: "auto", containIntrinsicSize: "auto 160px" }}
      >
        <table className="w-full border-collapse">
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
                      // Cell shading reproduces the .docx (content, not chrome).
                      style={
                        cell.shading
                          ? { backgroundColor: `#${cell.shading}` }
                          : undefined
                      }
                      className="border border-neutral-300 px-2 py-1 align-top"
                    >
                      {cell.paragraphs.map((paragraph) => (
                        <EditableParagraph
                          key={paragraph.addr}
                          paragraph={paragraph}
                          override={overrides[paragraph.addr]}
                          onOverrideChange={onOverrideChange}
                          inCell
                          trailing={paragraphImages(documentId, paragraph)}
                        />
                      ))}
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
