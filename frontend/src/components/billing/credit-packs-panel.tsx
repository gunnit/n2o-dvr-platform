"use client";

/**
 * Buying AI credits — the top-up funnel (closes D-14).
 *
 * A pack is a one-time PayPal order, not a plan change, so the flow is
 * deliberately shorter than the subscription one: pick, approve, come back,
 * done. The page handles the return in `useCreditReturn`; this component only
 * has to get the customer to PayPal and be honest about what happens when they
 * are not allowed to go.
 *
 * The expiry line is not fine print. `overage_credits` lives on the current
 * period's counter and does not roll over, so a customer buying 10.000 credits
 * a week before renewal needs to know that before paying, not after.
 */

import { useCallback, useState } from "react";
import { CheckCircle2, Loader2, Plus, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import {
  type CreditPack,
  type CreditPurchase,
  type Entitlements,
  PURCHASE_STATUS_LABELS,
  formatDateTime,
  formatEuro,
  formatNumber,
  formatPeriodEnd,
} from "@/lib/billing";
import { cn } from "@/lib/utils";

export function CreditPacksPanel({
  ent,
  packs,
  purchases,
  /** False for a role that may read billing but not spend (BILLING_MANAGE). */
  canBuy,
}: {
  ent: Entitlements;
  packs: CreditPack[];
  purchases: CreditPurchase[];
  canBuy: boolean;
}) {
  const { apiFetch } = useApi();
  const [busy, setBusy] = useState<string | null>(null);

  const buy = useCallback(
    async (pack: CreditPack) => {
      setBusy(pack.pack_code);
      try {
        const res = await apiFetch<{ approval_url: string }>(
          "/api/v1/billing/credits/checkout",
          { method: "POST", body: JSON.stringify({ pack_code: pack.pack_code }) }
        );
        if (res.approval_url) {
          window.location.href = res.approval_url;
          return;
        }
        // The endpoint only ever returns 200 with a link; anything else is a
        // contract break worth surfacing rather than a silent no-op.
        toast.error("PayPal non ha restituito un link di pagamento.");
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Acquisto non riuscito");
      } finally {
        setBusy(null);
      }
    },
    [apiFetch]
  );

  // Nothing to sell to a plan with no ceiling, and nothing to sell before there
  // is a plan at all — `/credits/checkout` refuses both, so offering the cards
  // would be an invitation to a 409.
  const unmetered = ent.usage.ai_credits_allowance === null;
  if (unmetered || packs.length === 0) return null;

  const until = formatPeriodEnd(ent.period_end);
  const blockedReason = !ent.subscribed
    ? "Attiva prima un abbonamento: i pacchetti si aggiungono a un piano esistente."
    : !ent.is_active
      ? "Rinnova l'abbonamento per poter acquistare crediti aggiuntivi."
      : null;

  return (
    <div className="rounded-lg border bg-card">
      <div className="border-b p-6">
        <h2 className="flex items-center gap-2 font-heading text-[15px] font-medium">
          <Plus className="h-4 w-4" strokeWidth={1.75} />
          Crediti aggiuntivi
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Pacchetti una tantum che si sommano ai crediti del piano.
          {until && (
            <>
              {" "}
              Valgono per il periodo in corso, fino al <strong>{until}</strong>.
            </>
          )}
        </p>
      </div>

      <div className="space-y-4 p-6">
        {blockedReason && (
          <p className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
            {blockedReason}
          </p>
        )}

        <div className="grid gap-4 md:grid-cols-3">
          {packs.map((pack) => (
            <div
              key={pack.pack_code}
              className={cn(
                "flex flex-col rounded-lg border p-4",
                pack.recommended && "border-primary ring-1 ring-primary/25"
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium">{pack.display_name}</h3>
                {pack.recommended && (
                  <span className="shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary">
                    Consigliato
                  </span>
                )}
              </div>
              <p className="mt-2 font-heading text-2xl font-semibold">
                {formatEuro(pack.price_cents)}
              </p>
              <p className="text-xs text-muted-foreground">
                una tantum, IVA esclusa ·{" "}
                {/* The unit price is what makes the tiers comparable at a
                    glance; three decimals because the biggest pack is under
                    10 cents a credit. */}
                {pack.price_per_credit_cents.toFixed(2).replace(".", ",")} cent per credito
              </p>
              <p className="mt-3 flex-1 text-sm text-muted-foreground">{pack.description}</p>
              <Button
                className="mt-4"
                variant={pack.recommended ? "default" : "outline"}
                disabled={!canBuy || busy !== null || blockedReason !== null}
                onClick={() => void buy(pack)}
              >
                {busy === pack.pack_code && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Acquista {formatNumber(pack.credits)} crediti
              </Button>
            </div>
          ))}
        </div>

        {!canBuy && (
          <p className="text-sm text-muted-foreground">
            Solo un amministratore dell&apos;organizzazione può acquistare crediti.
          </p>
        )}

        {purchases.length > 0 && <PurchaseHistory purchases={purchases} />}
      </div>
    </div>
  );
}

/**
 * Past top-ups, pending ones included.
 *
 * A customer who abandoned PayPal should see the attempt sitting here rather
 * than wonder whether the click registered — "In attesa di pagamento" answers
 * the support ticket before it is written.
 */
function PurchaseHistory({ purchases }: { purchases: CreditPurchase[] }) {
  return (
    <div className="space-y-2 border-t pt-4">
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Acquisti recenti
      </p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[32rem] text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground">
              <th className="py-2 pr-4 font-medium">Data</th>
              <th className="py-2 pr-4 font-medium">Pacchetto</th>
              <th className="py-2 pr-4 text-right font-medium">Crediti</th>
              <th className="py-2 pr-4 text-right font-medium">Importo</th>
              <th className="py-2 font-medium">Stato</th>
            </tr>
          </thead>
          <tbody>
            {purchases.map((p) => (
              <tr key={p.id} className="border-t">
                <td className="py-2 pr-4 text-muted-foreground">
                  {formatDateTime(p.completed_at ?? p.created_at)}
                </td>
                <td className="py-2 pr-4">{p.display_name}</td>
                <td className="py-2 pr-4 text-right tabular-nums">
                  {formatNumber(p.credits)}
                </td>
                <td className="py-2 pr-4 text-right tabular-nums">
                  {formatEuro(p.amount_cents)}
                </td>
                <td className="py-2">
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 whitespace-nowrap text-xs",
                      p.status === "completed"
                        ? "text-emerald-600 dark:text-emerald-400"
                        : p.status === "pending"
                          ? "text-amber-600 dark:text-amber-400"
                          : "text-muted-foreground"
                    )}
                  >
                    {p.status === "completed" ? (
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5" />
                    )}
                    {PURCHASE_STATUS_LABELS[p.status]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
