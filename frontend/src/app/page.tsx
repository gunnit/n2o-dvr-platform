import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { HeroVideo } from "@/components/landing/hero-video";

export const metadata: Metadata = {
  title: "DVR e documenti di sicurezza sul lavoro | N2O DVR",
  description:
    "La piattaforma N2O compone DVR, allegati di valutazione e piani operativi a partire dai dati del sopralluogo. Conforme al D.Lgs. 81/2008.",
};

const RISK_LEVELS = [
  { label: "Accettabile", range: "3–4", color: "var(--color-risk-green)" },
  { label: "Modesto", range: "5–6", color: "var(--color-risk-yellow)" },
  { label: "Grave", range: "7–8", color: "var(--color-risk-orange)" },
  { label: "Gravissimo", range: "9–12", color: "var(--color-risk-red)" },
];

const CATALOG: { group: string; rows: [string, string, string][] }[] = [
  {
    group: "Documento principale",
    rows: [
      [
        "DVR",
        "Documento di Valutazione dei Rischi",
        "Pericoli, indici e misure per ogni ambiente di lavoro",
      ],
    ],
  },
  {
    group: "Allegati di valutazione",
    rows: [
      ["MMC", "Movimentazione manuale dei carichi", "Metodo NIOSH"],
      ["VDT", "Videoterminali", "Esposizione ≥ 20 h/settimana"],
      ["STRESS", "Stress lavoro-correlato", "Checklist INAIL, 76 indicatori"],
      ["GESTANTI", "Tutela delle lavoratrici madri", "D.Lgs. 151/2001"],
      ["INCENDIO", "Rischio incendio", "D.M. 3 settembre 2021"],
      ["MICROCLIMA", "Comfort termico e caldo severo", "UNI EN ISO 7730 / 7933"],
      ["BIOLOGICO", "Rischio biologico", "Varianti per settore"],
    ],
  },
  {
    group: "Documenti complementari",
    rows: [
      ["PEE", "Piano di Emergenza ed Evacuazione", "Per aziende e strutture pubbliche"],
      ["DUVRI", "Valutazione dei rischi da interferenze", "Contratti d'appalto e fornitura"],
      ["POS", "Piano Operativo di Sicurezza", "Cantieri temporanei o mobili"],
      ["HACCP", "Manuale di autocontrollo alimentare", "Con 16 schede operative"],
    ],
  },
];

const METHODS: { name: string; description: string; formula: string }[] = [
  {
    name: "Indice di rischio",
    description: "Probabilità e danno su scala 3–12, quattro livelli di priorità",
    formula: "I = 2·D + P",
  },
  {
    name: "NIOSH (MMC)",
    description: "Peso limite raccomandato e indice di sollevamento per ogni compito di movimentazione",
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

export default async function Home() {
  const session = await auth();
  if (session) {
    redirect("/dashboard");
  }

  return (
    <div className="bg-white">
      <main>
      {/* ================= Hero ================= */}
      <section className="dark-section relative flex min-h-[92svh] flex-col overflow-hidden bg-[#061b31]">
        <HeroVideo />

        <header className="relative z-10">
          <div className="mx-auto flex w-full max-w-[1080px] items-center justify-between px-6 pt-7">
            <span className="font-heading text-[15px] font-light tracking-[0.18em] text-white/90 uppercase">
              N2O <span className="text-white/50">·</span> DVR
            </span>
            <nav
              aria-label="Sezioni della pagina"
              className="hidden items-center gap-8 md:flex"
            >
              <a
                href="#come-funziona"
                className="text-[14px] font-light text-white/75 transition-colors hover:text-white"
              >
                Come funziona
              </a>
              <a
                href="#documenti"
                className="text-[14px] font-light text-white/75 transition-colors hover:text-white"
              >
                Documenti
              </a>
              <a
                href="#metodo"
                className="text-[14px] font-light text-white/75 transition-colors hover:text-white"
              >
                Metodo e normativa
              </a>
            </nav>
            <Link
              href="/login"
              className="rounded-md border border-white/35 px-4 py-2 text-[14px] font-medium text-white transition-colors hover:border-white/60 hover:bg-white/10"
            >
              Accedi
            </Link>
          </div>
        </header>

        <div className="relative z-10 mx-auto flex w-full max-w-[1080px] flex-1 flex-col justify-center px-6 py-24">
          <h1
            className="landing-rise max-w-[16ch] font-heading text-[clamp(2.5rem,5.5vw,3.75rem)] leading-[1.05] font-light tracking-[-0.03em] text-balance text-white"
          >
            Dal sopralluogo al DVR, senza ricopiare un dato.
          </h1>
          <p
            className="landing-rise mt-6 max-w-[600px] text-[17px] leading-[1.55] font-light text-white/80"
            style={{ animationDelay: "120ms" }}
          >
            La piattaforma di N2O raccoglie i dati una sola volta in azienda e
            compone l&apos;intero fascicolo della sicurezza sul lavoro: DVR,
            allegati di valutazione e piani operativi, conformi al
            D.Lgs.&nbsp;81/2008 e pronti per la revisione del consulente.
          </p>
          <div
            className="landing-rise mt-10 flex flex-wrap items-center gap-4"
            style={{ animationDelay: "240ms" }}
          >
            <Link
              href="/login"
              className="inline-flex h-11 items-center rounded-md bg-white px-6 text-[15px] font-medium text-[#061b31] shadow-stripe-ambient transition-colors hover:bg-[#e5edf5]"
            >
              Accedi alla piattaforma
            </Link>
            <a
              href="#come-funziona"
              className="inline-flex h-11 items-center rounded-md border border-white/35 px-6 text-[15px] font-light text-white transition-colors hover:border-white/60 hover:bg-white/10"
            >
              Scopri come funziona
            </a>
          </div>
          <p
            className="landing-rise mt-14 text-[13px] tracking-wide text-white/55"
            style={{ animationDelay: "360ms" }}
          >
            16 documenti generati&ensp;·&ensp;7 metodi di calcolo
            documentati&ensp;·&ensp;Conforme D.Lgs. 81/2008
          </p>
        </div>
      </section>

      {/* ================= Come funziona ================= */}
      <section id="come-funziona" className="py-24 sm:py-28">
        <div className="mx-auto w-full max-w-[1080px] px-6">
          <h2 className="max-w-[22ch] font-heading text-[clamp(1.75rem,3vw,2.25rem)] leading-[1.12] font-light tracking-[-0.02em] text-balance text-[#061b31]">
            Un solo flusso, dal campo al documento.
          </h2>
          <p className="mt-4 max-w-[560px] text-[16px] leading-[1.55] text-[#64748d]">
            Ogni dato viene rilevato una volta e riusato ovunque serva: nelle
            valutazioni, nelle tabelle e in ogni allegato del fascicolo.
          </p>

          <div className="mt-16 space-y-20 sm:mt-20 sm:space-y-24">
            {/* Step 1 */}
            <div className="grid items-center gap-10 md:grid-cols-2 md:gap-14">
              <div>
                <div className="flex items-baseline gap-4">
                  <span
                    aria-hidden
                    className="font-heading text-[40px] leading-none font-light text-[#003d74]"
                  >
                    1
                  </span>
                  <h3 className="font-heading text-[22px] font-normal tracking-[-0.015em] text-[#061b31]">
                    Sopralluogo digitale
                  </h3>
                </div>
                <p className="mt-4 text-[15px] leading-[1.6] text-[#64748d]">
                  L&apos;operatore rileva in azienda organico, ambienti,
                  attrezzature e sostanze con un questionario strutturato che
                  guida la visita. Niente appunti da trascrivere al rientro: i
                  dati nascono già ordinati e collegati all&apos;azienda.
                </p>
              </div>
              <Image
                src="/landing/sopralluogo.webp"
                alt="Consulente con tablet durante il sopralluogo in un'officina meccanica"
                width={1600}
                height={1200}
                sizes="(min-width: 768px) 50vw, 100vw"
                className="rounded-lg shadow-stripe-elevated"
              />
            </div>

            {/* Step 2 — text first in DOM (heading outline + mobile order), card pulled left on desktop */}
            <div className="grid items-center gap-10 md:grid-cols-2 md:gap-14">
              <div>
                <div className="flex items-baseline gap-4">
                  <span
                    aria-hidden
                    className="font-heading text-[40px] leading-none font-light text-[#003d74]"
                  >
                    2
                  </span>
                  <h3 className="font-heading text-[22px] font-normal tracking-[-0.015em] text-[#061b31]">
                    Valutazioni e calcoli
                  </h3>
                </div>
                <p className="mt-4 text-[15px] leading-[1.6] text-[#64748d]">
                  Indice di rischio, protocollo NIOSH per la movimentazione dei
                  carichi, soglie videoterminali, checklist INAIL per lo stress
                  lavoro-correlato, rischio incendio e comfort termico: ogni
                  metodo viene applicato automaticamente ai dati rilevati, con
                  risultati tracciabili in ogni tabella.
                </p>
              </div>
              <div className="rounded-lg border border-[#e5edf5] bg-white p-6 shadow-stripe-elevated md:order-first">
                <div className="flex items-baseline justify-between gap-4">
                  <p className="text-[15px] font-medium text-[#273951]">
                    Indice di rischio
                  </p>
                  <span className="font-mono text-[13px] text-[#003d74]">
                    I = 2·D + P
                  </span>
                </div>
                <ul className="mt-4">
                  {RISK_LEVELS.map((level) => (
                    <li
                      key={level.label}
                      className="flex items-center justify-between border-b border-[#eef2f7] py-2.5 last:border-b-0"
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
                <p className="mt-4 text-[12px] leading-[1.5] text-[#64748d]">
                  La scala applicata a ogni pericolo individuato nel
                  sopralluogo.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="grid items-center gap-10 md:grid-cols-2 md:gap-14">
              <div>
                <div className="flex items-baseline gap-4">
                  <span
                    aria-hidden
                    className="font-heading text-[40px] leading-none font-light text-[#003d74]"
                  >
                    3
                  </span>
                  <h3 className="font-heading text-[22px] font-normal tracking-[-0.015em] text-[#061b31]">
                    Generazione e revisione
                  </h3>
                </div>
                <p className="mt-4 text-[15px] leading-[1.6] text-[#64748d]">
                  La piattaforma compone i documenti Word con la struttura, le
                  tabelle e le intestazioni del modello N2O, li mostra in
                  anteprima nel browser e consente correzioni inline. Il
                  consulente rivede, corregge dove serve e approva.
                </p>
              </div>
              <Image
                src="/landing/dvr-documento.webp"
                alt="Copia rilegata del Documento di Valutazione dei Rischi con le tabelle allegate"
                width={1600}
                height={1200}
                sizes="(min-width: 768px) 50vw, 100vw"
                className="rounded-lg shadow-stripe-elevated"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ================= Documenti ================= */}
      <section id="documenti" className="bg-[#f6f9fc] py-24 sm:py-28">
        <div className="mx-auto w-full max-w-[1080px] px-6">
          <h2 className="max-w-[24ch] font-heading text-[clamp(1.75rem,3vw,2.25rem)] leading-[1.12] font-light tracking-[-0.02em] text-balance text-[#061b31]">
            Un fascicolo completo, un&apos;unica base dati.
          </h2>
          <p className="mt-4 max-w-[560px] text-[16px] leading-[1.55] text-[#64748d]">
            Tutto è ancorato al DVR Master: ogni allegato riusa gli stessi
            dati del sopralluogo e resta coerente con il documento principale.
          </p>

          <div className="mt-12 overflow-hidden rounded-lg border border-[#e5edf5] bg-white shadow-stripe-standard">
            {CATALOG.map((section) => (
              <div key={section.group}>
                <p className="border-b border-[#e5edf5] bg-[#f6f9fc] px-6 py-2.5 text-[12px] font-medium tracking-[0.04em] text-[#273951]">
                  {section.group}
                </p>
                <ul>
                  {section.rows.map(([code, name, note]) => (
                    <li
                      key={code}
                      className="grid grid-cols-[92px_1fr] items-baseline gap-x-4 gap-y-1 border-b border-[#eef2f7] px-6 py-3.5 last:border-b-0 sm:grid-cols-[110px_1fr_auto]"
                    >
                      <span className="font-mono text-[12px] tracking-[0.05em] text-[#003d74]">
                        {code}
                      </span>
                      <span className="text-[15px] text-[#061b31]">{name}</span>
                      <span className="col-start-2 text-[13px] text-[#64748d] sm:col-start-3 sm:text-right">
                        {note}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ================= Metodo e normativa ================= */}
      <section id="metodo" className="dark-section bg-[#18244e] py-24 sm:py-28">
        <div className="mx-auto w-full max-w-[1080px] px-6">
          <h2 className="max-w-[24ch] font-heading text-[clamp(1.75rem,3vw,2.25rem)] leading-[1.14] font-light tracking-[-0.02em] text-balance text-white">
            Calcoli verificabili, riferimenti puntuali.
          </h2>
          <p className="mt-4 max-w-[560px] text-[16px] leading-[1.6] font-light text-white/70">
            Ogni valore che entra in tabella ha un metodo dichiarato e una
            fonte normativa: chi revisiona può sempre risalire al calcolo.
          </p>

          <dl className="mt-12">
            {METHODS.map((method) => (
              <div
                key={method.name}
                className="grid gap-x-8 gap-y-1 border-b border-white/10 py-4 md:grid-cols-[220px_1fr_auto] md:items-baseline"
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

          <div className="mt-16 grid gap-6 border-t border-white/10 pt-12 md:grid-cols-[minmax(0,320px)_1fr] md:gap-14">
            <h3 className="font-heading text-[22px] leading-[1.2] font-light tracking-[-0.015em] text-white">
              L&apos;AI assiste, il consulente decide.
            </h3>
            <p className="max-w-[62ch] text-[15px] leading-[1.65] font-light text-white/70">
              I modelli di intelligenza artificiale leggono le schede di
              sicurezza delle sostanze chimiche, propongono descrizioni
              aziendali e misure di miglioramento. Ogni testo generato passa
              dalla revisione di un professionista prima di entrare nel
              documento, e i dati anagrafici e sanitari non vengono mai inviati
              ai modelli.
            </p>
          </div>
        </div>
      </section>

      {/* ================= Chiusura ================= */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto w-full max-w-[820px] px-6 text-center">
          <figure>
            <blockquote className="font-heading text-[clamp(1.5rem,2.8vw,2.125rem)] leading-[1.25] font-light tracking-[-0.02em] text-balance text-[#061b31]">
              «Il nostro deve essere solo una questione di revisione, non di
              inserimento del dato.»
            </blockquote>
            <figcaption className="mt-5 text-[13px] tracking-wide text-[#64748d]">
              Il principio da cui nasce la piattaforma
            </figcaption>
          </figure>
          <div className="mt-12 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/login"
              className="inline-flex h-11 items-center rounded-md bg-[#003d74] px-6 text-[15px] font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
            >
              Accedi alla piattaforma
            </Link>
            <a
              href="mailto:support@dvr-sicurezza.it"
              className="text-[15px] font-medium text-[#003d74] hover:underline"
            >
              Scrivici: support@dvr-sicurezza.it
            </a>
          </div>
        </div>
      </section>
      </main>

      {/* ================= Footer ================= */}
      <footer className="border-t border-[#e5edf5]">
        <div className="mx-auto flex w-full max-w-[1080px] flex-col gap-6 px-6 py-10 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-heading text-[14px] font-light tracking-[0.18em] text-[#061b31] uppercase">
              N2O <span className="text-[#64748d]">·</span> DVR
            </p>
            <p className="mt-1.5 text-[13px] text-[#64748d]">
              © {new Date().getFullYear()} N2O SRL · Conforme D.Lgs. 81/2008 ·
              Powered by Niuexa
            </p>
          </div>
          <nav aria-label="Collegamenti" className="flex items-center gap-6">
            <Link
              href="/login"
              className="text-[14px] font-medium text-[#003d74] hover:underline"
            >
              Accedi
            </Link>
            <Link
              href="/register"
              className="text-[14px] font-medium text-[#003d74] hover:underline"
            >
              Registrati
            </Link>
            <a
              href="mailto:support@dvr-sicurezza.it"
              className="text-[14px] text-[#64748d] hover:text-[#061b31]"
            >
              support@dvr-sicurezza.it
            </a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
