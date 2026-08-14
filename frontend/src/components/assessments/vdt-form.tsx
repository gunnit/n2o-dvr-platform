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
import { Callout } from "@/components/ui/callout";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";

// ---------------------------------------------------------------------------
// Domain — mirrors backend/app/services/vdt_calculator.py and
// backend/app/schemas/vdt.py.  D.Lgs. 81/2008 Titolo VII: worker with
// >= 20h/week VDT use = ESPOSTO. When the same worker uses multiple
// devices/postazioni, the weekly hours are SUMMED across all their rows
// and the exposure is classified on the TOTAL (client feedback 2026-08).
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
  attivita: string; // ATTIVITÀ svolta alla postazione (client feedback 2026-08)
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
  // surveillance — periodicità is computed from the worker's age
  // (data_nascita); eta_50_plus is derived from it and kept only because
  // the backend still accepts it as a legacy fallback.
  eta_50_plus: boolean;
  data_nascita: string | ""; // YYYY-MM-DD
  idoneita_visiva: IdoneitaVisiva | "";
  note: string;
}

export interface VdtWorkerResult extends VdtWorker {
  esposizione: Esposizione | null; // null = ore not yet provided
  sorveglianza_sanitaria: boolean;
  // Person-level total across all rows of the same persona (equals the
  // row's own hours for generic rows). Drives the classification.
  ore_totali: number | null;
}

export interface VdtSummary {
  workers: VdtWorkerResult[];
  total: number;
  esposti: number;
  non_esposti: number;
  incompleti: number; // workers without ore_settimanali or postazione
}

/** Whole years of age at `on` for an ISO date string, or null if unparsable. */
export function ageOn(birthIso: string, on: Date = new Date()): number | null {
  if (!birthIso) return null;
  const b = new Date(`${birthIso}T00:00:00`);
  if (isNaN(b.getTime())) return null;
  let age = on.getFullYear() - b.getFullYear();
  const m = on.getMonth() - b.getMonth();
  if (m < 0 || (m === 0 && on.getDate() < b.getDate())) age -= 1;
  return age;
}

/** Art. 176 c.3: biennale for 50+ or "con prescrizioni", else quinquennale. */
export function periodicitaFor(worker: VdtWorker): "biennale" | "quinquennale" {
  const age = ageOn(worker.data_nascita);
  const over50 = age !== null ? age >= 50 : worker.eta_50_plus;
  return over50 || worker.idoneita_visiva === "con prescrizioni"
    ? "biennale"
    : "quinquennale";
}

export function classifyWorker(
  worker: VdtWorker,
  personTotals?: Map<string, number>,
): VdtWorkerResult {
  if (worker.ore_settimanali == null || isNaN(worker.ore_settimanali)) {
    return {
      ...worker,
      esposizione: null,
      sorveglianza_sanitaria: false,
      ore_totali: null,
    };
  }
  // One person on several devices: classify on the SUM of their hours
  // across all rows, not on this row alone (12h + 10h => 22h => ESPOSTO).
  const total =
    worker.persona_id && personTotals?.has(worker.persona_id)
      ? personTotals.get(worker.persona_id)!
      : worker.ore_settimanali;
  const esposizione: Esposizione =
    total >= VDT_EXPOSURE_THRESHOLD_HOURS ? "ESPOSTO" : "NON_ESPOSTO";
  return {
    ...worker,
    esposizione,
    sorveglianza_sanitaria: esposizione === "ESPOSTO",
    ore_totali: total,
  };
}

export function summarize(workers: VdtWorker[]): VdtSummary {
  // Person-level hour totals: same persona on multiple rows sums up.
  const personTotals = new Map<string, number>();
  for (const w of workers) {
    if (
      w.persona_id &&
      w.ore_settimanali != null &&
      !isNaN(w.ore_settimanali)
    ) {
      personTotals.set(
        w.persona_id,
        (personTotals.get(w.persona_id) ?? 0) + w.ore_settimanali,
      );
    }
  }
  const classified = workers.map((w) => classifyWorker(w, personTotals));
  let esposti = 0;
  let non_esposti = 0;
  let incompleti = 0;
  // Esposti/non esposti are counted per PERSON (or per generic row), not
  // per row — a worker on two devices is one exposure, not two.
  const countedPersone = new Set<string>();
  for (const w of classified) {
    const missingOre = w.esposizione === null;
    const missingPost = !w.postazione.trim();
    if (missingOre || missingPost) {
      incompleti += 1;
      continue;
    }
    if (w.persona_id) {
      if (countedPersone.has(w.persona_id)) continue;
      countedPersone.add(w.persona_id);
    }
    if (w.esposizione === "ESPOSTO") esposti += 1;
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
    attivita: "",
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
    data_nascita: "",
    idoneita_visiva: "",
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

  const updateWorkerFields = useCallback(
    (id: string, fields: Partial<VdtWorker>) => {
      setWorkers((prev) =>
        prev.map((w) => (w.id === id ? { ...w, ...fields } : w)),
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
          <div className="flex items-center justify-between rounded-md bg-[rgba(239,68,68,0.1)] px-3 py-2">
            <span className="text-muted-foreground">Esposti</span>
            <span className="font-medium tabular-nums text-[#b01e2e]">
              {summary.esposti}
            </span>
          </div>
          <div className="flex items-center justify-between rounded-md bg-[rgba(21,190,83,0.1)] px-3 py-2">
            <span className="text-muted-foreground">Non esposti</span>
            <span className="font-medium tabular-nums text-[#0c6b2f]">
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
                      <Select
                        id={`${w.id}-persona`}
                        value={w.persona_id ?? ""}
                        onChange={(e) => {
                          const personaId = e.target.value || null;
                          // Prefill ATTIVITÀ from the mansione so the
                          // operator only corrects (review, never re-enter).
                          const mansione = personaId
                            ? persone.find((p) => p.id === personaId)
                                ?.mansione ?? ""
                            : "";
                          updateWorkerFields(w.id, {
                            persona_id: personaId,
                            ...(w.attivita.trim() === "" && mansione
                              ? { attivita: mansione }
                              : {}),
                          });
                        }} size="sm"
                      >
                        <option value="">— Generica —</option>
                        {persone.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.nominativo}
                            {p.mansione ? ` — ${p.mansione}` : ""}
                          </option>
                        ))}
                      </Select>
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
                        maxLength={200}
                        required
                        value={w.postazione}
                        onChange={(e) =>
                          updateWorker(w.id, "postazione", e.target.value)
                        }
                      />
                    </div>

                    <div className="min-w-[180px] flex-1 space-y-1">
                      <Label
                        htmlFor={`${w.id}-attivita`}
                        className="text-[11px] text-muted-foreground"
                      >
                        Attività
                      </Label>
                      <Input
                        id={`${w.id}-attivita`}
                        type="text"
                        placeholder="es. Data entry, contabilità"
                        maxLength={200}
                        value={w.attivita}
                        onChange={(e) =>
                          updateWorker(w.id, "attivita", e.target.value)
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
                      {w.persona_id &&
                        w.ore_totali != null &&
                        w.ore_settimanali != null &&
                        w.ore_totali !== w.ore_settimanali && (
                          <span
                            className="text-[11px] tabular-nums text-muted-foreground"
                            title="Somma delle ore su tutte le postazioni di questo lavoratore"
                          >
                            Σ {w.ore_totali} h/sett
                          </span>
                        )}
                      {w.esposizione === "ESPOSTO" && (
                        <span className="inline-flex items-center rounded-md bg-[rgba(239,68,68,0.16)] px-2.5 py-1 text-xs font-medium text-[#b01e2e] ring-1 ring-[rgba(239,68,68,0.34)]">
                          ESPOSTO
                        </span>
                      )}
                      {w.esposizione === "NON_ESPOSTO" && (
                        <span className="inline-flex items-center rounded-md bg-[rgba(21,190,83,0.16)] px-2.5 py-1 text-xs font-medium text-[#0c6b2f] ring-1 ring-[rgba(21,190,83,0.34)]">
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
                        <div className="rounded-md border border-[rgba(155,104,41,0.26)] bg-[rgba(155,104,41,0.05)] p-3">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#8a5c23]">
                            Sorveglianza sanitaria
                          </p>
                          <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
                            <div className="space-y-1">
                              <Label
                                htmlFor={`${w.id}-nascita`}
                                className="text-[11px] text-muted-foreground"
                              >
                                Data di nascita
                              </Label>
                              <Input
                                id={`${w.id}-nascita`}
                                type="date"
                                value={w.data_nascita}
                                onChange={(e) => {
                                  const v = e.target.value;
                                  const age = ageOn(v);
                                  updateWorkerFields(w.id, {
                                    data_nascita: v,
                                    // Legacy fallback flag kept in sync so
                                    // the backend derives the same cadence.
                                    eta_50_plus:
                                      age !== null
                                        ? age >= 50
                                        : w.eta_50_plus,
                                  });
                                }}
                              />
                            </div>

                            <div className="space-y-1">
                              <Label
                                htmlFor={`${w.id}-idoneita`}
                                className="text-[11px] text-muted-foreground"
                              >
                                Idoneità visiva
                              </Label>
                              <Select
                                id={`${w.id}-idoneita`}
                                value={w.idoneita_visiva}
                                onChange={(e) =>
                                  updateWorker(
                                    w.id,
                                    "idoneita_visiva",
                                    e.target.value as VdtWorker["idoneita_visiva"],
                                  )
                                } size="sm" className="text-xs"
                              >
                                <option value="">—</option>
                                <option value="idoneo">Idoneo</option>
                                <option value="con prescrizioni">
                                  Con prescrizioni
                                </option>
                                <option value="non idoneo">Non idoneo</option>
                              </Select>
                            </div>

                            <div className="space-y-1">
                              <span className="text-[11px] text-muted-foreground">
                                Periodicità (calcolata dall&apos;età)
                              </span>
                              <p className="text-xs font-medium">
                                {periodicitaFor(w)}
                                {ageOn(w.data_nascita) !== null && (
                                  <span className="ml-1 font-normal text-muted-foreground">
                                    · {ageOn(w.data_nascita)} anni
                                  </span>
                                )}
                              </p>
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
        <Callout tone="warn">
          <p className="font-semibold">Sorveglianza sanitaria obbligatoria</p>
          <p className="mt-0.5">
            Visita medica oculistica prima dell&apos;adibizione al VDT e a
            intervalli stabiliti dal medico competente: cadenza standard 5
            anni; 2 anni per età ≥ 50 anni o con prescrizioni.
          </p>
        </Callout>
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
