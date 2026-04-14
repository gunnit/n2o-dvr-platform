"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  IncendioForm,
  computeFireRisk,
  type FireLivello,
  type FireResult,
} from "@/components/assessments/incendio-form";
import type { Azienda } from "@/types";

// Italian action text per livello (mirrors backend/app/api/v1/calculations.py::_FIRE_AZIONE).
const AZIONE_PER_LIVELLO: Record<FireLivello, string> = {
  Basso:
    "Rischio incendio basso: mantenere in efficienza le misure di prevenzione e protezione esistenti, verificare periodicamente estintori, vie di esodo e segnaletica, e aggiornare la formazione antincendio del personale.",
  Medio:
    "Rischio incendio medio: adottare misure aggiuntive di prevenzione e protezione (rilevazione automatica, compartimentazione, controllo sorgenti di innesco), designare e formare gli addetti alla gestione dell'emergenza e aggiornare il piano di emergenza ed evacuazione.",
  Alto:
    "Rischio incendio alto: attivare immediatamente misure straordinarie di prevenzione e protezione, coinvolgere il professionista antincendio, presentare SCIA ai VV.F. ove dovuta, adottare impianti di rilevazione e spegnimento automatici e garantire formazione di livello 3 agli addetti all'emergenza.",
};

const BAND_CLASS: Record<FireLivello, string> = {
  Basso:
    "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30 dark:text-emerald-400",
  Medio:
    "bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-300",
  Alto: "bg-rose-500/15 text-rose-700 ring-rose-500/30 dark:text-rose-400",
};

// ---------------------------------------------------------------------------

export default function IncendioAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [result, setResult] = useState<FireResult>(() => computeFireRisk({}));
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeMessage, setFinalizeMessage] = useState<string | null>(null);

  // Load azienda metadata (best-effort — mirrors stress page pattern).
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

  const finalize = useCallback(async () => {
    if (!result.complete || result.inf === undefined || result.si === undefined || result.pi === undefined) {
      return;
    }
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

      const res = await fetch(`${apiUrl}/api/v1/calculate/fire-risk`, {
        method: "POST",
        headers: token
          ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
          : { "Content-Type": "application/json" },
        body: JSON.stringify({
          inf: result.inf,
          si: result.si,
          pi: result.pi,
        }),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();

      // Confirm backend matches local computation
      if (data.totale !== result.totale || data.livello !== result.livello) {
        throw new Error(
          `Discrepanza: locale ${result.totale}/${result.livello}, server ${data.totale}/${data.livello}`,
        );
      }

      setFinalizeMessage(
        `Valutazione archiviata: totale ${data.totale} — livello ${data.livello}.`,
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
  }, [result]);

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
            <Badge variant="secondary">Allegato Rischio Incendio</Badge>
            <span>D.Lgs. 81/2008 · D.M. 03/09/2021</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">
            Valutazione Rischio Incendio
          </h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
      </div>

      <IncendioForm aziendaId={aziendaId} onResultChange={setResult} />

      {/* Recommended action */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-sm">Azione consigliata</CardTitle>
              <CardDescription className="text-xs">
                {result.livello
                  ? AZIONE_PER_LIVELLO[result.livello]
                  : "Completa i tre parametri per ottenere l'azione consigliata."}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide text-muted-foreground">
                livello attuale
              </span>
              {result.livello ? (
                <span
                  className={cn(
                    "inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium ring-1",
                    BAND_CLASS[result.livello],
                  )}
                >
                  {result.livello}
                </span>
              ) : (
                <Badge variant="secondary">—</Badge>
              )}
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Finalize */}
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div>
            <p className="text-sm font-medium">Conferma valutazione</p>
            <p className="text-xs text-muted-foreground">
              {result.complete
                ? "Tutti i parametri compilati. La valutazione sarà archiviata nel fascicolo cliente."
                : "Completa i tre parametri (INF, SI, PI) per confermare la valutazione."}
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
              disabled={!result.complete || finalizing}
              onClick={finalize}
            >
              {finalizing ? "Conferma in corso…" : "Conferma valutazione"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <p className="text-[11px] text-muted-foreground">
        Bozza salvata in locale (chiave: <code>incendio-draft-{aziendaId}</code>)
      </p>
    </div>
  );
}
