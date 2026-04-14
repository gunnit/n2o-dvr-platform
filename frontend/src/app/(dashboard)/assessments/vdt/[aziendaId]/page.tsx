"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  VdtForm,
  summarize,
  type VdtSummary,
} from "@/components/assessments/vdt-form";
import type { Azienda } from "@/types";

// ---------------------------------------------------------------------------

const EMPTY_SUMMARY: VdtSummary = summarize([]);

export default function VdtAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [summary, setSummary] = useState<VdtSummary>(EMPTY_SUMMARY);
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeMessage, setFinalizeMessage] = useState<string | null>(null);

  // Load azienda metadata (best-effort — mirrors incendio/mmc pattern).
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        let token: string | null = null;
        try {
          const s = await fetch("/api/auth/session");
          const session = await s.json();
          token = session?.accessToken ?? null;
        } catch {
          /* noop */
        }
        const res = await fetch(`${apiUrl}/api/v1/aziende/${aziendaId}`, {
          headers: token
            ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
            : { "Content-Type": "application/json" },
        });
        if (!res.ok) throw new Error(`Errore ${res.status}`);
        const data = (await res.json()) as Azienda;
        if (!cancelled) setAzienda(data);
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error ? err.message : "Impossibile caricare l'azienda",
          );
        }
      }
    }
    if (aziendaId) load();
    return () => {
      cancelled = true;
    };
  }, [aziendaId]);

  const allClassified =
    summary.total > 0 && summary.incompleti === 0;

  const finalize = useCallback(async () => {
    setFinalizing(true);
    setFinalizeMessage(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      let token: string | null = null;
      try {
        const s = await fetch("/api/auth/session");
        const session = await s.json();
        token = session?.accessToken ?? null;
      } catch {
        /* noop */
      }

      const body = {
        workers: summary.workers
          .filter((w) => w.ore_settimanali != null)
          .map((w) => ({
            id: w.id,
            nome: w.nome || null,
            ore_settimanali: w.ore_settimanali ?? 0,
          })),
      };

      const res = await fetch(`${apiUrl}/api/v1/calculate/vdt`, {
        method: "POST",
        headers: token
          ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
          : { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = (await res.json()) as {
        total: number;
        esposti: number;
        non_esposti: number;
      };

      // Confirm backend matches local computation
      if (
        data.total !== summary.total ||
        data.esposti !== summary.esposti ||
        data.non_esposti !== summary.non_esposti
      ) {
        throw new Error(
          `Discrepanza: locale ${summary.esposti}/${summary.total}, server ${data.esposti}/${data.total}`,
        );
      }

      setFinalizeMessage(
        `Valutazione archiviata: ${data.esposti} esposti / ${data.total} lavoratori.`,
      );
    } catch (err) {
      setFinalizeMessage(
        err instanceof Error
          ? `Errore conferma: ${err.message}`
          : "Errore conferma sconosciuto",
      );
    } finally {
      setFinalizing(false);
    }
  }, [summary]);

  const pageSubtitle = useMemo(() => {
    if (loadError) return `Azienda ${aziendaId} (metadati non disponibili)`;
    if (azienda) return azienda.ragione_sociale ?? `Azienda ${aziendaId}`;
    return "Caricamento…";
  }, [azienda, aziendaId, loadError]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
            <Badge variant="secondary">Allegato Rischio VDT</Badge>
            <span>D.Lgs. 81/2008 Titolo VII · ISO 9241</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">
            Valutazione Esposizione Videoterminali
          </h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
      </div>

      <VdtForm aziendaId={aziendaId} onSummaryChange={setSummary} />

      {/* Finalize */}
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div>
            <p className="text-sm font-medium">Conferma valutazione</p>
            <p className="text-xs text-muted-foreground">
              {summary.total === 0
                ? "Aggiungi almeno un lavoratore per confermare."
                : allClassified
                ? `Tutti i ${summary.total} lavoratori classificati. La valutazione sarà archiviata nel fascicolo cliente.`
                : `Completa le ore per ${summary.incompleti} lavoratori.`}
            </p>
            {finalizeMessage && (
              <p
                className={cn(
                  "mt-1 text-xs",
                  finalizeMessage.startsWith("Errore") ||
                    finalizeMessage.startsWith("Discrepanza")
                    ? "text-destructive"
                    : "text-emerald-700 dark:text-emerald-400",
                )}
              >
                {finalizeMessage}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              disabled={!allClassified || finalizing}
              onClick={finalize}
            >
              {finalizing ? "Conferma in corso…" : "Conferma valutazione"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <p className="text-[11px] text-muted-foreground">
        Bozza salvata in locale (chiave: <code>vdt-draft-{aziendaId}</code>)
      </p>
    </div>
  );
}
