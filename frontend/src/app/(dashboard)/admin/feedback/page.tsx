"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  AlertCircle,
  Bug,
  ExternalLink,
  Lightbulb,
  Loader2,
  MessageCircle,
  RefreshCw,
} from "lucide-react";
import { toast } from "sonner";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import { cn } from "@/lib/utils";

type FeedbackType = "bug" | "idea" | "observation";
type FeedbackStatus = "nuovo" | "in_revisione" | "risolto" | "non_fara";

interface FeedbackRow {
  id: string;
  type: FeedbackType;
  description: string;
  page_url: string | null;
  route: string | null;
  user_agent: string | null;
  status: FeedbackStatus;
  github_issue_number: number | null;
  github_issue_url: string | null;
  user_id: string | null;
  user_label: string | null;
  created_at: string;
  updated_at: string;
}

const TYPE_META: Record<
  FeedbackType,
  { label: string; icon: typeof Bug; tone: string }
> = {
  bug: { label: "Bug", icon: Bug, tone: "bg-rose-100 text-rose-700" },
  idea: { label: "Idea", icon: Lightbulb, tone: "bg-amber-100 text-amber-700" },
  observation: {
    label: "Osservazione",
    icon: MessageCircle,
    tone: "bg-sky-100 text-sky-700",
  },
};

const STATUS_OPTIONS: { value: FeedbackStatus; label: string; tone: string }[] =
  [
    {
      value: "nuovo",
      label: "Nuovo",
      tone: "bg-violet-100 text-violet-700",
    },
    {
      value: "in_revisione",
      label: "In revisione",
      tone: "bg-sky-100 text-sky-700",
    },
    {
      value: "risolto",
      label: "Risolto",
      tone: "bg-emerald-100 text-emerald-700",
    },
    {
      value: "non_fara",
      label: "Non farà",
      tone: "bg-slate-100 text-slate-700",
    },
  ];

const STATUS_LABEL: Record<FeedbackStatus, string> = Object.fromEntries(
  STATUS_OPTIONS.map((s) => [s.value, s.label]),
) as Record<FeedbackStatus, string>;

type StatusFilter = FeedbackStatus | "all";

const FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "Tutti" },
  { value: "nuovo", label: "Nuovi" },
  { value: "in_revisione", label: "In revisione" },
  { value: "risolto", label: "Risolti" },
  { value: "non_fara", label: "Non farà" },
];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("it-IT", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function TypeBadge({ type }: { type: FeedbackType }) {
  const meta = TYPE_META[type];
  const Icon = meta.icon;
  return (
    <Badge className={cn(meta.tone, "gap-1 hover:" + meta.tone)}>
      <Icon className="h-3 w-3" strokeWidth={2} />
      {meta.label}
    </Badge>
  );
}

export default function AdminFeedbackPage() {
  const { apiFetch } = useApi();
  const { data: session, status: sessionStatus } = useSession();
  const router = useRouter();

  const [rows, setRows] = useState<FeedbackRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [savingId, setSavingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    if (sessionStatus !== "authenticated") return;
    const role = (session?.user as { role?: string } | undefined)?.role;
    if (role !== "admin") {
      router.replace("/dashboard");
    }
  }, [session, sessionStatus, router]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<FeedbackRow[]>("/api/v1/feedback");
      setRows(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Caricamento feedback non riuscito.",
      );
    } finally {
      setLoading(false);
    }
  }, [apiFetch]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(
    () => (filter === "all" ? rows : rows.filter((r) => r.status === filter)),
    [rows, filter],
  );

  const counts = useMemo(() => {
    const c: Record<StatusFilter, number> = {
      all: rows.length,
      nuovo: 0,
      in_revisione: 0,
      risolto: 0,
      non_fara: 0,
    };
    for (const r of rows) c[r.status]++;
    return c;
  }, [rows]);

  async function changeStatus(row: FeedbackRow, status: FeedbackStatus) {
    if (row.status === status) return;
    setSavingId(row.id);
    // Optimistic update
    const prev = rows;
    setRows(rows.map((r) => (r.id === row.id ? { ...r, status } : r)));
    try {
      await apiFetch(`/api/v1/feedback/${row.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
    } catch (err) {
      setRows(prev);
      toast.error(
        err instanceof Error ? err.message : "Aggiornamento non riuscito.",
      );
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="type-h1">Feedback</h1>
          <p className="text-muted-foreground">
            Segnalazioni, idee e osservazioni inviate dagli utenti.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          {loading ? (
            <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="mr-1 h-3.5 w-3.5" />
          )}
          Aggiorna
        </Button>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => {
          const active = filter === f.value;
          return (
            <button
              key={f.value}
              type="button"
              onClick={() => setFilter(f.value)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                active
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-[#e5edf5] bg-white text-[#334155] hover:bg-slate-50",
              )}
            >
              {f.label}
              <span
                className={cn(
                  "ml-1.5 rounded-full px-1.5 py-0.5 text-[10px]",
                  active ? "bg-white/20" : "bg-slate-100 text-slate-600",
                )}
              >
                {counts[f.value]}
              </span>
            </button>
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Segnalazioni</CardTitle>
          <CardDescription>
            Ordinate per data di invio. Cambia lo stato per tracciare il
            triage.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filtered.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              {loading ? "Caricamento..." : "Nessuna segnalazione."}
            </p>
          ) : (
            <Table className="table-fixed">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[110px]">Tipo</TableHead>
                  <TableHead>Descrizione</TableHead>
                  <TableHead className="w-[150px]">Utente</TableHead>
                  <TableHead className="w-[160px]">Pagina</TableHead>
                  <TableHead className="w-[80px]">Issue</TableHead>
                  <TableHead className="w-[100px]">Data</TableHead>
                  <TableHead className="w-[160px]">Stato</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((row) => {
                  const expanded = expandedId === row.id;
                  return (
                    <TableRow key={row.id} className="align-top">
                      <TableCell className="py-3">
                        <TypeBadge type={row.type} />
                      </TableCell>
                      <TableCell className="py-3">
                        <p
                          className={cn(
                            "text-sm text-[#0f172a]",
                            expanded ? "whitespace-pre-wrap" : "line-clamp-2",
                          )}
                          title={row.description}
                        >
                          {row.description}
                        </p>
                        {(row.description.length > 120 || row.user_agent) && (
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedId(expanded ? null : row.id)
                            }
                            className="mt-1 text-[11px] font-medium text-primary hover:underline"
                          >
                            {expanded ? "Nascondi dettagli" : "Dettagli"}
                          </button>
                        )}
                        {expanded && row.user_agent && (
                          <p
                            className="mt-2 break-all rounded bg-slate-50 px-2 py-1 text-[11px] text-muted-foreground"
                            title={row.user_agent}
                          >
                            <span className="font-medium text-slate-600">
                              UA:
                            </span>{" "}
                            {row.user_agent}
                          </p>
                        )}
                      </TableCell>
                      <TableCell className="truncate py-3 text-sm">
                        {row.user_label ?? (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="py-3 text-sm">
                        {row.route ? (
                          <code
                            className="block truncate rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-700"
                            title={row.route}
                          >
                            {row.route}
                          </code>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                        {row.page_url && (
                          <a
                            href={row.page_url}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-1 block truncate text-[11px] text-primary hover:underline"
                            title={row.page_url}
                          >
                            apri pagina
                          </a>
                        )}
                      </TableCell>
                      <TableCell className="py-3 text-sm">
                        {row.github_issue_url && row.github_issue_number ? (
                          <a
                            href={row.github_issue_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-700 hover:bg-slate-200"
                            title="Apri issue su GitHub"
                          >
                            <ExternalLink className="h-3 w-3" strokeWidth={2} />#
                            {row.github_issue_number}
                          </a>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="py-3 text-sm text-muted-foreground">
                        {formatDate(row.created_at)}
                      </TableCell>
                      <TableCell className="py-3">
                        <div className="flex items-center gap-1.5">
                          <select
                            value={row.status}
                            disabled={savingId === row.id}
                            onChange={(e) =>
                              changeStatus(
                                row,
                                e.target.value as FeedbackStatus,
                              )
                            }
                            className="h-8 w-full min-w-0 rounded-md border border-[#e5edf5] bg-white px-2 text-xs text-[#061b31] outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
                            aria-label={`Stato segnalazione: ${STATUS_LABEL[row.status]}`}
                          >
                            {STATUS_OPTIONS.map((s) => (
                              <option key={s.value} value={s.value}>
                                {s.label}
                              </option>
                            ))}
                          </select>
                          {savingId === row.id && (
                            <Loader2 className="h-3 w-3 shrink-0 animate-spin text-muted-foreground" />
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
