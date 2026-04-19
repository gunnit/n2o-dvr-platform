"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Baby,
  Brain,
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

type AssessmentType = {
  slug: string;
  title: string;
  subtitle: string;
  icon: LucideIcon;
};

// Route slugs match the existing /assessments/<slug>/[aziendaId] pages.
const assessmentTypes: AssessmentType[] = [
  {
    slug: "mmc",
    title: "Movimentazione Manuale dei Carichi",
    subtitle: "Metodo NIOSH \u00b7 UNI EN ISO 11228",
    icon: Package,
  },
  {
    slug: "vdt",
    title: "Videoterminali",
    subtitle: "D.Lgs. 81/2008 \u00b7 Titolo VII",
    icon: Monitor,
  },
  {
    slug: "stress",
    title: "Stress Lavoro-Correlato",
    subtitle: "Metodo INAIL",
    icon: Brain,
  },
  {
    slug: "incendio",
    title: "Rischio Incendio",
    subtitle: "D.M. 03/09/2021",
    icon: Flame,
  },
  {
    slug: "microclima",
    title: "Microclima",
    subtitle: "UNI EN ISO 7730 / 7933",
    icon: Thermometer,
  },
  {
    slug: "biologico",
    title: "Rischio Biologico",
    subtitle: "D.Lgs. 81/2008 \u00b7 Titolo X",
    icon: Microscope,
  },
  {
    slug: "gestanti",
    title: "Gestanti, Puerpere, Allattamento",
    subtitle: "D.Lgs. 151/2001",
    icon: Baby,
  },
  {
    slug: "pos",
    title: "POS \u2014 Piano Operativo di Sicurezza",
    subtitle: "Cantieri temporanei o mobili",
    icon: Construction,
  },
  {
    slug: "duvri",
    title: "DUVRI",
    subtitle: "Rischi da interferenza (appalti)",
    icon: Handshake,
  },
  {
    slug: "pee",
    title: "Piano di Emergenza ed Evacuazione",
    subtitle: "D.M. 02/09/2021",
    icon: AlertTriangle,
  },
  {
    slug: "haccp",
    title: "HACCP \u2014 Sicurezza alimentare",
    subtitle: "Reg. CE 852/2004",
    icon: Utensils,
  },
];

export default function AssessmentsIndexPage() {
  const [aziende, setAziende] = useState<Azienda[]>([]);
  const [selectedAziendaId, setSelectedAziendaId] = useState<string>("");
  const [loadingAziende, setLoadingAziende] = useState(true);

  useEffect(() => {
    apiCall<Azienda[]>("/api/v1/aziende")
      .then(setAziende)
      .catch(() => {})
      .finally(() => setLoadingAziende(false));
  }, []);

  const selectedAzienda = aziende.find((a) => a.id === selectedAziendaId);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="type-h1">Valutazioni</h1>
        <p className="type-body mt-2">
          Seleziona un&apos;azienda e apri la valutazione specifica.
        </p>
      </div>

      {/* Azienda selector — mirrors the /documents page so users have a single
          mental model for "pick a company, then work on it". */}
      <div className="rounded-md border border-[#e5edf5] bg-white p-6 shadow-stripe-ambient">
        <div className="space-y-2">
          <Label htmlFor="azienda-select">Seleziona Azienda</Label>
          {loadingAziende ? (
            <p className="text-sm text-[#64748d]">Caricamento aziende...</p>
          ) : aziende.length === 0 ? (
            <p className="text-sm text-[#64748d]">
              Nessuna azienda registrata. Aggiungi un&apos;azienda per iniziare.
            </p>
          ) : (
            <select
              id="azienda-select"
              value={selectedAziendaId}
              onChange={(e) => setSelectedAziendaId(e.target.value)}
              className="w-full max-w-md rounded-xl border-none bg-surface-low px-4 py-3 text-sm outline-none transition-all focus:ring-2 focus:ring-primary-container"
            >
              <option value="">-- Seleziona un&apos;azienda --</option>
              {aziende.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.ragione_sociale}
                  {a.sede_operativa_citta ? ` - ${a.sede_operativa_citta}` : ""}
                </option>
              ))}
            </select>
          )}
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
        <>
          {selectedAzienda && (
            <p className="type-body">
              Valutazioni per{" "}
              <span className="font-medium text-[#061b31]">
                {selectedAzienda.ragione_sociale}
              </span>
            </p>
          )}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {assessmentTypes.map((t) => {
              const Icon = t.icon;
              return (
                <Link
                  key={t.slug}
                  href={`/assessments/${t.slug}/${selectedAziendaId}`}
                  className="group rounded-md border border-[#e5edf5] bg-white p-5 shadow-stripe-ambient transition-[box-shadow,transform] duration-200 hover:shadow-stripe-elevated hover:-translate-y-0.5"
                >
                  <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-[rgba(0,61,116,0.08)]">
                    <Icon
                      className="h-5 w-5 text-primary"
                      strokeWidth={1.75}
                    />
                  </div>
                  <h3 className="font-heading text-[16px] font-medium leading-[1.25] tracking-[-0.01em] text-[#061b31]">
                    {t.title}
                  </h3>
                  <p className="mt-1.5 text-[12px] text-[#64748d]">
                    {t.subtitle}
                  </p>
                </Link>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
