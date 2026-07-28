"use client";

import { Check } from "lucide-react";
import Link from "next/link";
import { useEffect, useState, type KeyboardEvent } from "react";
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
        // Below lg the cards stack or pair up and a flex column is enough.
        // From lg they sit in one row, where `subgrid` makes every card share
        // the same seven row tracks — so price, setup note, feature list and
        // CTA line up across columns no matter how many lines each string
        // wraps to. Without it a two-line setup note pushes that card's
        // features 18px out of step with its neighbours.
        "flex flex-col rounded-[10px] border p-6 sm:px-6 sm:py-7",
        "lg:row-span-7 lg:grid lg:grid-rows-subgrid lg:gap-0",
        dark
          ? "dark-section border-[#061b31] bg-[#061b31] shadow-stripe-standard"
          : plan.featured
            ? "border-[#003d74] bg-white shadow-stripe-elevated"
            : "border-[#e5edf5] bg-white shadow-stripe-standard",
      ].join(" ")}
    >
      <div className="flex items-center justify-between gap-3">
        <p
          className={`font-heading text-[19px] font-medium tracking-[-0.015em] ${dark ? "text-white" : "text-[#061b31]"}`}
        >
          {plan.name}
        </p>
        {/* Kept inside the card edge on purpose: the row is pulled up into the
            dark hero, and a navy badge overhanging that band sat at 1.6:1. */}
        {plan.featured && (
          <span
            className={`shrink-0 rounded-[4px] px-2 py-[3px] text-[10.5px] font-semibold tracking-[0.08em] uppercase ${
              dark ? "bg-white text-[#061b31]" : "bg-[#003d74] text-white"
            }`}
          >
            Consigliato
          </span>
        )}
      </div>
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
            {/* A check, not an em dash: the comparison table below uses "—"
                to mean *not* included, and the same glyph cannot carry both
                meanings on one page. */}
            <Check
              aria-hidden
              strokeWidth={2.5}
              className={`mt-[3px] size-[13px] shrink-0 ${dark ? "text-[#a5c8ff]" : "text-[#003d74]"}`}
            />
            {feature}
          </li>
        ))}
      </ul>

      {plan.cta === "checkout" ? (
        <Link
          href={checkoutHref(plan, signedIn)}
          className={[
            "mt-6 inline-flex h-11 items-center justify-center rounded-[4px] text-[14.5px] font-medium transition-colors",
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
            "mt-6 inline-flex h-11 items-center justify-center rounded-[4px] text-[14.5px] font-medium transition-colors",
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
  // The label column stays pinned while the plan columns scroll, so a reader
  // 400px into the horizontal scroll still knows which row they are on.
  // `inset` shadow rather than `border-r`: with border-collapse a real border
  // on a sticky cell scrolls away from it.
  const stickyLabel =
    "sticky left-0 z-10 shadow-[inset_-1px_0_0_#e5edf5,6px_0_10px_-8px_rgba(6,27,49,0.14)]";

  return (
    <div className="mt-16">
      <h2 className="font-heading text-[24px] font-light tracking-[-0.022em] text-[#061b31]">
        Confronto completo
      </h2>
      <p className="mt-1.5 text-[12.5px] text-[#64748d] lg:hidden">
        Scorri la tabella in orizzontale per confrontare tutti i piani.
      </p>
      <div className="mt-5 overflow-x-auto rounded-[10px] border border-[#e5edf5] bg-white shadow-stripe-standard">
        <table className="w-full min-w-[760px] border-collapse text-[13.5px]">
          <thead>
            <tr className="bg-[#f6f9fc]">
              <th
                scope="col"
                className={`${stickyLabel} z-20 border-b border-[#e5edf5] bg-[#f6f9fc] px-[22px] py-3.5 text-left text-[11.5px] font-semibold tracking-[0.08em] text-[#273951] uppercase`}
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
              <tr key={label} className="group">
                <th
                  scope="row"
                  className={`${stickyLabel} border-b border-[#eef2f7] bg-white px-[22px] py-[13px] text-left font-normal text-[#64748d] group-hover:bg-[#f9fbfd]`}
                >
                  {label}
                </th>
                {values.map((value, i) => (
                  <td
                    key={`${label}-${table.columns[i]}`}
                    className={[
                      "tnum border-b border-[#eef2f7] px-[18px] py-[13px]",
                      // Tracking a row across five columns needs a hover
                      // target; the highlighted column keeps its own tint so
                      // it stays legible as a band under the cursor.
                      i === table.highlight
                        ? "bg-[#f6f9fc] group-hover:bg-[#eaf1f8]"
                        : "group-hover:bg-[#f9fbfd]",
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
      <h2 className="font-heading text-[24px] font-light tracking-[-0.022em] text-[#061b31]">
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

  // Arrow keys move between tabs, as the ARIA tabs pattern expects. Paired
  // with the roving tabindex below, so Tab leaves the tablist rather than
  // stepping through every tab.
  function onTabKeys(event: KeyboardEvent<HTMLButtonElement>) {
    const order = TABS.map((t) => t.id);
    const at = order.indexOf(audience);
    const next =
      event.key === "ArrowRight"
        ? order[(at + 1) % order.length]
        : event.key === "ArrowLeft"
          ? order[(at - 1 + order.length) % order.length]
          : event.key === "Home"
            ? order[0]
            : event.key === "End"
              ? order[order.length - 1]
              : null;
    if (!next) return;
    event.preventDefault();
    select(next);
    document.getElementById(`tab-${next}`)?.focus();
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
                  // Only one panel is ever in the DOM, and its id is the
                  // audience itself (it doubles as the /prezzi#aziende scroll
                  // anchor). Pointing the inactive tab at an id that does not
                  // exist is worse than omitting the attribute.
                  aria-controls={on ? tab.id : undefined}
                  tabIndex={on ? 0 : -1}
                  onKeyDown={onTabKeys}
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
              // The row laps 56px up into the dark hero, and that hero is
              // `relative` with an opaque background — without a stacking
              // context of its own this grid paints *under* it and the top of
              // every card is swallowed. z-10 stays well below the z-60 nav.
              "relative z-10 -mt-14 grid items-stretch gap-[18px] sm:grid-cols-2",
              plans.length === 4 ? "lg:grid-cols-4" : "lg:grid-cols-3",
              // Seven tracks — name, audience, price, price note, setup note,
              // features (the one that stretches), CTA — for the cards to
              // subgrid onto. Only from lg, where every card is on one row.
              "lg:grid-rows-[auto_auto_auto_auto_auto_1fr_auto]",
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
                  Imprese che documentano la propria sicurezza, entro i limiti
                  di sedi e addetti di ciascun piano. Restano fuori il POS del
                  cantiere temporaneo o mobile e il manuale HACCP: non sono
                  inclusi in nessun piano diretto e passano da uno studio
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
