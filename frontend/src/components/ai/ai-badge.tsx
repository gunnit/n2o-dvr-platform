"use client";

import { Sparkles, Pencil, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * Shared AI provenance badge (US-5.3).
 *
 * Renders a small pill indicating whether a piece of content was produced by
 * AI, edited from an AI draft, or written manually. Hover reveals a native
 * tooltip explaining the state and (optionally) when the AI contribution was
 * made — the "revisiona prima della pubblicazione" prompt required by the
 * acceptance criteria.
 *
 * Kept intentionally dependency-free (no Tooltip lib) so it can be dropped
 * into any existing AI surface without wiring new providers.
 */

export type AIProvenance = "ai" | "edited" | "manual";

interface AIBadgeProps {
  provenance: AIProvenance;
  /** ISO timestamp of the AI generation, shown in tooltip when present. */
  timestamp?: string | Date | null;
  /** Optional label override. Default uses the Italian phrase per AC. */
  label?: string;
  className?: string;
  /** Compact size (xs) for dense tables. */
  size?: "sm" | "xs";
}

const defaults: Record<AIProvenance, { label: string; icon: typeof Sparkles; classes: string }> = {
  ai: {
    label: "Generato da AI",
    icon: Sparkles,
    classes: "bg-violet-100 text-violet-800 hover:bg-violet-100",
  },
  edited: {
    label: "Modificato dall'utente",
    icon: Pencil,
    classes: "bg-sky-100 text-sky-800 hover:bg-sky-100",
  },
  manual: {
    label: "Manuale",
    icon: User,
    classes: "bg-slate-100 text-slate-700 hover:bg-slate-100",
  },
};

function formatTimestamp(ts: string | Date): string {
  const d = typeof ts === "string" ? new Date(ts) : ts;
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function AIBadge({ provenance, timestamp, label, className, size = "sm" }: AIBadgeProps) {
  const spec = defaults[provenance];
  const Icon = spec.icon;
  const displayLabel = label ?? spec.label;

  const tooltipParts: string[] = [];
  if (provenance === "ai") {
    tooltipParts.push("Generato da AI - revisiona prima della pubblicazione.");
  } else if (provenance === "edited") {
    tooltipParts.push("Testo originato dall'AI e poi modificato manualmente.");
  } else {
    tooltipParts.push("Inserimento manuale.");
  }
  if (timestamp) {
    const formatted = formatTimestamp(timestamp);
    if (formatted) tooltipParts.push(`Ultimo aggiornamento: ${formatted}`);
  }

  return (
    <Badge
      data-ai-provenance={provenance}
      variant="secondary"
      className={cn(spec.classes, size === "xs" && "h-[18px] px-1.5 text-[11px]", className)}
      title={tooltipParts.join(" ")}
    >
      <Icon className={cn("mr-1", size === "xs" ? "h-2.5 w-2.5" : "h-3 w-3")} />
      {displayLabel}
    </Badge>
  );
}
