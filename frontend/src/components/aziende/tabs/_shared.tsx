import type { Building2 } from "lucide-react";
import type { ComponentType, ReactNode } from "react";

export type PanelAccent =
  | "navy"
  | "sky"
  | "violet"
  | "emerald"
  | "amber"
  | "slate"
  | "ruby";

export const PANEL_ACCENT: Record<
  PanelAccent,
  { rail: string; icon: string; bg: string }
> = {
  navy: {
    rail: "bg-[#003d74]",
    icon: "text-[#003d74]",
    bg: "bg-[rgba(0,61,116,0.08)]",
  },
  sky: {
    rail: "bg-[#0ea5e9]",
    icon: "text-[#0ea5e9]",
    bg: "bg-[rgba(14,165,233,0.1)]",
  },
  violet: {
    rail: "bg-[#7c3aed]",
    icon: "text-[#7c3aed]",
    bg: "bg-[rgba(124,58,237,0.1)]",
  },
  emerald: {
    rail: "bg-[#059669]",
    icon: "text-[#059669]",
    bg: "bg-[rgba(5,150,105,0.1)]",
  },
  amber: {
    rail: "bg-[#d97706]",
    icon: "text-[#d97706]",
    bg: "bg-[rgba(217,119,6,0.1)]",
  },
  slate: {
    rail: "bg-[#94a3b8]",
    icon: "text-[#64748d]",
    bg: "bg-[#f6f9fc]",
  },
  ruby: {
    rail: "bg-[#b51648]",
    icon: "text-[#b51648]",
    bg: "bg-[rgba(234,34,97,0.08)]",
  },
};

export function StatusPill({
  className,
  children,
}: {
  className: string;
  children: ReactNode;
}) {
  return (
    <span
      className={
        "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium " +
        className
      }
    >
      {children}
    </span>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="type-eyebrow">{children}</p>;
}

export function InfoRow({
  label,
  value,
  tnum = false,
  showWhenEmpty = false,
}: {
  label: string;
  value: string | null | undefined;
  tnum?: boolean;
  /**
   * When false (default) the row is skipped entirely if value is null,
   * undefined or empty. Feedback 04/05 #4: read-only displays of azienda
   * data should hide unfilled fields rather than show "-" placeholders,
   * which the operator reads as "we don't have this" noise.
   * Set to true on rows where the absence is itself information
   * (e.g. "Stato firma: non firmato").
   */
  showWhenEmpty?: boolean;
}) {
  const hasValue =
    value !== null && value !== undefined && String(value).trim() !== "";
  if (!hasValue && !showWhenEmpty) return null;
  return (
    <div className="flex flex-col gap-1">
      <span className="type-eyebrow">{label}</span>
      <span
        className={
          "text-[14px] leading-[1.4] text-[#061b31] " + (tnum ? "tnum" : "")
        }
      >
        {hasValue ? value : "-"}
      </span>
    </div>
  );
}

export function Panel({
  children,
  className = "",
  accent,
}: {
  children: ReactNode;
  className?: string;
  accent?: PanelAccent;
}) {
  const accentClass = accent ? PANEL_ACCENT[accent].rail : "";
  return (
    <div
      className={
        "relative overflow-hidden rounded-md border border-[#e5edf5] bg-white shadow-stripe-ambient " +
        className
      }
    >
      {accent && (
        <span
          aria-hidden
          className={"absolute inset-x-0 top-0 h-[2px] " + accentClass}
        />
      )}
      {children}
    </div>
  );
}

export function PanelHeader({
  icon: Icon,
  title,
  subtitle,
  action,
  accent,
}: {
  icon?: ComponentType<{ className?: string; strokeWidth?: number }> | typeof Building2;
  title: string;
  subtitle?: ReactNode;
  action?: ReactNode;
  accent?: PanelAccent;
}) {
  const accentMeta = accent ? PANEL_ACCENT[accent] : null;
  return (
    // `flex-wrap`, not a breakpoint: the action is arbitrary — one icon button
    // on some panels, three labelled ones on Miglioramento — so the only honest
    // rule is "drop to your own row when you no longer fit". The title keeps a
    // floor of 11rem so it is the *action* that wraps rather than the heading
    // shrinking to an ellipsis beside it; `Panel` is `overflow-hidden`, so
    // anything that does not fit is not merely cramped, it is invisible.
    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-b border-[#e5edf5] px-6 py-4">
      <div className="flex min-w-[11rem] flex-1 items-center gap-2.5">
        {Icon &&
          (accentMeta ? (
            <span
              className={
                "inline-flex h-7 w-7 items-center justify-center rounded-md " +
                accentMeta.bg
              }
            >
              <Icon
                className={"h-3.5 w-3.5 " + accentMeta.icon}
                strokeWidth={2}
              />
            </span>
          ) : (
            <Icon className="h-4 w-4 text-[#64748d]" strokeWidth={1.75} />
          ))}
        <div className="min-w-0">
          <h3 className="font-heading text-[15px] font-semibold tracking-[-0.005em] text-[#061b31] truncate">
            {title}
          </h3>
          {subtitle && (
            <p className="text-[12px] text-[#64748d] truncate">{subtitle}</p>
          )}
        </div>
      </div>
      {action}
    </div>
  );
}

// Risk-level chip palette — navy for critical, green for accettabile,
// per DESIGN.md §0 (no pink accents in safety domain except destructive).
export const riskLevelStyles: Record<string, string> = {
  ACCETTABILE:
    "bg-[rgba(21,190,83,0.2)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
  MODESTO:
    "bg-[rgba(155,104,41,0.12)] text-[#9b6829] border border-[rgba(155,104,41,0.3)]",
  GRAVE:
    "bg-[rgba(0,61,116,0.12)] text-primary border border-[rgba(0,61,116,0.3)]",
  GRAVISSIMO:
    "bg-[rgba(234,34,97,0.08)] text-[#b51648] border border-[rgba(234,34,97,0.3)]",
};

// Document status labels/styles and the downloadable-status set used to live
// here as well, duplicating (and drifting from) the copies in
// components/documents/document-types.ts — that module is now the single
// source of truth for the status vocabulary. Import DOC_STATUS,
// DOC_STATUS_TONE_CLASS, isReadyStatus and isBusyStatus from there.

// Compact stat tile used by tab headers / summaries.
export function StatTile({
  label,
  value,
  sublabel,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  sublabel?: ReactNode;
  tone?: "default" | "ok" | "warn" | "danger" | "navy";
}) {
  const toneClass =
    tone === "ok"
      ? "text-[#108c3d]"
      : tone === "warn"
        ? "text-[#9b6829]"
        : tone === "danger"
          ? "text-[#b51648]"
          : tone === "navy"
            ? "text-primary"
            : "text-[#061b31]";
  return (
    <div className="flex flex-col gap-1 rounded-md border border-[#e5edf5] bg-white px-4 py-3 shadow-stripe-ambient">
      <span className="type-eyebrow">{label}</span>
      <span
        className={
          "tnum font-heading text-[22px] font-semibold leading-none tracking-[-0.01em] " +
          toneClass
        }
      >
        {value}
      </span>
      {sublabel && (
        <span className="text-[12px] text-[#64748d] tnum">{sublabel}</span>
      )}
    </div>
  );
}

// Moved to components/ui/empty-state.tsx so the page-level screens can reach
// it too. Re-exported here because the seven azienda tabs already import it
// from this module alongside Panel / InfoRow / StatTile.
export { EmptyState } from "@/components/ui/empty-state";
