"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { Building2, MapPin, Plus, Search, CalendarPlus } from "lucide-react";
import type { Azienda } from "@/types";
import { useApi } from "@/hooks/use-api";
import { Monogram } from "@/components/cards/Monogram";
import { StatusBadge } from "@/components/cards/StatusBadge";
import { MetaCell } from "@/components/cards/MetaCell";
import { AtecoPill } from "@/components/cards/AtecoPill";
import { monogramFor } from "@/lib/ui/monogram";
import { formatRelative } from "@/lib/ui/relative-time";
import {
  SURVEY_STATUS_META,
  surveyStatusKey,
  type SurveyStatusKey,
} from "@/lib/ui/status-map";

const FILTERS: { id: "all" | SurveyStatusKey; label: string }[] = [
  { id: "all", label: "Tutte" },
  { id: "completed", label: "Completate" },
  { id: "in_progress", label: "In corso" },
  { id: "in_revisione", label: "In revisione" },
  { id: "draft", label: "Bozze" },
];

export default function AziendePage() {
  const { apiFetch, isAuthenticated } = useApi();
  const { data: session } = useSession();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const role = (session?.user as any)?.role as string | undefined;
  const isAdmin = role === "admin";
  const [aziende, setAziende] = useState<Azienda[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<(typeof FILTERS)[number]["id"]>("all");

  useEffect(() => {
    if (!isAuthenticated) return;
    apiFetch<Azienda[]>("/api/v1/aziende")
      .then(setAziende)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [apiFetch, isAuthenticated]);

  const counts = useMemo(() => {
    const map: Record<string, number> = { all: aziende.length };
    for (const a of aziende) {
      const k = surveyStatusKey(a.survey_status);
      map[k] = (map[k] ?? 0) + 1;
    }
    return map;
  }, [aziende]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return aziende.filter((a) => {
      if (activeFilter !== "all" && surveyStatusKey(a.survey_status) !== activeFilter) {
        return false;
      }
      if (!q) return true;
      return (
        a.ragione_sociale.toLowerCase().includes(q) ||
        (a.partita_iva ?? "").toLowerCase().includes(q) ||
        (a.codice_ateco ?? "").toLowerCase().includes(q) ||
        (a.sede_operativa_citta ?? "").toLowerCase().includes(q) ||
        (a.sede_legale_citta ?? "").toLowerCase().includes(q)
      );
    });
  }, [aziende, query, activeFilter]);

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="type-h1">Aziende</h1>
          <p className="type-body mt-2">
            Gestione clienti
            {aziende.length > 0 && (
              <>
                {" · "}
                <span className="tnum">{aziende.length}</span>{" "}
                {aziende.length === 1 ? "azienda" : "aziende"}
              </>
            )}
          </p>
        </div>
        {isAdmin && (
          <Link
            href="/aziende/new"
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
          >
            <Plus className="h-4 w-4" strokeWidth={2} />
            Nuova Azienda
          </Link>
        )}
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
              placeholder="Cerca azienda, P.IVA, ATECO…"
              className="h-9 w-full rounded-md border border-[#e5edf5] bg-white pl-9 pr-3 text-[13.5px] text-[#061b31] placeholder:text-[#94a3b8] focus:border-primary focus:outline-none focus:ring-2 focus:ring-[rgba(0,61,116,0.12)]"
            />
          </div>
          {FILTERS.map((f) => {
            const count = counts[f.id] ?? 0;
            const active = activeFilter === f.id;
            return (
              <button
                key={f.id}
                type="button"
                onClick={() => setActiveFilter(f.id)}
                className={`inline-flex h-9 items-center gap-1.5 rounded-md border px-3 text-[13px] font-medium transition-colors ${
                  active
                    ? "border-[#061b31] bg-[#061b31] text-white"
                    : "border-[#e5edf5] bg-white text-[#273951] hover:border-[#d1d9e3]"
                }`}
              >
                {f.label}
                {count > 0 && (
                  <span
                    className={`tnum text-[11.5px] ${active ? "opacity-70" : "text-[#94a3b8]"}`}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {loading ? (
        <p className="type-body">Caricamento...</p>
      ) : aziende.length === 0 ? (
        <div className="rounded-md border border-[#e5edf5] bg-white p-14 text-center shadow-stripe-ambient">
          <Building2 className="mx-auto mb-4 h-10 w-10 text-[#c2c6d2]" strokeWidth={1.5} />
          <p className="type-body">Nessuna azienda registrata</p>
          {isAdmin && (
            <Link
              href="/aziende/new"
              className="mt-5 inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
            >
              <Plus className="h-4 w-4" strokeWidth={2} />
              Aggiungi la prima azienda
            </Link>
          )}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-md border border-dashed border-[#e5edf5] bg-white p-10 text-center">
          <p className="type-body">Nessun risultato per i filtri attivi.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((azienda) => {
            const meta = SURVEY_STATUS_META[surveyStatusKey(azienda.survey_status)];
            const city =
              azienda.sede_operativa_citta || azienda.sede_legale_citta || null;
            const createdLabel = azienda.created_at
              ? new Date(azienda.created_at).toLocaleDateString("it-IT", {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                })
              : null;
            const mono = monogramFor(azienda.ragione_sociale);

            return (
              <Link
                key={azienda.id}
                href={`/aziende/${azienda.id}`}
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

                {(azienda.partita_iva || createdLabel) && (
                  <div className="grid grid-cols-2 gap-3 border-t border-[#eef2f7] pt-3">
                    <MetaCell label="P. IVA" tnum>
                      {azienda.partita_iva || "—"}
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
                )}

                <div className="flex items-center justify-between pt-1">
                  {azienda.codice_ateco ? (
                    <AtecoPill code={azienda.codice_ateco} />
                  ) : (
                    <span />
                  )}
                  <span className="text-[11px] font-medium text-[#94a3b8]">
                    Agg. {formatRelative(azienda.updated_at)}
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
