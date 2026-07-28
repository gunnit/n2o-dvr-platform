"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ADDONS,
  COMPARISON,
  PLANS,
  SUPPORT_EMAIL,
  type Audience,
  type PricingPlan,
} from "@/components/landing/pricing-data";

const TABS: { id: Audience; label: string; note: string }[] = [
  {
    id: "consulenti",
    label: "Consulenti e studi",
    note: "Per chi vende sicurezza a più aziende clienti sotto il proprio marchio.",
  },
  {
    id: "aziende",
    label: "Aziende",
    note: "Per il datore di lavoro che deve tenere aggiornato il fascicolo della propria impresa.",
  },
];

function contactHref(plan: PricingPlan) {
  const subject = `Richiesta piano ${plan.name} — N2O DVR`;
  return `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(subject)}`;
}

/**
 * Where a self-serve card sends the customer. Signed-out visitors have to
 * create the organization first, so they go through registration carrying the
 * plan; signed-in ones land straight on the billing screen with it preselected.
 * Either way `?piano=` is only a hint — the plan is re-validated server-side
 * before PayPal is ever called.
 */
function checkoutHref(plan: PricingPlan, signedIn: boolean) {
  const target = signedIn ? "/billing" : "/register";
  return `${target}?piano=${encodeURIComponent(plan.planCode)}`;
}

function PlanCard({ plan, signedIn }: { plan: PricingPlan; signedIn: boolean }) {
  const dark = plan.dark ?? false;

  return (
    <article
      className={[
        "relative flex flex-col rounded-[10px] border p-6 sm:px-6 sm:py-7",
        dark
          ? "border-[#061b31] bg-[#061b31] shadow-stripe-standard"
          : plan.featured
            ? "border-[#003d74] bg-white shadow-stripe-elevated"
            : "border-[#e5edf5] bg-white shadow-stripe-standard",
      ].join(" ")}
    >
      {plan.featured && (
        <span className="absolute -top-[11px] left-6 rounded-[4px] bg-[#003d74] px-2.5 py-[3px] text-[11px] font-semibold tracking-[0.08em] text-white uppercase">
          Consigliato
        </span>
      )}
      <p
        className={`font-heading text-[19px] font-medium tracking-[-0.015em] ${dark ? "text-white" : "text-[#061b31]"}`}
      >
        {plan.name}
      </p>
      <p
        className={`mt-1.5 min-h-10 text-[13.5px] leading-[1.5] ${dark ? "text-white/62" : "text-[#64748d]"}`}
      >
        {plan.audience}
      </p>
      <p
        className={`tnum mt-[22px] font-heading text-[34px] font-light tracking-[-0.03em] ${dark ? "text-white" : "text-[#061b31]"}`}
      >
        {plan.price}
      </p>
      <p className={`mt-1 text-[12.5px] ${dark ? "text-white/60" : "text-[#64748d]"}`}>
        {plan.priceNote}
      </p>
      <p
        className={`mt-3 rounded-[4px] px-2.5 py-[7px] text-[12.5px] ${dark ? "bg-white/8 text-white/82" : "bg-[#f6f9fc] text-[#273951]"}`}
      >
        {plan.setupNote}
      </p>

      <ul className="mt-[22px] grid flex-1 gap-[9px]">
        {plan.features.map((feature) => (
          <li
            key={feature}
            className={`flex gap-[9px] text-[13.5px] leading-[1.45] ${dark ? "text-white/82" : "text-[#273951]"}`}
          >
            <span aria-hidden className={dark ? "text-[#a5c8ff]" : "text-[#003d74]"}>
              —
            </span>
            {feature}
          </li>
        ))}
      </ul>

      {plan.cta === "checkout" ? (
        <Link
          href={checkoutHref(plan, signedIn)}
          className={[
            "mt-6 inline-flex h-[42px] items-center justify-center rounded-[4px] text-[14.5px] font-medium transition-colors",
            plan.featured
              ? "bg-[#003d74] text-white hover:bg-[#1b5594]"
              : "border border-[#003d74] bg-white text-[#003d74] hover:bg-[#f6f9fc]",
          ].join(" ")}
        >
          {plan.ctaLabel}
        </Link>
      ) : (
        <a
          href={contactHref(plan)}
          className={[
            "mt-6 inline-flex h-[42px] items-center justify-center rounded-[4px] text-[14.5px] font-medium transition-colors",
            dark
              ? "bg-white text-[#061b31] hover:bg-[#e5edf5]"
              : plan.featured
                ? "bg-[#003d74] text-white hover:bg-[#1b5594]"
                : "border border-[#003d74] bg-white text-[#003d74] hover:bg-[#f6f9fc]",
          ].join(" ")}
        >
          {plan.ctaLabel}
        </a>
      )}
    </article>
  );
}

function ComparisonTable({ audience }: { audience: Audience }) {
  const table = COMPARISON[audience];
  const headCell =
    "border-b border-[#e5edf5] px-[18px] py-3.5 text-left text-[13.5px] font-semibold";

  return (
    <div className="mt-16">
      <h2 className="font-heading text-[22px] font-normal tracking-[-0.018em] text-[#061b31]">
        Confronto completo
      </h2>
      <div className="mt-5 overflow-x-auto rounded-[10px] border border-[#e5edf5] bg-white shadow-stripe-standard">
        <table className="w-full min-w-[760px] border-collapse text-[13.5px]">
          <thead>
            <tr className="bg-[#f6f9fc]">
              <th
                scope="col"
                className="border-b border-[#e5edf5] px-[22px] py-3.5 text-left text-[11.5px] font-semibold tracking-[0.08em] text-[#273951] uppercase"
              >
                Caratteristica
              </th>
              {table.columns.map((col, i) => (
                <th
                  key={col}
                  scope="col"
                  className={`${headCell} ${i === table.highlight ? "text-[#003d74]" : "text-[#061b31]"}`}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map(([label, ...values]) => (
              <tr key={label}>
                <th
                  scope="row"
                  className="border-b border-[#eef2f7] px-[22px] py-[13px] text-left font-normal text-[#64748d]"
                >
                  {label}
                </th>
                {values.map((value, i) => (
                  <td
                    key={`${label}-${table.columns[i]}`}
                    className={[
                      "tnum border-b border-[#eef2f7] px-[18px] py-[13px]",
                      i === table.highlight ? "bg-[#f6f9fc]" : "",
                      value === "Sì"
                        ? "text-[#108c3d]"
                        : value === "—"
                          ? "text-[#64748d]"
                          : "text-[#061b31]",
                    ].join(" ")}
                  >
                    {value}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-4 max-w-[88ch] text-[13px] leading-[1.6] text-[#64748d]">
        {table.note}
      </p>
    </div>
  );
}

function AddOns({ audience }: { audience: Audience }) {
  return (
    <div className="mt-14">
      <h2 className="font-heading text-[22px] font-normal tracking-[-0.018em] text-[#061b31]">
        Add-on
      </h2>
      <div className="mt-5 grid gap-px overflow-hidden rounded-[10px] border border-[#e5edf5] bg-[#e5edf5] sm:grid-cols-2 lg:grid-cols-3">
        {ADDONS[audience].map((addon) => (
          <div key={addon.name} className="bg-white px-6 py-[22px]">
            <p className="text-[14.5px] font-medium text-[#061b31]">{addon.name}</p>
            <p className="tnum mt-2 font-heading text-[20px] font-light text-[#003d74]">
              {addon.price}
              {addon.per && (
                <span className="text-[13px] text-[#64748d]">{addon.per}</span>
              )}
            </p>
            {addon.note && (
              <p className="mt-2 text-[12.5px] leading-[1.5] text-[#64748d]">
                {addon.note}
              </p>
            )}
          </div>
        ))}
      </div>
      <p className="mt-4 text-[13px] leading-[1.6] text-[#64748d]">
        Gli add-on e i costi di onboarding sono fatturati separatamente
        dall&apos;abbonamento: scrivici a{" "}
        <a className="text-[#003d74] hover:underline" href={`mailto:${SUPPORT_EMAIL}`}>
          {SUPPORT_EMAIL}
        </a>{" "}
        e li aggiungiamo al tuo contratto.
      </p>
    </div>
  );
}

export function PricingTabs({ signedIn }: { signedIn: boolean }) {
  const [audience, setAudience] = useState<Audience>("consulenti");

  // Honour /prezzi#aziende on arrival, and keep responding to hash changes so
  // the in-page links from the landing's two role cards land on the right tab.
  useEffect(() => {
    const fromHash = () => {
      const hash = window.location.hash.replace("#", "");
      if (hash === "aziende" || hash === "consulenti") setAudience(hash);
    };
    fromHash();
    window.addEventListener("hashchange", fromHash);
    return () => window.removeEventListener("hashchange", fromHash);
  }, []);

  function select(next: Audience) {
    setAudience(next);
    // replaceState, not a hash assignment: switching tabs should not add a
    // history entry the back button has to chew through, nor scroll the page.
    window.history.replaceState(null, "", `#${next}`);
  }

  const activeNote = TABS.find((t) => t.id === audience)?.note;
  const plans = PLANS[audience];

  return (
    <>
      <section
        id="top"
        className="dark-section relative overflow-hidden bg-[#061b31] pt-[132px]"
      >
        <div
          aria-hidden
          className="absolute inset-0 bg-[radial-gradient(ellipse_62%_70%_at_74%_8%,rgba(27,85,148,.5)_0%,rgba(6,27,49,0)_68%)]"
        />
        <div className="relative mx-auto w-full max-w-[1160px] px-6 sm:px-7">
          <p className="landing-rise mb-[18px] text-[12px] font-medium tracking-[0.16em] text-[#a5c8ff] uppercase">
            Prezzi
          </p>
          <h1
            className="landing-rise max-w-[20ch] font-heading text-[clamp(2.2rem,4.4vw,3.3rem)] leading-[1.06] font-light tracking-[-0.032em] text-balance text-white"
            style={{ animationDelay: "60ms" }}
          >
            Si paga la capacità che libera, non i file che produce.
          </h1>
          <p
            className="landing-rise mt-[22px] max-w-[60ch] text-[16.5px] leading-[1.62] font-light text-white/76"
            style={{ animationDelay: "140ms" }}
          >
            Abbonamento annuale, IVA esclusa. Attivi il piano, carichi la prima
            azienda e generi il fascicolo lo stesso giorno.
          </p>

          <div
            role="tablist"
            aria-label="Tipo di cliente"
            className="mt-11 inline-flex gap-1 rounded-lg border border-white/16 bg-white/9 p-[5px]"
          >
            {TABS.map((tab) => {
              const on = tab.id === audience;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  id={`tab-${tab.id}`}
                  aria-selected={on}
                  aria-controls={`panel-${tab.id}`}
                  onClick={() => select(tab.id)}
                  className={[
                    "cursor-pointer rounded-[5px] px-[22px] py-[11px] text-[14.5px] font-medium transition-colors",
                    on
                      ? "bg-white text-[#061b31]"
                      : "bg-transparent text-white/78 hover:text-white",
                  ].join(" ")}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>
          <p className="mt-4 text-[13.5px] text-white/55">{activeNote}</p>
          <div className="h-16" />
        </div>
      </section>

      <section
        id={audience}
        role="tabpanel"
        aria-labelledby={`tab-${audience}`}
        className="scroll-mt-20 border-b border-[#e5edf5] bg-[#f6f9fc]"
      >
        <div className="mx-auto w-full max-w-[1160px] px-6 pb-[84px] sm:px-7">
          <div
            className={[
              "-mt-14 grid items-stretch gap-[18px] sm:grid-cols-2",
              plans.length === 4 ? "lg:grid-cols-4" : "lg:grid-cols-3",
            ].join(" ")}
          >
            {plans.map((plan) => (
              <PlanCard key={plan.planCode} plan={plan} signedIn={signedIn} />
            ))}
          </div>

          {audience === "aziende" && (
            <div className="mt-9 grid gap-9 rounded-[10px] border border-[#e5edf5] bg-white px-[26px] py-[22px] md:grid-cols-2">
              <div>
                <p className="text-[11.5px] font-semibold tracking-[0.1em] text-[#003d74] uppercase">
                  Non è un DVR fai-da-te
                </p>
                <p className="mt-2.5 text-[14px] leading-[1.6] text-[#64748d]">
                  Il datore di lavoro firma il documento e ne porta la
                  responsabilità. La piattaforma scrive struttura, calcoli e
                  testi; la revisione con controfirma di un RSPP certificato è
                  inclusa da Plus e disponibile come add-on su Base.
                </p>
              </div>
              <div>
                <p className="text-[11.5px] font-semibold tracking-[0.1em] text-[#003d74] uppercase">
                  A chi sono pensati
                </p>
                <p className="mt-2.5 text-[14px] leading-[1.6] text-[#64748d]">
                  Imprese che documentano la propria sicurezza, entro le soglie
                  dimensionali e di rischio di ciascun piano. Restano fuori il
                  POS del cantiere temporaneo o mobile e il manuale HACCP: non
                  sono inclusi in nessun piano diretto e passano da uno studio
                  partner, che mantiene il cliente. Se la tua impresa rientra in
                  questi casi{" "}
                  <a
                    className="text-[#003d74] hover:underline"
                    href={`mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(
                      "Richiesta studio partner — N2O DVR"
                    )}`}
                  >
                    scrivici
                  </a>{" "}
                  e ti mettiamo in contatto.
                </p>
              </div>
            </div>
          )}

          <ComparisonTable audience={audience} />
          <AddOns audience={audience} />
        </div>
      </section>
    </>
  );
}
