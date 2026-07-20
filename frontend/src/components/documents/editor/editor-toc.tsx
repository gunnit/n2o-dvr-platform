"use client";

import { useEffect, useRef, useState } from "react";
import { ListTree } from "lucide-react";

import { cn } from "@/lib/utils";
import type { PreviewBlock } from "@/types";

export interface TocEntry {
  addr: string;
  level: number;
  text: string;
}

/**
 * TOC entries from the top-level heading blocks. Uses the effective text
 * (override first) so inline edits to a heading update the sidebar too.
 */
export function buildTocEntries(
  blocks: PreviewBlock[],
  overrides: Record<string, string>,
): TocEntry[] {
  const entries: TocEntry[] = [];
  for (const block of blocks) {
    if (block.kind !== "paragraph" || block.heading_level === null) continue;
    const text = (
      overrides[block.addr] ?? block.runs.map((r) => r.text).join("")
    ).trim();
    if (!text) continue;
    entries.push({ addr: block.addr, level: block.heading_level, text });
  }
  return entries;
}

// Vertical offset (px) under which a heading counts as "current" — sticky
// header height plus a little breathing room. Matches the blocks'
// scroll-mt-28 anchor offset.
const SPY_OFFSET = 120;

/**
 * rAF-throttled scrollspy: the active heading is the last one whose top
 * edge has crossed under the sticky header. Headings come in document
 * order (tops ascending), so the loop can bail at the first one below the
 * threshold instead of measuring all ~200 DVR headings per frame.
 */
function useActiveHeading(entries: TocEntry[]): string | null {
  const [active, setActive] = useState<string | null>(null);
  const tickingRef = useRef(false);

  useEffect(() => {
    if (entries.length === 0) return;

    const update = () => {
      tickingRef.current = false;
      let current: string | null = entries[0].addr;
      for (const entry of entries) {
        const el = document.getElementById(`block-${entry.addr}`);
        if (!el) continue;
        const rect = el.getBoundingClientRect();
        // Headings inside content-visibility-skipped sheets measure 0x0;
        // never-rendered content is below the viewport by definition, so
        // stop scanning rather than mistake top 0 for "already passed".
        if (rect.width === 0 && rect.height === 0) break;
        if (rect.top <= SPY_OFFSET) current = entry.addr;
        else break;
      }
      setActive(current);
    };

    const onScroll = () => {
      if (tickingRef.current) return;
      tickingRef.current = true;
      window.requestAnimationFrame(update);
    };

    // Initial sync goes through rAF too, so state settles after paint
    // instead of cascading inside the effect body.
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [entries]);

  // Derive the empty case instead of resetting state in the effect.
  return entries.length === 0 ? null : active;
}

export function EditorToc({ entries }: { entries: TocEntry[] }) {
  const active = useActiveHeading(entries);

  // Keep the highlighted entry visible inside the sidebar's own scroll.
  useEffect(() => {
    if (!active) return;
    document
      .getElementById(`toc-${active}`)
      ?.scrollIntoView({ block: "nearest" });
  }, [active]);

  if (entries.length === 0) {
    return (
      <p className="px-2 py-1 text-[12px] text-[#64748d]">
        Nessuna intestazione trovata nel documento.
      </p>
    );
  }

  return (
    <nav aria-label="Indice del documento">
      <p className="type-eyebrow mb-2 flex items-center gap-1.5 px-2">
        <ListTree className="h-3.5 w-3.5" strokeWidth={1.75} />
        Indice
      </p>
      <ul className="space-y-0.5">
        {entries.map((entry) => (
          <li key={entry.addr}>
            <button
              type="button"
              id={`toc-${entry.addr}`}
              onClick={() => {
                document
                  .getElementById(`block-${entry.addr}`)
                  ?.scrollIntoView({ behavior: "smooth", block: "start" });
              }}
              aria-current={active === entry.addr ? "true" : undefined}
              title={entry.text}
              className={cn(
                "block w-full truncate rounded-sm px-2 py-1 text-left text-[12px] leading-[1.35] transition-colors",
                entry.level === 1 && "font-medium",
                entry.level === 2 && "pl-4",
                entry.level === 3 && "pl-6",
                entry.level >= 4 && "pl-8",
                active === entry.addr
                  ? "bg-[rgba(0,61,116,0.08)] font-medium text-primary"
                  : "text-[#64748d] hover:bg-[#f6f9fc] hover:text-[#061b31]",
              )}
            >
              {entry.text}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
