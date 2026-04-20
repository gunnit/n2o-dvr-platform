"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Baby,
  Brain,
  Building2,
  Construction,
  FlaskConical,
  Flame,
  Handshake,
  Microscope,
  Monitor,
  Package,
  Thermometer,
  Utensils,
  type LucideIcon,
} from "lucide-react";
import { Label } from "@/components/ui/label";
import type { Azienda } from "@/types";
import { apiCall } from "@/lib/api-client";
import { Monogram, type AccentKey } from "@/components/cards/Monogram";

type AssessmentType = {
  slug: string;
  title: string;
  metodo: string;
  description: string;
  icon: LucideIcon;
  accent: AccentKey;
};

const assessmentTypes: AssessmentType[] = [
  {
    slug: "mmc",
    title: "Movimentazione Manuale dei Carichi",
    metodo: "NIOSH · UNI EN ISO 11228",
    description: "Indice di sollevamento, PLR, fattori correttivi.",
    icon: Package,
    accent: "amber",
  },
  {
    slug: "vdt",
    title: "Videoterminali",
    metodo: "D.Lgs. 81/2008 · Titolo VII",
    description: "Esposizione ≥ 20h/settimana, postura, illuminotecnica.",
    icon: Monitor,
    accent: "sky",
  },
  {
    slug: "stress",
    title: "Stress Lavoro-Correlato",
    metodo: "Metodo INAIL",
    description: "Check-list 76 indicatori · analisi preliminare e approfondita.",
    icon: Brain,
    accent: "violet",
  },
  {
    slug: "incendio",
    title: "Rischio Incendio",
    metodo: "D.M. 03/09/2021",
    description: "Scoring INF + SI + PI · classificazione livello basso/medio/alto.",
    icon: Flame,
    accent: "rose",
  },
  {
    slug: "microclima",
    title: "Microclima",
    metodo: "UNI EN ISO 7730 / 7933",
    description: "PMV/PPD per ambienti moderati; PHS per ambienti caldo-severi.",
    icon: Thermometer,
    accent: "emerald",
  },
  {
    slug: "biologico",
    title: "Rischio Biologico",
    metodo: "D.Lgs. 81/2008 · Titolo X",
    description: "Agenti biologici · alimentare, asilo, odontoiatrico.",
    icon: Microscope,
    accent: "navy",
  },
  {
    slug: "gestanti",
    title: "Gestanti, Puerpere, Allattamento",
    metodo: "D.Lgs. 151/2001",
    description: "Valutazione per lavoratrici madri · mansioni compatibili.",
    icon: Baby,
    accent: "rose",
  },
  {
    slug: "pos",
    title: "Piano Operativo di Sicurezza",
    metodo: "Cantieri temporanei o mobili",
    description: "POS per imprese esecutrici in cantiere.",
    icon: Construction,
    accent: "amber",
  },
  {
    slug: "duvri",
    title: "DUVRI",
    metodo: "Art. 26 D.Lgs. 81/2008",
    description: "Rischi da interferenza in appalti · oneri della sicurezza.",
    icon: Handshake,
    accent: "navy",
  },
  {
    slug: "pee",
    title: "Piano di Emergenza ed Evacuazione",
    metodo: "D.M. 02/09/2021",
    description: "Procedure evacuazione, squadre, planimetrie.",
    icon: AlertTriangle,
    accent: "rose",
  },
  {
    slug: "haccp",
    title: "HACCP — Sicurezza alimentare",
    metodo: "Reg. CE 852/2004",
    description: "CCP, schede auto-controllo, manuale aziendale.",
    icon: Utensils,
    accent: "emerald",
  },
];

export default function AssessmentsIndexPage() {
  const [aziende, setAziende] = useState<Azienda[]>([]);
  const [selectedAziendaId, setSelectedAziendaId] = useState<string>("");
  const [loadingAziende, setLoadingAziende] = useState(true);
  const [query, setQuery] = useState("");

  useEffect(() => {
    apiCall<Azienda[]>("/api/v1/aziende")
      .then(setAziende)
      .catch(() => {})
      .finally(() => setLoadingAziende(false));
  }, []);

  const selectedAzienda = aziende.find((a) => a.id === selectedAziendaId);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return assessmentTypes;
    return assessmentTypes.filter(
      (t) =>
        t.title.toLowerCase().includes(q) ||
        t.metodo.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q),
    );
  }, [query]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="type-h1">Valutazioni</h1>
        <p className="type-body mt-2">
          Seleziona un&apos;azienda e apri la valutazione specifica. Ogni valutazione
          segue un metodo normato e produce documenti allegati al DVR.
        </p>
      </div>

      <div className="rounded-md border border-[#e5edf5] bg-white p-5 shadow-stripe-ambient">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:gap-6">
          <div className="flex-1 space-y-1.5">
            <Label htmlFor="azienda-select" className="flex items-center gap-1.5">
              <Building2 className="h-3.5 w-3.5 text-[#64748d]" strokeWidth={1.75} />
              Seleziona Azienda
            </Label>
            {loadingAziende ? (
              <p className="text-sm text-[#64748d]">Caricamento aziende…</p>
            ) : aziende.length === 0 ? (
              <p className="text-sm text-[#64748d]">
                Nessuna azienda registrata. Aggiungi un&apos;azienda per iniziare.
              </p>
            ) : (
              <select
                id="azienda-select"
                value={selectedAziendaId}
                onChange={(e) => setSelectedAziendaId(e.target.value)}
                className="h-10 w-full rounded-md border border-[#e5edf5] bg-white px-3 text-sm text-[#061b31] outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-[rgba(0,61,116,0.12)]"
              >
                <option value="">— Seleziona un&apos;azienda —</option>
                {aziende.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.ragione_sociale}
                    {a.sede_operativa_citta ? ` · ${a.sede_operativa_citta}` : ""}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className="flex-1 space-y-1.5">
            <Label htmlFor="assessment-search">Cerca valutazione</Label>
            <input
              id="assessment-search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="MMC, VDT, stress, incendio…"
              className="h-10 w-full rounded-md border border-[#e5edf5] bg-white px-3 text-sm text-[#061b31] placeholder:text-[#94a3b8] focus:border-primary focus:outline-none focus:ring-2 focus:ring-[rgba(0,61,116,0.12)]"
            />
          </div>
        </div>
      </div>

      {!selectedAziendaId ? (
        <div className="rounded-md border border-[#e5edf5] bg-white p-14 text-center shadow-stripe-ambient">
          <FlaskConical
            className="mx-auto mb-4 h-10 w-10 text-[#c2c6d2]"
            strokeWidth={1.5}
          />
          <p className="type-body">
            Seleziona un&apos;azienda per accedere alle valutazioni.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {selectedAzienda && (
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold uppercase tracking-[0.06em] text-[#94a3b8]">
                Contesto
              </span>
              <span className="rounded-full bg-[#f6f9fc] px-2.5 py-0.5 text-[12px] font-medium text-[#273951]">
                {selectedAzienda.ragione_sociale}
                {selectedAzienda.sede_operativa_citta && (
                  <span className="text-[#64748d]">
                    {" · "}
                    {selectedAzienda.sede_operativa_citta}
                  </span>
                )}
              </span>
              <span className="tnum text-[11px] text-[#94a3b8]">
                {filtered.length} valutazion{filtered.length === 1 ? "e" : "i"}
              </span>
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filtered.map((t) => {
              const Icon = t.icon;
              return (
                <Link
                  key={t.slug}
                  href={`/assessments/${t.slug}/${selectedAziendaId}`}
                  className="group relative flex flex-col gap-3 rounded-md border border-[#e5edf5] bg-white p-[18px] shadow-stripe-ambient transition-[box-shadow,transform,border-color] duration-200 hover:-translate-y-0.5 hover:border-[#d1d9e3] hover:shadow-stripe-elevated"
                >
                  <div className="flex items-start gap-3">
                    <Monogram accent={t.accent}>
                      <Icon className="h-5 w-5" strokeWidth={1.75} />
                    </Monogram>
                    <div className="min-w-0 flex-1">
                      <h3 className="font-heading text-[15px] font-semibold leading-[1.25] tracking-[-0.005em] text-[#061b31]">
                        {t.title}
                      </h3>
                      <p className="mt-1 text-[12px] font-medium uppercase tracking-[0.04em] text-[#94a3b8]">
                        {t.metodo}
                      </p>
                    </div>
                  </div>

                  <p className="text-[13px] leading-[1.45] text-[#64748d]">
                    {t.description}
                  </p>

                  <div className="mt-auto flex items-center justify-between border-t border-[#eef2f7] pt-3">
                    <span className="font-mono text-[11px] uppercase tracking-[0.06em] text-[#94a3b8]">
                      /{t.slug}
                    </span>
                    <span className="inline-flex items-center gap-1 text-[12.5px] font-semibold text-primary transition-transform group-hover:translate-x-0.5">
                      Apri
                      <ArrowRight className="h-3 w-3" strokeWidth={2.25} />
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
