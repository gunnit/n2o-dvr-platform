"use client";

import { cn } from "@/lib/utils";
import type { Allegato } from "./types";

const LABEL: Record<Allegato, string> = {
  A: "Allegato A",
  B: "Allegato B",
  C: "Allegato C",
};

const TOOLTIP: Record<Allegato, string> = {
  A: "Lavori vietati: riallocazione o astensione anticipata obbligatoria.",
  B: "Lavori vietati salvo deroga con valutazione specifica del rischio.",
  C: "Agenti e condizioni per cui e' richiesta valutazione specifica.",
};

// Base band colors (reuse the project palette: emerald/amber/rose).
// A = rose (maximum severity), B = amber, C = emerald (soft warning).
const CLASSNAME: Record<Allegato, string> = {
  A: "bg-rose-500/15 text-rose-700 ring-rose-500/30",
  B: "bg-amber-500/15 text-amber-800 ring-amber-500/30",
  C: "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30",
};

export function AllegatoBadge({ allegato }: { allegato: Allegato }) {
  return (
    <span
      title={TOOLTIP[allegato]}
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ring-1",
        CLASSNAME[allegato],
      )}
    >
      {LABEL[allegato]}
    </span>
  );
}
