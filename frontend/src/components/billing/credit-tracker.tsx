"use client";

/**
 * The AI credit tracker — "how many credits do we still have", answered once.
 *
 * The product owner's requirement, and the one number the whole billing screen
 * exists to make unambiguous. Three design calls behind it:
 *
 * * **It leads with what is left, not what is spent.** "1.260 rimanenti" is the
 *   number someone about to run a batch of SDS extractions needs; "1.240 usati"
 *   makes them do the subtraction.
 * * **Included and purchased credits are shown separately.** They behave
 *   identically when spent but not when the period rolls over — packs do not
 *   carry across — so collapsing them into one figure would hide the only
 *   difference that matters.
 * * **The breakdown is part of the tracker, not a separate report.** "You have
 *   used 60% of your credits" is not actionable. "…and 80% of that went on
 *   schede di sicurezza" tells the operator what to change.
 */

import { Sparkles, Zap } from "lucide-react";

import { Callout } from "@/components/ui/callout";

import {
  type Entitlements,
  creditKindLabel,
  creditsPercent,
  formatNumber,
  formatPeriodEnd,
  meterTone,
} from "@/lib/billing";
import { cn } from "@/lib/utils";

const TONE_BAR: Record<string, string> = {
  ok: "bg-[#15be53]",
  warn: "bg-[#f59e0b]",
  bad: "bg-[#ef4444]",
};

const TONE_TEXT: Record<string, string> = {
  ok: "text-[#0f7a37] dark:text-[#0f7a37]",
  warn: "text-[#8a5c23] dark:text-[#8a5c23]",
  bad: "text-[#b01e2e] dark:text-[#b01e2e]",
};

export function CreditTracker({
  ent,
  /** Rendered under the meter — the "Acquista crediti" button, when allowed. */
  action,
}: {
  ent: Entitlements;
  action?: React.ReactNode;
}) {
  const { usage } = ent;
  const unmetered = usage.ai_credits_allowance === null;
  const percent = creditsPercent(usage);
  const tone = meterTone(percent);
  const until = formatPeriodEnd(ent.period_end);
  const breakdown = usage.by_kind ?? [];
  const totalBreakdown = breakdown.reduce((sum, row) => sum + row.credits, 0);

  return (
    <div className="rounded-lg border bg-card">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b p-6">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Zap className="h-4 w-4" strokeWidth={1.75} />
          </span>
          <div>
            <h2 className="font-heading text-[15px] font-medium">Crediti AI</h2>
            <p className="text-sm text-muted-foreground">
              {unmetered
                ? "Il tuo piano non ha un tetto di crediti."
                : until
                  ? `Periodo corrente, fino al ${until}.`
                  : "Periodo corrente."}
            </p>
          </div>
        </div>

        {/* The headline. Unmetered plans get a word, not a number: rendering
            "∞ rimanenti" next to a progress bar at 0% reads as a bug. */}
        <div className="text-right">
          {unmetered ? (
            <p className="font-heading text-3xl font-semibold tabular-nums">Illimitati</p>
          ) : (
            <>
              <p
                className={cn(
                  "font-heading text-3xl font-semibold tabular-nums",
                  TONE_TEXT[tone]
                )}
              >
                {formatNumber(usage.ai_credits_remaining ?? 0)}
              </p>
              <p className="text-xs text-muted-foreground">
                crediti rimanenti su {formatNumber(usage.ai_credits_allowance ?? 0)}
              </p>
            </>
          )}
        </div>
      </div>

      {!unmetered && (
        <div className="space-y-5 p-6">
          <div className="space-y-2">
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className={cn("h-full rounded-full transition-all", TONE_BAR[tone])}
                style={{ width: `${percent ?? 0}%` }}
                role="progressbar"
                aria-valuenow={percent ?? 0}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Crediti AI consumati"
              />
            </div>
            <div className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground">
              <span>
                {formatNumber(usage.ai_credits_used)} usati ({percent ?? 0}%)
              </span>
              <span className="tabular-nums">
                {formatNumber(usage.ai_credits_included ?? 0)} inclusi nel piano
                {usage.ai_credits_overage > 0 && (
                  <> · +{formatNumber(usage.ai_credits_overage)} acquistati</>
                )}
              </span>
            </div>
          </div>

          {tone !== "ok" && (
            <Callout tone={tone === "bad" ? "danger" : "warn"}>
              {tone === "bad" ? (
                <>
                  Hai usato oltre il 90% dei crediti del periodo. Quando finiscono,
                  le funzioni AI si fermano — la generazione dei documenti senza AI
                  e il download restano sempre disponibili.
                </>
              ) : (
                <>
                  Hai usato oltre il 75% dei crediti del periodo. Se prevedi altre
                  estrazioni, conviene aggiungere un pacchetto prima di restare a
                  secco a metà pratica.
                </>
              )}
            </Callout>
          )}

          {breakdown.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Dove sono andati
              </p>
              <ul className="space-y-2">
                {breakdown.map((row) => {
                  // Share of *consumption*, not of the allowance: the question
                  // this list answers is "what is eating my credits".
                  const share =
                    totalBreakdown > 0
                      ? Math.round((row.credits / totalBreakdown) * 100)
                      : 0;
                  return (
                    <li key={row.kind} className="space-y-1">
                      <div className="flex items-baseline justify-between gap-3 text-sm">
                        <span className="min-w-0 truncate">{creditKindLabel(row.kind)}</span>
                        <span className="shrink-0 tabular-nums text-muted-foreground">
                          {formatNumber(row.credits)} cr · {formatNumber(row.actions)}{" "}
                          {row.actions === 1 ? "azione" : "azioni"}
                        </span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-primary/60"
                          style={{ width: `${share}%` }}
                        />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {breakdown.length === 0 && usage.ai_credits_used === 0 && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Sparkles className="h-4 w-4" />
              Nessun credito consumato in questo periodo.
            </p>
          )}

          {action}
        </div>
      )}
    </div>
  );
}
