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
  MmcForm,
  computeMmc,
  DEFAULT_INPUTS,
  type MmcInputs,
  type MmcResult,
} from "@/components/assessments/mmc/mmc-form";
import type { Azienda } from "@/types";

// ---------------------------------------------------------------------------

export default function MmcAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [result, setResult] = useState<MmcResult>(() => computeMmc(DEFAULT_INPUTS));
  const [inputs, setInputs] = useState<MmcInputs>(DEFAULT_INPUTS);
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeMessage, setFinalizeMessage] = useState<string | null>(null);

  // Load azienda metadata (best-effort — if auth not set up, we fall back to
  // the raw id so the UI still works for testing).
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

  const allAnswered = result.unanswered.length === 0;

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

      // Guard: backend requires every factor > 0 (strict gt validator). If any
      // input produces a zero multiplier the server will reject with 422, so
      // surface that immediately rather than sending a bad payload.
      const zeroFactors: string[] = [];
      if (result.a <= 0) zeroFactors.push("A (altezza)");
      if (result.b <= 0) zeroFactors.push("B (dislocazione)");
      if (result.c <= 0) zeroFactors.push("C (distanza)");
      if (result.d <= 0) zeroFactors.push("D (angolo)");
      if (result.e <= 0) zeroFactors.push("E (presa)");
      if (result.f <= 0) zeroFactors.push("F (frequenza)");
      if (zeroFactors.length > 0) {
        throw new Error(
          `Fattore fuori soglia: ${zeroFactors.join(", ")}. Correggi i parametri prima di confermare.`,
        );
      }

      const body = {
        peso_sollevato: inputs.peso_sollevato ?? 0,
        cp: result.cp,
        fattore_a: result.a,
        fattore_b: result.b,
        fattore_c: result.c,
        fattore_d: result.d,
        fattore_e: result.e,
        fattore_f: result.f,
      };

      const res = await fetch(`${apiUrl}/api/v1/calculate/niosh`, {
        method: "POST",
        headers: token
          ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
          : { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = (await res.json()) as { plr: number; ir: number; livello: string };
      setFinalizeMessage(
        `Valutazione confermata: PLR ${data.plr.toFixed(2)} kg · IR ${data.ir.toFixed(
          2,
        )} · zona ${data.livello}`,
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
  }, [aziendaId, inputs, result]);

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
            <Badge variant="secondary">Allegato Rischio MMC</Badge>
            <span>D.Lgs. 81/2008 · NIOSH ISO 11228-1</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">
            Valutazione Movimentazione Manuale dei Carichi
          </h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
      </div>

      <MmcForm
        aziendaId={aziendaId}
        onResultChange={setResult}
        onInputsChange={setInputs}
      />

      {/* Finalize */}
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div>
            <p className="text-sm font-medium">Conferma valutazione</p>
            <p className="text-xs text-muted-foreground">
              {allAnswered
                ? "Parametri completi. Il backend ricalcolerà PLR e IR per l'archiviazione."
                : `Mancano ${result.unanswered.length} parametri. Completa il modulo per confermare.`}
            </p>
            {finalizeMessage && (
              <p
                className={cn(
                  "mt-1 text-xs",
                  finalizeMessage.startsWith("Errore")
                    ? "text-destructive"
                    : "text-emerald-700 dark:text-emerald-400",
                )}
              >
                {finalizeMessage}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button disabled={!allAnswered || finalizing} onClick={finalize}>
              {finalizing ? "Conferma in corso…" : "Conferma valutazione"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <p className="text-[11px] text-muted-foreground">
        Bozza salvata in locale (chiave: <code>mmc-draft-{aziendaId}</code>)
      </p>
    </div>
  );
}
