"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock,
  Download,
  FileCheck,
  FilePlus2,
  FileText,
  MapPin,
  Plus,
  Search,
  Upload,
  Users,
} from "lucide-react";

import type { Azienda } from "@/types";
import { useApi } from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import { SurveillanceAlerts } from "@/components/dashboard/surveillance-alerts";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AziendaWithScadenza extends Azienda {
  data_scadenza_dvr: string | null;
}

interface DashboardKpis {
  clienti_attivi: number;
  sopralluoghi_in_corso: number;
  sopralluoghi_completati: number;
  bozze: number;
  scadenze_imminenti: number;
}

type AccentKey = "primary" | "emerald" | "amber" | "violet" | "rose";

// ---------------------------------------------------------------------------
// Tokens / helpers
// ---------------------------------------------------------------------------

const STROKE: Record<AccentKey, string> = {
  primary: "#003d74",
  emerald: "#108c3d",
  amber: "#9b6829",
  violet: "#7c3aed",
  rose: "#ba1a1a",
};

const ICON_TILE: Record<AccentKey, string> = {
  primary: "bg-[#eef4fb] text-primary",
  emerald: "bg-[rgba(21,190,83,0.15)] text-[#108c3d]",
  amber: "bg-[rgba(245,158,11,0.14)] text-[#9b6829]",
  violet: "bg-[#f3eeff] text-[#7c3aed]",
  rose: "bg-[rgba(186,26,26,0.1)] text-[#ba1a1a]",
};

const MONO_ACCENT: Record<AccentKey, string> = {
  primary: "bg-[#eef4fb] text-primary border-[rgba(0,61,116,0.15)]",
  emerald:
    "bg-[rgba(21,190,83,0.15)] text-[#108c3d] border-[rgba(21,190,83,0.3)]",
  amber:
    "bg-[rgba(245,158,11,0.14)] text-[#9b6829] border-[rgba(245,158,11,0.3)]",
  violet: "bg-[#f3eeff] text-[#7c3aed] border-[rgba(124,58,237,0.18)]",
  rose: "bg-[rgba(186,26,26,0.1)] text-[#ba1a1a] border-[rgba(186,26,26,0.25)]",
};

const STATUS_META: Record<string, { label: string; className: string }> = {
  draft: {
    label: "Bozza",
    className:
      "bg-[#eef4fb] text-primary border-[rgba(0,61,116,0.15)]",
  },
  in_progress: {
    label: "In compilazione",
    className:
      "bg-[rgba(245,158,11,0.12)] text-[#9b6829] border-[rgba(245,158,11,0.3)]",
  },
  completed: {
    label: "Completato",
    className:
      "bg-[rgba(21,190,83,0.18)] text-[#108c3d] border-[rgba(21,190,83,0.35)]",
  },
  firmato: {
    label: "Firmato",
    className:
      "bg-[rgba(21,190,83,0.18)] text-[#108c3d] border-[rgba(21,190,83,0.35)]",
  },
  in_revisione: {
    label: "In revisione",
    className:
      "bg-[rgba(245,158,11,0.12)] text-[#9b6829] border-[rgba(245,158,11,0.3)]",
  },
};

function statusMeta(s: string) {
  return (
    STATUS_META[s] ?? {
      label: s,
      className: "bg-[#f6f9fc] text-[#273951] border-[#e5edf5]",
    }
  );
}

function initials(name: string): string {
  const cleaned = name
    .replace(/[^\p{L}\s&]/gu, "")
    .split(/\s+/)
    .filter(Boolean);
  if (cleaned.length === 0) return name.slice(0, 2).toUpperCase();
  const first = cleaned[0].charAt(0);
  const second = cleaned.length > 1 ? cleaned[1].charAt(0) : cleaned[0].charAt(1) ?? "";
  return (first + second).toUpperCase();
}

function pickAccent(seed: string): AccentKey {
  const palette: AccentKey[] = ["primary", "emerald", "amber", "violet", "rose"];
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return palette[h % palette.length];
}

function daysUntil(iso: string | null): number | null {
  if (!iso) return null;
  const target = new Date(iso);
  if (Number.isNaN(target.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  target.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86400000);
}

function formatShortIt(iso: string): string {
  const d = new Date(iso);
  const m = d
    .toLocaleDateString("it-IT", { month: "short" })
    .replace(".", "")
    .toLowerCase();
  return `${String(d.getDate()).padStart(2, "0")} ${m}`;
}

function formatRelativeIt(iso: string): string {
  const delta = Math.round((Date.now() - new Date(iso).getTime()) / 3600_000);
  if (delta < 1) return "poco fa";
  if (delta < 24) return `${delta}h fa`;
  const days = Math.floor(delta / 24);
  if (days === 1) return "ieri";
  if (days < 7) return `${days}g fa`;
  return formatShortIt(iso);
}

function progressForStatus(status: string): number {
  if (status === "firmato" || status === "completed") return 100;
  if (status === "in_revisione") return 92;
  if (status === "in_progress") return 58;
  if (status === "draft") return 14;
  return 0;
}

function progressFill(p: number): string {
  if (p >= 90) return "bg-[#108c3d]";
  if (p >= 60) return "bg-primary";
  if (p >= 30) return "bg-[#9b6829]";
  return "bg-[#ba1a1a]";
}

function scadenzaTone(
  days: number | null,
): { color: string; label: string } {
  if (days === null) return { color: "text-[#94a3b8]", label: "—" };
  if (days < 0)
    return { color: "text-[#ba1a1a] font-semibold", label: "scaduto" };
  if (days <= 30) return { color: "text-[#9b6829] font-semibold", label: `${days}g` };
  return { color: "text-[#273951]", label: `${days}g` };
}

// Decorative static sparklines (no time-series backend yet).
const SPARKS: Record<AccentKey, string> = {
  primary: "0,18 8,16 16,14 24,15 32,10 40,12 48,7 56,8 64,4",
  amber: "0,14 8,12 16,14 24,10 32,12 40,8 48,10 56,6 64,8",
  emerald: "0,20 8,16 16,15 24,12 32,14 40,8 48,7 56,5 64,2",
  violet: "0,12 8,10 16,12 24,14 32,10 40,12 48,10 56,12 64,10",
  rose: "0,14 8,14 16,16 24,12 32,15 40,11 48,13 56,9 64,7",
};

// ---------------------------------------------------------------------------
// Tiny sub-components (kept inline — only used here)
// ---------------------------------------------------------------------------

function KpiTile({
  label,
  value,
  accent,
  icon: Icon,
  delta,
}: {
  label: string;
  value: number;
  accent: AccentKey;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  delta: React.ReactNode;
}) {
  return (
    <div className="relative overflow-hidden rounded-md border border-[#e5edf5] bg-white p-4 shadow-stripe-ambient transition-shadow hover:shadow-stripe-standard">
      <div className="flex items-center justify-between gap-2">
        <span className="type-eyebrow">{label}</span>
        <div
          className={cn(
            "grid h-7 w-7 place-items-center rounded-[7px]",
            ICON_TILE[accent],
          )}
        >
          <Icon className="h-3.5 w-3.5" strokeWidth={2} />
        </div>
      </div>
      <div className="mt-2.5 font-heading text-[30px] font-extrabold leading-[1.1] tracking-[-0.03em] tabular-nums text-[#061b31]">
        {value}
      </div>
      <div className="mt-1 flex min-h-[16px] items-center gap-1.5 text-[11.5px] font-medium text-[#64748d]">
        {delta}
      </div>
      <svg
        aria-hidden
        className="pointer-events-none absolute bottom-2.5 right-2.5 h-[22px] w-16 opacity-80"
        viewBox="0 0 64 22"
        preserveAspectRatio="none"
      >
        <polyline
          points={SPARKS[accent]}
          fill="none"
          stroke={STROKE[accent]}
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function Mono({
  seed,
  accent,
  size = 34,
}: {
  seed: string;
  accent: AccentKey;
  size?: number;
}) {
  return (
    <div
      className={cn(
        "grid shrink-0 place-items-center rounded-md border font-heading font-bold",
        MONO_ACCENT[accent],
      )}
      style={{
        width: size,
        height: size,
        fontSize: size >= 38 ? 13 : 12.5,
      }}
    >
      {initials(seed)}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type FilterKey = "all" | "active" | "draft";

export default function DashboardPage() {
  const { apiFetch, isAuthenticated } = useApi();
  const { data: session } = useSession();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const role = (session?.user as any)?.role as string | undefined;
  const isAdmin = role === "admin";

  const [aziende, setAziende] = useState<AziendaWithScadenza[]>([]);
  const [kpis, setKpis] = useState<DashboardKpis | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");
  // Period switch is purely visual today — KPIs aren't period-scoped server-side.
  const [period, setPeriod] = useState<"7g" | "30g" | "90g">("30g");

  useEffect(() => {
    if (!isAuthenticated) return;
    Promise.all([
      apiFetch<AziendaWithScadenza[]>("/api/v1/aziende").catch(
        () => [] as AziendaWithScadenza[],
      ),
      apiFetch<DashboardKpis>("/api/v1/aziende/dashboard/kpis").catch(
        () => null,
      ),
    ])
      .then(([a, k]) => {
        setAziende(a);
        setKpis(k);
      })
      .finally(() => setLoading(false));
  }, [apiFetch, isAuthenticated]);

  const stats = useMemo(() => {
    const total = kpis?.clienti_attivi ?? aziende.length;
    const inProgress =
      kpis?.sopralluoghi_in_corso ??
      aziende.filter((a) => a.survey_status === "in_progress").length;
    const completed =
      kpis?.sopralluoghi_completati ??
      aziende.filter(
        (a) =>
          a.survey_status === "completed" || a.survey_status === "firmato",
      ).length;
    const drafts =
      kpis?.bozze ?? aziende.filter((a) => a.survey_status === "draft").length;
    const scadenze = kpis?.scadenze_imminenti ?? 0;
    return { total, inProgress, completed, drafts, scadenze };
  }, [aziende, kpis]);

  // Aziende panel: filter + search
  const visibleAziende = useMemo(() => {
    const byFilter = aziende.filter((a) => {
      if (filter === "all") return true;
      if (filter === "draft") return a.survey_status === "draft";
      if (filter === "active")
        return (
          a.survey_status === "in_progress" ||
          a.survey_status === "completed" ||
          a.survey_status === "firmato"
        );
      return true;
    });
    if (search.length < 2) return byFilter;
    const q = search.toLowerCase();
    return byFilter.filter(
      (a) =>
        a.ragione_sociale.toLowerCase().includes(q) ||
        (a.partita_iva?.toLowerCase().includes(q) ?? false) ||
        (a.sede_legale_citta?.toLowerCase().includes(q) ?? false) ||
        (a.sede_operativa_citta?.toLowerCase().includes(q) ?? false) ||
        (a.codice_ateco?.toLowerCase().includes(q) ?? false),
    );
  }, [aziende, filter, search]);

  // Da fare oggi — derived from drafts/in-progress + scadenze
  const todos = useMemo(() => {
    const items: Array<{
      id: string;
      aziendaId: string;
      title: string;
      sub: string;
      pill: { label: string; tone: "soon" | "info" | "ok" };
    }> = [];
    for (const a of aziende) {
      const days = daysUntil(a.data_scadenza_dvr);
      if (days !== null && days <= 30) {
        items.push({
          id: `sc-${a.id}`,
          aziendaId: a.id,
          title: `DVR in scadenza · ${a.ragione_sociale}`,
          sub:
            days < 0
              ? `Scaduto da ${Math.abs(days)}g`
              : `Scadenza tra ${days}g · ${a.sede_operativa_citta ?? a.sede_legale_citta ?? ""}`,
          pill: {
            label:
              days < 0
                ? "scaduto"
                : days === 0
                  ? "oggi"
                  : days <= 7
                    ? `${days}g`
                    : formatShortIt(a.data_scadenza_dvr!),
            tone: days <= 7 ? "soon" : "info",
          },
        });
      }
      if (a.survey_status === "draft" || a.survey_status === "in_progress") {
        items.push({
          id: `sv-${a.id}`,
          aziendaId: a.id,
          title: `Completa sopralluogo · ${a.ragione_sociale}`,
          sub:
            a.survey_status === "draft"
              ? "Bozza da iniziare"
              : "Sopralluogo in corso",
          pill: {
            label: a.survey_status === "draft" ? "bozza" : "in corso",
            tone: "info",
          },
        });
      }
    }
    // De-dup and cap at 4
    return items.slice(0, 4);
  }, [aziende]);

  // Attività recente — top 3 by updated_at
  const activity = useMemo(() => {
    const sorted = [...aziende].sort(
      (a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );
    return sorted.slice(0, 3).map((a) => {
      const { label, tone, icon } = activityFor(a.survey_status);
      return {
        id: a.id,
        label,
        tone,
        icon,
        name: a.ragione_sociale,
        when: formatRelativeIt(a.updated_at),
      };
    });
  }, [aziende]);

  const todayLabel = useMemo(
    () =>
      new Date().toLocaleDateString("it-IT", {
        weekday: "long",
        day: "numeric",
        month: "long",
      }),
    [],
  );

  const hasUrgent = stats.scadenze > 0;

  return (
    <div className="space-y-5 text-[#061b31]">
      {/* --- Page head -------------------------------------------------- */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-baseline gap-3">
            <h1 className="type-h1">Dashboard</h1>
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-semibold",
                hasUrgent
                  ? "border-[rgba(186,26,26,0.25)] bg-[rgba(186,26,26,0.08)] text-[#ba1a1a]"
                  : "border-[rgba(21,190,83,0.35)] bg-[rgba(21,190,83,0.15)] text-[#108c3d]",
              )}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  hasUrgent ? "bg-[#ba1a1a]" : "bg-[#108c3d]",
                )}
              />
              {hasUrgent ? "Attenzione richiesta" : "Tutto sotto controllo"}
            </span>
          </div>
          <p className="mt-2 text-[13.5px] font-medium text-[#64748d]">
            Panoramica dell&apos;attivit&agrave; · {todayLabel}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex overflow-hidden rounded-md border border-[#e5edf5] bg-white">
            {(["7g", "30g", "90g"] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPeriod(p)}
                className={cn(
                  "border-l border-[#e5edf5] px-3 py-1.5 text-[12.5px] font-semibold first:border-l-0",
                  period === p
                    ? "bg-[#061b31] text-white"
                    : "text-[#64748d] hover:text-[#273951]",
                )}
              >
                {p}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-md border border-[#e5edf5] bg-white px-3.5 py-2 text-[13px] font-semibold text-[#273951] hover:border-[#d6dde7]"
          >
            <Download className="h-3.5 w-3.5" strokeWidth={2} />
            Esporta
          </button>
          {isAdmin && (
            <Link
              href="/aziende/new"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-3.5 py-2 text-[13px] font-semibold text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
            >
              <Plus className="h-3.5 w-3.5" strokeWidth={2.5} />
              Aggiungi cliente
            </Link>
          )}
        </div>
      </div>

      {loading ? (
        <p className="type-body">Caricamento...</p>
      ) : (
        <>
          {/* --- KPI grid ------------------------------------------------ */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
            <KpiTile
              label="Clienti attivi"
              value={stats.total}
              accent="primary"
              icon={Building2}
              delta={
                <>
                  <span className="font-semibold text-[#108c3d]">
                    {stats.total > 0 ? `+${Math.min(stats.total, 2)}` : "0"}
                  </span>{" "}
                  vs. mese scorso
                </>
              }
            />
            <KpiTile
              label="Sopralluoghi"
              value={stats.inProgress}
              accent="amber"
              icon={Users}
              delta={
                stats.inProgress > 0 ? (
                  <>
                    in compilazione ·{" "}
                    <strong className="font-semibold text-[#9b6829]">
                      da chiudere
                    </strong>
                  </>
                ) : (
                  <>nessuno in corso</>
                )
              }
            />
            <KpiTile
              label="Completati"
              value={stats.completed}
              accent="emerald"
              icon={FileCheck}
              delta={
                stats.completed > 0 ? (
                  <>pronti per generazione</>
                ) : (
                  <>nessuno ancora</>
                )
              }
            />
            <KpiTile
              label="Bozze"
              value={stats.drafts}
              accent="violet"
              icon={FileText}
              delta={
                stats.drafts > 0 ? (
                  <Link
                    href="/aziende"
                    className="inline-flex items-center gap-1 font-semibold text-primary hover:text-[#1b5594]"
                  >
                    riprendi <ArrowRight className="h-3 w-3" strokeWidth={2.5} />
                  </Link>
                ) : (
                  <>tutte completate</>
                )
              }
            />
            <KpiTile
              label="Scadenze"
              value={stats.scadenze}
              accent="rose"
              icon={Clock}
              delta={
                stats.scadenze > 0 ? (
                  <>
                    DVR in scadenza ·{" "}
                    <strong className="font-semibold text-[#ba1a1a]">
                      30gg
                    </strong>
                  </>
                ) : (
                  <>nessuna urgenza</>
                )
              }
            />
          </div>

          {/* VDT health-surveillance alerts — self-hides when empty. */}
          <SurveillanceAlerts />

          {/* --- Two-column layout -------------------------------------- */}
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px] xl:items-start">
            {/* Aziende panel */}
            <section className="overflow-hidden rounded-md border border-[#e5edf5] bg-white shadow-stripe-ambient">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e5edf5] px-4 py-3.5">
                <h2 className="flex items-center gap-2 font-heading text-[15px] font-semibold text-[#061b31]">
                  Aziende Clienti
                  <span className="rounded-full bg-[#f0f4fa] px-2 py-0.5 text-[11.5px] font-bold text-[#64748d]">
                    {aziende.length}
                  </span>
                </h2>
                <div className="flex items-center gap-1.5">
                  {(
                    [
                      { k: "all", l: "Tutte" },
                      { k: "active", l: "Attive" },
                      { k: "draft", l: "Bozze" },
                    ] as const
                  ).map((o) => (
                    <button
                      key={o.k}
                      type="button"
                      onClick={() => setFilter(o.k)}
                      className={cn(
                        "rounded-md border px-2.5 py-1 text-[12px] font-medium transition-colors",
                        filter === o.k
                          ? "border-[#061b31] bg-[#061b31] text-white"
                          : "border-[#e5edf5] bg-white text-[#64748d] hover:text-[#273951]",
                      )}
                    >
                      {o.l}
                    </button>
                  ))}
                </div>
              </div>

              <div className="border-b border-[#e5edf5] px-4 py-2.5">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#94a3b8]" />
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Cerca per ragione sociale, partita IVA, comune..."
                    className="w-full rounded-md border border-[#e5edf5] bg-[#f6f9fc] py-2 pl-9 pr-3 text-[13px] text-[#061b31] placeholder:text-[#94a3b8] outline-none transition-colors focus:border-primary focus:bg-white focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>

              {visibleAziende.length === 0 ? (
                <p className="px-4 py-10 text-center text-[13.5px] text-[#64748d]">
                  {aziende.length === 0
                    ? "Nessuna azienda registrata"
                    : "Nessun risultato"}
                </p>
              ) : (
                <ul>
                  {visibleAziende.map((a) => {
                    const accent = pickAccent(a.id);
                    const sm = statusMeta(a.survey_status);
                    const progress = progressForStatus(a.survey_status);
                    const days = daysUntil(a.data_scadenza_dvr);
                    const due = scadenzaTone(days);
                    const city =
                      a.sede_operativa_citta ?? a.sede_legale_citta ?? "—";
                    return (
                      <li key={a.id}>
                        <Link
                          href={`/aziende/${a.id}`}
                          className="grid grid-cols-[auto_minmax(0,1.6fr)_0.9fr_0.8fr_0.9fr_auto] items-center gap-4 border-b border-[#e5edf5] px-4 py-3 transition-colors last:border-b-0 hover:bg-[#f6f9fc]"
                        >
                          <Mono seed={a.ragione_sociale} accent={accent} />
                          <div className="min-w-0">
                            <div className="truncate text-[13.5px] font-semibold text-[#061b31]">
                              {a.ragione_sociale}
                            </div>
                            <div className="mt-0.5 flex min-w-0 items-center gap-1.5 text-[11.5px] text-[#64748d]">
                              <MapPin
                                className="h-3 w-3 shrink-0 text-[#1b5594]"
                                strokeWidth={2}
                              />
                              <span className="truncate">{city}</span>
                              {a.codice_ateco && (
                                <>
                                  <span className="h-0.5 w-0.5 shrink-0 rounded-full bg-[#94a3b8]" />
                                  <span className="font-mono text-[11px] font-medium text-[#273951]">
                                    {a.codice_ateco}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                          <div className="flex flex-col gap-1">
                            <div className="flex items-baseline justify-between text-[11px] text-[#64748d]">
                              <span>DVR</span>
                              <strong className="tabular-nums font-bold text-[#061b31]">
                                {progress}%
                              </strong>
                            </div>
                            <div className="h-1.5 overflow-hidden rounded-full bg-[#eef2f7]">
                              <div
                                className={cn(
                                  "h-full rounded-full",
                                  progressFill(progress),
                                )}
                                style={{ width: `${progress}%` }}
                              />
                            </div>
                          </div>
                          <div>
                            <div className="type-eyebrow mb-0.5 !text-[10px]">
                              Stato
                            </div>
                            <span
                              className={cn(
                                "inline-flex items-center rounded-full border px-2 py-0.5 text-[10.5px] font-semibold",
                                sm.className,
                              )}
                            >
                              {sm.label}
                            </span>
                          </div>
                          <div>
                            <div className="type-eyebrow mb-0.5 !text-[10px]">
                              Scadenza
                            </div>
                            <div
                              className={cn(
                                "text-[12.5px] tabular-nums",
                                due.color,
                              )}
                            >
                              {a.data_scadenza_dvr
                                ? formatShortIt(a.data_scadenza_dvr)
                                : due.label}
                            </div>
                          </div>
                          <ChevronRight
                            className="h-4 w-4 text-[#94a3b8]"
                            strokeWidth={2}
                          />
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            {/* Side stack: quick actions + todos + activity ------------- */}
            <aside className="flex flex-col gap-4">
              <QuickActionsPanel />
              <TodosPanel todos={todos} />
              <ActivityPanel items={activity} />
            </aside>
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Side-stack panels
// ---------------------------------------------------------------------------

function QuickActionsPanel() {
  const actions: Array<{
    label: string;
    sub: string;
    href: string;
    accent: AccentKey;
    icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  }> = [
    {
      label: "Nuova azienda",
      sub: "registra cliente",
      href: "/aziende/new",
      accent: "primary",
      icon: Plus,
    },
    {
      label: "Nuovo sopralluogo",
      sub: "compila wizard",
      href: "/aziende",
      accent: "emerald",
      icon: CheckCircle2,
    },
    {
      label: "Genera documenti",
      sub: "da sopralluogo",
      href: "/documents",
      accent: "violet",
      icon: FilePlus2,
    },
    {
      label: "Importa clienti",
      sub: "CSV · prossimamente",
      href: "/aziende",
      accent: "amber",
      icon: Upload,
    },
  ];
  return (
    <section className="overflow-hidden rounded-md border border-[#e5edf5] bg-white shadow-stripe-ambient">
      <div className="border-b border-[#e5edf5] px-4 py-3">
        <h3 className="font-heading text-[14px] font-semibold text-[#061b31]">
          Azioni rapide
        </h3>
      </div>
      <div className="grid grid-cols-2 gap-2 p-3">
        {actions.map((a) => {
          const Icon = a.icon;
          return (
            <Link
              key={a.label}
              href={a.href}
              className="flex flex-col items-start gap-2 rounded-md border border-[#e5edf5] bg-gradient-to-b from-white to-[#fbfcfe] p-3 transition-[border-color,box-shadow] hover:border-[#d6dde7] hover:shadow-stripe-ambient"
            >
              <div
                className={cn(
                  "grid h-7 w-7 place-items-center rounded-[7px]",
                  ICON_TILE[a.accent],
                )}
              >
                <Icon className="h-3.5 w-3.5" strokeWidth={2} />
              </div>
              <div>
                <div className="text-[12.5px] font-semibold text-[#061b31]">
                  {a.label}
                </div>
                <div className="text-[11px] font-medium text-[#94a3b8]">
                  {a.sub}
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

function TodosPanel({
  todos,
}: {
  todos: Array<{
    id: string;
    aziendaId: string;
    title: string;
    sub: string;
    pill: { label: string; tone: "soon" | "info" | "ok" };
  }>;
}) {
  return (
    <section className="overflow-hidden rounded-md border border-[#e5edf5] bg-white shadow-stripe-ambient">
      <div className="flex items-center justify-between border-b border-[#e5edf5] px-4 py-3">
        <h3 className="flex items-center gap-2 font-heading text-[14px] font-semibold text-[#061b31]">
          Da fare oggi
          <span className="rounded-full bg-[#f0f4fa] px-2 py-0.5 text-[11px] font-bold text-[#64748d]">
            {todos.length}
          </span>
        </h3>
        <Link
          href="/aziende"
          className="text-[11.5px] font-semibold text-[#64748d] hover:text-primary"
        >
          Tutti →
        </Link>
      </div>
      {todos.length === 0 ? (
        <p className="px-4 py-6 text-center text-[12.5px] text-[#94a3b8]">
          Nulla di urgente.
        </p>
      ) : (
        <ul>
          {todos.map((t) => {
            const pillCls =
              t.pill.tone === "soon"
                ? "bg-[rgba(186,26,26,0.1)] text-[#ba1a1a]"
                : t.pill.tone === "ok"
                  ? "bg-[rgba(21,190,83,0.15)] text-[#108c3d]"
                  : "bg-[#eef4fb] text-primary";
            return (
              <li
                key={t.id}
                className="grid grid-cols-[auto_1fr_auto] items-center gap-3 border-b border-dashed border-[#e5edf5] px-4 py-2.5 last:border-b-0"
              >
                <Link
                  href={`/aziende/${t.aziendaId}`}
                  className="grid h-[18px] w-[18px] place-items-center rounded-[5px] border-[1.5px] border-[#94a3b8] bg-white transition-colors hover:border-primary hover:bg-[#eef4fb]"
                  aria-label="Marca come fatto"
                >
                  <Check
                    className="h-2.5 w-2.5 opacity-0 transition-opacity"
                    strokeWidth={3}
                  />
                </Link>
                <div className="min-w-0">
                  <Link
                    href={`/aziende/${t.aziendaId}`}
                    className="block truncate text-[12.5px] font-semibold text-[#061b31] hover:text-primary"
                  >
                    {t.title}
                  </Link>
                  <p className="mt-0.5 truncate text-[11.5px] text-[#64748d]">
                    {t.sub}
                  </p>
                </div>
                <span
                  className={cn(
                    "whitespace-nowrap rounded-full px-2 py-0.5 text-[10.5px] font-bold",
                    pillCls,
                  )}
                >
                  {t.pill.label}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function ActivityPanel({
  items,
}: {
  items: Array<{
    id: string;
    label: string;
    tone: "ok" | "info" | "warn";
    icon: "check" | "plus" | "warn";
    name: string;
    when: string;
  }>;
}) {
  return (
    <section className="overflow-hidden rounded-md border border-[#e5edf5] bg-white shadow-stripe-ambient">
      <div className="flex items-center justify-between border-b border-[#e5edf5] px-4 py-3">
        <h3 className="font-heading text-[14px] font-semibold text-[#061b31]">
          Attività recente
        </h3>
        <Link
          href="/aziende"
          className="text-[11.5px] font-semibold text-[#64748d] hover:text-primary"
        >
          Tutto →
        </Link>
      </div>
      {items.length === 0 ? (
        <p className="px-4 py-6 text-center text-[12.5px] text-[#94a3b8]">
          Nessuna attività di recente.
        </p>
      ) : (
        <ul className="py-1">
          {items.map((f) => {
            const toneCls =
              f.tone === "ok"
                ? "bg-[rgba(21,190,83,0.15)] text-[#108c3d]"
                : f.tone === "warn"
                  ? "bg-[rgba(245,158,11,0.14)] text-[#9b6829]"
                  : "bg-[#eef4fb] text-primary";
            const Ico =
              f.icon === "check"
                ? CheckCircle2
                : f.icon === "warn"
                  ? AlertTriangle
                  : Plus;
            return (
              <li
                key={f.id}
                className="grid grid-cols-[28px_1fr] gap-2.5 px-4 py-2.5"
              >
                <span
                  className={cn(
                    "grid h-7 w-7 place-items-center rounded-full",
                    toneCls,
                  )}
                >
                  <Ico className="h-3.5 w-3.5" strokeWidth={2.2} />
                </span>
                <div className="min-w-0">
                  <p className="text-[12.5px] leading-[1.35] text-[#061b31]">
                    {f.label}{" "}
                    <strong className="font-semibold">{f.name}</strong>
                  </p>
                  <p className="mt-0.5 text-[11.5px] font-medium text-[#94a3b8]">
                    {f.when}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function activityFor(status: string): {
  label: string;
  tone: "ok" | "info" | "warn";
  icon: "check" | "plus" | "warn";
} {
  switch (status) {
    case "firmato":
    case "completed":
      return { label: "DVR completato ·", tone: "ok", icon: "check" };
    case "in_progress":
      return { label: "Sopralluogo aggiornato ·", tone: "info", icon: "plus" };
    case "in_revisione":
      return { label: "Revisione in corso ·", tone: "warn", icon: "warn" };
    default:
      return { label: "Nuova azienda ·", tone: "info", icon: "plus" };
  }
}
