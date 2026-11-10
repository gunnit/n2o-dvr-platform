"use client";

/**
 * The sheet a document is drawn on: page size and margins from the
 * document, the full-page art of covers and dividers, and the running
 * header and footer bands of content pages (spec 2026-11-10 §4.3.2).
 *
 * Inside the sheet the document keeps its own look (Arial, points, the
 * kit's colours); the app chrome around it keeps DESIGN.md. A sheet wider
 * than the column is scaled down to fit it — the document is never
 * reflowed and the page never scrolls sideways.
 */

import {
  createContext,
  useContext,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import { ImageOff } from "lucide-react";

import type {
  Sheet,
  SheetGeometry,
  SheetRole,
} from "@/components/documents/editor/doc-sheets";
import {
  DOC_FONT_FAMILY,
  DOC_LINE_HEIGHT,
  DOC_NAVY,
  DOC_RULE,
  DOC_SLATE,
} from "@/components/documents/editor/doc-typography";
import {
  useDocumentImage,
  useNearViewport,
} from "@/components/documents/editor/use-document-image";
import type { PreviewFurniture } from "@/types";

// ---------------------------------------------------------------------------
// Stack: fits the sheets to the column width
// ---------------------------------------------------------------------------

const SheetScaleContext = createContext(1);

/**
 * The column of sheets. Measures its own width and scales every sheet
 * down to it when the page is wider than the column (phones, and desktops
 * with the sidebar and index open).
 */
export function SheetStack({
  geometry,
  children,
}: {
  geometry: SheetGeometry;
  children: ReactNode;
}) {
  const stackRef = useRef<HTMLDivElement | null>(null);
  const [availablePx, setAvailablePx] = useState<number | null>(null);

  // Layout effect: the first paint already shows the fitted scale.
  useLayoutEffect(() => {
    const stack = stackRef.current;
    if (!stack) return;
    const observer = new ResizeObserver(() => setAvailablePx(stack.clientWidth));
    observer.observe(stack);
    setAvailablePx(stack.clientWidth);
    return () => observer.disconnect();
  }, []);

  const scale =
    availablePx !== null && availablePx > 0
      ? Math.min(1, availablePx / geometry.widthPx)
      : 1;

  return (
    <div
      ref={stackRef}
      className="mx-auto flex w-full flex-col gap-6"
      style={{ maxWidth: geometry.widthPx }}
    >
      <SheetScaleContext.Provider value={scale}>{children}</SheetScaleContext.Provider>
    </div>
  );
}

/**
 * Layout height of an element, kept current. A CSS transform leaves layout
 * untouched, so the box around a scaled sheet takes its height from here.
 */
function useLayoutHeight(
  ref: RefObject<HTMLElement | null>,
  enabled: boolean,
): number | null {
  const [height, setHeight] = useState<number | null>(null);

  useLayoutEffect(() => {
    if (!enabled) return;
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver(() => setHeight(element.offsetHeight));
    observer.observe(element);
    setHeight(element.offsetHeight);
    return () => observer.disconnect();
  }, [enabled, ref]);

  return enabled ? height : null;
}

// ---------------------------------------------------------------------------
// Art background, header and footer bands
// ---------------------------------------------------------------------------

/** Full-bleed art of a cover, divider or back cover, fetched near the viewport. */
function SheetArt({
  documentId,
  imageId,
}: {
  documentId: string;
  imageId: string | null;
}) {
  const artRef = useRef<HTMLDivElement | null>(null);
  const near = useNearViewport(artRef);
  const { src, failed } = useDocumentImage(documentId, imageId, near);
  const missing = failed || !imageId;

  return (
    <>
      <div
        ref={artRef}
        aria-hidden
        className="pointer-events-none absolute inset-0 overflow-hidden rounded-sm"
        style={src || missing ? undefined : { backgroundColor: "#f6f9fc" }}
      >
        {src && (
          // Authenticated blob object URL — next/image adds nothing here.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={src}
            alt=""
            draggable={false}
            className="h-full w-full object-cover"
          />
        )}
      </div>
      {missing && (
        // A missing picture leaves a white page with its live title, as
        // in the printed document; this note is app chrome, not paper.
        <span className="absolute top-3 left-3 inline-flex items-center gap-1.5 rounded-sm border border-[#e5edf5] bg-white px-2 py-1 font-body text-[11px] font-normal text-[#64748d] not-italic normal-case">
          <ImageOff className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
          Immagine di sfondo non disponibile
        </span>
      )}
    </>
  );
}

function HeaderBand({
  furniture,
  geometry,
}: {
  furniture: PreviewFurniture | null;
  geometry: SheetGeometry;
}) {
  const left = furniture?.header_left?.trim() || null;
  const right = furniture?.header_right?.trim() || null;
  if (!left && !right) return null;
  return (
    // Repeated on every sheet like the printed header, so hidden from
    // assistive technology. Halfway into the top margin: the kit's 1.0 cm
    // header distance over its 2.0 cm margin.
    <div
      aria-hidden
      className="pointer-events-none absolute flex items-end justify-between gap-[12pt]"
      style={{
        top: geometry.paddingTopPx / 2,
        left: geometry.paddingLeftPx,
        right: geometry.paddingRightPx,
        fontSize: "9pt",
        lineHeight: 1.15,
        fontWeight: 700,
        color: DOC_NAVY,
        textTransform: "uppercase",
        paddingBottom: "3pt",
        borderBottom: `0.75pt solid ${DOC_RULE}`,
      }}
    >
      <span className="min-w-0">{left}</span>
      <span className="min-w-0 text-right">{right}</span>
    </div>
  );
}

function FooterBand({
  furniture,
  geometry,
  logoSrc,
}: {
  furniture: PreviewFurniture | null;
  geometry: SheetGeometry;
  logoSrc: string | null;
}) {
  const text = furniture?.footer_text?.trim() || null;
  if (!text && !furniture?.footer_logo_image_id) return null;
  return (
    // Logo and revision line over a hairline. No "Pag. X di Y": a sheet
    // is not a printed page, and a wrong number would mislead a reviewer.
    <div
      aria-hidden
      className="pointer-events-none absolute flex items-center"
      style={{
        bottom: geometry.paddingBottomPx / 2,
        left: geometry.paddingLeftPx,
        right: geometry.paddingRightPx,
        fontSize: "8.5pt",
        lineHeight: 1.15,
        color: DOC_SLATE,
        paddingTop: "3pt",
        borderTop: `0.75pt solid ${DOC_RULE}`,
      }}
    >
      {logoSrc && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={logoSrc}
          alt=""
          draggable={false}
          style={{ maxWidth: "2.4cm", maxHeight: "0.85cm", marginRight: "6pt" }}
        />
      )}
      {text && <span className="min-w-0">{text}</span>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sheet
// ---------------------------------------------------------------------------

const ROLE_LABEL: Record<SheetRole, string | null> = {
  cover: "Copertina",
  divider: "Pagina divisoria",
  back_cover: "Retro di copertina",
  content: null,
};

export interface DocumentSheetProps {
  sheet: Sheet;
  /** Position in the document, for the accessible name of a content sheet. */
  index: number;
  documentId: string;
  geometry: SheetGeometry;
  furniture: PreviewFurniture | null;
  /** The footer logo, fetched once for every sheet. */
  footerLogoSrc: string | null;
  /** The sheet's blocks, already rendered. */
  children: ReactNode;
}

export function DocumentSheet({
  sheet,
  index,
  documentId,
  geometry,
  furniture,
  footerLogoSrc,
  children,
}: DocumentSheetProps) {
  const scale = useContext(SheetScaleContext);
  const scaled = scale < 1;
  const sectionRef = useRef<HTMLElement | null>(null);
  const layoutHeight = useLayoutHeight(sectionRef, scaled);
  const isArt = sheet.role !== "content";

  return (
    <div
      className="shrink-0"
      style={
        scaled
          ? {
              width: geometry.widthPx * scale,
              height: layoutHeight === null ? undefined : layoutHeight * scale,
            }
          : undefined
      }
    >
      <section
        ref={sectionRef}
        aria-label={ROLE_LABEL[sheet.role] ?? `Foglio ${index + 1}`}
        className="relative rounded-sm bg-white shadow-stripe-standard"
        style={{
          width: geometry.widthPx,
          minHeight: geometry.heightPx,
          padding: `${geometry.paddingTopPx}px ${geometry.paddingRightPx}px ${geometry.paddingBottomPx}px ${geometry.paddingLeftPx}px`,
          // The document's own type, scoped to the sheet (Word's "auto"
          // ink is black).
          fontFamily: DOC_FONT_FAMILY,
          lineHeight: DOC_LINE_HEIGHT,
          color: "#000000",
          transform: scaled ? `scale(${scale})` : undefined,
          transformOrigin: "top left",
          // Skipped off screen, a sheet is this placeholder plus its padding:
          // one page. A bigger one sends every jump from the index past
          // its heading.
          contentVisibility: "auto",
          containIntrinsicSize: `auto ${geometry.contentWidthPx}px auto ${geometry.contentHeightPx}px`,
        }}
      >
        {isArt ? (
          <SheetArt documentId={documentId} imageId={sheet.backgroundImageId} />
        ) : (
          <>
            <HeaderBand furniture={furniture} geometry={geometry} />
            <FooterBand furniture={furniture} geometry={geometry} logoSrc={footerLogoSrc} />
          </>
        )}
        {/* Positioned so the content paints over the art. A flex column,
            because Word adds a paragraph's space after to the next one's
            space before where CSS block margins would collapse. */}
        <div className="relative flex flex-col">{children}</div>
      </section>
    </div>
  );
}
