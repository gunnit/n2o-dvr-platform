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
    <div className="flex items-center justify-between gap-3 border-b border-[#e5edf5] px-6 py-4">
      <div className="flex items-center gap-2.5 min-w-0">
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

export const docStatusStyles: Record<string, string> = {
  pending: "bg-[#f6f9fc] text-[#273951] border border-[#e5edf5]",
  in_progress:
    "bg-[rgba(155,104,41,0.12)] text-[#9b6829] border border-[rgba(155,104,41,0.3)]",
  completed:
    "bg-[rgba(21,190,83,0.2)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
  failed:
    "bg-[rgba(234,34,97,0.08)] text-[#b51648] border border-[rgba(234,34,97,0.25)]",
  bozza: "bg-[#f6f9fc] text-[#273951] border border-[#e5edf5]",
};

export const docStatusLabels: Record<string, string> = {
  pending: "In attesa",
  in_progress: "In generazione",
  completed: "Pronto",
  failed: "Errore",
  bozza: "Bozza",
};

// Documents whose status indicates a downloadable file is available
// on the server.
export const DOWNLOADABLE_DOC_STATUSES = new Set([
  "completed",
  "ready",
  "pronto",
]);

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

export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
}: {
  icon?: ComponentType<{ className?: string; strokeWidth?: number }>;
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
      {Icon && (
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-[#f6f9fc]">
          <Icon className="h-5 w-5 text-[#64748d]" strokeWidth={1.5} />
        </span>
      )}
      <div className="space-y-1">
        <p className="text-[14px] font-medium text-[#273951]">{title}</p>
        {body && (
          <p className="max-w-[420px] text-[13px] text-[#64748d]">{body}</p>
        )}
      </div>
      {action}
    </div>
  );
}
