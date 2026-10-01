import type { Metadata } from "next";
import { ArrowDown, ArrowRight, Check, FileText, Lock, UserCheck } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { plexMono } from "@/components/landing/fonts";
import { HeroStage } from "@/components/landing/hero-stage";
import { Reveal } from "@/components/landing/reveal";
import { RiskMatrix } from "@/components/landing/risk-matrix";
import { SiteFooter } from "@/components/landing/site-footer";
import { SiteNav } from "@/components/landing/site-nav";

export const metadata: Metadata = {
  title: "DVR e documenti di sicurezza sul lavoro | N2O DVR",
  description:
    "La piattaforma N2O compone DVR, allegati di valutazione e piani operativi a partire dai dati del sopralluogo. Conforme al D.Lgs. 81/2008.",
};

/**
 * Four facts a buyer can hold us to — no targets dressed up as results. Each
 * one answers a doubt: how much, how reliable, what happens to my data, what
 * happens to my documents if I stop paying.
 */
const FACTS = [
  { title: "17 documenti", body: "DVR, allegati e piani da un'unica base dati" },
  { title: "7 metodi di calcolo", body: "Dichiarati e verificabili in ogni tabella" },
  {
    title: "Tutela dei dati",
    body: "Codice fiscale, documenti d'identità e dati sanitari mai inviati all'AI",
  },
  { title: "Documenti sempre tuoi", body: "Consultabili e scaricabili anche dopo la disdetta" },
];

const RISK_LEVELS = [
  { label: "Accettabile", range: "3–4", color: "var(--color-risk-green)" },
  { label: "Modesto", range: "5–6", color: "var(--color-risk-yellow)" },
  { label: "Grave", range: "7–8", color: "var(--color-risk-orange)" },
  { label: "Gravissimo", range: "9–12", color: "var(--color-risk-red)" },
];

type Step = {
  n: string;
  title: string;
  body: string;
  image: { src: string; alt: string };
  bullets?: string[];
};

const STEPS: Step[] = [
  {
    n: "01",
    title: "Sopralluogo digitale",
    body: "In azienda rilevi organico, ambienti, attrezzature e sostanze con un questionario che guida la visita. Niente appunti da trascrivere al rientro.",
    image: {
      src: "/landing/modello-sopralluogo.webp",
      alt: "Tablet con il questionario di sopralluogo, casco e lista di controllo",
    },
    bullets: [
      "Anagrafica compilata dalla sola P.IVA",
      "Scheda di sicurezza PDF → sostanza strutturata",
      "Foto del reparto → inventario attrezzature",
    ],
  },
  {
    n: "02",
    title: "Valutazioni e calcoli",
    body: "Indice di rischio, NIOSH, videoterminali, stress INAIL, incendio e microclima: ogni metodo si applica ai dati rilevati, con il calcolo sempre visibile.",
    image: {
      src: "/landing/modello-valutazione.webp",
      alt: "Matrice di rischio in blocchi, dal verde al rosso al crescere dell'indice",
    },
  },
  {
    n: "03",
    title: "Revisione e approvazione",
    body: "I documenti Word escono con la struttura, le tabelle e le intestazioni del modello. Li rivedi in anteprima, correggi dove serve e approvi.",
    image: {
      src: "/landing/modello-revisione.webp",
      alt: "Documento rilegato in blu con un timbro",
    },
    bullets: [
      "Anteprima e correzioni nel browser",
      "File .docx sempre modificabili",
      "Cambia un dato, il fascicolo resta coerente",
    ],
  },
];

type Doc = { code: string; title: string; norm: string };

/** The 17 documents, in the order the fascicolo is assembled. */
const DOCUMENT_GROUPS: { label: string; docs: Doc[] }[] = [
  {
    label: "Documento principale",
    docs: [
      { code: "DVR", title: "Documento di valutazione dei rischi", norm: "D.Lgs. 81/2008 · artt. 17 e 28" },
    ],
  },
  {
    label: "Allegati di valutazione · 10",
    docs: [
      { code: "MMC", title: "Movimentazione manuale dei carichi", norm: "UNI ISO 11228-1 · NIOSH" },
      { code: "VDT", title: "Videoterminali", norm: "D.Lgs. 81/2008 · Titolo VII" },
      { code: "STRESS", title: "Stress lavoro-correlato", norm: "Metodologia INAIL" },
      { code: "GESTANTI", title: "Tutela delle lavoratrici madri", norm: "D.Lgs. 151/2001" },
      { code: "INCENDIO", title: "Rischio incendio", norm: "D.M. 3 settembre 2021" },
      { code: "MICROCLIMA", title: "Comfort termico", norm: "UNI EN ISO 7730" },
      { code: "CALDO", title: "Ambienti severi caldi", norm: "UNI EN ISO 7933" },
      { code: "BIOLOGICO", title: "Rischio biologico · alimentare", norm: "D.Lgs. 81/2008 · Titolo X" },
      { code: "BIOLOGICO", title: "Rischio biologico · asilo nido", norm: "D.Lgs. 81/2008 · Titolo X" },
      { code: "BIOLOGICO", title: "Rischio biologico · odontoiatria", norm: "D.Lgs. 81/2008 · Titolo X" },
    ],
  },
  {
    label: "Documenti complementari · 6",
    docs: [
      { code: "PEE", title: "Piano di emergenza ed evacuazione", norm: "Aziende private" },
      { code: "PEE", title: "Piano di emergenza, struttura pubblica", norm: "Comuni, enti ed eventi" },
      { code: "DUVRI", title: "Rischi da interferenze", norm: "D.Lgs. 81/2008 · art. 26" },
      { code: "POS", title: "Piano operativo di sicurezza", norm: "D.Lgs. 81/2008 · Titolo IV" },
      { code: "HACCP", title: "Manuale di autocontrollo", norm: "Reg. CE 852/2004" },
      { code: "HACCP", title: "16 schede operative", norm: "Registrazioni di autocontrollo" },
    ],
  },
];

const METHODS: { name: string; description: string; formula: string }[] = [
  {
    name: "Indice di rischio",
    description: "Probabilità e danno su scala 3–12, con quattro livelli di priorità",
    formula: "I = 2·D + P",
  },
  {
    name: "NIOSH · movimentazione carichi",
    description: "Peso limite raccomandato e indice di sollevamento per ogni compito",
    formula: "PLR = CP·A·B·C·D·E·F",
  },
  {
    name: "Videoterminali",
    description: "Esposizione calcolata sull'orario settimanale effettivo",
    formula: "soglia 20 h/sett.",
  },
  {
    name: "Stress lavoro-correlato",
    description: "Checklist INAIL: eventi sentinella, contenuto e contesto del lavoro",
    formula: "76 indicatori",
  },
  {
    name: "Rischio incendio",
    description: "Infiammabilità, sviluppo e propagazione dell'incendio",
    formula: "INF + SI + PI",
  },
  {
    name: "Microclima · comfort termico",
    description: "Indici PMV e PPD negli ambienti termici moderati",
    formula: "PMV · PPD",
  },
  {
    name: "Microclima · caldo severo",
    description: "Sollecitazione termica prevedibile negli ambienti severi caldi",
    formula: "PHS",
  },
];

/**
 * Worded to the letter of the privacy rule (CLAUDE.md): codice fiscale,
 * identity documents and health data never reach a model. Company data does —
 * that is how descriptions get proposed — so never widen this to "dati
 * anagrafici" or "dati personali".
 */
const AI_POINTS = [
  {
    icon: FileText,
    title: "Legge le schede di sicurezza",
    body: "Dal PDF della scheda di sicurezza ricava la sostanza chimica già strutturata, pronta per la valutazione.",
  },
  {
    icon: UserCheck,
    title: "Propone, non decide",
    body: "Descrizioni aziendali e misure di miglioramento arrivano come proposte da accettare, correggere o scartare.",
  },
  {
    icon: Lock,
    title: "Dati personali protetti",
    body: "Codice fiscale, documenti d'identità e dati sanitari non vengono mai inviati ai modelli.",
  },
];

const PERCORSI = [
  {
    id: "consulenti",
    label: "Per consulenti, RSPP e studi",
    title: "Produci per tutto il tuo portafoglio clienti.",
    body: "Un ambiente multi-azienda con la tua carta intestata: logo, P.IVA e nominativo RSPP su ogni documento. Per il cliente finale, il lavoro resta firmato da te.",
    bullets: [
      "Tutti i 17 documenti, su ogni piano",
      "Da 15 aziende clienti attive fino a illimitate",
      "Migrazione dei tuoi template e API, dal piano Studio",
      "Portali self-service per i clienti, dal piano Network",
    ],
    price: "€1.490",
    cta: { href: "/prezzi#consulenti", label: "Piani per consulenti" },
    image: {
      src: "/landing/modello-portafoglio.webp",
      alt: "Dodici modelli in scala di aziende diverse, ciascuno sulla propria base",
      width: 1400,
      height: 1045,
      className: "h-[210px] w-auto sm:h-[270px]",
    },
  },
  {
    id: "aziende",
    label: "Per aziende e datori di lavoro",
    title: "Tieni aggiornato il tuo fascicolo, invece di rifarlo.",
    body: "Non è un DVR fai-da-te: la piattaforma scrive struttura, calcoli e testi, un RSPP certificato rivede e controfirma su richiesta. La responsabilità della valutazione resta del datore di lavoro.",
    bullets: [
      "Revisioni e rigenerazioni illimitate",
      "Promemoria di aggiornamento, art.\u00a029\u00a0c.3",
      "Data certa con marca temporale e PEC, inclusa da Plus",
      "Revisione RSPP con controfirma, inclusa da Plus",
    ],
    price: "€490",
    cta: { href: "/prezzi#aziende", label: "Piani per aziende" },
    image: {
      src: "/landing/modello-azienda.webp",
      alt: "Modello in scala di un capannone con palazzina uffici",
      width: 1200,
      height: 896,
      className: "h-[200px] w-auto sm:h-[250px]",
    },
  },
];

const SETTORI = [
  {
    src: "/landing/modello-ristorazione.webp",
    alt: "Modello in scala di una cucina professionale",
    name: "Ristorazione",
    note: "HACCP · biologico alimentare",
  },
  {
    src: "/landing/modello-edilizia.webp",
    alt: "Modello in scala di un cantiere con ponteggi e gru",
    name: "Edilizia",
    note: "POS · DUVRI · Titolo IV",
  },
  {
    src: "/landing/modello-logistica.webp",
    alt: "Modello in scala di un magazzino con scaffalature e carrello elevatore",
    name: "Logistica",
    note: "MMC · attrezzature · PEE",
  },
  {
    src: "/landing/modello-terziario.webp",
    alt: "Modello in scala di un ufficio open space",
    name: "Terziario",
    note: "VDT · stress · microclima",
  },
];

const FATTURAZIONE: { label: string; title: string; body: string }[] = [
  {
    label: "Ciclo",
    title: "Annuale, IVA esclusa",
    body: "Prezzi di listino al netto dell'IVA 22%. Prepagato triennale con sconto, su richiesta.",
  },
  {
    label: "Pagamento",
    title: "PayPal",
    body: "L'attivazione parte solo dopo la conferma di PayPal. Nessun addebito se annulli l'approvazione.",
  },
  {
    label: "Pagamenti non riusciti",
    title: "Accesso completo durante i tentativi",
    body: "PayPal riprova nei giorni successivi e nel frattempo continui a lavorare.",
  },
  {
    label: "Disdetta",
    title: "I documenti restano tuoi",
    body: "Accesso fino a fine periodo pagato. Dopo, consulti e scarichi sempre quanto generato, come richiede la conservazione prevista dal D.Lgs. 81/2008.",
  },
];

const CONTAINER = "mx-auto w-full max-w-[1160px] px-6 sm:px-7";
const SECTION_H2 =
  "font-heading text-[clamp(2rem,3.4vw,2.75rem)] leading-[1.1] font-light tracking-[-0.03em] text-balance";
const LEAD = "text-[16px] leading-[1.6] text-pretty sm:text-[17px]";
/** Small technical label — a norm, a code, a column head. Not an eyebrow. */
const TECH = "font-plex text-[12px]";

function FeatureList({ items }: { items: string[] }) {
  return (
    <ul className="mt-5 grid gap-2.5">
      {items.map((item) => (
        <li key={item} className="flex gap-2.5 text-[14.5px] leading-[1.5] text-[#273951]">
          <Check
            aria-hidden
            strokeWidth={2.5}
            className="mt-[4px] size-[14px] shrink-0 text-[#003d74]"
          />
          {item}
        </li>
      ))}
    </ul>
  );
}

function RiskScale() {
  return (
    <div className="mt-5">
      <div className="flex items-baseline justify-between">
        <span className="text-[13px] font-medium text-[#273951]">Indice di rischio</span>
        <span className={`${TECH} text-[13px] text-[#003d74]`}>I = 2·D + P</span>
      </div>
      <ul className="mt-2.5 grid grid-cols-4 gap-1">
        {RISK_LEVELS.map((level) => (
          <li key={level.label} className="flex flex-col gap-1.5">
            <span aria-hidden className="h-1.5 rounded-[2px]" style={{ background: level.color }} />
            <span className={`${TECH} text-[#273951]`}>{level.range}</span>
            <span className="text-[12.5px] text-[#64748d]">{level.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default async function Home() {
  const session = await auth();
  if (session) {
    redirect("/dashboard");
  }

  return (
    <div className={`${plexMono.variable} bg-white`}>
      <SiteNav variant="overlay" />

      <main id="contenuto" tabIndex={-1} className="outline-none">
        {/* ================= Hero ================= */}
        <section id="top" className="dark-section relative overflow-hidden bg-[#061930]">
          <div
            aria-hidden
            className="absolute inset-0 bg-[radial-gradient(ellipse_60%_46%_at_50%_42%,rgba(27,85,148,0.26),rgba(6,25,48,0)_72%)] lg:bg-[radial-gradient(ellipse_44%_58%_at_70%_48%,rgba(27,85,148,0.26),rgba(6,25,48,0)_72%)]"
          />

          <div
            className={`${CONTAINER} hero-grid relative z-2 pt-[92px] pb-9 sm:pt-[112px] sm:pb-12 lg:min-h-[min(880px,calc(100svh-132px))] lg:pt-[84px] lg:pb-10`}
          >
            <p
              className={`hero-kicker landing-rise ${TECH} text-[12.5px] tracking-[0.02em] text-[#a5c8ff]`}
            >
              Sicurezza sul lavoro · D.Lgs. 81/2008
            </p>
            <h1
              className="hero-title landing-rise mt-4 font-heading text-[clamp(2.4rem,4.1vw,3.625rem)] leading-[1.04] font-light tracking-[-0.035em] text-balance text-white sm:mt-5 md:text-[3.1rem] lg:text-[clamp(2.6rem,4.1vw,3.625rem)]"
              style={{ animationDelay: "60ms" }}
            >
              {/* The three-line break is the desktop composition; narrower
                  columns balance the lines themselves. */}
              Dal sopralluogo <br className="hidden lg:inline" />
              al DVR, senza <br className="hidden lg:inline" />
              ricopiare un dato.
            </h1>

            <div className="hero-model-slot mt-6 sm:mt-8 lg:mt-0">
              <HeroStage />
            </div>

            <p
              className="hero-lead landing-rise mt-6 max-w-[480px] text-[16px] leading-[1.6] text-pretty text-white/80 sm:mt-7 sm:text-[18px] lg:mt-6"
              style={{ animationDelay: "140ms" }}
            >
              Raccogli i dati una volta sola, in azienda. La piattaforma compone
              DVR, allegati e piani operativi conformi al D.Lgs.&nbsp;81/2008: a te
              resta solo la revisione.
            </p>

            <div
              className="hero-actions landing-rise mt-7 flex flex-wrap gap-2.5 sm:gap-3 lg:mt-8"
              style={{ animationDelay: "220ms" }}
            >
              <Link
                href="/prezzi"
                className="inline-flex h-[50px] grow basis-[150px] items-center justify-center gap-2 rounded-md bg-white px-3.5 text-[15px] font-semibold whitespace-nowrap text-[#061b31] shadow-stripe-deep transition-colors hover:bg-[#e5edf5] sm:grow-0 sm:basis-auto sm:gap-2.5 sm:px-[22px]"
              >
                Scegli il piano
                <ArrowRight aria-hidden className="size-4" strokeWidth={1.8} />
              </Link>
              <a
                href="#come-funziona"
                className="inline-flex h-[50px] grow basis-[150px] items-center justify-center gap-2 rounded-md border border-white/28 bg-white/5 px-3.5 text-[15px] font-medium whitespace-nowrap text-white transition-colors hover:border-white/50 hover:bg-white/12 sm:grow-0 sm:basis-auto sm:gap-2.5 sm:px-5"
              >
                Come funziona
                <ArrowDown aria-hidden className="size-4" strokeWidth={1.8} />
              </a>
            </div>
            <p
              className="hero-price landing-rise mt-5 text-[13px] leading-[1.5] text-pretty text-white/68 sm:text-[13.5px]"
              style={{ animationDelay: "260ms" }}
            >
              Consulenti e RSPP da{" "}
              <strong className="tnum font-semibold text-white">€1.490</strong> · aziende
              da <strong className="tnum font-semibold text-white">€490</strong> ·
              all&apos;anno, IVA&nbsp;esclusa
            </p>
          </div>

          <div className="relative z-2 border-t border-white/12">
            <ul className={`${CONTAINER} grid grid-cols-2 lg:grid-cols-4`}>
              {FACTS.map((fact, i) => (
                <li
                  key={fact.title}
                  className={[
                    "flex flex-col gap-1 py-[18px] sm:py-5",
                    i % 2 === 1 ? "border-l border-white/12 pl-4 sm:pl-6" : "pr-4 sm:pr-6",
                    i >= 2 ? "border-t border-white/12 lg:border-t-0" : "",
                    // One row at lg: every cell but the first carries the rule.
                    i === 0
                      ? "lg:pr-6 lg:pl-0"
                      : i === FACTS.length - 1
                        ? "lg:border-l lg:pr-0 lg:pl-6"
                        : "lg:border-l lg:px-6",
                  ].join(" ")}
                >
                  <p className="font-heading text-[16px] text-white sm:text-[18px]">
                    {fact.title}
                  </p>
                  <p className="text-[12.5px] leading-[1.45] text-white/64 sm:text-[13px]">
                    {fact.body}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* ================= Come funziona ================= */}
        <section id="come-funziona" className="section-y-loose scroll-mt-[68px] bg-white">
          <div className={CONTAINER}>
            <Reveal className="grid gap-10 lg:grid-cols-2 lg:items-end lg:gap-20">
              <div>
                <h2 className={`max-w-[520px] ${SECTION_H2} text-[#061b31]`}>
                  Un solo flusso, dal campo al documento.
                </h2>
                <p className={`mt-5 max-w-[500px] ${LEAD} text-[#64748d]`}>
                  Ogni dato si rileva una volta e si riusa ovunque serva: nelle
                  valutazioni, nelle tabelle, in ogni allegato del fascicolo.
                </p>
              </div>
              <figure className="border-t border-[#e5edf5] pt-[22px]">
                <p className={`${TECH} text-[#003d74]`}>Il principio di progetto</p>
                <blockquote className="mt-3.5 font-heading text-[20px] leading-[1.45] font-light tracking-[-0.012em] text-pretty text-[#061b31] sm:text-[24px] sm:leading-[1.4]">
                  «Il nostro deve essere solo una questione di revisione, non di
                  inserimento del dato.»
                </blockquote>
                <figcaption className="mt-3.5 text-[13.5px] text-[#64748d]">
                  I consulenti di N2O SRL, da cui la piattaforma è nata
                </figcaption>
              </figure>
            </Reveal>

            <ol className="mt-12 grid gap-14 sm:mt-20 lg:grid-cols-3 lg:gap-6">
              {STEPS.map((step, i) => (
                <Reveal
                  as="li"
                  key={step.n}
                  delay={i * 80}
                  className="flex flex-col md:grid md:grid-cols-[280px_minmax(0,1fr)] md:grid-rows-[auto_auto_auto_1fr] md:gap-x-10 lg:flex lg:flex-col"
                >
                    <div className="flex h-[240px] items-center justify-center overflow-hidden rounded-[14px] border border-[#eef2f7] bg-[#f6f9fc] sm:h-[320px] md:row-span-4 md:h-[280px] lg:h-[320px]">
                      <Image
                        src={step.image.src}
                        alt={step.image.alt}
                        width={960}
                        height={960}
                        sizes="290px"
                        className="parallax-sm size-[220px] object-contain sm:size-[290px] md:size-[240px] lg:size-[290px]"
                      />
                    </div>
                    <div className="mt-6 flex items-center gap-3 sm:mt-7 md:mt-1 lg:mt-7">
                      <span className={`${TECH} text-[13px] text-[#003d74]`}>{step.n}</span>
                      <span aria-hidden className="h-px flex-1 bg-[#e5edf5]" />
                    </div>
                    <h3 className="mt-4 font-heading text-[21px] leading-[1.25] font-normal tracking-[-0.018em] text-[#061b31] sm:text-[23px]">
                      {step.title}
                    </h3>
                    <p className="mt-2.5 text-[15px] leading-[1.62] text-pretty text-[#64748d] sm:text-[15.5px]">
                      {step.body}
                    </p>
                    {step.bullets ? <FeatureList items={step.bullets} /> : <RiskScale />}
                </Reveal>
              ))}
            </ol>
          </div>
        </section>

        {/* ================= Il fascicolo ================= */}
        <section
          id="fascicolo"
          className="dark-section section-y-loose scroll-mt-[68px] overflow-hidden bg-[#061b31]"
        >
          <div className={CONTAINER}>
            <div className="grid items-center gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,600px)] lg:gap-10">
              <Reveal>
                <h2 className={`max-w-[500px] ${SECTION_H2} text-white`}>
                  Diciassette documenti, un&apos;unica base dati.
                </h2>
                <p className={`mt-5 max-w-[470px] ${LEAD} text-white/72`}>
                  Ogni allegato riusa gli ambienti, le persone e le attrezzature del
                  sopralluogo. Correggi un dato una volta: resta coerente in tutto il
                  fascicolo.
                </p>
                <p className={`mt-6 flex flex-wrap gap-x-6 gap-y-2 ${TECH} text-[13px] text-[#a5c8ff]`}>
                  <span>
                    <strong className="font-medium text-white">1</strong> principale
                  </span>
                  <span>
                    <strong className="font-medium text-white">10</strong> allegati
                  </span>
                  <span>
                    <strong className="font-medium text-white">6</strong> complementari
                  </span>
                </p>
              </Reveal>
              <Image
                src="/landing/modello-fascicolo.webp"
                alt="Raccoglitore blu aperto con fogli e divisori, accanto a un timbro"
                width={1600}
                height={1195}
                sizes="(min-width: 1024px) 600px, 100vw"
                className="parallax-lg -mx-6 w-[calc(100%+3rem)] max-w-none [mask-image:radial-gradient(ellipse_62%_64%_at_52%_50%,#000_58%,transparent_100%)] sm:-mx-7 sm:w-[calc(100%+3.5rem)] lg:mx-0 lg:w-full lg:max-w-full"
              />
            </div>

            {/* Two columns from md, both starting on a group label so their
                first rules line up: the ten allegati on the right, the main
                document and the six complementari on the left. Phones keep
                the order the fascicolo is assembled in. */}
            <div className="mt-12 grid gap-y-9 md:grid-cols-2 md:grid-rows-[auto_1fr] md:gap-x-12 md:[grid-template-areas:'principale_allegati'_'complementari_allegati'] lg:mt-16 lg:gap-x-16">
              {DOCUMENT_GROUPS.map((group, g) => (
                <div
                  key={group.label}
                  className={
                    ["md:[grid-area:principale]", "md:[grid-area:allegati]", "md:[grid-area:complementari]"][g]
                  }
                >
                  <p className={`mb-3 ${TECH} text-white/60`}>{group.label}</p>
                  <ul>
                    {group.docs.map((doc) => (
                      <li key={doc.title} className="flex gap-4 border-t border-white/12 py-3.5">
                        <span
                          className={`w-[92px] shrink-0 ${TECH} text-[11.5px] leading-5 text-[#a5c8ff]`}
                        >
                          {doc.code}
                        </span>
                        <span className="flex flex-col gap-[3px]">
                          <span className="text-[14.5px] leading-5 text-white">{doc.title}</span>
                          <span className={`${TECH} text-[11.5px] text-white/58`}>{doc.norm}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <p className="mt-10 max-w-[760px] text-[14px] leading-[1.6] text-white/66">
              Nei piani per consulenti sono inclusi tutti e 17. Nei piani per
              aziende, POS e manuale HACCP passano da uno studio partner.
            </p>
          </div>
        </section>

        {/* ================= Metodo ================= */}
        <section id="metodo" className="section-y-loose scroll-mt-[68px] bg-white">
          <div className={CONTAINER}>
            <Reveal className="grid gap-5 lg:grid-cols-2 lg:items-end lg:gap-20">
              <h2 className={`max-w-[520px] ${SECTION_H2} text-[#061b31]`}>
                Calcoli verificabili, riferimenti puntuali.
              </h2>
              <p className={`max-w-[500px] ${LEAD} text-[#64748d]`}>
                Ogni valore che entra in tabella ha un metodo dichiarato e una fonte
                normativa: chi rivede può sempre risalire al calcolo.
              </p>
            </Reveal>

            <Reveal className="mt-10 rounded-[14px] border border-[#e5edf5] bg-white p-6 shadow-stripe-standard sm:mt-14 sm:p-10">
              <RiskMatrix />
            </Reveal>

            <Reveal className="mt-14 sm:mt-20">
              <div
                aria-hidden
                className={`hidden gap-8 pb-3 ${TECH} text-[#64748d] md:grid md:grid-cols-[240px_minmax(0,1fr)_220px] lg:grid-cols-[280px_minmax(0,1fr)_240px]`}
              >
                <span>Metodo</span>
                <span>Cosa calcola</span>
                <span className="text-right">Formula o soglia</span>
              </div>
              <dl className="border-b border-[#e5edf5]">
                {METHODS.map((method) => (
                  <div
                    key={method.name}
                    className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-1 border-t border-[#e5edf5] py-4 md:grid-cols-[240px_minmax(0,1fr)_220px] md:items-baseline md:gap-8 md:py-[18px] lg:grid-cols-[280px_minmax(0,1fr)_240px]"
                  >
                    <dt className="text-[15px] font-medium text-[#061b31] md:text-[15.5px]">
                      {method.name}
                    </dt>
                    <dd
                      className={`${TECH} text-right text-[12.5px] whitespace-nowrap text-[#003d74] md:order-3 md:text-[13.5px]`}
                    >
                      {method.formula}
                    </dd>
                    <dd className="col-span-2 text-[14px] leading-[1.55] text-[#64748d] md:order-2 md:col-span-1 md:text-[15px]">
                      {method.description}
                    </dd>
                  </div>
                ))}
              </dl>
              <p className="mt-4 text-[13px] leading-[1.6] text-[#64748d] sm:mt-5 sm:text-[13.5px]">
                Riferimenti: D.Lgs. 81/2008, D.Lgs. 151/2001, D.M. 3 settembre 2021,
                Reg. CE 852/2004, UNI EN ISO 7730, UNI EN ISO 7933, UNI ISO 11228-1.
              </p>
            </Reveal>

            <Reveal className="mt-14 grid gap-8 border-t border-[#e5edf5] pt-8 sm:mt-24 sm:pt-12 lg:grid-cols-[340px_minmax(0,1fr)] lg:gap-16">
              <div>
                <h3 className="font-heading text-[26px] leading-[1.15] font-light tracking-[-0.025em] text-[#061b31] sm:text-[30px]">
                  L&apos;AI assiste, il consulente decide.
                </h3>
                <p className="mt-3.5 text-[15px] leading-[1.6] text-[#64748d]">
                  Ogni testo generato passa dalla revisione di un professionista prima
                  di entrare nel documento.
                </p>
              </div>
              <ul className="grid gap-6 md:grid-cols-3 md:gap-8">
                {AI_POINTS.map(({ icon: Icon, title, body }) => (
                  <li key={title} className="flex gap-3.5 md:flex-col md:gap-3">
                    <Icon
                      aria-hidden
                      strokeWidth={1.6}
                      className="size-6 shrink-0 text-[#003d74]"
                    />
                    <div>
                      <p className="text-[15px] font-medium text-[#061b31] md:text-[15.5px]">
                        {title}
                      </p>
                      <p className="mt-1 text-[14px] leading-[1.6] text-[#64748d] md:mt-2 md:text-[14.5px]">
                        {body}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </Reveal>
          </div>
        </section>

        {/* ================= Per chi è ================= */}
        <section
          id="per-chi"
          className="section-y-loose scroll-mt-[68px] border-t border-[#e5edf5] bg-[#f6f9fc]"
        >
          <div className={CONTAINER}>
            <Reveal>
              <h2 className={`max-w-[560px] ${SECTION_H2} text-[#061b31]`}>
                La stessa piattaforma, due modi di usarla.
              </h2>
            </Reveal>

            <div className="mt-8 grid gap-4 sm:mt-14 md:grid-cols-2 md:gap-6">
              {PERCORSI.map((percorso, i) => (
                <Reveal
                  as="article"
                  key={percorso.id}
                  id={percorso.id}
                  delay={i * 80}
                  className="flex scroll-mt-[90px] flex-col overflow-hidden rounded-[14px] border border-[#e5edf5] bg-white shadow-stripe-standard"
                >
                  <div className="flex h-[220px] items-center justify-center bg-[#eef2f7] sm:h-[300px]">
                    <Image
                      src={percorso.image.src}
                      alt={percorso.image.alt}
                      width={percorso.image.width}
                      height={percorso.image.height}
                      sizes="(min-width: 768px) 400px, 300px"
                      className={`${percorso.image.className} parallax-sm object-contain`}
                    />
                  </div>
                  <div className="flex flex-1 flex-col p-6 sm:p-9">
                    <p className={`${TECH} text-[#003d74]`}>{percorso.label}</p>
                    {/* Reserved line boxes once the cards sit side by side
                        (three at md, two from lg): the titles wrap to
                        different lengths, which would otherwise push one
                        card's body out of step with the other's. */}
                    <h3 className="mt-3 font-heading text-[22px] leading-[1.25] font-light tracking-[-0.02em] text-[#061b31] sm:text-[25px] md:min-h-[3lh] lg:min-h-[2lh]">
                      {percorso.title}
                    </h3>
                    <p className="mt-3.5 text-[15px] leading-[1.62] text-[#64748d]">
                      {percorso.body}
                    </p>
                    <FeatureList items={percorso.bullets} />
                    <div className="mt-auto flex flex-col gap-3.5 pt-7 sm:pt-8 xl:flex-row xl:items-center xl:justify-between">
                      <p className="text-[14px] text-[#64748d]">
                        da{" "}
                        <strong className="tnum font-heading text-[22px] font-normal text-[#061b31]">
                          {percorso.price}
                        </strong>{" "}
                        /anno · IVA esclusa
                      </p>
                      <Link
                        href={percorso.cta.href}
                        className="inline-flex h-12 items-center justify-center gap-2 rounded-md bg-[#003d74] px-5 text-[15px] font-semibold whitespace-nowrap text-white transition-colors hover:bg-[#1b5594] sm:h-[46px] sm:text-[14.5px]"
                      >
                        {percorso.cta.label}
                        <ArrowRight aria-hidden className="size-[15px]" strokeWidth={1.8} />
                      </Link>
                    </div>
                  </div>
                </Reveal>
              ))}
            </div>

            <p className="mt-6 max-w-[820px] text-[13.5px] leading-[1.6] text-[#5c6b84] sm:mt-7">
              I piani per aziende sono pensati per le imprese che documentano la
              propria sicurezza, entro i limiti di sedi e addetti di ciascun piano. POS
              e manuale HACCP non sono inclusi: se la tua attività li richiede, ti
              mettiamo in contatto con uno studio partner.
            </p>
          </div>
        </section>

        {/* ================= Settori ================= */}
        <section className="section-y bg-white">
          <div className={CONTAINER}>
            <Reveal className="flex flex-wrap items-end justify-between gap-x-12 gap-y-4">
              <h2 className={`max-w-[520px] ${SECTION_H2} text-[#061b31]`}>
                Le varianti che il settore richiede.
              </h2>
              <p className="max-w-[430px] text-[15.5px] leading-[1.6] text-pretty text-[#64748d] sm:text-[16px]">
                Il rischio biologico di un asilo nido non è quello di uno studio
                odontoiatrico. Gli allegati esistono nelle varianti che la normativa
                distingue.
              </p>
            </Reveal>
            <div className="mt-8 grid grid-cols-2 gap-x-4 gap-y-6 sm:mt-12 sm:gap-6 lg:grid-cols-4">
              {SETTORI.map((settore, i) => (
                <Reveal as="figure" key={settore.name} delay={i * 60} className="flex flex-col gap-2.5 sm:gap-3.5">
                  <div className="overflow-hidden rounded-[10px] bg-[#e3e9f1] sm:rounded-xl">
                    <Image
                      src={settore.src}
                      alt={settore.alt}
                      width={900}
                      height={900}
                      sizes="(min-width: 1024px) 272px, 50vw"
                      className="parallax-tile aspect-square w-full object-cover"
                    />
                  </div>
                  <figcaption className="flex flex-col gap-1">
                    <span className="text-[15px] font-medium text-[#061b31] sm:text-[16px]">
                      {settore.name}
                    </span>
                    <span className={`${TECH} text-[11.5px] leading-[1.4] text-[#64748d] sm:text-[12px]`}>
                      {settore.note}
                    </span>
                  </figcaption>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ================= Fatturazione ================= */}
        <section className="section-y border-t border-[#e5edf5] bg-[#f6f9fc]">
          <div className={`${CONTAINER} grid items-start gap-8 lg:grid-cols-[360px_minmax(0,1fr)] lg:gap-[72px]`}>
            <Reveal>
              <h2 className="font-heading text-[clamp(1.75rem,2.8vw,2.25rem)] leading-[1.12] font-light tracking-[-0.026em] text-balance text-[#061b31]">
                Nessuna sorpresa a fine anno.
              </h2>
              <p className="mt-4 text-[15.5px] leading-[1.64] text-[#5c6b84]">
                Abbonamento annuale, pagamento con PayPal, consumi sempre visibili
                nella pagina Abbonamento. Gli avvisi arrivano al 75% e al 90% del
                limite, non quando l&apos;hai già superato.
              </p>
              <Link
                href="/prezzi#fatturazione"
                className="mt-2 inline-flex min-h-11 items-center gap-2 text-[14.5px] font-semibold text-[#003d74] underline-offset-4 hover:underline"
              >
                Domande sulla fatturazione
                <ArrowRight aria-hidden className="size-[15px]" strokeWidth={1.8} />
              </Link>
            </Reveal>

            <Reveal className="grid gap-px overflow-hidden rounded-xl border border-[#e5edf5] bg-[#e5edf5] sm:grid-cols-2">
              {FATTURAZIONE.map((item) => (
                <div key={item.label} className="flex flex-col gap-1.5 bg-white p-5 sm:gap-2 sm:p-7">
                  <p className={`${TECH} text-[#003d74]`}>{item.label}</p>
                  <p className="font-heading text-[17px] font-normal tracking-[-0.015em] text-[#061b31] sm:text-[19px]">
                    {item.title}
                  </p>
                  <p className="text-[14px] leading-[1.6] text-[#64748d]">{item.body}</p>
                </div>
              ))}
            </Reveal>
          </div>
        </section>

        {/* ================= Chiusura ================= */}
        <section id="accedi" className="dark-section section-y-loose scroll-mt-[68px] bg-[#061930]">
          <Reveal className={`${CONTAINER} flex flex-col items-center text-center`}>
            <div aria-hidden className="flex gap-2.5">
              {RISK_LEVELS.map((level) => (
                <span
                  key={level.label}
                  className="size-2.5 rounded-full"
                  style={{ background: level.color }}
                />
              ))}
            </div>
            <h2 className="mt-6 max-w-[760px] font-heading text-[clamp(2.1rem,3.6vw,3rem)] leading-[1.1] font-light tracking-[-0.032em] text-balance text-white sm:mt-7">
              Il fascicolo parte dal prossimo sopralluogo.
            </h2>
            <p className="mt-5 max-w-[580px] text-[16px] leading-[1.6] text-pretty text-white/74 sm:text-[17px]">
              Scegli il piano per il tuo studio o la tua impresa, attiva
              l&apos;abbonamento con PayPal e carica subito la prima azienda. Il piano
              Solo non ha costi di attivazione.
            </p>
            <div className="mt-8 flex w-full flex-col gap-2.5 sm:mt-10 sm:w-auto sm:flex-row sm:gap-3">
              <Link
                href="/prezzi"
                className="inline-flex h-[50px] items-center justify-center gap-2.5 rounded-md bg-white px-6 text-[15px] font-semibold text-[#061b31] transition-colors hover:bg-[#e5edf5]"
              >
                Scegli il piano
                <ArrowRight aria-hidden className="size-4" strokeWidth={1.8} />
              </Link>
              <a
                href="mailto:support@dvr-sicurezza.it"
                className="inline-flex h-[50px] items-center justify-center rounded-md border border-white/28 px-[22px] text-[15px] font-medium text-white transition-colors hover:border-white/50 hover:bg-white/12"
              >
                Parla con noi
              </a>
            </div>
          </Reveal>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
