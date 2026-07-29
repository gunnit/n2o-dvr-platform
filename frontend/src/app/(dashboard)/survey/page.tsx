"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ClipboardList, MapPin, Search, CalendarPlus } from "lucide-react";
import type { Azienda } from "@/types";
import { apiCall } from "@/lib/api-client";
import { Monogram } from "@/components/cards/Monogram";
import { StatusBadge } from "@/components/cards/StatusBadge";
import { MetaCell } from "@/components/cards/MetaCell";
import { AtecoPill } from "@/components/cards/AtecoPill";
import { monogramFor } from "@/lib/ui/monogram";
import { formatRelative } from "@/lib/ui/relative-time";
import { parseApiDate } from "@/lib/ui/api-date";
import { EmptyStateCard } from "@/components/ui/empty-state";
import { FilterTabs } from "@/components/ui/filter-tabs";
import {
  SURVEY_STATUS_META,
  surveyStatusKey,
  statusBucketFor,
  matchesBucket,
  type SurveyStatusKey,
  type SurveyStatusBucket,
} from "@/lib/ui/status-map";

const FILTERS: { id: SurveyStatusBucket; label: string }[] = [
  { id: "all", label: "Tutti" },
  { id: "in_progress", label: "In corso" },
  { id: "draft", label: "Da iniziare" },
  { id: "in_revisione", label: "In revisione" },
  { id: "completed", label: "Completati" },
];

const CTA_LABEL: Record<SurveyStatusKey, string> = {
  draft: "Avvia sopralluogo",
  in_progress: "Continua",
  in_revisione: "Rivedi",
  completed: "Rivedi",
  firmato: "Rivedi",
};

export default function SurveyPage() {
  const [aziende, setAziende] = useState<Azienda[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [activeFilter, setActiveFilter] =
    useState<(typeof FILTERS)[number]["id"]>("all");

  useEffect(() => {
    apiCall<Azienda[]>("/api/v1/aziende")
      .then(setAziende)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const counts = useMemo(() => {
    const map: Record<string, number> = { all: aziende.length };
    for (const a of aziende) {
      const b = statusBucketFor(a.survey_status);
      map[b] = (map[b] ?? 0) + 1;
    }
    return map;
  }, [aziende]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return aziende.filter((a) => {
      if (!matchesBucket(a.survey_status, activeFilter)) {
        return false;
      }
      if (!q) return true;
      return (
        a.ragione_sociale.toLowerCase().includes(q) ||
        (a.codice_ateco ?? "").toLowerCase().includes(q) ||
        (a.sede_operativa_citta ?? "").toLowerCase().includes(q) ||
        (a.sede_legale_citta ?? "").toLowerCase().includes(q)
      );
    });
  }, [aziende, query, activeFilter]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="type-h1">Sopralluoghi</h1>
        <p className="type-body mt-2">
          Seleziona un&apos;azienda per avviare o continuare il sopralluogo
          digitale.
        </p>
      </div>

      {aziende.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative max-w-sm flex-1">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#94a3b8]"
              strokeWidth={2}
            />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Cerca azienda, ATECO, città…"
              className="h-9 w-full rounded-md border border-[#e5edf5] bg-white pl-9 pr-3 text-[13.5px] text-[#061b31] placeholder:text-[#94a3b8] focus:border-primary focus:outline-none focus:ring-2 focus:ring-[rgba(0,61,116,0.12)]"
            />
          </div>
          <FilterTabs
            tabs={FILTERS.map((f) => ({ ...f, count: counts[f.id] ?? 0 }))}
            value={activeFilter}
            onChange={setActiveFilter}
          />
        </div>
      )}

      {loading ? (
        <p className="type-body">Caricamento...</p>
      ) : aziende.length === 0 ? (
        <EmptyStateCard
          icon={ClipboardList}
          title="Nessuna azienda registrata"
          body="Un sopralluogo parte sempre da un cliente. Registrane uno per iniziare a raccogliere i dati."
          action={
            <Link
              href="/aziende/new"
              className="inline-flex h-9 items-center rounded-md border border-[#e5edf5] bg-white px-3 text-[13px] font-medium text-[#273951] transition-colors hover:border-[#d1d9e3]"
            >
              Aggiungi azienda
            </Link>
          }
        />
      ) : filtered.length === 0 ? (
        <EmptyStateCard
          icon={Search}
          title="Nessun risultato"
          body="Nessuna azienda corrisponde alla ricerca o ai filtri attivi."
          dashed
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((azienda) => {
            const key = surveyStatusKey(azienda.survey_status);
            const meta = SURVEY_STATUS_META[key];
            const city =
              azienda.sede_operativa_citta || azienda.sede_legale_citta || null;
            const createdLabel = azienda.created_at
              ? (parseApiDate(azienda.created_at) ?? new Date(0)).toLocaleDateString("it-IT", {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                })
              : null;
            const mono = monogramFor(azienda.ragione_sociale);

            return (
              <Link
                key={azienda.id}
                href={`/survey/${azienda.id}`}
                className="group flex flex-col gap-3.5 rounded-md border border-[#e5edf5] bg-white p-[18px] shadow-stripe-ambient transition-[box-shadow,transform,border-color] duration-200 hover:-translate-y-0.5 hover:border-[#d1d9e3] hover:shadow-stripe-elevated"
              >
                <div className="flex items-start gap-3">
                  <Monogram accent={meta.accent}>{mono}</Monogram>
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate font-heading text-[15px] font-semibold leading-[1.25] tracking-[-0.005em] text-[#061b31]">
                      {azienda.ragione_sociale}
                    </h3>
                    {city ? (
                      <div className="mt-1 flex items-center gap-1.5 text-[12.5px] text-[#64748d]">
                        <MapPin className="h-3 w-3 text-[#0ea5e9]" strokeWidth={2} />
                        <span className="truncate">{city}</span>
                      </div>
                    ) : (
                      <div className="mt-1 text-[12.5px] italic text-[#94a3b8]">
                        Sede non specificata
                      </div>
                    )}
                  </div>
                  <StatusBadge className={meta.badge}>{meta.label}</StatusBadge>
                </div>

                <div className="grid grid-cols-2 gap-3 border-t border-[#eef2f7] pt-3">
                  <MetaCell label="Ultimo aggiornamento" tone="muted">
                    {formatRelative(azienda.updated_at) || "—"}
                  </MetaCell>
                  <MetaCell label="Creata il" tone="muted">
                    {createdLabel ? (
                      <>
                        <CalendarPlus className="h-3 w-3" strokeWidth={2} />
                        <span className="truncate">{createdLabel}</span>
                      </>
                    ) : (
                      "—"
                    )}
                  </MetaCell>
                </div>

                <div className="flex items-center justify-between pt-1">
                  {azienda.codice_ateco ? (
                    <AtecoPill code={azienda.codice_ateco} />
                  ) : (
                    <span />
                  )}
                  <span className="text-[12px] font-semibold text-primary transition-transform group-hover:translate-x-0.5">
                    {CTA_LABEL[key]} →
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
