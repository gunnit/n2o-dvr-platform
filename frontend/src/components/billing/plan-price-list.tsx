"use client";

/**
 * The price list, rendered when live checkout is unavailable.
 *
 * `GET /billing/plans` returns only plans PayPal can actually sell — rows with
 * a `paypal_plan_id`. When a deployment has not been provisioned against a
 * PayPal merchant yet, that list is empty, and the customer used to get a
 * three-line block of text and a mailto: no plan names, no prices, nothing to
 * decide with. Somebody evaluating the product would have to email support to
 * find out what it costs.
 *
 * So this renders the same catalogue the public `/prezzi` page renders, from
 * the same static data, with the buttons off and one honest sentence about why.
 * A price the customer can read is worth more than a button they cannot press.
 *
 * The prices here are marketing copy kept in step with
 * `backend/app/billing/plan_catalogue.py` by the header comment in
 * `pricing-data.ts` — this component never quotes a number of its own.
 */

import { Check, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PLANS, SUPPORT_EMAIL, type Audience } from "@/components/landing/pricing-data";
import { cn } from "@/lib/utils";

/**
 * Which price list belongs to this tenant.
 *
 * The channel guardrail (INV-9) applies to *showing* a price as much as to
 * charging it: a direct company must never be quoted a consultant plan, since
 * `/billing/subscribe` would refuse it with a 403 anyway.
 */
function audienceFor(accountType: string): Audience {
  return accountType === "direct" ? "aziende" : "consulenti";
}

export function PlanPriceList({
  accountType,
  /** The plan already in force, so it can be marked rather than re-offered. */
  currentPlanCode,
  /** `?piano=` carried from the public price list through signup. */
  preselected,
}: {
  accountType: string;
  currentPlanCode: string | null;
  preselected?: string | null;
}) {
  const plans = PLANS[audienceFor(accountType)];
  const chosen = plans.find((p) => p.planCode === preselected);

  const subject = encodeURIComponent(
    chosen
      ? `Attivazione piano ${chosen.name} — N2O DVR`
      : "Attivazione abbonamento — N2O DVR"
  );

  return (
    <div className="rounded-lg border bg-card">
      <div className="border-b p-6">
        <h2 className="font-heading text-[15px] font-medium">Piani disponibili</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Prezzi annuali, IVA esclusa. I costi di attivazione una tantum sono
          fatturati a parte.
        </p>
      </div>

      <div className="space-y-5 p-6">
        {/* Stated once, above the cards, so every disabled button below is
            already explained by the time it is read. */}
        <div className="flex gap-3 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
          <Mail className="mt-0.5 h-4 w-4 shrink-0" />
          <div className="space-y-1">
            <p className="font-medium">
              Il pagamento online non è attivo su questo ambiente.
            </p>
            <p>
              {chosen ? (
                <>
                  Hai scelto il piano <strong>{chosen.name}</strong>. Scrivici a{" "}
                </>
              ) : (
                <>Per attivare un piano scrivici a </>
              )}
              <a
                className="font-medium underline underline-offset-2"
                href={`mailto:${SUPPORT_EMAIL}?subject=${subject}`}
              >
                {SUPPORT_EMAIL}
              </a>{" "}
              e lo attiviamo noi, di norma in giornata.
            </p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {plans.map((plan) => {
            const current = plan.planCode === currentPlanCode;
            const highlighted = !current && plan.planCode === preselected;
            return (
              <div
                key={plan.planCode}
                className={cn(
                  "flex flex-col rounded-lg border p-4",
                  current && "border-emerald-500 bg-emerald-50/40 dark:bg-emerald-950/20",
                  highlighted && "border-primary ring-1 ring-primary/30"
                )}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <h3 className="font-heading font-semibold">{plan.name}</h3>
                  {current && (
                    <span className="shrink-0 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                      Attuale
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{plan.audience}</p>

                <p className="mt-3 font-heading text-2xl font-semibold tabular-nums">
                  {plan.price}
                </p>
                <p className="text-xs text-muted-foreground">{plan.priceNote}</p>
                <p className="mt-1 text-xs text-muted-foreground">{plan.setupNote}</p>

                <ul className="mt-4 flex-1 space-y-1.5 text-sm text-muted-foreground">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex gap-2">
                      <Check
                        className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600 dark:text-emerald-400"
                        strokeWidth={2.5}
                      />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* Disabled, not hidden: the shape of the page should not change
                    when provisioning lands, and a missing button reads as a
                    plan that cannot be bought at all. */}
                <Button
                  className="mt-4 w-full"
                  variant={highlighted ? "default" : "outline"}
                  disabled
                  title="Attivazione tramite il supporto"
                >
                  {current ? "Piano attuale" : plan.ctaLabel}
                </Button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
