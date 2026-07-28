import type { Metadata } from "next";
import { Check } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { FascicoloStack } from "@/components/landing/fascicolo-stack";
import { ParallaxImage } from "@/components/landing/parallax-image";
import { Reveal } from "@/components/landing/reveal";
import { SiteFooter } from "@/components/landing/site-footer";
import { SiteNav } from "@/components/landing/site-nav";

export const metadata: Metadata = {
  title: "DVR e documenti di sicurezza sul lavoro | N2O DVR",
  description:
    "La piattaforma N2O compone DVR, allegati di valutazione e piani operativi a partire dai dati del sopralluogo. Conforme al D.Lgs. 81/2008.",
};

const STATS: { value: string; label: string; tabular?: boolean }[] = [
  { value: "17", label: "tipi di documento", tabular: true },
  { value: "7", label: "metodi di calcolo documentati", tabular: true },
  { value: "60–70%", label: "obiettivo di riduzione dei tempi", tabular: true },
  { value: "D.Lgs. 81/2008", label: "e normativa collegata" },
];

const RISK_LEVELS = [
  { label: "Accettabile", range: "3–4", color: "var(--color-risk-green)" },
  { label: "Modesto", range: "5–6", color: "var(--color-risk-yellow)" },
  { label: "Grave", range: "7–8", color: "var(--color-risk-orange)" },
  { label: "Gravissimo", range: "9–12", color: "var(--color-risk-red)" },
];

const METHODS: { name: string; description: string; formula: string }[] = [
  {
    name: "Indice di rischio",
    description: "Probabilità e danno su scala 3–12, quattro livelli di priorità",
    formula: "I = 2·D + P",
  },
  {
    name: "NIOSH (MMC)",
    description:
      "Peso limite raccomandato e indice di sollevamento per ogni compito di movimentazione",
    formula: "PLR = CP·A·B·C·D·E·F",
  },
  {
    name: "Videoterminali",
    description: "Esposizione calcolata sull'orario settimanale effettivo",
    formula: "soglia 20 h/sett.",
  },
  {
    name: "Stress lavoro-correlato",
    description:
      "Checklist INAIL: eventi sentinella, contenuto e contesto del lavoro",
    formula: "76 indicatori",
  },
  {
    name: "Rischio incendio",
    description: "Infiammabilità, sviluppo e propagazione dell'incendio",
    formula: "INF + SI + PI",
  },
  {
    name: "Microclima: comfort termico",
    description: "Indici PMV e PPD per gli ambienti termici moderati",
    formula: "PMV · PPD",
  },
  {
    name: "Microclima: caldo severo",
    description: "Sollecitazione termica prevedibile negli ambienti severi caldi",
    formula: "PHS",
  },
];

const SETTORI: { src: string; alt: string; name: string; note: string; position?: string }[] = [
  {
    src: "/landing/settore-cucina.webp",
    alt: "Cucina professionale in acciaio inox",
    name: "Ristorazione",
    note: "HACCP · biologico alimentare",
  },
  {
    src: "/landing/settore-cantiere.webp",
    alt: "Cantiere edile con ponteggi",
    name: "Edilizia",
    note: "POS · DUVRI · Titolo IV",
  },
  {
    src: "/landing/settore-magazzino.webp",
    alt: "Magazzino con scaffalature e carrello elevatore",
    name: "Logistica",
    note: "MMC · attrezzature · PEE",
  },
  {
    src: "/landing/ruolo-ufficio.webp",
    alt: "Consulente di sicurezza in un ufficio",
    name: "Terziario",
    note: "VDT · stress · microclima",
    position: "50% 24%",
  },
];

const FATTURAZIONE: { label: string; title: string; body: string }[] = [
  {
    label: "Ciclo",
    title: "Annuale, IVA esclusa",
    body: "Prezzi di listino al netto dell'IVA 22%. Prepagato tre anni con sconto su richiesta.",
  },
  {
    label: "Pagamento",
    title: "PayPal",
    body: "L'attivazione è confermata solo dopo la conferma di PayPal. Nessun addebito se annulli l'approvazione.",
  },
  {
    label: "Insoluti",
    title: "Accesso completo durante i tentativi",
    body: "Se un pagamento non va a buon fine PayPal riprova nei giorni successivi: nel frattempo continui a lavorare.",
  },
  {
    label: "Disdetta",
    title: "I documenti restano tuoi",
    body: "Mantieni l'accesso fino a fine periodo pagato. Dopo puoi sempre consultare e scaricare quanto già generato: la conservazione richiesta dal D.Lgs. 81/2008 è garantita.",
  },
];

const EYEBROW = "text-[12px] font-medium tracking-[0.16em] uppercase";
const SECTION_H2 =
  "font-heading text-[clamp(1.9rem,3.2vw,2.6rem)] leading-[1.1] font-light tracking-[-0.028em] text-balance";
/** Card and sub-section heads. Weight 300 like every other heading here. */
const CARD_H3 =
  "font-heading text-[23px] font-light leading-[1.28] tracking-[-0.018em] text-[#061b31]";

/**
 * "What you get" lists. A check, not an em dash — /prezzi's comparison table
 * spends "—" on *not* included, and the two pages have to agree on the glyph.
 */
function FeatureList({ items, className }: { items: string[]; className?: string }) {
  return (
    <ul className={`grid gap-[11px] ${className ?? "mt-6"}`}>
      {items.map((item) => (
        <li
          key={item}
          className="flex gap-[11px] text-[14.5px] leading-[1.5] text-[#273951]"
        >
          <Check
            aria-hidden
            strokeWidth={2.5}
            className="mt-[4px] size-[13px] shrink-0 text-[#003d74]"
          />
          {item}
        </li>
      ))}
    </ul>
  );
}

export default async function Home() {
  const session = await auth();
  if (session) {
    redirect("/dashboard");
  }

  return (
    <div className="bg-white">
      <SiteNav variant="overlay" />

      <main>
        {/* ================= Hero ================= */}
        <section
          id="top"
          className="dark-section relative flex min-h-[96svh] flex-col overflow-hidden bg-[#061b31]"
        >
          <div aria-hidden className="absolute inset-x-0 -inset-y-[8%] overflow-hidden">
            <ParallaxImage
              src="/landing/hero-officina.webp"
              alt=""
              width={1376}
              height={768}
              speed={0.14}
              priority
              sizes="100vw"
              wrapperClassName="h-full w-full"
              className="h-full w-full object-cover"
            />
          </div>
          <div
            aria-hidden
            className="absolute inset-0 bg-[linear-gradient(180deg,rgba(6,27,49,.72)_0%,rgba(6,27,49,.44)_38%,rgba(6,27,49,.9)_100%)]"
          />
          <div
            aria-hidden
            className="absolute inset-0 bg-[radial-gradient(ellipse_62%_54%_at_28%_56%,rgba(6,27,49,.62)_0%,rgba(6,27,49,0)_72%)]"
          />

          <div className="relative z-2 mx-auto flex w-full max-w-[1160px] flex-1 flex-col justify-center px-6 pt-[150px] pb-16 sm:px-7">
            <p className={`landing-rise mb-[26px] ${EYEBROW} text-[#a5c8ff]`}>
              Piattaforma per la sicurezza sul lavoro
            </p>
            <h1
              className="landing-rise max-w-[17ch] font-heading text-[clamp(2.6rem,5.4vw,4.1rem)] leading-[1.03] font-light tracking-[-0.035em] text-balance text-white"
              style={{ animationDelay: "60ms" }}
            >
              Dal sopralluogo al DVR, senza ricopiare un dato.
            </h1>
            <p
              className="landing-rise mt-[26px] max-w-[600px] text-[17px] leading-[1.6] font-light text-white/82"
              style={{ animationDelay: "160ms" }}
            >
              I dati si raccolgono una volta sola, in azienda. La piattaforma
              compone l&apos;intero fascicolo — DVR, allegati di valutazione,
              piani operativi — conforme al D.Lgs.&nbsp;81/2008 e pronto per la
              revisione del professionista.
            </p>

            <div
              className="landing-rise mt-9 flex flex-wrap gap-3.5"
              style={{ animationDelay: "260ms" }}
            >
              <a
                href="#consulenti"
                className="inline-flex min-w-[236px] flex-col gap-[3px] rounded-md bg-white px-[22px] py-[15px] shadow-stripe-deep transition-transform duration-250 ease-[cubic-bezier(.16,1,.3,1)] hover:-translate-y-0.5"
              >
                <span className="text-[15px] font-semibold text-[#061b31]">
                  Sono un consulente
                </span>
                <span className="text-[13px] text-[#64748d]">
                  Studi e RSPP · più aziende clienti
                </span>
              </a>
              <a
                href="#aziende"
                className="inline-flex min-w-[236px] flex-col gap-[3px] rounded-md border border-white/28 bg-white/6 px-[22px] py-[15px] transition-[transform,background-color,border-color] duration-250 ease-[cubic-bezier(.16,1,.3,1)] hover:-translate-y-0.5 hover:border-white/50 hover:bg-white/13"
              >
                <span className="text-[15px] font-semibold text-white">
                  Sono un&apos;azienda
                </span>
                <span className="text-[13px] text-white/66">
                  Datore di lavoro · una sola impresa
                </span>
              </a>
            </div>
          </div>

          <div className="relative z-2 border-t border-white/13">
            <div className="mx-auto grid w-full max-w-[1160px] grid-cols-1 px-6 sm:grid-cols-2 sm:px-7 lg:grid-cols-4">
              {STATS.map((stat, i) => (
                <div
                  key={stat.label}
                  className={[
                    "py-[22px] lg:px-6",
                    i === 0 ? "lg:pl-0" : "",
                    i === STATS.length - 1 ? "lg:pr-0" : "lg:border-r lg:border-white/13",
                  ].join(" ")}
                >
                  <p
                    className={`font-heading text-[26px] font-light tracking-[-0.02em] text-white ${stat.tabular ? "tnum" : ""}`}
                  >
                    {stat.value}
                  </p>
                  <p className="mt-1 text-[12.5px] text-white/60">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ================= Il fascicolo (scroll stack) ================= */}
        <FascicoloStack />

        {/* ================= Come funziona ================= */}
        <section id="come-funziona" className="bg-white py-[120px] sm:pb-[130px]">
          <div className="mx-auto w-full max-w-[1160px] px-6 sm:px-7">
            <Reveal>
              <p className={`mb-[18px] ${EYEBROW} text-[#003d74]`}>Come funziona</p>
              <h2 className={`max-w-[20ch] ${SECTION_H2} text-[#061b31]`}>
                Un solo flusso, dal campo al documento.
              </h2>
              <p className="mt-[18px] max-w-[56ch] text-[16px] leading-[1.6] text-[#64748d]">
                Ogni dato viene rilevato una volta e riusato ovunque serva: nelle
                valutazioni, nelle tabelle e in ogni allegato del fascicolo.
              </p>
            </Reveal>

            <div className="mt-16 grid gap-20 sm:mt-[84px] sm:gap-24">
              {/* Step 1 */}
              <Reveal className="grid items-center gap-10 md:grid-cols-[minmax(0,1fr)_minmax(0,1.08fr)] md:gap-[60px]">
                <div>
                  <div className="flex items-baseline gap-4">
                    <span
                      aria-hidden
                      className="tnum font-heading text-[40px] leading-none font-light text-[#003d74]"
                    >
                      1
                    </span>
                    <h3 className={CARD_H3}>
                      Sopralluogo digitale
                    </h3>
                  </div>
                  <p className="mt-[18px] max-w-[48ch] text-[15.5px] leading-[1.65] text-[#64748d]">
                    L&apos;operatore rileva in azienda organico, ambienti,
                    attrezzature e sostanze con un questionario strutturato che
                    guida la visita. Niente appunti da trascrivere al rientro: i
                    dati nascono già ordinati e collegati all&apos;azienda.
                  </p>
                  <FeatureList
                    items={[
                      "Autofill dell'anagrafica dalla sola P.IVA",
                      "Scheda di sicurezza PDF → sostanza chimica strutturata",
                      "Foto del reparto → inventario attrezzature",
                    ]}
                  />
                </div>
                <ParallaxImage
                  src="/landing/sopralluogo.webp"
                  alt="Consulente con tablet durante il sopralluogo in un'officina meccanica"
                  width={1600}
                  height={1200}
                  speed={0.06}
                  sizes="(min-width: 768px) 50vw, 100vw"
                  wrapperClassName="overflow-hidden rounded-[10px] shadow-stripe-elevated"
                  className="block h-auto w-full"
                />
              </Reveal>

              {/* Step 2 — text first in the DOM, card pulled left on desktop */}
              <Reveal className="grid items-center gap-10 md:grid-cols-[minmax(0,1.08fr)_minmax(0,1fr)] md:gap-[60px]">
                <div className="md:order-2">
                  <div className="flex items-baseline gap-4">
                    <span
                      aria-hidden
                      className="tnum font-heading text-[40px] leading-none font-light text-[#003d74]"
                    >
                      2
                    </span>
                    <h3 className={CARD_H3}>
                      Valutazioni e calcoli
                    </h3>
                  </div>
                  <p className="mt-[18px] max-w-[48ch] text-[15.5px] leading-[1.65] text-[#64748d]">
                    Indice di rischio, protocollo NIOSH, soglie videoterminali,
                    checklist INAIL, rischio incendio e comfort termico: ogni
                    metodo viene applicato automaticamente ai dati rilevati, con
                    risultati tracciabili in ogni tabella.
                  </p>
                </div>
                <div className="rounded-[10px] border border-[#e5edf5] bg-white p-[30px] shadow-stripe-elevated md:order-1">
                  <div className="flex items-baseline justify-between gap-4">
                    <p className="text-[15px] font-medium text-[#273951]">
                      Indice di rischio
                    </p>
                    <span className="font-mono text-[13px] text-[#003d74]">
                      I = 2·D + P
                    </span>
                  </div>
                  <ul className="mt-[18px]">
                    {RISK_LEVELS.map((level) => (
                      <li
                        key={level.label}
                        className="flex items-center justify-between border-b border-[#eef2f7] py-[11px] last:border-b-0"
                      >
                        <span className="flex items-center gap-3">
                          <span
                            aria-hidden
                            className="h-2.5 w-2.5 rounded-full"
                            style={{ backgroundColor: level.color }}
                          />
                          <span className="text-[14px] text-[#061b31]">
                            {level.label}
                          </span>
                        </span>
                        <span className="tnum text-[13px] text-[#64748d]">
                          {level.range}
                        </span>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-4 text-[12.5px] leading-[1.5] text-[#64748d]">
                    La scala applicata a ogni pericolo individuato nel
                    sopralluogo.
                  </p>
                </div>
              </Reveal>

              {/* Step 3 */}
              <Reveal className="grid items-center gap-10 md:grid-cols-[minmax(0,1fr)_minmax(0,1.08fr)] md:gap-[60px]">
                <div>
                  <div className="flex items-baseline gap-4">
                    <span
                      aria-hidden
                      className="tnum font-heading text-[40px] leading-none font-light text-[#003d74]"
                    >
                      3
                    </span>
                    <h3 className={CARD_H3}>
                      Generazione e revisione
                    </h3>
                  </div>
                  <p className="mt-[18px] max-w-[48ch] text-[15.5px] leading-[1.65] text-[#64748d]">
                    La piattaforma compone i documenti Word con la struttura, le
                    tabelle e le intestazioni del modello, li mostra in anteprima
                    nel browser e consente correzioni inline. Il consulente
                    rivede, corregge dove serve e approva.
                  </p>
                  <p className="mt-6 border-l-2 border-[#003d74] bg-[#f6f9fc] px-[18px] py-4 text-[14.5px] leading-[1.6] text-[#273951]">
                    «Il nostro deve essere solo una questione di revisione, non
                    di inserimento del dato.»
                  </p>
                </div>
                <ParallaxImage
                  src="/landing/fascicolo.webp"
                  alt="Il DVR rilegato con gli allegati e il timbro"
                  width={1200}
                  height={896}
                  speed={0.06}
                  sizes="(min-width: 768px) 50vw, 100vw"
                  wrapperClassName="overflow-hidden rounded-[10px] shadow-stripe-elevated"
                  className="block h-auto w-full"
                />
              </Reveal>
            </div>
          </div>
        </section>

        {/* ================= Due percorsi ================= */}
        <section
          id="consulenti"
          className="scroll-mt-[90px] border-t border-[#e5edf5] bg-[#f6f9fc] py-[110px]"
        >
          <div className="mx-auto w-full max-w-[1160px] px-6 sm:px-7">
            <Reveal>
              <p className={`mb-[18px] ${EYEBROW} text-[#003d74]`}>Due percorsi</p>
              <h2 className={`max-w-[24ch] ${SECTION_H2} text-[#061b31]`}>
                La stessa piattaforma, due modi di usarla.
              </h2>
            </Reveal>

            <div className="mt-13 grid gap-7 md:grid-cols-2">
              <Reveal
                as="article"
                className="flex flex-col overflow-hidden rounded-[10px] border border-[#e5edf5] bg-white shadow-stripe-standard"
              >
                <div className="h-[250px] overflow-hidden bg-[#061b31]">
                  <Image
                    src="/landing/ruolo-campo.webp"
                    alt="Tecnico della sicurezza con tablet in officina"
                    width={896}
                    height={1200}
                    sizes="(min-width: 768px) 50vw, 100vw"
                    className="h-full w-full object-cover"
                    style={{ objectPosition: "50% 26%" }}
                  />
                </div>
                <div className="flex flex-1 flex-col p-8">
                  <p className="text-[11.5px] font-semibold tracking-[0.12em] text-[#003d74] uppercase">
                    Per consulenti e studi
                  </p>
                  {/* min-h of two line boxes: these two cards sit side by side
                      and one title wraps to two lines, which used to push its
                      whole column — body, bullets — 36px out of step. */}
                  <h3 className={`${CARD_H3} mt-3 md:min-h-[2lh]`}>
                    Produci per tutto il tuo portafoglio clienti
                  </h3>
                  <p className="mt-3.5 text-[15px] leading-[1.62] text-[#64748d]">
                    Un ambiente multi-azienda con la tua carta intestata: logo,
                    P.IVA e nominativo RSPP stampati su ogni documento. La
                    piattaforma resta invisibile al cliente finale.
                  </p>
                  <FeatureList
                    items={[
                      "Tutti e 17 i tipi di documento su ogni piano",
                      "Da 15 a 200+ aziende clienti attive",
                      "Migrazione dei tuoi template, white-label, API",
                      "Portali self-service per i clienti (da Network)",
                    ]}
                  />
                  <div className="mt-auto flex items-baseline gap-3.5 pt-7">
                    <Link
                      href="/prezzi#consulenti"
                      className="inline-flex h-[42px] items-center rounded-[4px] bg-[#003d74] px-5 text-[14.5px] font-medium text-white transition-colors hover:bg-[#1b5594]"
                    >
                      Vedi i piani
                    </Link>
                    <span className="text-[13.5px] text-[#64748d]">
                      da{" "}
                      <strong className="tnum font-medium text-[#061b31]">
                        €1.490
                      </strong>
                      /anno
                    </span>
                  </div>
                </div>
              </Reveal>

              {/* The anchor belongs on the card, not on its photo: the id had
                  landed on the inner image box, so "Sono un'azienda" in the
                  hero scrolled 312px past the section heading to the top of a
                  picture. The article already carried the scroll-mt for it. */}
              <Reveal
                as="article"
                id="aziende"
                className="flex scroll-mt-[90px] flex-col overflow-hidden rounded-[10px] border border-[#e5edf5] bg-white shadow-stripe-standard"
              >
                <div className="h-[250px] overflow-hidden bg-[#061b31]">
                  <Image
                    src="/landing/ruolo-datore.webp"
                    alt="Datore di lavoro davanti alla propria officina"
                    width={896}
                    height={1200}
                    sizes="(min-width: 768px) 50vw, 100vw"
                    className="h-full w-full object-cover"
                    style={{ objectPosition: "50% 22%" }}
                  />
                </div>
                <div className="flex flex-1 flex-col p-8">
                  <p className="text-[11.5px] font-semibold tracking-[0.12em] text-[#003d74] uppercase">
                    Per aziende
                  </p>
                  {/* min-h of two line boxes: these two cards sit side by side
                      and one title wraps to two lines, which used to push its
                      whole column — body, bullets — 36px out of step. */}
                  <h3 className={`${CARD_H3} mt-3 md:min-h-[2lh]`}>
                    Tieni aggiornato il tuo fascicolo, non rifarlo ogni volta
                  </h3>
                  <p className="mt-3.5 text-[15px] leading-[1.62] text-[#64748d]">
                    Non è un DVR fai-da-te. La piattaforma scrive struttura,
                    calcoli e testi; un RSPP certificato rivede e controfirma su
                    richiesta. Il datore di lavoro resta il responsabile e lo sa.
                  </p>
                  <FeatureList
                    items={[
                      "Revisioni e rigenerazioni illimitate",
                      "Promemoria di aggiornamento art. 29 c.3",
                      "Data certa: marca temporale e deposito PEC",
                      "Revisione RSPP assistita inclusa da Plus",
                    ]}
                  />
                  <div className="mt-auto flex items-baseline gap-3.5 pt-7">
                    <Link
                      href="/prezzi#aziende"
                      className="inline-flex h-[42px] items-center rounded-[4px] border border-[#003d74] bg-white px-5 text-[14.5px] font-medium text-[#003d74] transition-colors hover:bg-[#f6f9fc]"
                    >
                      Vedi i piani
                    </Link>
                    <span className="text-[13.5px] text-[#64748d]">
                      da{" "}
                      <strong className="tnum font-medium text-[#061b31]">
                        €490
                      </strong>
                      /anno
                    </span>
                  </div>
                </div>
              </Reveal>
            </div>

            <Reveal>
              <p className="mt-[26px] max-w-[80ch] text-[13.5px] leading-[1.6] text-[#64748d]">
                I piani diretti sono riservati alle imprese sotto le soglie
                dimensionali e di rischio previste. Cantieri, classi ATECO ad
                alto rischio e organici superiori vengono indirizzati a uno
                studio partner.
              </p>
            </Reveal>
          </div>
        </section>

        {/* ================= Metodo e normativa ================= */}
        <section id="metodo" className="dark-section scroll-mt-[70px] bg-[#18244e] py-[110px]">
          <div className="mx-auto w-full max-w-[1160px] px-6 sm:px-7">
            <Reveal>
              <p className={`mb-[18px] ${EYEBROW} text-[#a5c8ff]`}>
                Metodo e normativa
              </p>
              <h2 className={`max-w-[24ch] ${SECTION_H2} text-white`}>
                Calcoli verificabili, riferimenti puntuali.
              </h2>
              <p className="mt-[18px] max-w-[58ch] text-[16px] leading-[1.62] font-light text-white/70">
                Ogni valore che entra in tabella ha un metodo dichiarato e una
                fonte normativa: chi revisiona può sempre risalire al calcolo.
              </p>
            </Reveal>

            <Reveal>
              <dl className="mt-13">
                {METHODS.map((method) => (
                  <div
                    key={method.name}
                    className="grid gap-x-8 gap-y-1 border-b border-white/11 py-[17px] last:border-b-0 md:grid-cols-[230px_minmax(0,1fr)_auto] md:items-baseline"
                  >
                    <dt className="text-[15px] font-medium text-white">
                      {method.name}
                    </dt>
                    <dd className="text-[14px] leading-[1.55] font-light text-white/65">
                      {method.description}
                    </dd>
                    <dd className="font-mono text-[13px] whitespace-nowrap text-[#a5c8ff]">
                      {method.formula}
                    </dd>
                  </div>
                ))}
              </dl>
              <p className="mt-6 text-[13px] leading-[1.6] text-white/55">
                Riferimenti: D.Lgs. 81/2008, D.Lgs. 151/2001, D.M. 3 settembre
                2021, Reg. CE 852/2004, UNI EN ISO 7730, 7933 e 11228.
              </p>
            </Reveal>

            <Reveal className="mt-16 grid gap-14 border-t border-white/11 pt-12 md:grid-cols-[minmax(0,330px)_minmax(0,1fr)]">
              <h3 className="font-heading text-[23px] leading-[1.2] font-light tracking-[-0.02em] text-white">
                L&apos;AI assiste, il consulente decide.
              </h3>
              <p className="max-w-[64ch] text-[15px] leading-[1.68] font-light text-white/70">
                I modelli leggono le schede di sicurezza delle sostanze chimiche,
                propongono descrizioni aziendali e misure di miglioramento. Ogni
                testo generato passa dalla revisione di un professionista prima
                di entrare nel documento, e i dati anagrafici e sanitari non
                vengono mai inviati ai modelli.
              </p>
            </Reveal>
          </div>
        </section>

        {/* ================= Settori ================= */}
        <section className="bg-white py-[110px]">
          <div className="mx-auto w-full max-w-[1160px] px-6 sm:px-7">
            <div className="flex flex-wrap items-end justify-between gap-10">
              <Reveal>
                <p className={`mb-[18px] ${EYEBROW} text-[#003d74]`}>Settori</p>
                <h2 className={`max-w-[22ch] ${SECTION_H2} text-[#061b31]`}>
                  Le varianti che il settore richiede.
                </h2>
              </Reveal>
              <Reveal>
                <p className="max-w-[44ch] text-[15px] leading-[1.6] text-[#64748d]">
                  Il rischio biologico di un asilo non è quello di un laboratorio
                  odontoiatrico. Gli allegati esistono nelle varianti che la
                  normativa distingue.
                </p>
              </Reveal>
            </div>

            <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {SETTORI.map((settore) => (
                <Reveal
                  key={settore.name}
                  as="figure"
                  className="relative aspect-[1/1.12] overflow-hidden rounded-[10px] bg-[#061b31]"
                >
                  <Image
                    src={settore.src}
                    alt={settore.alt}
                    fill
                    sizes="(min-width: 1024px) 25vw, (min-width: 640px) 50vw, 100vw"
                    className="object-cover"
                    style={{ objectPosition: settore.position ?? "50% 50%" }}
                  />
                  <figcaption className="absolute inset-x-0 bottom-0 bg-[linear-gradient(180deg,rgba(6,27,49,0),rgba(6,27,49,.88))] px-5 pt-13 pb-[18px] text-white">
                    <span className="block text-[15px] font-medium">
                      {settore.name}
                    </span>
                    <span className="mt-[3px] block text-[12.5px] text-white/66">
                      {settore.note}
                    </span>
                  </figcaption>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ================= Fatturazione ================= */}
        <section className="border-t border-[#e5edf5] bg-[#f6f9fc] py-[110px]">
          <div className="mx-auto w-full max-w-[1160px] px-6 sm:px-7">
            <div className="grid items-start gap-16 md:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
              <Reveal>
                <p className={`mb-[18px] ${EYEBROW} text-[#003d74]`}>
                  Fatturazione
                </p>
                <h2 className="font-heading text-[clamp(1.7rem,2.8vw,2.25rem)] leading-[1.12] font-light tracking-[-0.026em] text-balance text-[#061b31]">
                  Nessuna sorpresa a fine anno.
                </h2>
                <p className="mt-[18px] text-[15.5px] leading-[1.64] text-[#64748d]">
                  Abbonamento annuale, pagamento con PayPal, consumi sempre
                  visibili nella schermata Abbonamento. Nessun blocco improvviso:
                  gli avvisi arrivano prima del limite, non quando lo hai già
                  superato.
                </p>
                <Link
                  href="/prezzi#fatturazione"
                  className="mt-[26px] inline-flex h-[42px] items-center rounded-[4px] bg-[#003d74] px-5 text-[14.5px] font-medium text-white transition-colors hover:bg-[#1b5594]"
                >
                  Domande sulla fatturazione
                </Link>
              </Reveal>

              <Reveal className="grid gap-px overflow-hidden rounded-[10px] border border-[#e5edf5] bg-[#e5edf5] sm:grid-cols-2">
                {FATTURAZIONE.map((item) => (
                  <div key={item.label} className="bg-white p-7">
                    <p className="text-[11.5px] font-semibold tracking-[0.1em] text-[#003d74] uppercase">
                      {item.label}
                    </p>
                    <p className="mt-3 font-heading text-[19px] font-normal tracking-[-0.015em] text-[#061b31]">
                      {item.title}
                    </p>
                    <p className="mt-[9px] text-[14px] leading-[1.6] text-[#64748d]">
                      {item.body}
                    </p>
                  </div>
                ))}
              </Reveal>
            </div>

            <Reveal className="mt-9 grid gap-9 rounded-[10px] bg-[#061b31] px-[30px] py-[26px] md:grid-cols-3">
              {[
                {
                  label: "Consumi visibili",
                  body: "Crediti AI e aziende attive, con barra di avanzamento e avviso al 75% e al 90%.",
                },
                {
                  label: "Un solo metro",
                  body: "Si conta l'azienda con almeno un documento generato o revisionato nell'anno. Le archiviate restano leggibili e non contano.",
                },
                {
                  label: "Amministrazione",
                  body: "Solo un amministratore dell'organizzazione può cambiare piano o disdire.",
                },
              ].map((item) => (
                <div key={item.label}>
                  <p className="text-[11.5px] font-semibold tracking-[0.1em] text-[#a5c8ff] uppercase">
                    {item.label}
                  </p>
                  <p className="mt-2.5 text-[14px] leading-[1.6] text-white/72">
                    {item.body}
                  </p>
                </div>
              ))}
            </Reveal>
          </div>
        </section>

        {/* ================= Chiusura ================= */}
        <section id="accedi" className="scroll-mt-[70px] bg-white py-[130px]">
          <div className="mx-auto w-full max-w-[820px] px-6 text-center sm:px-7">
            <Reveal>
              <h2 className="font-heading text-[clamp(1.8rem,3.4vw,2.6rem)] leading-[1.16] font-light tracking-[-0.028em] text-balance text-[#061b31]">
                Attiva la piattaforma e comincia dal primo sopralluogo.
              </h2>
              <p className="mx-auto mt-5 max-w-[56ch] text-[16px] leading-[1.62] text-[#64748d]">
                Scegli il piano adatto allo studio o all&apos;impresa, attiva
                l&apos;abbonamento con PayPal e carica subito la prima azienda.
                Il piano Solo non ha costi di attivazione.
              </p>
              <div className="mt-9 flex flex-wrap justify-center gap-3.5">
                <Link
                  href="/prezzi"
                  className="inline-flex h-[46px] items-center rounded-[4px] bg-[#003d74] px-[26px] text-[15px] font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
                >
                  Vedi i piani
                </Link>
                <a
                  href="mailto:support@dvr-sicurezza.it"
                  className="inline-flex h-[46px] items-center rounded-[4px] border border-[#e5edf5] bg-white px-[26px] text-[15px] font-medium text-[#003d74] transition-colors hover:border-[#003d74] hover:bg-[#f6f9fc]"
                >
                  Parla con noi
                </a>
              </div>
            </Reveal>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
