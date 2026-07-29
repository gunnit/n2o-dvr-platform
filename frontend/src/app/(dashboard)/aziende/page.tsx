"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Building2, MapPin, Plus, Search, CalendarPlus } from "lucide-react";
import type { Azienda } from "@/types";
import { useApi } from "@/hooks/use-api";
import { Monogram } from "@/components/cards/Monogram";
import { StatusBadge } from "@/components/cards/StatusBadge";
import { MetaCell } from "@/components/cards/MetaCell";
import { AtecoPill } from "@/components/cards/AtecoPill";
import { monogramFor } from "@/lib/ui/monogram";
import { formatRelative } from "@/lib/ui/relative-time";
import { parseApiDate } from "@/lib/ui/api-date";
import { useTenantVocabulary } from "@/hooks/use-tenant-vocabulary";
import { useEntitlementsContext } from "@/components/billing/entitlements-provider";
import {
  SURVEY_STATUS_META,
  surveyStatusKey,
  statusBucketFor,
  matchesBucket,
  type SurveyStatusKey,
  type SurveyStatusBucket,
} from "@/lib/ui/status-map";
import { Callout } from "@/components/ui/callout";
import { usePermissions } from "@/hooks/use-permissions";
import { AZIENDE_CREATE } from "@/lib/permissions";

const FILTERS: { id: SurveyStatusBucket; label: string }[] = [
  { id: "all", label: "Tutte" },
  { id: "completed", label: "Completate" },
  { id: "in_progress", label: "In corso" },
  { id: "in_revisione", label: "In revisione" },
  { id: "draft", label: "Bozze" },
];

export default function AziendePage() {
  const { apiFetch, isAuthenticated } = useApi();
  // "May I add one?" is a capability, not a role: the check moves with the
  // matrix in `lib/permissions` instead of being re-guessed at each button.
  const { can } = usePermissions();
  const canCreate = can(AZIENDE_CREATE);
  const vocab = useTenantVocabulary();
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
      const b = statusBucketFor(a.survey_status);
      map[b] = (map[b] ?? 0) + 1;
    }
    return map;
  }, [aziende]);

  // Plan usage, shown next to the heading. A consultant is metered on client
  // companies, a direct tenant on its own sedi — the same rows, a different
  // ceiling (INV-4).
  const { entitlements } = useEntitlementsContext();
  const isDirect = entitlements?.account_type === "direct";
  // A direct tenant's meter is the *row count* — `_ensure_can_add_azienda`
  // counts `aziende` rows against `max_sites`, so the pill has to count the
  // same thing or it contradicts the 402. `usage.active_companies` is the Model
  // A meter (companies with a document this period) and reads as 0 for a direct
  // tenant that owns two sedi, which is simply the wrong number here.
  const unitsUsed = isDirect
    ? aziende.length
    : (entitlements?.usage.active_companies ?? aziende.length);
  const unitsTotal = isDirect
    ? (entitlements?.max_sites ?? null)
    : (entitlements?.usage.max_companies ?? null);
  // An unsubscribed tenant has every limit null, which rendered as "∞" — while
  // the server refuses to create even the first one. Show the state instead of
  // a ceiling nobody holds.
  const showUsagePill = entitlements !== null && entitlements.subscribed;
  /**
   * Creating a company is never blocked for a consultant: the contract meters
   * *active* companies at generation time, so a studio may register a prospect
   * it has not started documenting. A direct tenant's sedi are a hard count, so
   * that one does block — but only once the backend actually enforces.
   */
  const siteLimitReached =
    entitlements !== null &&
    entitlements.enforced &&
    isDirect &&
    entitlements.max_sites !== null &&
    aziende.length >= entitlements.max_sites;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return aziende.filter((a) => {
      if (!matchesBucket(a.survey_status, activeFilter)) {
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
          <div className="flex flex-wrap items-baseline gap-3">
            <h1 className="type-h1">{vocab.companiesTitle}</h1>
            {showUsagePill ? (
              <Link
                href="/billing"
                className="rounded-full border border-[#e5edf5] bg-[#f6f9fc] px-2.5 py-0.5 text-[11.5px] font-semibold text-[#273951] transition-colors hover:border-primary/40 hover:text-primary"
                title="Incluse nel tuo piano"
              >
                <span className="tnum">
                  {unitsUsed} / {unitsTotal === null ? "∞" : unitsTotal}
                </span>{" "}
                {vocab.activeCompanies.toLowerCase()}
              </Link>
            ) : entitlements && !entitlements.subscribed ? (
              <Link
                href="/billing"
                className="rounded-full border border-[rgba(155,104,41,0.3)] bg-[rgba(155,104,41,0.12)] px-2.5 py-0.5 text-[11.5px] font-semibold text-[#8a5c23] transition-colors hover:border-[rgba(155,104,41,0.5)]"
              >
                Nessun piano attivo
              </Link>
            ) : null}
          </div>
          <p className="type-body mt-2">
            {vocab.listLead}
            {aziende.length > 0 && (
              <>
                {" · "}
                <span className="tnum">{aziende.length}</span>{" "}
                {aziende.length === 1 ? "azienda" : "aziende"}
              </>
            )}
          </p>
        </div>
        {canCreate &&
          (siteLimitReached ? (
            <span
              className="inline-flex h-10 cursor-not-allowed items-center gap-2 rounded-md border border-[#e5edf5] bg-[#f6f9fc] px-4 text-sm font-medium text-[#94a3b8]"
              title="Hai raggiunto il numero di sedi incluse nel piano"
            >
              <Plus className="h-4 w-4" strokeWidth={2} />
              {vocab.addCompany}
            </span>
          ) : (
            <Link
              href="/aziende/new"
              className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
            >
              <Plus className="h-4 w-4" strokeWidth={2} />
              Nuova Azienda
            </Link>
          ))}
      </div>

      {siteLimitReached && (
        <Callout tone="warn" dense>
          Hai registrato tutte le sedi incluse nel piano.{" "}
          <Link href="/billing" className="font-semibold underline underline-offset-2">
            Aggiorna il piano
          </Link>{" "}
          per aggiungerne altre.
        </Callout>
      )}

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
          {canCreate && !siteLimitReached && (
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
