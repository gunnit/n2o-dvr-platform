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
  draft:
    "bg-[#f6f9fc] text-[#273951] border border-[#e5edf5]",
  in_progress:
    "bg-[rgba(245,158,11,0.12)] text-[#9b6829] border border-[rgba(245,158,11,0.3)]",
  completed:
    "bg-[rgba(21,190,83,0.2)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
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
  const base = "tnum border";
  if (days === null)
    return `${base} bg-[#f6f9fc] text-[#64748d] border-[#e5edf5]`;
  if (days <= 7)
    return `${base} bg-[rgba(186,26,26,0.1)] text-[#ba1a1a] border-[rgba(186,26,26,0.3)]`;
  if (days <= 30)
    return `${base} bg-[rgba(245,158,11,0.12)] text-[#9b6829] border-[rgba(245,158,11,0.3)]`;
  return `${base} bg-[#f6f9fc] text-[#64748d] border-[#e5edf5]`;
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
        accent: "text-primary",
      },
      {
        name: "Sopralluoghi in corso",
        value: inProgress,
        icon: Users,
        description: "In fase di compilazione",
        accent: "text-[#9b6829]",
      },
      {
        name: "Sopralluoghi completati",
        value: completed,
        icon: FileCheck,
        description: "Pronti per generazione",
        accent: "text-[#108c3d]",
      },
      {
        name: "Bozze",
        value: drafts,
        icon: FileText,
        description: "Da completare",
        accent: "text-[#64748d]",
      },
      {
        name: "Scadenze imminenti",
        value: scadenze,
        icon: Clock,
        description: "DVR in scadenza entro 30 giorni",
        accent: "text-[#ba1a1a]",
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
    <div className="space-y-10">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="type-h1">Dashboard</h1>
          <p className="type-body mt-2">
            Panoramica dell&apos;attivit&agrave;
          </p>
        </div>
        {isAdmin && (
          <Link
            href="/aziende/new"
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-white transition-colors hover:bg-[#1b5594] shadow-stripe-ambient"
          >
            <Plus className="h-4 w-4" strokeWidth={2} />
            Aggiungi cliente
          </Link>
        )}
      </div>

      {loading ? (
        <p className="type-body">Caricamento...</p>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            {stats.map((stat) => (
              <div
                key={stat.name}
                className="group rounded-md border border-[#e5edf5] bg-white p-5 shadow-stripe-ambient transition-[box-shadow,transform] duration-200 hover:shadow-stripe-elevated hover:-translate-y-0.5"
              >
                <div className="mb-5 flex items-start justify-between">
                  <span className="type-eyebrow">{stat.name}</span>
                  <stat.icon
                    className={`h-4 w-4 ${stat.accent}`}
                    strokeWidth={1.75}
                  />
                </div>
                <div className="type-numeral">{stat.value}</div>
                <p className="type-caption mt-2">{stat.description}</p>
              </div>
            ))}
          </div>

          {/* VDT health-surveillance alerts (US-3.5). Self-hides when
              there's nothing to flag — no empty-state clutter. */}
          <SurveillanceAlerts />

          <div className="rounded-md border border-[#e5edf5] bg-white p-6 shadow-stripe-ambient">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="type-h2">Aziende Clienti</h2>
            </div>
            <div className="relative mb-5">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#64748d]" />
              <input
                placeholder="Cerca per ragione sociale, partita IVA, comune..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-md border border-[#e5edf5] bg-white px-10 py-2.5 text-sm text-[#061b31] placeholder:text-[#64748d] outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div>
              {sortedAndFiltered.length === 0 ? (
                <p className="py-8 text-center type-body">
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
                          <TableCell className="tnum text-[#64748d]">
                            {azienda.codice_ateco || "-"}
                          </TableCell>
                          <TableCell className="text-[#64748d]">
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
                          <TableCell className="tnum text-[#64748d]">
                            {formatDate(azienda.updated_at)}
                          </TableCell>
                          <TableCell>
                            {azienda.data_scadenza_dvr ? (
                              <Badge className={scadenzaChipClass(days)}>
                                {formatDate(azienda.data_scadenza_dvr)}
                              </Badge>
                            ) : (
                              <span className="text-[#64748d]">-</span>
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
