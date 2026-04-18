"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  AlertCircle,
  Loader2,
  RefreshCw,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";

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

/**
 * Admin AI feedback panel (US-5.3 second half).
 *
 * Surfaces where AI suggestions are getting rejected most so the team can
 * decide whether the prompts / models need adjusting. Two sections:
 *
 *  1. Per-entity-type KPI cards — total thumbs_down / thumbs_up grouped by
 *     where the signal originated (misura_suggerita, company_description,
 *     sds_extraction, …). Sorted by rejection count desc.
 *  2. Recent rejections table — last 50 thumbs_down events with azienda +
 *     user labels and a context preview so the admin can scan reasons
 *     without expanding individual rows. Toggle to flip to thumbs_up if
 *     the team wants to see what's working.
 *
 * Admin-only: the backend already returns 403 for non-admins; this page
 * also bounces non-admin sessions to /dashboard for UX symmetry with the
 * backups panel (US-5.4).
 */

interface SummaryRow {
  entity_type: string;
  thumbs_down_count: number;
  thumbs_up_count: number;
}

interface Summary {
  rows: SummaryRow[];
  total_thumbs_down: number;
  total_thumbs_up: number;
}

interface RecentRow {
  id: string;
  signal: "thumbs_down" | "thumbs_up";
  entity_type: string;
  entity_id: string | null;
  reason: string | null;
  azienda_id: string | null;
  azienda_label: string | null;
  user_id: string | null;
  user_label: string | null;
  context_preview: string | null;
  created_at: string;
}

// Friendlier Italian labels for the entity_type values the backend emits.
// Unknown types fall through to the raw key — better an admin sees
// "sds_extraction" than nothing when a new surface is added.
const ENTITY_TYPE_LABEL: Record<string, string> = {
  misura_suggerita: "Misura suggerita",
  company_description: "Descrizione azienda",
  sds_extraction: "Estrazione SDS",
};

function formatEntityType(t: string): string {
  return ENTITY_TYPE_LABEL[t] ?? t;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("it-IT", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AdminAIFeedbackPage() {
  const { apiFetch } = useApi();
  const { data: session, status: sessionStatus } = useSession();
  const router = useRouter();

  const [summary, setSummary] = useState<Summary | null>(null);
  const [recent, setRecent] = useState<RecentRow[]>([]);
  const [signalFilter, setSignalFilter] = useState<"thumbs_down" | "thumbs_up">(
    "thumbs_down",
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Bounce non-admins back to the dashboard. Backend will 403 anyway —
  // mirrors the backups panel pattern (US-5.4) for UX symmetry.
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
      const [sum, rec] = await Promise.all([
        apiFetch<Summary>("/api/v1/ai-feedback/admin/summary"),
        apiFetch<RecentRow[]>(
          `/api/v1/ai-feedback/admin/recent?signal=${signalFilter}&limit=50`,
        ),
      ]);
      setSummary(sum);
      setRecent(rec);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Caricamento feedback non riuscito.",
      );
    } finally {
      setLoading(false);
    }
  }, [apiFetch, signalFilter]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="type-h1">
            Feedback AI
          </h1>
          <p className="text-muted-foreground">
            Visibilità sui segnali di accettazione e rifiuto raccolti dalle
            superfici AI (misure suggerite, descrizioni azienda, estrazione
            SDS). Usa questi dati per capire dove i suggerimenti vanno
            migliorati.
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

      {/* Top-line totals */}
      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <ThumbsDown className="h-4 w-4 text-rose-600" />
              Rifiuti totali
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="type-numeral">
              {summary?.total_thumbs_down ?? "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              Suggerimenti AI scartati con &quot;Rifiuta&quot;.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <ThumbsUp className="h-4 w-4 text-emerald-600" />
              Accettazioni totali
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="type-numeral">
              {summary?.total_thumbs_up ?? "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              Suggerimenti AI accettati con segnale esplicito.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Sparkles className="h-4 w-4 text-violet-600" />
              Tipi di superficie
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="type-numeral">
              {summary?.rows.length ?? "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              Superfici AI distinte che hanno raccolto feedback.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Per-entity-type breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Rifiuti per superficie AI</CardTitle>
          <CardDescription>
            Ordinati per numero di rifiuti — le superfici in cima sono quelle
            su cui conviene rivedere prompt o modello.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!summary || summary.rows.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Nessun feedback ancora registrato. Le righe appariranno appena
              gli operatori cliccano Rifiuta o Accetta su un suggerimento AI.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Superficie</TableHead>
                  <TableHead className="text-right">Rifiuti</TableHead>
                  <TableHead className="text-right">Accettazioni</TableHead>
                  <TableHead className="text-right">Rapporto</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.rows.map((row) => {
                  const total = row.thumbs_down_count + row.thumbs_up_count;
                  const ratio =
                    total === 0
                      ? "—"
                      : `${Math.round(
                          (row.thumbs_down_count / total) * 100,
                        )}% rifiutato`;
                  return (
                    <TableRow key={row.entity_type}>
                      <TableCell className="font-medium">
                        {formatEntityType(row.entity_type)}
                        <span className="ml-2 text-xs font-mono text-muted-foreground">
                          {row.entity_type}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge className="bg-rose-100 text-rose-700 hover:bg-rose-100">
                          {row.thumbs_down_count}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
                          {row.thumbs_up_count}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right text-sm text-muted-foreground">
                        {ratio}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Recent feedback */}
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>
                {signalFilter === "thumbs_down"
                  ? "Ultimi rifiuti"
                  : "Ultime accettazioni"}
              </CardTitle>
              <CardDescription>
                Ultimi 50 segnali con azienda, operatore e anteprima del
                contenuto coinvolto.
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant={signalFilter === "thumbs_down" ? "default" : "outline"}
                onClick={() => setSignalFilter("thumbs_down")}
              >
                <ThumbsDown className="mr-1 h-3.5 w-3.5" />
                Rifiuti
              </Button>
              <Button
                size="sm"
                variant={signalFilter === "thumbs_up" ? "default" : "outline"}
                onClick={() => setSignalFilter("thumbs_up")}
              >
                <ThumbsUp className="mr-1 h-3.5 w-3.5" />
                Accettazioni
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {recent.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              {loading
                ? "Caricamento..."
                : signalFilter === "thumbs_down"
                  ? "Nessun rifiuto registrato."
                  : "Nessuna accettazione registrata."}
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[120px]">Quando</TableHead>
                  <TableHead className="w-[140px]">Superficie</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Operatore</TableHead>
                  <TableHead>Contenuto</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recent.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(row.created_at)}
                    </TableCell>
                    <TableCell className="text-xs">
                      {formatEntityType(row.entity_type)}
                    </TableCell>
                    <TableCell className="text-sm">
                      {row.azienda_label ?? (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm">
                      {row.user_label ?? (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="max-w-[420px]">
                      {row.context_preview ? (
                        <p className="text-sm leading-snug">
                          {row.context_preview}
                        </p>
                      ) : row.reason ? (
                        <p className="text-sm leading-snug">{row.reason}</p>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          Nessuna anteprima
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
