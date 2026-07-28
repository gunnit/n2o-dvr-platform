"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import {
  Building2,
  CheckCircle2,
  CreditCard,
  FileText,
  Loader2,
  MapPin,
  Users,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { PLAN_DISPLAY_NAMES } from "@/components/landing/pricing-data";
import { Meter, Notice, StatusPill, planDisplayName } from "@/components/billing/billing-ui";
import { CreditTracker } from "@/components/billing/credit-tracker";
import { CreditPacksPanel } from "@/components/billing/credit-packs-panel";
import { useEntitlementsContext } from "@/components/billing/entitlements-provider";
import { useApi } from "@/hooks/use-api";
import { useCreditPacks, usePlans } from "@/hooks/use-entitlements";
import { usePermissions } from "@/hooks/use-permissions";
import { useTenantVocabulary } from "@/hooks/use-tenant-vocabulary";
import { BILLING_MANAGE } from "@/lib/permissions";
import {
  type Entitlements,
  type Plan,
  companiesPercent,
  formatEuro,
  formatLimit,
  formatNumber,
  formatPeriodEnd,
  formatSeats,
  shouldSuggestTopUp,
} from "@/lib/billing";

/**
 * `useSearchParams` opts the tree into client-side rendering and `next build`
 * fails without a Suspense boundary above it. Everything that reads the PayPal
 * return params lives inside `BillingPageInner` for that reason.
 */
export default function BillingPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Caricamento…
        </div>
      }
    >
      <BillingPageInner />
    </Suspense>
  );
}

function BillingPageInner() {
  const { can } = usePermissions();
  const canManage = can(BILLING_MANAGE);
  // Shared with the sidebar badge and the dashboard card — one fetch per shell,
  // and `refresh()` after a PayPal return updates all of them at once.
  const { entitlements, loading, error, refresh } = useEntitlementsContext();
  const { packs, purchases, refresh: refreshPacks } = useCreditPacks();
  const params = useSearchParams();

  // PayPal bounces the customer back here after approval. The subscription is
  // NOT active yet — the webhook decides that — so we refresh rather than
  // announce success we cannot vouch for.
  const esito = params.get("esito");
  // Carried from the public price list through signup. A hint for the UI only:
  // `/billing/subscribe` re-checks that the plan exists, is checkoutable and
  // belongs to this tenant's channel before PayPal is called (INV-5, INV-9).
  const piano = params.get("piano");

  useEffect(() => {
    if (esito === "ok") {
      toast.success(
        "Pagamento approvato. L'attivazione può richiedere qualche istante."
      );
      const t = setTimeout(() => void refresh(), 3000);
      return () => clearTimeout(t);
    }
    if (esito === "annullato") toast.info("Pagamento annullato. Nessun addebito effettuato.");
  }, [esito, refresh]);

  useCreditReturn({ onSettled: () => Promise.all([refresh(), refreshPacks()]) });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="type-h1">Abbonamento e crediti</h1>
        <p className="type-body mt-2">
          Il tuo piano, quanto hai consumato e come aggiungere crediti AI
        </p>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Caricamento del piano…
        </div>
      )}

      {error && !loading && (
        <div className="rounded-lg border bg-card p-6 text-sm text-muted-foreground">
          Non è stato possibile caricare i dati dell&apos;abbonamento. Questo non
          limita in alcun modo il tuo lavoro.
        </div>
      )}

      {entitlements && (
        <>
          <PlanSummary ent={entitlements} />

          {/* Consumption against a plan the tenant does not hold is not a
              meaningful reading — the meters would show "0 / ∞" and claim
              "nessun limite su questo piano" for a plan that isn't there. */}
          {entitlements.subscribed && (
            <>
              <CreditTracker
                ent={entitlements}
                action={
                  canManage && shouldSuggestTopUp(entitlements.usage) ? (
                    <a
                      href="#crediti"
                      className="inline-flex h-9 items-center justify-center rounded-md border border-input px-4 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
                    >
                      Aggiungi crediti
                    </a>
                  ) : undefined
                }
              />
              <PlanLimits ent={entitlements} />
              <div id="crediti" className="scroll-mt-24">
                <CreditPacksPanel
                  ent={entitlements}
                  packs={packs}
                  purchases={purchases}
                  canBuy={canManage}
                />
              </div>
            </>
          )}

          {canManage ? (
            <PlanPicker ent={entitlements} onChanged={refresh} preselected={piano} />
          ) : (
            <p className="text-sm text-muted-foreground">
              Solo un amministratore dell&apos;organizzazione può modificare
              l&apos;abbonamento o acquistare crediti.
            </p>
          )}
        </>
      )}
    </div>
  );
}

/**
 * Finish a credit purchase when PayPal returns the customer to `/billing`.
 *
 * PayPal appends its own `token` (the order id) to our return URL, so the whole
 * capture is driven from what is already in the address bar — no state has to
 * survive the redirect, which is what makes this robust against a customer who
 * completes payment in a different tab.
 *
 * The webhook is doing the same thing concurrently. Both call
 * `/credits/capture`, the row-status guard decides which one actually grants,
 * and the toast is worded so it reads correctly either way: `granted: false`
 * means "someone else banked it a second ago", not "nothing happened".
 *
 * Guarded by a ref rather than by state: React 19 Strict Mode runs effects
 * twice in development, and a duplicate capture would be a second POST against
 * a payment endpoint.
 */
function useCreditReturn({ onSettled }: { onSettled: () => Promise<unknown> }) {
  const params = useSearchParams();
  const { apiFetch } = useApi();
  const handled = useRef<string | null>(null);

  const crediti = params.get("crediti");
  const orderId = params.get("token");

  useEffect(() => {
    if (!crediti || !orderId) return;
    if (handled.current === orderId) return;
    handled.current = orderId;

    if (crediti === "annullato") {
      toast.info("Acquisto annullato. Nessun addebito effettuato.");
      void apiFetch("/api/v1/billing/credits/abandon", {
        method: "POST",
        body: JSON.stringify({ paypal_order_id: orderId }),
      }).catch(() => {
        // Housekeeping only — the purchase stays `pending` and simply reads as
        // an unfinished attempt in the history. Nothing to tell the user.
      });
      return;
    }

    void (async () => {
      try {
        const res = await apiFetch<{ granted: boolean; credits: number }>(
          "/api/v1/billing/credits/capture",
          { method: "POST", body: JSON.stringify({ paypal_order_id: orderId }) }
        );
        toast.success(
          res.granted
            ? `${formatNumber(res.credits)} crediti aggiunti al tuo piano.`
            : "Pagamento già registrato: i crediti sono sul tuo piano."
        );
      } catch (e) {
        toast.error(
          e instanceof Error
            ? e.message
            : "Non è stato possibile completare il pagamento."
        );
      } finally {
        // Refresh either way: the webhook may have granted the credits even on
        // the path where our own capture call errored.
        await onSettled();
      }
    })();
  }, [crediti, orderId, apiFetch, onSettled]);
}

/** The plan headline: what you are on, whether it is live, and until when. */
function PlanSummary({ ent }: { ent: Entitlements }) {
  const until = formatPeriodEnd(ent.period_end);

  return (
    <div className="rounded-lg border bg-card">
      <div className="flex flex-wrap items-start justify-between gap-4 p-6">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <CreditCard className="h-4 w-4" strokeWidth={1.75} />
          </span>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Piano attuale
            </p>
            {/* `plan_code` is an internal identifier: the customer bought
                "Studio", not "A_STUDIO". */}
            <p className="font-heading text-2xl font-semibold">
              {ent.subscribed ? planDisplayName(ent) : "Nessun piano attivo"}
            </p>
            {until && (
              <p className="mt-1 text-sm text-muted-foreground">
                Periodo corrente fino al <strong>{until}</strong>.
              </p>
            )}
          </div>
        </div>
        <StatusPill status={ent.status} />
      </div>

      <div className="space-y-3 px-6 pb-6">
        {/* A tenant that has never purchased has no plan limits to report —
            listing "illimitato" against every row would describe rights it does
            not hold. Show what it means instead. */}
        {!ent.subscribed && (
          <Notice tone="warn">
            Non hai ancora attivato un abbonamento.{" "}
            {ent.enforced
              ? "Attiva un piano qui sotto per generare i documenti."
              : "Puoi già usare la piattaforma: durante questa fase nessuna operazione viene bloccata. Attiva un piano qui sotto per mettere in regola l'abbonamento."}
          </Notice>
        )}
        {ent.status === "past_due" && (
          <Notice tone="warn">
            Un pagamento non è andato a buon fine. PayPal riproverà nei prossimi
            giorni: <strong>continui ad avere accesso completo</strong> nel frattempo.
          </Notice>
        )}
        {ent.status === "canceled" && (
          <Notice tone="bad">
            L&apos;abbonamento non è attivo. Puoi <strong>consultare e scaricare</strong>{" "}
            tutti i documenti già generati — la conservazione richiesta dal D.Lgs.
            81/2008 è garantita — ma non generarne di nuovi.
          </Notice>
        )}
        {!ent.enforced && (
          <p className="text-xs text-muted-foreground">
            I limiti sono attualmente indicativi: nessuna operazione viene bloccata.
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * Everything the plan caps apart from credits, metered against actual use.
 *
 * The two channels cap different things and always have: a consultant plan sells
 * *active client companies*, a direct plan sells *sedi*. Rendering the other
 * channel's row is how "illimitato aziende attive" ended up on a Base plan that
 * never promised any.
 */
function PlanLimits({ ent }: { ent: Entitlements }) {
  const vocabulary = useTenantVocabulary();
  const isDirect = ent.account_type === "direct";

  return (
    <div className="rounded-lg border bg-card">
      <div className="border-b p-6">
        <h2 className="font-heading text-[15px] font-medium">Limiti del piano</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Quanto del piano stai usando, oltre ai crediti AI.
        </p>
      </div>
      <div className="grid gap-6 p-6 sm:grid-cols-2">
        {isDirect ? (
          // Nothing meters sedi yet, so this is a stated ceiling rather than a
          // reading. A bar at an invented denominator would look like data.
          <LimitRow
            icon={<MapPin className="h-4 w-4" />}
            label="Sedi incluse"
            value={formatLimit(ent.max_sites)}
          />
        ) : (
          <Meter
            icon={<Building2 className="h-4 w-4" />}
            label={vocabulary.activeCompanies}
            used={ent.usage.active_companies}
            total={ent.usage.max_companies}
            percent={companiesPercent(ent.usage)}
          />
        )}

        {/* Seats are counted server-side as "rows in `users`", so there is no
            separate usage figure to read here — the ceiling is the fact. */}
        <LimitRow
          icon={<Users className="h-4 w-4" />}
          label="Utenti inclusi"
          value={formatSeats(ent.seats)}
        />
        <LimitRow
          icon={<FileText className="h-4 w-4" />}
          label="Tipi di documento"
          value={
            ent.allowed_doc_types === null
              ? "tutti e 17"
              : `${ent.allowed_doc_types.length} inclusi`
          }
          hint={
            ent.allowed_doc_types === null
              ? undefined
              : "I tipi non inclusi restano visibili ma bloccati."
          }
        />
        <LimitRow
          icon={<CreditCard className="h-4 w-4" />}
          label="Crediti AI inclusi / anno"
          value={
            ent.ai_credits_year === null
              ? "illimitati"
              : formatNumber(ent.ai_credits_year)
          }
        />
      </div>
    </div>
  );
}

function LimitRow({
  icon,
  label,
  value,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="flex items-center gap-2 font-medium">
          {icon}
          {label}
        </span>
        <span className="tabular-nums text-muted-foreground">{value}</span>
      </div>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function PlanPicker({
  ent,
  onChanged,
  preselected,
}: {
  ent: Entitlements;
  onChanged: () => void;
  /** `?piano=` from the public price list, or null. */
  preselected?: string | null;
}) {
  const { plans, loading } = usePlans();
  const { apiFetch } = useApi();
  const [busy, setBusy] = useState<string | null>(null);

  const start = useCallback(
    async (plan: Plan) => {
      setBusy(plan.plan_code);
      try {
        // `revise` when there is already a live PayPal subscription, `subscribe`
        // otherwise — both return an approval URL the customer must visit.
        const endpoint = ent.status === "active" && ent.plan_code !== "A_FOUNDING"
          ? "/api/v1/billing/revise"
          : "/api/v1/billing/subscribe";
        const res = await apiFetch<{ approval_url: string }>(endpoint, {
          method: "POST",
          body: JSON.stringify({ plan_code: plan.plan_code }),
        });
        if (res.approval_url) {
          window.location.href = res.approval_url;
          return;
        }
        toast.success("Modifica registrata presso PayPal.");
        onChanged();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Operazione non riuscita");
      } finally {
        setBusy(null);
      }
    },
    [apiFetch, ent.plan_code, ent.status, onChanged]
  );

  const cancel = useCallback(async () => {
    setBusy("cancel");
    try {
      await apiFetch("/api/v1/billing/cancel", {
        method: "POST",
        body: JSON.stringify({ reason: "Richiesta dell'utente" }),
      });
      toast.success(
        "Disdetta inviata. L'abbonamento resta attivo fino alla fine del periodo pagato."
      );
      onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Disdetta non riuscita");
    } finally {
      setBusy(null);
    }
  }, [apiFetch, onChanged]);

  if (loading) return null;
  if (plans.length === 0) {
    // The customer may have arrived here straight from "Attiva Base" on the
    // public price list. Dropping that intent silently — which is what a bare
    // "nessun piano disponibile" does — reads as if the click did nothing.
    // Name the plan back to them and hand over a route that still works.
    const chosen = PLAN_DISPLAY_NAMES[preselected ?? ""];
    const subject = encodeURIComponent(
      chosen
        ? `Attivazione piano ${chosen} — N2O DVR`
        : "Attivazione abbonamento — N2O DVR"
    );
    return (
      <div className="rounded-lg border bg-card">
        <div className="border-b p-6">
          <h2 className="font-heading text-[15px] font-medium">
            {chosen ? `Attivazione del piano ${chosen}` : "Attivazione abbonamento"}
          </h2>
        </div>
        <div className="space-y-3 p-6 text-sm text-muted-foreground">
          {chosen ? (
            <p>
              Hai scelto il piano <strong className="text-foreground">{chosen}</strong>. Il
              pagamento online non è al momento attivo su questo ambiente, quindi
              non possiamo portarti su PayPal.
            </p>
          ) : (
            <p>Il pagamento online non è al momento attivo su questo ambiente.</p>
          )}
          <p>
            Scrivici a{" "}
            <a
              className="text-primary hover:underline"
              href={`mailto:support@dvr-sicurezza.it?subject=${subject}`}
            >
              support@dvr-sicurezza.it
            </a>{" "}
            e attiviamo il piano per te.
            {/* This sentence used to promise "puoi continuare a usare la
                piattaforma senza limitazioni" unconditionally. That was written
                during the shadow window and became false the moment
                ENTITLEMENTS_ENFORCE went on: an unsubscribed tenant is refused
                document generation and azienda creation. Telling someone they
                are unrestricted while the server 402s them is the worst
                possible combination, so the claim now follows `enforced`. */}
            {ent.enforced ? (
              <>
                {" "}
                Nel frattempo puoi consultare e scaricare i documenti già
                generati, ma non crearne di nuovi.
              </>
            ) : (
              <> Nel frattempo puoi continuare a usare la piattaforma senza limitazioni.</>
            )}
          </p>
        </div>
      </div>
    );
  }

  // Only honour `?piano=` when it names a plan actually on offer and not the
  // one already in force — otherwise the banner would promise something the
  // picker below cannot deliver.
  const wanted = plans.find(
    (p) => p.plan_code === preselected && p.plan_code !== ent.plan_code
  );

  return (
    <div className="rounded-lg border bg-card">
      <div className="border-b p-6">
        <h2 className="font-heading text-[15px] font-medium">
          {ent.subscribed ? "Cambia piano" : "Piani disponibili"}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Prezzi annuali, IVA esclusa. Il pagamento avviene tramite PayPal e
          l&apos;attivazione è confermata solo dopo la conferma di PayPal.
        </p>
      </div>
      <div className="space-y-4 p-6">
        {wanted && (
          <div className="flex gap-2 rounded-md border border-primary/30 bg-primary/5 p-3 text-sm">
            <CreditCard className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <p>
              Hai scelto il piano <strong>{wanted.display_name}</strong> a{" "}
              {formatEuro(wanted.price_year_cents)} all&apos;anno, IVA esclusa.
              Completa l&apos;attivazione qui sotto: verrai portato su PayPal per
              approvare l&apos;abbonamento.
            </p>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {plans.map((plan) => {
            const current = plan.plan_code === ent.plan_code;
            const highlighted = wanted?.plan_code === plan.plan_code;
            return (
              <div
                key={plan.plan_code}
                className={
                  "flex flex-col rounded-lg border p-4 " +
                  (current
                    ? "border-emerald-500 bg-emerald-50/40 dark:bg-emerald-950/20"
                    : highlighted
                      ? "border-primary ring-1 ring-primary/30"
                      : "")
                }
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">{plan.display_name}</h3>
                  {current && (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-label="Piano attuale" />
                  )}
                </div>
                <p className="mt-2 text-2xl font-semibold">{formatEuro(plan.price_year_cents)}</p>
                <p className="text-xs text-muted-foreground">all&apos;anno, IVA esclusa</p>
                <ul className="mt-3 flex-1 space-y-1 text-sm text-muted-foreground">
                  <li>{plan.seats} utenti</li>
                  {/* The two channels meter different things: a consultant plan
                      caps client companies, a direct plan caps the company's own
                      sedi. Showing "illimitato aziende attive" on a Base plan —
                      which is what max_companies=null renders as — would read as
                      a promise it never made. */}
                  <li>
                    {plan.model === "B"
                      ? `${formatLimit(plan.max_sites)} sedi`
                      : `${formatLimit(plan.max_companies)} aziende attive`}
                  </li>
                  <li>
                    {plan.ai_credits_year === null
                      ? "Crediti AI illimitati"
                      : `${formatNumber(plan.ai_credits_year)} crediti AI`}
                  </li>
                </ul>
                <Button
                  className="mt-4"
                  disabled={current || busy !== null}
                  onClick={() => void start(plan)}
                >
                  {busy === plan.plan_code && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {current
                    ? "Piano attuale"
                    : highlighted
                      ? "Attiva questo piano"
                      : "Passa a questo piano"}
                </Button>
              </div>
            );
          })}
        </div>

        {/* Nothing to disdire when there is no subscription — and `canceled`
            already has none live either. */}
        {ent.subscribed && ent.status !== "canceled" && (
          <div className="border-t pt-4">
            <Button variant="outline" disabled={busy !== null} onClick={() => void cancel()}>
              {busy === "cancel" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Disdici abbonamento
            </Button>
            <p className="mt-2 text-xs text-muted-foreground">
              Manterrai l&apos;accesso fino alla fine del periodo già pagato e potrai
              sempre scaricare i documenti già generati.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
