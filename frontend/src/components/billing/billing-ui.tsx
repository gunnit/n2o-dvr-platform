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
import { AlertTriangle } from "lucide-react";

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
        "rounded-full px-3 py-1 text-xs font-medium",
        tone === "ok"
          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
          : tone === "warn"
            ? "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300"
            : "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
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
            (tone === "bad" ? "bg-red-500" : tone === "warn" ? "bg-amber-500" : "bg-emerald-500")
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

export function Notice({
  tone,
  children,
  className,
}: {
  tone: "warn" | "bad";
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex gap-2 rounded-md border p-3 text-sm",
        tone === "warn"
          ? "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
          : "border-red-300 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200",
        className
      )}
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div>{children}</div>
    </div>
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
