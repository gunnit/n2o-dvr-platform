"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { AlertTriangle, CheckCircle2, CreditCard, Loader2, Users, Zap } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useApi } from "@/hooks/use-api";
import { useEntitlements, usePlans } from "@/hooks/use-entitlements";
import {
  type Entitlements,
  type Plan,
  STATUS_LABELS,
  STATUS_TONE,
  companiesPercent,
  creditsPercent,
  formatEuro,
  formatLimit,
  formatPeriodEnd,
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
  const { data: session } = useSession();
  const isAdmin = (session?.user as { role?: string } | undefined)?.role === "admin";
  const { entitlements, loading, error, refresh } = useEntitlements();
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

  return (
    <div className="space-y-8">
      <div>
        <h1 className="type-h1">Abbonamento</h1>
        <p className="type-body mt-2">Piano, consumi e fatturazione</p>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Caricamento del piano…
        </div>
      )}

      {error && !loading && (
        <Card>
          <CardContent className="pt-6 text-sm text-muted-foreground">
            Non è stato possibile caricare i dati dell&apos;abbonamento. Questo non
            limita in alcun modo il tuo lavoro.
          </CardContent>
        </Card>
      )}

      {entitlements && (
        <>
          <CurrentPlanCard ent={entitlements} />
          <UsageCard ent={entitlements} />
          {isAdmin && (
            <PlanPicker ent={entitlements} onChanged={refresh} preselected={piano} />
          )}
          {!isAdmin && (
            <p className="text-sm text-muted-foreground">
              Solo un amministratore dell&apos;organizzazione può modificare
              l&apos;abbonamento.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function CurrentPlanCard({ ent }: { ent: Entitlements }) {
  const tone = STATUS_TONE[ent.status];
  const until = formatPeriodEnd(ent.period_end);
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <CreditCard className="h-5 w-5" /> Piano attuale
        </CardTitle>
        <span
          className={
            "rounded-full px-3 py-1 text-xs font-medium " +
            (tone === "ok"
              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
              : tone === "warn"
                ? "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300"
                : "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300")
          }
        >
          {STATUS_LABELS[ent.status]}
        </span>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-2xl font-semibold">{ent.plan_code}</p>
        <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
          <Row label="Utenti inclusi" value={String(ent.seats)} />
          {/* A consultant plan meters client companies; a direct plan meters the
              tenant's own sedi. `max_companies` is null on every B plan, so
              showing that row to a direct tenant would read "illimitato". */}
          {ent.account_type === "direct" ? (
            <Row label="Sedi incluse" value={formatLimit(ent.max_sites)} />
          ) : (
            <Row label="Aziende attive" value={formatLimit(ent.max_companies)} />
          )}
          <Row
            label="Crediti AI / anno"
            value={ent.ai_credits_year === null ? "illimitati" : String(ent.ai_credits_year)}
          />
          <Row
            label="Tipi di documento"
            value={
              ent.allowed_doc_types === null
                ? "tutti"
                : `${ent.allowed_doc_types.length} inclusi`
            }
          />
        </dl>
        {until && (
          <p className="text-sm text-muted-foreground">
            Periodo corrente fino al <strong>{until}</strong>.
          </p>
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
      </CardContent>
    </Card>
  );
}

function UsageCard({ ent }: { ent: Entitlements }) {
  const credits = creditsPercent(ent.usage);
  const companies = companiesPercent(ent.usage);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Consumi del periodo</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <Meter
          icon={<Zap className="h-4 w-4" />}
          label="Crediti AI"
          used={ent.usage.ai_credits_used}
          total={ent.usage.ai_credits_allowance}
          percent={credits}
          extra={
            ent.usage.ai_credits_overage > 0
              ? `include ${ent.usage.ai_credits_overage} crediti extra acquistati`
              : undefined
          }
        />
        {/* The active-company meter is a Model A concept: it counts how many
            *client* companies a studio touched this period. A direct tenant
            documents one company — its own — so the meter would always read
            "1 / ∞" and mean nothing. Sedi are the direct-channel limit, but
            nothing meters them yet, so we show no bar rather than a fake one. */}
        {ent.account_type !== "direct" && (
          <Meter
            icon={<Users className="h-4 w-4" />}
            label="Aziende attive"
            used={ent.usage.active_companies}
            total={ent.usage.max_companies}
            percent={companies}
          />
        )}
      </CardContent>
    </Card>
  );
}

function Meter({
  icon,
  label,
  used,
  total,
  percent,
  extra,
}: {
  icon: React.ReactNode;
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
    return (
      <Card>
        <CardContent className="pt-6 text-sm text-muted-foreground">
          Nessun piano acquistabile online al momento. Scrivi a{" "}
          <a className="text-primary hover:underline" href="mailto:support@dvr-sicurezza.it">
            support@dvr-sicurezza.it
          </a>{" "}
          e attiviamo il piano per te.
        </CardContent>
      </Card>
    );
  }

  // Only honour `?piano=` when it names a plan actually on offer and not the
  // one already in force — otherwise the banner would promise something the
  // picker below cannot deliver.
  const wanted = plans.find(
    (p) => p.plan_code === preselected && p.plan_code !== ent.plan_code
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Piani disponibili</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
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
                      : `${plan.ai_credits_year} crediti AI`}
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

        <p className="text-xs text-muted-foreground">
          I prezzi sono annuali e IVA esclusa. Il pagamento avviene tramite PayPal;
          l&apos;attivazione è confermata solo dopo la conferma di PayPal.
        </p>

        {ent.status !== "canceled" && (
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
      </CardContent>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 sm:block">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

function Notice({ tone, children }: { tone: "warn" | "bad"; children: React.ReactNode }) {
  return (
    <div
      className={
        "flex gap-2 rounded-md border p-3 text-sm " +
        (tone === "warn"
          ? "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
          : "border-red-300 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200")
      }
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div>{children}</div>
    </div>
  );
}
