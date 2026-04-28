"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  MmcForm,
  type MmcFormValues,
  type MmcResult,
} from "@/components/assessments/mmc/mmc-form";
import type { Azienda } from "@/types";

// ---------------------------------------------------------------------------

export default function MmcAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeMessage, setFinalizeMessage] = useState<string | null>(null);
  const [latestResult, setLatestResult] = useState<MmcResult | null>(null);

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

  const pageSubtitle = useMemo(() => {
    if (loadError) return `Azienda ${aziendaId} (metadati non disponibili)`;
    if (azienda) return azienda.ragione_sociale ?? `Azienda ${aziendaId}`;
    return "Caricamento in corso...";
  }, [azienda, aziendaId, loadError]);

  const handleFinalize = async (values: MmcFormValues, result: MmcResult) => {
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

      const worst = result.worst;
      if (!worst || worst.plr <= 0) {
        throw new Error(
          "Parametri incompleti o fuori soglia. Correggi i sollevamenti prima di salvare.",
        );
      }

      const body = {
        peso_sollevato: values.lifts[0]?.peso_reale ?? 0,
        cp: result.cp,
        fattore_a: worst.a,
        fattore_b: worst.b,
        fattore_c: worst.c,
        fattore_d: worst.d,
        fattore_e: worst.e,
        fattore_f: worst.f,
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
        `Valutazione salvata: PLR ${data.plr.toFixed(2)} kg · IR ${data.ir.toFixed(
          2,
        )} · zona ${data.livello} · ${values.lifts.length} sollevamento/i registrato/i.`,
      );
    } catch (err) {
      setFinalizeMessage(
        err instanceof Error
          ? `Errore salvataggio: ${err.message}`
          : "Errore salvataggio sconosciuto",
      );
    } finally {
      setFinalizing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
            <Badge variant="secondary">Allegato Rischio MMC</Badge>
            <span>D.Lgs. 81/2008 · NIOSH ISO 11228-1</span>
          </div>
          <h1 className="mt-2 type-h1">
            Valutazione Movimentazione Manuale dei Carichi
          </h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
      </div>

      {finalizeMessage && (
        <div
          className={cn(
            "rounded-md border px-4 py-3 text-sm",
            finalizeMessage.startsWith("Errore")
              ? "border-rose-300 bg-rose-100 text-rose-900"
              : "border-emerald-300 bg-emerald-100 text-emerald-900",
          )}
        >
          {finalizeMessage}
        </div>
      )}

      <MmcForm
        aziendaId={aziendaId}
        finalizing={finalizing}
        onFinalize={handleFinalize}
        onResult={setLatestResult}
      />

      {latestResult?.perLift.length ? (
        <p className="text-[11px] text-muted-foreground">
          {latestResult.perLift.length} sollevamento/i calcolato/i. Salva la
          valutazione per archiviarla nel DVR.
        </p>
      ) : null}
    </div>
  );
}
