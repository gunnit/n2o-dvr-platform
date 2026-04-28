"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Domain — mirrors backend/app/services/vdt_calculator.py.
// D.Lgs. 81/2008 Titolo VII: worker with >= 20h/week VDT use = ESPOSTO.
// ---------------------------------------------------------------------------

export const VDT_EXPOSURE_THRESHOLD_HOURS = 20;

export type Esposizione = "ESPOSTO" | "NON_ESPOSTO";

export interface VdtWorker {
  id: string;
  nome: string;
  ore_settimanali: number | null;
}

export interface VdtWorkerResult extends VdtWorker {
  esposizione: Esposizione | null; // null = ore not yet provided
  sorveglianza_sanitaria: boolean;
}

export interface VdtSummary {
  workers: VdtWorkerResult[];
  total: number;
  esposti: number;
  non_esposti: number;
  incompleti: number; // workers without ore_settimanali
}

export function classifyWorker(worker: VdtWorker): VdtWorkerResult {
  if (worker.ore_settimanali == null || isNaN(worker.ore_settimanali)) {
    return { ...worker, esposizione: null, sorveglianza_sanitaria: false };
  }
  const esposizione: Esposizione =
    worker.ore_settimanali >= VDT_EXPOSURE_THRESHOLD_HOURS
      ? "ESPOSTO"
      : "NON_ESPOSTO";
  return {
    ...worker,
    esposizione,
    sorveglianza_sanitaria: esposizione === "ESPOSTO",
  };
}

export function summarize(workers: VdtWorker[]): VdtSummary {
  const classified = workers.map(classifyWorker);
  let esposti = 0;
  let non_esposti = 0;
  let incompleti = 0;
  for (const w of classified) {
    if (w.esposizione === null) incompleti += 1;
    else if (w.esposizione === "ESPOSTO") esposti += 1;
    else non_esposti += 1;
  }
  return {
    workers: classified,
    total: classified.length,
    esposti,
    non_esposti,
    incompleti,
  };
}

// ---------------------------------------------------------------------------
// Utility — stable ids for workers on the client (client-only).
// ---------------------------------------------------------------------------

function makeId(): string {
  return `w_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface VdtFormProps {
  aziendaId: string;
  onSummaryChange?: (summary: VdtSummary) => void;
}

export function VdtForm({ aziendaId, onSummaryChange }: VdtFormProps) {
  const storageKey = `vdt-draft-${aziendaId}`;

  const [workers, setWorkers] = useState<VdtWorker[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Hydrate from localStorage
  useEffect(() => {
    try {
      const raw =
        typeof window !== "undefined"
          ? window.localStorage.getItem(storageKey)
          : null;
      if (raw) {
        const parsed = JSON.parse(raw) as VdtWorker[];
        if (Array.isArray(parsed)) {
          setWorkers(parsed);
        } else {
          setWorkers([]);
        }
      } else {
        setWorkers([]);
      }
    } catch {
      setWorkers([]);
    } finally {
      setHydrated(true);
    }
  }, [storageKey]);

  // Persist on change (after hydration so we don't overwrite a saved draft
  // with the empty initial state).
  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(workers));
    } catch {
      // ignore quota / privacy mode errors
    }
  }, [workers, storageKey, hydrated]);

  const summary = useMemo(() => summarize(workers), [workers]);

  useEffect(() => {
    onSummaryChange?.(summary);
  }, [summary, onSummaryChange]);

  const addWorker = useCallback(() => {
    setWorkers((prev) => [
      ...prev,
      { id: makeId(), nome: "", ore_settimanali: null },
    ]);
  }, []);

  const removeWorker = useCallback((id: string) => {
    setWorkers((prev) => prev.filter((w) => w.id !== id));
  }, []);

  const updateWorker = useCallback(
    <K extends keyof VdtWorker>(id: string, key: K, value: VdtWorker[K]) => {
      setWorkers((prev) =>
        prev.map((w) => (w.id === id ? { ...w, [key]: value } : w)),
      );
    },
    [],
  );

  const resetDraft = useCallback(() => {
    setWorkers([]);
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
  }, [storageKey]);

  const hasEsposti = summary.esposti > 0;

  return (
    <div className="space-y-6">
      {/* Sticky summary */}
      <Card className="sticky top-4 z-10 shadow-sm">
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">Esposizione VDT</CardTitle>
              <CardDescription className="text-xs">
                Soglia D.Lgs. 81/2008 · uso VDT ≥ 20 ore/settimana ⇒ ESPOSTO
              </CardDescription>
            </div>
            <div className="flex items-center gap-3 text-right">
              <div>
                <div className="text-2xl font-semibold tabular-nums">
                  {summary.esposti}
                  <span className="text-sm font-normal text-muted-foreground">
                    {" "}
                    / {summary.total}
                  </span>
                </div>
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  esposti
                </div>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-2 pt-4 text-xs sm:grid-cols-4">
          <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
            <span className="text-muted-foreground">Totale</span>
            <span className="font-medium tabular-nums">{summary.total}</span>
          </div>
          <div className="flex items-center justify-between rounded-md bg-rose-500/10 px-3 py-2">
            <span className="text-muted-foreground">Esposti</span>
            <span className="font-medium tabular-nums text-rose-700 dark:text-rose-400">
              {summary.esposti}
            </span>
          </div>
          <div className="flex items-center justify-between rounded-md bg-emerald-500/10 px-3 py-2">
            <span className="text-muted-foreground">Non esposti</span>
            <span className="font-medium tabular-nums text-emerald-700 dark:text-emerald-400">
              {summary.non_esposti}
            </span>
          </div>
          <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
            <span className="text-muted-foreground">Incompleti</span>
            <span className="font-medium tabular-nums">
              {summary.incompleti}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Workers list */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-sm">Lavoratori al videoterminale</CardTitle>
              <CardDescription className="text-xs">
                Per ogni lavoratore indicare le ore settimanali di utilizzo del
                VDT. La classificazione è calcolata automaticamente.
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-[10px]">
              {workers.length} lavoratori
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          {workers.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Nessun lavoratore aggiunto. Usa il pulsante qui sotto per iniziare.
            </p>
          )}
          <ul className="space-y-2">
            {summary.workers.map((w, idx) => (
              <li
                key={w.id}
                className="rounded-md border border-border bg-background p-3"
              >
                <div className="flex flex-wrap items-center gap-3">
                  <Badge variant="outline" className="shrink-0 text-[10px]">
                    {idx + 1}
                  </Badge>
                  <div className="min-w-[160px] flex-1 space-y-1">
                    <Label
                      htmlFor={`${w.id}-nome`}
                      className="text-[11px] text-muted-foreground"
                    >
                      Nome / riferimento
                    </Label>
                    <Input
                      id={`${w.id}-nome`}
                      type="text"
                      placeholder="es. Mario R. — ufficio vendite"
                      value={w.nome}
                      onChange={(e) =>
                        updateWorker(w.id, "nome", e.target.value)
                      }
                    />
                  </div>
                  <div className="w-40 space-y-1">
                    <Label
                      htmlFor={`${w.id}-ore`}
                      className="text-[11px] text-muted-foreground"
                    >
                      Ore / settimana
                    </Label>
                    <Input
                      id={`${w.id}-ore`}
                      type="number"
                      inputMode="decimal"
                      min={0}
                      max={168}
                      step={0.5}
                      placeholder="es. 25"
                      value={w.ore_settimanali ?? ""}
                      onChange={(e) => {
                        const raw = e.target.value;
                        if (raw === "") {
                          updateWorker(w.id, "ore_settimanali", null);
                        } else {
                          const n = Number(raw);
                          updateWorker(
                            w.id,
                            "ore_settimanali",
                            isNaN(n) ? null : n,
                          );
                        }
                      }}
                    />
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {w.esposizione === "ESPOSTO" && (
                      <span className="inline-flex items-center rounded-md bg-rose-500/15 px-2.5 py-1 text-xs font-medium text-rose-700 ring-1 ring-rose-500/30 dark:text-rose-400">
                        ESPOSTO
                      </span>
                    )}
                    {w.esposizione === "NON_ESPOSTO" && (
                      <span className="inline-flex items-center rounded-md bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-500/30 dark:text-emerald-400">
                        NON ESPOSTO
                      </span>
                    )}
                    {w.esposizione === null && (
                      <Badge variant="secondary" className="text-xs">
                        —
                      </Badge>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive"
                      onClick={() => removeWorker(w.id)}
                    >
                      Rimuovi
                    </Button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <Button variant="outline" size="sm" onClick={addWorker}>
              + Aggiungi lavoratore
            </Button>
            <p className="text-[11px] text-muted-foreground">
              Privacy · non inserire il codice fiscale. Usa un riferimento
              identificativo interno.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Health surveillance notice (only when there is at least 1 ESPOSTO) */}
      {hasEsposti && (
        <div
          className={cn(
            "rounded-md border border-amber-300 bg-amber-100 p-4 text-xs text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200",
          )}
        >
          <div className="font-medium">Sorveglianza sanitaria obbligatoria</div>
          <p className="mt-1 leading-relaxed">
            Sorveglianza sanitaria obbligatoria — visita medica prima
            dell&apos;adibizione al VDT e a intervalli stabiliti dal medico
            competente (in genere 5 anni, o 2 anni per età &gt;50 o prescrizione
            specifica).
          </p>
        </div>
      )}

      {/* Reset */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 p-4">
        <div className="text-xs text-muted-foreground">
          Bozza salvata automaticamente ·{" "}
          {summary.incompleti === 0 && summary.total > 0
            ? "tutti i lavoratori classificati"
            : summary.total === 0
            ? "nessun lavoratore inserito"
            : `mancano le ore per ${summary.incompleti} lavoratori`}
        </div>
        <button
          type="button"
          onClick={resetDraft}
          className="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          Azzera bozza
        </button>
      </div>
    </div>
  );
}
