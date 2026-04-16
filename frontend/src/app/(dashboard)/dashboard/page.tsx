"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import {
  ArrowDown,
  ArrowUp,
  Building2,
  Clock,
  FileCheck,
  FileText,
  Plus,
  Search,
  Users,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Azienda } from "@/types";
import { useApi } from "@/hooks/use-api";
import { SurveillanceAlerts } from "@/components/dashboard/surveillance-alerts";

// US-5.1: orchestrator will add `data_scadenza_dvr` to the canonical Azienda
// type. Until then we extend it locally so the dashboard can typecheck.
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

type SortKey =
  | "ragione_sociale"
  | "codice_ateco"
  | "updated_at"
  | "data_scadenza_dvr";
type SortDir = "asc" | "desc";

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  in_progress: "bg-yellow-100 text-yellow-700",
  completed: "bg-green-100 text-green-700",
};

const statusLabels: Record<string, string> = {
  draft: "Bozza",
  in_progress: "In corso",
  completed: "Completato",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = d.getFullYear();
  return `${day}/${month}/${year}`;
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

function scadenzaChipClass(days: number | null): string {
  if (days === null) return "bg-gray-100 text-gray-500";
  if (days <= 7) return "bg-red-100 text-red-700";
  if (days <= 30) return "bg-amber-100 text-amber-700";
  return "bg-gray-100 text-gray-600";
}

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
  const [sortKey, setSortKey] = useState<SortKey>("updated_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  useEffect(() => {
    if (!isAuthenticated) return;
    Promise.all([
      apiFetch<AziendaWithScadenza[]>("/api/v1/aziende").catch(
        () => [] as AziendaWithScadenza[]
      ),
      apiFetch<DashboardKpis>("/api/v1/aziende/dashboard/kpis").catch(
        () => null
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
      aziende.filter((a) => a.survey_status === "completed").length;
    const drafts =
      kpis?.bozze ?? aziende.filter((a) => a.survey_status === "draft").length;
    const scadenze = kpis?.scadenze_imminenti ?? 0;

    return [
      {
        name: "Clienti attivi",
        value: total,
        icon: Building2,
        description: "Aziende registrate",
        accent: "text-blue-600",
      },
      {
        name: "Sopralluoghi in corso",
        value: inProgress,
        icon: Users,
        description: "In fase di compilazione",
        accent: "text-yellow-600",
      },
      {
        name: "Sopralluoghi completati",
        value: completed,
        icon: FileCheck,
        description: "Pronti per generazione",
        accent: "text-green-600",
      },
      {
        name: "Bozze",
        value: drafts,
        icon: FileText,
        description: "Da completare",
        accent: "text-gray-500",
      },
      {
        name: "Scadenze imminenti",
        value: scadenze,
        icon: Clock,
        description: "DVR in scadenza entro 30 giorni",
        accent: "text-orange-600",
      },
    ];
  }, [aziende, kpis]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "updated_at" ? "desc" : "asc");
    }
  }

  const sortedAndFiltered = useMemo(() => {
    const filtered =
      search.length < 2
        ? [...aziende]
        : aziende.filter((a) => {
            const q = search.toLowerCase();
            return (
              a.ragione_sociale.toLowerCase().includes(q) ||
              (a.partita_iva && a.partita_iva.toLowerCase().includes(q)) ||
              (a.sede_legale_citta &&
                a.sede_legale_citta.toLowerCase().includes(q)) ||
              (a.sede_operativa_citta &&
                a.sede_operativa_citta.toLowerCase().includes(q)) ||
              (a.attivita && a.attivita.toLowerCase().includes(q))
            );
          });

    const dir = sortDir === "asc" ? 1 : -1;
    filtered.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      // Null/undefined always sorts last regardless of direction
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;

      if (sortKey === "updated_at" || sortKey === "data_scadenza_dvr") {
        return (
          (new Date(av as string).getTime() -
            new Date(bv as string).getTime()) *
          dir
        );
      }
      return String(av).localeCompare(String(bv)) * dir;
    });
    return filtered;
  }, [aziende, search, sortKey, sortDir]);

  function SortIndicator({ column }: { column: SortKey }) {
    if (sortKey !== column) return null;
    return sortDir === "asc" ? (
      <ArrowUp className="ml-1 inline h-3 w-3" />
    ) : (
      <ArrowDown className="ml-1 inline h-3 w-3" />
    );
  }

  function sortableHeaderClass(): string {
    return "cursor-pointer select-none";
  }

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-heading text-3xl font-bold text-on-surface">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-on-surface-variant">
            Panoramica dell&apos;attivit&agrave;
          </p>
        </div>
        {isAdmin && (
          <Link
            href="/aziende/new"
            className="flex items-center gap-2 rounded-lg bg-primary-container px-5 py-2.5 text-sm font-bold text-white shadow-lg transition-all hover:-translate-y-0.5 hover:shadow-primary-container/30 active:translate-y-0"
          >
            <Plus className="h-4 w-4" strokeWidth={2.5} />
            Aggiungi cliente
          </Link>
        )}
      </div>

      {loading ? (
        <p className="text-on-surface-variant">Caricamento...</p>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            {stats.map((stat) => (
              <div
                key={stat.name}
                className="rounded-xl bg-white p-5 ambient-shadow transition-transform hover:-translate-y-0.5"
              >
                <div className="mb-4 flex items-start justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant">
                    {stat.name}
                  </span>
                  <stat.icon
                    className={`h-4 w-4 ${stat.accent}`}
                    strokeWidth={2}
                  />
                </div>
                <div className="font-heading text-3xl font-bold tracking-tight text-on-surface">
                  {stat.value}
                </div>
                <p className="mt-1 text-xs text-on-surface-variant">
                  {stat.description}
                </p>
              </div>
            ))}
          </div>

          {/* VDT health-surveillance alerts (US-3.5). Self-hides when
              there's nothing to flag — no empty-state clutter. */}
          <SurveillanceAlerts />

          <div className="rounded-xl bg-white p-6 ambient-shadow">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-heading text-xl font-bold text-on-surface">
                Aziende Clienti
              </h2>
            </div>
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface-variant" />
              <input
                placeholder="Cerca per ragione sociale, partita IVA, comune..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-xl border-none bg-surface-low px-10 py-3 text-sm outline-none transition-all focus:ring-2 focus:ring-primary-container"
              />
            </div>
            <div>
              {sortedAndFiltered.length === 0 ? (
                <p className="py-6 text-center text-on-surface-variant">
                  {aziende.length === 0
                    ? "Nessuna azienda registrata"
                    : "Nessun risultato trovato"}
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead
                        className={sortableHeaderClass()}
                        onClick={() => toggleSort("ragione_sociale")}
                      >
                        Ragione Sociale
                        <SortIndicator column="ragione_sociale" />
                      </TableHead>
                      <TableHead
                        className={sortableHeaderClass()}
                        onClick={() => toggleSort("codice_ateco")}
                      >
                        Codice ATECO
                        <SortIndicator column="codice_ateco" />
                      </TableHead>
                      <TableHead>Citta</TableHead>
                      <TableHead>Stato</TableHead>
                      <TableHead
                        className={sortableHeaderClass()}
                        onClick={() => toggleSort("updated_at")}
                      >
                        Ultimo Aggiornamento
                        <SortIndicator column="updated_at" />
                      </TableHead>
                      <TableHead
                        className={sortableHeaderClass()}
                        onClick={() => toggleSort("data_scadenza_dvr")}
                      >
                        Scadenza DVR
                        <SortIndicator column="data_scadenza_dvr" />
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedAndFiltered.map((azienda) => {
                      const days = daysUntil(azienda.data_scadenza_dvr);
                      return (
                        <TableRow key={azienda.id}>
                          <TableCell>
                            <Link
                              href={`/aziende/${azienda.id}`}
                              className="font-medium text-primary hover:underline"
                            >
                              {azienda.ragione_sociale}
                            </Link>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {azienda.codice_ateco || "-"}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {azienda.sede_operativa_citta ||
                              azienda.sede_legale_citta ||
                              "-"}
                          </TableCell>
                          <TableCell>
                            <Badge
                              className={statusColors[azienda.survey_status]}
                            >
                              {statusLabels[azienda.survey_status]}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {formatDate(azienda.updated_at)}
                          </TableCell>
                          <TableCell>
                            {azienda.data_scadenza_dvr ? (
                              <Badge className={scadenzaChipClass(days)}>
                                {formatDate(azienda.data_scadenza_dvr)}
                              </Badge>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
