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
  Lock,
  Microscope,
  Monitor,
  Package,
  ShieldAlert,
  Thermometer,
  Utensils,
  type LucideIcon,
} from "lucide-react";
import { Label } from "@/components/ui/label";
import type { Azienda } from "@/types";
import { apiCall } from "@/lib/api-client";
import { Monogram, type AccentKey } from "@/components/cards/Monogram";
import { cn } from "@/lib/utils";
import { useEntitlementsContext } from "@/components/billing/entitlements-provider";
import { isDocTypeGated } from "@/hooks/use-entitlements";
import { Select } from "@/components/ui/select";
import { aziendaOptionLabel } from "@/lib/ui/azienda-label";
import { EmptyStateCard } from "@/components/ui/empty-state";

type AssessmentType = {
  slug: string;
  /**
   * The `tipo_documento` values this assessment feeds. A plan that grants none
   * of them cannot produce anything from this screen, so the card renders
   * locked — the channel guardrail (INV-9) made visible instead of discovered
   * as a 402 at the end of an hour's data entry.
   *
   * A list, not a single key: "Microclima" produces both the moderate and the
   * severe-heat allegato, and holding either is enough to make the work useful.
   */
  docTypes: string[];
  title: string;
  metodo: string;
  description: string;
  icon: LucideIcon;
  accent: AccentKey;
};

const assessmentTypes: AssessmentType[] = [
  {
    slug: "risk",
    docTypes: ["dvr_master"],
    title: "Valutazione Rischi",
    metodo: "D.Lgs. 81/2008 · Formula I = 2D + P",
    description:
      "Catalogo pericoli per ambiente · scoring P/D · livello accettabile→gravissimo.",
    icon: ShieldAlert,
    accent: "rose",
  },
  {
    slug: "mmc",
    docTypes: ["allegato_mmc"],
    title: "Movimentazione Manuale dei Carichi",
    metodo: "NIOSH · UNI EN ISO 11228",
    description: "Indice di sollevamento, PLR, fattori correttivi.",
    icon: Package,
    accent: "amber",
  },
  {
    slug: "vdt",
    docTypes: ["allegato_vdt"],
    title: "Videoterminali",
    metodo: "D.Lgs. 81/2008 · Titolo VII",
    description: "Esposizione ≥ 20h/settimana, postura, illuminotecnica.",
    icon: Monitor,
    accent: "sky",
  },
  {
    slug: "stress",
    docTypes: ["allegato_stress"],
    title: "Stress Lavoro-Correlato",
    metodo: "Metodo INAIL",
    description: "Check-list 76 indicatori · analisi preliminare e approfondita.",
    icon: Brain,
    accent: "slate",
  },
  {
    slug: "incendio",
    docTypes: ["allegato_incendio"],
    title: "Rischio Incendio",
    metodo: "D.M. 03/09/2021",
    description: "Scoring INF + SI + PI · classificazione livello basso/medio/alto.",
    icon: Flame,
    accent: "rose",
  },
  {
    slug: "microclima",
    docTypes: ["allegato_microclima", "allegato_microclima_severo"],
    title: "Microclima",
    metodo: "UNI EN ISO 7730 / 7933",
    description: "PMV/PPD per ambienti moderati; PHS per ambienti caldo-severi.",
    icon: Thermometer,
    accent: "emerald",
  },
  {
    slug: "biologico",
    docTypes: ["allegato_biologico_alimentare", "allegato_biologico_asilo", "allegato_biologico_dentisti"],
    title: "Rischio Biologico",
    metodo: "D.Lgs. 81/2008 · Titolo X",
    description: "Agenti biologici · alimentare, asilo, odontoiatrico.",
    icon: Microscope,
    accent: "navy",
  },
  {
    slug: "gestanti",
    docTypes: ["allegato_gestanti"],
    title: "Gestanti, Puerpere, Allattamento",
    metodo: "D.Lgs. 151/2001",
    description: "Valutazione per lavoratrici madri · mansioni compatibili.",
    icon: Baby,
    accent: "rose",
  },
  {
    slug: "pos",
    docTypes: ["pos"],
    title: "Piano Operativo di Sicurezza",
    metodo: "Cantieri temporanei o mobili",
    description: "POS per imprese esecutrici in cantiere.",
    icon: Construction,
    accent: "amber",
  },
  {
    slug: "duvri",
    docTypes: ["duvri"],
    title: "DUVRI",
    metodo: "Art. 26 D.Lgs. 81/2008",
    description: "Rischi da interferenza in appalti · oneri della sicurezza.",
    icon: Handshake,
    accent: "navy",
  },
  {
    slug: "pee",
    docTypes: ["pee_azienda", "pee_comune"],
    title: "Piano di Emergenza ed Evacuazione",
    metodo: "D.M. 02/09/2021",
    description: "Procedure evacuazione, squadre, planimetrie.",
    icon: AlertTriangle,
    accent: "rose",
  },
  {
    slug: "haccp",
    docTypes: ["haccp", "haccp_forms"],
    title: "HACCP — Sicurezza alimentare",
    metodo: "Reg. CE 852/2004",
    description: "CCP, schede auto-controllo, manuale aziendale.",
    icon: Utensils,
    accent: "emerald",
  },
];

export default function AssessmentsIndexPage() {
  // What the *organization* bought. The other visibility axis — what this
  // *person* may do — is `usePermissions`, and the sidebar already hides this
  // whole section from a role without ASSESSMENTS_WRITE.
  const { entitlements } = useEntitlementsContext();
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
              <Select
                id="azienda-select"
                value={selectedAziendaId}
                onChange={(e) => setSelectedAziendaId(e.target.value)}
              >
                <option value="">— Seleziona un&apos;azienda —</option>
                {aziende.map((a) => (
                  <option key={a.id} value={a.id}>
                    {aziendaOptionLabel(a)}
                  </option>
                ))}
              </Select>
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
        <EmptyStateCard
          icon={FlaskConical}
          title="Nessuna azienda selezionata"
          body="Scegli un cliente qui sopra per aprire le sue valutazioni specialistiche."
        />
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
              // Locked when the plan grants none of the documents this
              // assessment produces. `isDocTypeGated` is deliberately
              // conservative — it answers false whenever we cannot be sure, so
              // a flaky entitlements fetch shows an open card rather than a
              // padlock on work the tenant is entitled to.
              const locked = t.docTypes.every((d) => isDocTypeGated(entitlements, d));
              // A locked card must not be a link: the whole point is that the
              // route behind it would end in a 402. The "Non incluso nel piano"
              // link to /billing at the bottom is the one affordance it keeps.
              const cardClass = cn(
                "group relative flex flex-col gap-3 rounded-md border border-[#e5edf5] bg-white p-[18px] shadow-stripe-ambient transition-[box-shadow,transform,border-color] duration-200",
                locked
                  ? "bg-[#fafbfc] opacity-75"
                  : "hover:-translate-y-0.5 hover:border-[#d1d9e3] hover:shadow-stripe-elevated"
              );
              const body = (
                <>
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
                    {locked ? (
                      <Link
                        href="/billing"
                        className="inline-flex items-center gap-1 text-[12.5px] font-semibold text-[#64748d] hover:text-primary"
                      >
                        <Lock className="h-3 w-3" strokeWidth={2.25} />
                        Non incluso nel piano
                      </Link>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[12.5px] font-semibold text-primary transition-transform group-hover:translate-x-0.5">
                        Apri
                        <ArrowRight className="h-3 w-3" strokeWidth={2.25} />
                      </span>
                    )}
                  </div>
                </>
              );

              return locked ? (
                <div key={t.slug} className={cardClass}>
                  {body}
                </div>
              ) : (
                <Link
                  key={t.slug}
                  href={`/assessments/${t.slug}/${selectedAziendaId}`}
                  className={cardClass}
                >
                  {body}
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
