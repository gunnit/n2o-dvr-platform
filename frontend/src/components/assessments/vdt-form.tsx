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
// Domain — mirrors backend/app/services/vdt_calculator.py and
// backend/app/schemas/vdt.py.  D.Lgs. 81/2008 Titolo VII: worker with
// >= 20h/week VDT use = ESPOSTO.
// ---------------------------------------------------------------------------

export const VDT_EXPOSURE_THRESHOLD_HOURS = 20;

export type Esposizione = "ESPOSTO" | "NON_ESPOSTO";
export type IdoneitaVisiva = "idoneo" | "con prescrizioni" | "non idoneo";

export interface PersonaOption {
  id: string;
  nominativo: string;
  mansione: string | null;
}

export interface VdtWorker {
  id: string; // client-side id only, never sent to server
  persona_id: string | null;
  postazione: string;
  ore_settimanali: number | null;
  // checklist
  schermo_conforme: boolean;
  tastiera_separata: boolean;
  sedile_regolabile: boolean;
  poggiapiedi_disponibile: boolean;
  illuminazione_adeguata: boolean;
  riflessi_assenti: boolean;
  spazio_adeguato: boolean;
  pause_previste: boolean;
  // surveillance
  eta_50_plus: boolean;
  idoneita_visiva: IdoneitaVisiva | "";
  data_ultima_visita: string | ""; // YYYY-MM-DD
  note: string;
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
  incompleti: number; // workers without ore_settimanali or postazione
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
    const missingOre = w.esposizione === null;
    const missingPost = !w.postazione.trim();
    if (missingOre || missingPost) incompleti += 1;
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

function makeId(): string {
  return `w_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

function makeWorker(): VdtWorker {
  return {
    id: makeId(),
    persona_id: null,
    postazione: "",
    ore_settimanali: null,
    schermo_conforme: true,
    tastiera_separata: true,
    sedile_regolabile: true,
    poggiapiedi_disponibile: true,
    illuminazione_adeguata: true,
    riflessi_assenti: true,
    spazio_adeguato: true,
    pause_previste: true,
    eta_50_plus: false,
    idoneita_visiva: "",
    data_ultima_visita: "",
    note: "",
  };
}

const CHECKLIST_FIELDS: Array<{ key: keyof VdtWorker; label: string }> = [
  { key: "schermo_conforme", label: "Schermo conforme" },
  { key: "tastiera_separata", label: "Tastiera separata e inclinabile" },
  { key: "sedile_regolabile", label: "Sedile regolabile" },
  { key: "poggiapiedi_disponibile", label: "Poggiapiedi disponibile" },
  { key: "illuminazione_adeguata", label: "Illuminazione adeguata (300-500 lux)" },
  { key: "riflessi_assenti", label: "Assenza di riflessi" },
  { key: "spazio_adeguato", label: "Spazio di lavoro sufficiente" },
  { key: "pause_previste", label: "Pause previste (15 min/2 h)" },
];

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface VdtFormProps {
  aziendaId: string;
  persone: PersonaOption[];
  onSummaryChange?: (summary: VdtSummary) => void;
  // Feedback #56: parent bumps this counter after a successful save so
  // the form clears its workers + localStorage draft. Operators were
  // reporting "non si salva" because the old draft kept sitting in the
  // form after a save, looking unsaved. A simple monotonic counter is
  // enough — comparing against the last value the form has seen.
  clearSignal?: number;
}

export function VdtForm({
  aziendaId,
  persone,
  onSummaryChange,
  clearSignal,
}: VdtFormProps) {
  const storageKey = `vdt-draft-${aziendaId}`;

  const [workers, setWorkers] = useState<VdtWorker[]>([]);
  const [hydrated, setHydrated] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  // Hydrate from localStorage
  useEffect(() => {
    try {
      const raw =
        typeof window !== "undefined"
          ? window.localStorage.getItem(storageKey)
          : null;
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<VdtWorker>[];
        if (Array.isArray(parsed)) {
          // Merge defaults so older drafts don't crash on missing fields.
          setWorkers(parsed.map((p) => ({ ...makeWorker(), ...p })));
        }
      }
    } catch {
      setWorkers([]);
    } finally {
      setHydrated(true);
    }
  }, [storageKey]);

  // Persist on change
  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(workers));
    } catch {
      /* noop */
    }
  }, [workers, storageKey, hydrated]);

  const summary = useMemo(() => summarize(workers), [workers]);

  useEffect(() => {
    onSummaryChange?.(summary);
  }, [summary, onSummaryChange]);

  const addWorker = useCallback(() => {
    setWorkers((prev) => [...prev, makeWorker()]);
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
      /* noop */
    }
  }, [storageKey]);

  // React to the parent's clearSignal bumps. Guarded by `hydrated` so
  // we never wipe a draft before it has loaded — that would race the
  // initial-hydration effect on mount.
  useEffect(() => {
    if (!hydrated) return;
    if (clearSignal === undefined) return;
    resetDraft();
    // Intentionally omit resetDraft from deps: it changes when storageKey
    // changes but we only want to react to clearSignal.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clearSignal, hydrated]);

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
            <span className="font-medium tabular-nums text-rose-700">
              {summary.esposti}
            </span>
          </div>
          <div className="flex items-center justify-between rounded-md bg-emerald-500/10 px-3 py-2">
            <span className="text-muted-foreground">Non esposti</span>
            <span className="font-medium tabular-nums text-emerald-700">
              {summary.non_esposti}
            </span>
          </div>
          <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
            <span className="text-muted-foreground">Incompleti</span>
            <span className="font-medium tabular-nums">{summary.incompleti}</span>
          </div>
        </CardContent>
      </Card>

      {/* Workers list */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-sm">Postazioni VDT da valutare</CardTitle>
              <CardDescription className="text-xs">
                Una riga per postazione/lavoratore. Il rischio è classificato
                in base alle ore settimanali; per gli esposti compaiono i
                campi sulla sorveglianza sanitaria.
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-[10px]">
              {workers.length} righe
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          {workers.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Nessuna postazione aggiunta. Usa il pulsante qui sotto per iniziare.
            </p>
          )}
          <ul className="space-y-3">
            {summary.workers.map((w, idx) => {
              const isExpanded = expanded[w.id] ?? false;
              const personaLabel = w.persona_id
                ? persone.find((p) => p.id === w.persona_id)?.nominativo ??
                  "(lavoratore non in elenco)"
                : "(generica / nessun lavoratore)";
              return (
                <li
                  key={w.id}
                  className="rounded-md border border-border bg-background p-3"
                >
                  <div className="flex flex-wrap items-start gap-3">
                    <Badge variant="outline" className="mt-2 shrink-0 text-[10px]">
                      {idx + 1}
                    </Badge>

                    <div className="min-w-[200px] flex-1 space-y-1">
                      <Label
                        htmlFor={`${w.id}-persona`}
                        className="text-[11px] text-muted-foreground"
                      >
                        Lavoratore
                      </Label>
                      <select
                        id={`${w.id}-persona`}
                        value={w.persona_id ?? ""}
                        onChange={(e) =>
                          updateWorker(
                            w.id,
                            "persona_id",
                            e.target.value || null,
                          )
                        }
                        className="block w-full rounded-md border bg-background px-2 py-1.5 text-sm"
                      >
                        <option value="">— Generica —</option>
                        {persone.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.nominativo}
                            {p.mansione ? ` — ${p.mansione}` : ""}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="min-w-[200px] flex-1 space-y-1">
                      <Label
                        htmlFor={`${w.id}-post`}
                        className="text-[11px] text-muted-foreground"
                      >
                        Postazione
                      </Label>
                      <Input
                        id={`${w.id}-post`}
                        type="text"
                        placeholder="es. PC ufficio amministrazione"
                        value={w.postazione}
                        onChange={(e) =>
                          updateWorker(w.id, "postazione", e.target.value)
                        }
                      />
                    </div>

                    <div className="w-32 space-y-1">
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
                        placeholder="25"
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

                    <div className="flex shrink-0 items-center gap-2 self-center">
                      {w.esposizione === "ESPOSTO" && (
                        <span className="inline-flex items-center rounded-md bg-rose-500/15 px-2.5 py-1 text-xs font-medium text-rose-700 ring-1 ring-rose-500/30">
                          ESPOSTO
                        </span>
                      )}
                      {w.esposizione === "NON_ESPOSTO" && (
                        <span className="inline-flex items-center rounded-md bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-500/30">
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
                        className="h-7 px-2 text-xs"
                        onClick={() =>
                          setExpanded((e) => ({ ...e, [w.id]: !isExpanded }))
                        }
                      >
                        {isExpanded ? "Nascondi" : "Dettaglio"}
                      </Button>
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

                  {isExpanded && (
                    <div className="mt-3 space-y-4 border-t pt-3">
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                          Check-list ergonomica · {personaLabel}
                        </p>
                        <div className="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-2">
                          {CHECKLIST_FIELDS.map(({ key, label }) => (
                            <label
                              key={key}
                              className="flex items-center gap-2 text-xs"
                            >
                              <input
                                type="checkbox"
                                checked={Boolean(w[key])}
                                onChange={(e) =>
                                  updateWorker(
                                    w.id,
                                    key,
                                    e.target.checked as VdtWorker[typeof key],
                                  )
                                }
                                className="h-3.5 w-3.5"
                              />
                              <span>{label}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      {w.esposizione === "ESPOSTO" && (
                        <div className="rounded-md border border-amber-300 bg-amber-50 p-3">
                          <p className="text-[11px] font-medium uppercase tracking-wide text-amber-900">
                            Sorveglianza sanitaria
                          </p>
                          <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
                            <label className="flex items-center gap-2 text-xs">
                              <input
                                type="checkbox"
                                checked={w.eta_50_plus}
                                onChange={(e) =>
                                  updateWorker(
                                    w.id,
                                    "eta_50_plus",
                                    e.target.checked,
                                  )
                                }
                                className="h-3.5 w-3.5"
                              />
                              <span>Età ≥ 50 anni (cadenza biennale)</span>
                            </label>

                            <div className="space-y-1">
                              <Label
                                htmlFor={`${w.id}-idoneita`}
                                className="text-[11px] text-muted-foreground"
                              >
                                Idoneità visiva
                              </Label>
                              <select
                                id={`${w.id}-idoneita`}
                                value={w.idoneita_visiva}
                                onChange={(e) =>
                                  updateWorker(
                                    w.id,
                                    "idoneita_visiva",
                                    e.target.value as VdtWorker["idoneita_visiva"],
                                  )
                                }
                                className="block w-full rounded-md border bg-background px-2 py-1.5 text-xs"
                              >
                                <option value="">—</option>
                                <option value="idoneo">Idoneo</option>
                                <option value="con prescrizioni">
                                  Con prescrizioni
                                </option>
                                <option value="non idoneo">Non idoneo</option>
                              </select>
                            </div>

                            <div className="space-y-1">
                              <Label
                                htmlFor={`${w.id}-data`}
                                className="text-[11px] text-muted-foreground"
                              >
                                Ultima visita
                              </Label>
                              <Input
                                id={`${w.id}-data`}
                                type="date"
                                value={w.data_ultima_visita}
                                onChange={(e) =>
                                  updateWorker(
                                    w.id,
                                    "data_ultima_visita",
                                    e.target.value,
                                  )
                                }
                              />
                            </div>
                          </div>
                        </div>
                      )}

                      <div className="space-y-1">
                        <Label
                          htmlFor={`${w.id}-note`}
                          className="text-[11px] text-muted-foreground"
                        >
                          Note (opzionali)
                        </Label>
                        <Input
                          id={`${w.id}-note`}
                          type="text"
                          placeholder="es. Postazione condivisa con altro lavoratore"
                          value={w.note}
                          onChange={(e) =>
                            updateWorker(w.id, "note", e.target.value)
                          }
                        />
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <Button variant="outline" size="sm" onClick={addWorker}>
              + Aggiungi postazione
            </Button>
            <p className="text-[11px] text-muted-foreground">
              Privacy · non inserire codice fiscale o dati clinici personali.
            </p>
          </div>
        </CardContent>
      </Card>

      {hasEsposti && (
        <div
          className={cn(
            "rounded-md border border-amber-300 bg-amber-100 p-4 text-xs text-amber-900",
          )}
        >
          <div className="font-medium">Sorveglianza sanitaria obbligatoria</div>
          <p className="mt-1 leading-relaxed">
            Visita medica oculistica prima dell&apos;adibizione al VDT e a
            intervalli stabiliti dal medico competente: cadenza standard 5
            anni; 2 anni per età ≥ 50 anni o con prescrizioni.
          </p>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 p-4">
        <div className="text-xs text-muted-foreground">
          Bozza salvata automaticamente ·{" "}
          {summary.incompleti === 0 && summary.total > 0
            ? "tutte le righe complete"
            : summary.total === 0
            ? "nessuna riga inserita"
            : `${summary.incompleti} righe incomplete`}
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
