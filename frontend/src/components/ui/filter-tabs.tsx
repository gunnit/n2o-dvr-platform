"use client";

import { cn } from "@/lib/utils";

/**
 * The "Tutte / Attive / Bozze" row that sits above a filtered list.
 *
 * Three screens grew their own: /aziende and /sopralluoghi rendered a 36px
 * rectangular tab with the count inline, while /admin/feedback rendered a
 * `rounded-full` pill with the count in a second nested pill and a different
 * active colour. DESIGN.md §7 rules pill shapes out, so the rectangle wins.
 *
 * The count is deliberately rendered even at zero here (unlike the older
 * aziende/sopralluoghi behaviour of hiding it): in a triage queue "Risolti 0"
 * is the answer the admin came for, and a tab that silently drops its number
 * reads as still loading.
 */

export type FilterTab<T extends string> = {
  id: T;
  label: string;
  /** Omit to render no count at all — a tab that has nothing to count. */
  count?: number;
};

export function FilterTabs<T extends string>({
  tabs,
  value,
  onChange,
  className,
}: {
  tabs: readonly FilterTab<T>[];
  value: T;
  onChange: (id: T) => void;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {tabs.map((tab) => {
        const active = tab.id === value;
        return (
          <button
            key={tab.id}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(tab.id)}
            className={cn(
              "inline-flex h-9 items-center gap-1.5 rounded-md border px-3 text-[13px] font-medium transition-colors",
              active
                ? "border-[#061b31] bg-[#061b31] text-white"
                : "border-[#e5edf5] bg-white text-[#273951] hover:border-[#d1d9e3]",
            )}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span
                className={cn(
                  "tnum text-[11.5px]",
                  active ? "opacity-70" : "text-[#94a3b8]",
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
