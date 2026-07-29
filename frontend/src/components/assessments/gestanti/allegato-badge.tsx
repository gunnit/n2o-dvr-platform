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
  C: "Agenti e condizioni per cui è richiesta valutazione specifica.",
};

// Base band colors (reuse the project palette: emerald/amber/rose).
// A = rose (maximum severity), B = amber, C = emerald (soft warning).
const CLASSNAME: Record<Allegato, string> = {
  A: "bg-[rgba(239,68,68,0.16)] text-[#b01e2e] ring-[rgba(239,68,68,0.34)]",
  B: "bg-[rgba(245,158,11,0.18)] text-[#8a5c23] ring-[rgba(245,158,11,0.36)]",
  C: "bg-[rgba(21,190,83,0.16)] text-[#0c6b2f] ring-[rgba(21,190,83,0.34)]",
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
