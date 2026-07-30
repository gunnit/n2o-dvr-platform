"use client";

/**
 * Shared chrome for every "scheda documento" in the app.
 *
 * Two surfaces render document cards — the /documents catalogue (one card per
 * generatable type) and the azienda Documenti tab (one card per type, headed
 * by its newest version) — and until now they shared nothing but a passing
 * resemblance. These are the parts they have in common; each call site still
 * supplies its own content, so nothing here needs a `mode` prop or a union of
 * every field either page might want.
 *
 * Layout rules the old cards broke, encoded here so they stay fixed:
 *
 *  - **Colour means status, and only status.** The catalogue used the same
 *    red/amber/green language for the static `complexity` chip as for the live
 *    status badge, so "Alta" complexity + "Pronto" put a red badge beside a
 *    green one on a card where nothing was wrong. Complexity is now plain text
 *    in the eyebrow.
 *  - **Action rows line up across a grid row.** The shell is `flex-col` with a
 *    `flex-1` body and the action row is `mt-auto`, so cards of unequal content
 *    still foot at the same height.
 *  - **One meta line, not a two-column label grid.** `v3 · 2 giorni fa · Marco
 *    Rossi` carries what the old `Stato`/`Versione · aggiornato` grid carried,
 *    with a fraction of the chrome, and degrades cleanly when a field is null.
 */

import type { ComponentType, ReactNode } from "react";
import { Fragment } from "react";

import { Monogram, type AccentKey } from "@/components/cards/Monogram";
import { cn } from "@/lib/utils";

import { DOC_STATUS, DOC_STATUS_TONE_CLASS } from "./document-types";

const TEXTURE_FADE = "linear-gradient(to bottom, #000 0%, rgba(0,0,0,0.35) 55%, transparent 100%)";

export function DocumentCard({
  rail,
  texture,
  dimmed,
  ready,
  className,
  children,
}: {
  /** Category rail colour, e.g. `bg-[#003d74]`. */
  rail: string;
  /** Category texture path; omitted for cards with no known category. */
  texture?: string;
  /** Blocked or plan-gated — drained rather than hidden. */
  dimmed?: boolean;
  /** Latest version generated cleanly; earns a slightly warmer border. */
  ready?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-md border bg-white",
        // Ambient at rest, elevated on hover — DESIGN.md §6 levels 1 and 3.
        // Radius stays at 6px: the neighbouring panels are all rounded-md and
        // §7 rules out 12px+ on cards.
        "shadow-stripe-ambient transition-[box-shadow,border-color] duration-200",
        "hover:border-[#d1d9e3] hover:shadow-stripe-elevated",
        ready ? "border-[#dbe7f2]" : "border-[#e5edf5]",
        // Drained, but not desaturated. Saturation loss turned the navy
        // "Genera" on a DVR-blocked card grey, i.e. indistinguishable from a
        // disabled one — and that button is deliberately still clickable so the
        // Italian reason surfaces. The callout carries the "inactive" meaning;
        // the styling only needs to recede.
        dimmed && "opacity-[0.88]",
        className,
      )}
    >
      <span
        className={cn("absolute inset-y-0 left-0 z-[1] w-[3px]", rail)}
        aria-hidden
      />
      {texture && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-[132px] bg-cover bg-center bg-no-repeat opacity-[0.14]"
          style={{
            backgroundImage: `url("${texture}")`,
            maskImage: TEXTURE_FADE,
            WebkitMaskImage: TEXTURE_FADE,
          }}
        />
      )}
      <div className="relative flex flex-1 flex-col gap-3 p-[18px] pl-[22px]">
        {children}
      </div>
    </div>
  );
}

export function DocumentCardHeader({
  icon: Icon,
  accent,
  title,
  eyebrow,
  trailing,
}: {
  icon: ComponentType<{ className?: string; strokeWidth?: number }>;
  accent: AccentKey;
  title: ReactNode;
  /** Static catalogue metadata — page count, complexity. Never colour-coded. */
  eyebrow?: ReactNode;
  /** Live signal, normally a `<DocumentStatusBadge>`. */
  trailing?: ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <Monogram accent={accent}>
        <Icon className="h-5 w-5" strokeWidth={1.75} />
      </Monogram>
      <div className="min-w-0 flex-1">
        <h4 className="font-heading text-[14.5px] font-semibold leading-[1.3] tracking-[-0.005em] text-[#061b31]">
          {title}
        </h4>
        {eyebrow && (
          <p className="mt-1 text-[11.5px] leading-[1.35] text-[#94a3b8]">
            {eyebrow}
          </p>
        )}
      </div>
      {trailing && (
        <div className="flex shrink-0 flex-col items-end gap-1">{trailing}</div>
      )}
    </div>
  );
}

export function DocumentStatusBadge({
  status,
  title,
  className,
}: {
  status: string;
  title?: string;
  className?: string;
}) {
  const config = DOC_STATUS[status];
  if (!config) return null;
  const Icon = config.icon;
  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-[3px] text-[11.5px] font-medium whitespace-nowrap",
        DOC_STATUS_TONE_CLASS[config.tone],
        className,
      )}
    >
      <Icon
        className={cn("h-3 w-3", config.spin && "animate-spin")}
        strokeWidth={2}
      />
      {config.label}
    </span>
  );
}

/**
 * Dense single meta line. Falsy entries are dropped before the separators are
 * interleaved, so an absent author or date never leaves a dangling `·`.
 *
 * Callers must put a `key` on any *element* they pass in `items` — React
 * validates the array literal at the call site, not the keyed fragments this
 * renders them into. Plain strings need nothing.
 */
export function DocumentCardMeta({
  items,
  className,
}: {
  items: ReactNode[];
  className?: string;
}) {
  const shown = items.filter(Boolean);
  if (shown.length === 0) return null;
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-1.5 gap-y-1 text-[12px] text-[#64748d]",
        className,
      )}
    >
      {shown.map((item, i) => (
        <Fragment key={i}>
          {i > 0 && (
            <span aria-hidden className="text-[#cbd5e1]">
              ·
            </span>
          )}
          <span className="inline-flex items-center gap-1">{item}</span>
        </Fragment>
      ))}
    </div>
  );
}

export function DocumentCardActions({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "mt-auto flex flex-wrap items-center gap-1.5 border-t border-[#eef2f7] pt-3",
        className,
      )}
    >
      {children}
    </div>
  );
}
