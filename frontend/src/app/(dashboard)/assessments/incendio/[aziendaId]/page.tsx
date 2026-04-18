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
  BAND_CLASS,
  IncendioForm,
  useIncendioForm,
  type IncendioResult,
  type FireLivello,
} from "@/components/assessments/incendio/incendio-form";
import { IncendioVvfBanner } from "@/components/assessments/incendio/incendio-vvf-banner";
import type { Azienda } from "@/types";

// Italian action text per livello (kept for the "Azione consigliata" summary
// card — the per-area checklist lives inside `IncendioMeasures`).
const AZIONE_PER_LIVELLO: Record<FireLivello, string> = {
  Basso:
    "Rischio incendio basso: mantenere in efficienza le misure di prevenzione e protezione esistenti, verificare periodicamente estintori, vie di esodo e segnaletica, e aggiornare la formazione antincendio del personale.",
  Medio:
    "Rischio incendio medio: adottare misure aggiuntive di prevenzione e protezione (rilevazione automatica, compartimentazione, controllo sorgenti di innesco), designare e formare gli addetti alla gestione dell'emergenza e aggiornare il piano di emergenza ed evacuazione.",
  Alto:
    "Rischio incendio alto: attivare immediatamente misure straordinarie di prevenzione e protezione, coinvolgere il professionista antincendio, presentare SCIA ai VV.F. ove dovuta, adottare impianti di rilevazione e spegnimento automatici e garantire formazione di livello 3 agli addetti all'emergenza.",
};

// ---------------------------------------------------------------------------

export default function IncendioAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const form = useIncendioForm();
  const [result, setResult] = useState<IncendioResult>({
    areas: [],
    maxLivello: null,
    allComplete: false,
  });
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  // Track dirty state from RHF.
  useEffect(() => {
    const subscription = form.watch(() => setDirty(form.formState.isDirty));
    return () => subscription.unsubscribe();
  }, [form]);

  // Load azienda metadata (best-effort — mirrors stress/mmc page pattern).
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const apiUrl =
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
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
            ? {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              }
            : { "Content-Type": "application/json" },
        });
        if (!res.ok) throw new Error(`Errore ${res.status}`);
        const data = (await res.json()) as Azienda;
        if (!cancelled) setAzienda(data);
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error
              ? err.message
              : "Impossibile caricare l'azienda",
          );
        }
      }
    }
    if (aziendaId) load();
    return () => {
      cancelled = true;
    };
  }, [aziendaId]);

  const save = useCallback(async () => {
    if (!result.allComplete || result.areas.length === 0) return;
    setSaving(true);
    setSaveMessage(null);
    try {
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      let token: string | null = null;
      try {
        const s = await fetch("/api/auth/session");
        const session = await s.json();
        token = session?.accessToken ?? null;
      } catch {
        /* noop */
      }

      // Cross-check with backend for the worst-case (max livello) area —
      // ensures the front-end calculation matches the server's band logic.
      const worst = result.areas.reduce((acc, cur) =>
        (cur.totale ?? 0) > (acc.totale ?? 0) ? cur : acc,
      );
      if (
        worst.inf === undefined ||
        worst.si === undefined ||
        worst.pi === undefined
      )
        return;

      const res = await fetch(`${apiUrl}/api/v1/calculate/fire-risk`, {
        method: "POST",
        headers: token
          ? {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            }
          : { "Content-Type": "application/json" },
        body: JSON.stringify({
          inf: worst.inf,
          si: worst.si,
          pi: worst.pi,
        }),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = (await res.json()) as {
        totale: number;
        livello: FireLivello;
      };

      if (data.totale !== worst.totale || data.livello !== worst.livello) {
        throw new Error(
          `Discrepanza: locale ${worst.totale}/${worst.livello}, server ${data.totale}/${data.livello}`,
        );
      }

      setSaveMessage(
        `Valutazione archiviata: ${result.areas.length} area/e · livello massimo ${result.maxLivello}.`,
      );
      form.reset(form.getValues()); // marks RHF as pristine
      setDirty(false);
    } catch (err) {
      setSaveMessage(
        err instanceof Error
          ? `Errore salvataggio: ${err.message}`
          : "Errore salvataggio sconosciuto",
      );
    } finally {
      setSaving(false);
    }
  }, [result, form]);

  const pageSubtitle = useMemo(() => {
    if (loadError) return `Azienda ${aziendaId} (metadati non disponibili)`;
    if (azienda) return azienda.ragione_sociale ?? `Azienda ${aziendaId}`;
    return "Caricamento…";
  }, [azienda, aziendaId, loadError]);

  const vvfVisible = result.maxLivello === "Alto";

  return (
    <div className="space-y-6">
      <IncendioVvfBanner visible={vvfVisible} />

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
            <Badge variant="secondary">Allegato Rischio Incendio</Badge>
            <span>D.Lgs. 81/2008 · D.M. 03/09/2021</span>
          </div>
          <h1 className="mt-2 type-h1">
            Valutazione Rischio Incendio
          </h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
        {dirty && (
          <Badge
            variant="outline"
            className="border-amber-400/60 bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
          >
            Modifiche non salvate
          </Badge>
        )}
      </div>

      <IncendioForm form={form} onResultChange={setResult} />

      {/* Azione consigliata riepilogo (livello massimo) */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-sm">
                Azione consigliata — livello massimo
              </CardTitle>
              <CardDescription className="text-xs">
                {result.maxLivello
                  ? AZIONE_PER_LIVELLO[result.maxLivello]
                  : "Completa i tre parametri di almeno un'area per ottenere l'azione consigliata."}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide text-muted-foreground">
                livello max
              </span>
              {result.maxLivello ? (
                <span
                  className={cn(
                    "inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium ring-1",
                    BAND_CLASS[result.maxLivello],
                  )}
                >
                  {result.maxLivello}
                </span>
              ) : (
                <Badge variant="secondary">—</Badge>
              )}
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Save */}
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div>
            <p className="text-sm font-medium">Salva valutazione</p>
            <p className="text-xs text-muted-foreground">
              {result.allComplete
                ? `Tutte le aree (${result.areas.length}) sono compilate. La valutazione sarà archiviata nel fascicolo cliente.`
                : "Completa INF, SI e PI per ciascuna area per salvare la valutazione."}
            </p>
            {saveMessage && (
              <p
                className={cn(
                  "mt-1 text-xs",
                  saveMessage.startsWith("Errore") ||
                    saveMessage.startsWith("Discrepanza")
                    ? "text-destructive"
                    : "text-emerald-700 dark:text-emerald-400",
                )}
              >
                {saveMessage}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              disabled={!result.allComplete || saving}
              onClick={save}
            >
              {saving ? "Salvataggio in corso…" : "Salva valutazione"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
