"use client";

/**
 * The shared vocabulary of the paywall UI.
 *
 * These three primitives (`Meter`, `Notice`, `StatusPill`) started life inside
 * `/billing/page.tsx`. They now live here because the same readings appear in
 * the sidebar, on the dashboard and in the no-plan banner, and three
 * hand-copied progress bars drift apart the first time a threshold changes.
 * The markup is lifted verbatim — `/billing` renders exactly as before.
 */

import type { ReactNode } from "react";

import { Callout } from "@/components/ui/callout";
import { PLAN_DISPLAY_NAMES } from "@/components/landing/pricing-data";
import { STATUS_LABELS, STATUS_TONE, type Entitlements } from "@/lib/billing";
import { cn } from "@/lib/utils";

/**
 * The human name of the tenant's plan.
 *
 * `plan_code` is an internal identifier — the price list calls `A_STUDIO`
 * "Studio" — and must never reach the customer. Codes that predate the public
 * catalogue (`A_FOUNDING`) have no marketing name, so they degrade to a neutral
 * label rather than leaking the code.
 */
export function planDisplayName(ent: Entitlements): string {
  if (!ent.subscribed || !ent.plan_code) return "Nessun piano";
  return PLAN_DISPLAY_NAMES[ent.plan_code] ?? "Piano attivo";
}

export function StatusPill({
  status,
  className,
}: {
  status: Entitlements["status"];
  className?: string;
}) {
  const tone = STATUS_TONE[status];
  return (
    <span
      className={cn(
        // Badge recipe from DESIGN.md §4: tinted fill, matching hairline, no
        // saturated block. Same three tones the callouts use.
        "rounded-full border px-3 py-1 text-xs font-medium",
        tone === "ok"
          ? "border-[rgba(21,190,83,0.4)] bg-[rgba(21,190,83,0.14)] text-[#0f7a37]"
          : tone === "warn"
            ? "border-[rgba(155,104,41,0.32)] bg-[rgba(155,104,41,0.12)] text-[#8a5c23]"
            : "border-[rgba(199,42,58,0.32)] bg-[rgba(199,42,58,0.1)] text-[#c72a3a]",
        className
      )}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

export function Meter({
  icon,
  label,
  used,
  total,
  percent,
  extra,
}: {
  icon: ReactNode;
  label: string;
  used: number;
  total: number | null;
  percent: number | null;
  extra?: string;
}) {
  // Warn before the wall, not at it: an operator who discovers the limit at
  // 100% has already been interrupted mid-job.
  const tone = percent === null ? "ok" : percent >= 90 ? "bad" : percent >= 75 ? "warn" : "ok";
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-2 font-medium">
          {icon}
          {label}
        </span>
        <span className="tabular-nums text-muted-foreground">
          {used} / {total === null ? "∞" : total}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={
            "h-full rounded-full transition-all " +
            (tone === "bad" ? "bg-[#ef4444]" : tone === "warn" ? "bg-[#f59e0b]" : "bg-[#15be53]")
          }
          style={{ width: `${percent ?? 0}%` }}
        />
      </div>
      {total === null && (
        <p className="text-xs text-muted-foreground">Nessun limite su questo piano.</p>
      )}
      {extra && <p className="text-xs text-muted-foreground">{extra}</p>}
    </div>
  );
}

/**
 * Billing's spelling of {@link Callout}.
 *
 * Kept as its own name because the billing screens speak in `"warn" | "bad"`
 * (the same vocabulary as `STATUS_TONE` and the meters), and translating that
 * at ~8 call sites would put the mapping in eight places instead of one.
 */
export function Notice({
  tone,
  children,
  className,
  action,
}: {
  tone: "warn" | "bad";
  children: ReactNode;
  className?: string;
  action?: ReactNode;
}) {
  return (
    <Callout tone={tone === "warn" ? "warn" : "danger"} action={action} className={className}>
      {children}
    </Callout>
  );
}

/**
 * Percentage of the metered unit consumed, or null when there is no ceiling.
 *
 * `companiesPercent` in `lib/billing` covers the consultant channel, which
 * meters `usage.max_companies`. A direct tenant is capped on `max_sites`
 * instead — same bar, different denominator.
 */
export function percentOf(used: number, total: number | null): number | null {
  if (total === null || total === 0) return null;
  return Math.min(100, Math.round((used / total) * 100));
}
