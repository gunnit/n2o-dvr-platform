"use client";

import { useCallback, useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import type { Ambiente, ValutazioneRischio } from "@/types";

interface StepRischiProps {
  aziendaId: string;
  ambienti: Ambiente[];
  valutazioni: ValutazioneRischio[];
  onChange: (valutazioni: ValutazioneRischio[]) => void;
}

const CATEGORIE_RISCHIO = [
  "Strutture",
  "Macchine",
  "Elettrici",
  "Incendio",
  "Chimici",
  "Fisici",
  "Biologici",
  "Cancerogeni",
  "Organizzazione",
  "Psicologici",
  "Ergonomici",
] as const;

type CategoriaRischio = (typeof CATEGORIE_RISCHIO)[number];

// ---------------------------------------------------------------------------
// Contextual filtering per ambiente.tipo (US-1.5)
// Lowercase ambiente.tipo keys matching survey options.
// ---------------------------------------------------------------------------
const RISCHI_PER_AMBIENTE: Record<string, CategoriaRischio[]> = {
  ufficio: [
    "Strutture",
    "Elettrici",
    "Incendio",
    "Fisici",
    "Organizzazione",
    "Psicologici",
    "Ergonomici",
  ],
  magazzino: [
    "Strutture",
    "Macchine",
    "Elettrici",
    "Incendio",
    "Fisici",
    "Ergonomici",
    "Organizzazione",
  ],
  cucina: [
    "Strutture",
    "Macchine",
    "Elettrici",
    "Incendio",
    "Chimici",
    "Fisici",
    "Biologici",
    "Ergonomici",
    "Organizzazione",
  ],
  produzione: [
    "Strutture",
    "Macchine",
    "Elettrici",
    "Incendio",
    "Chimici",
    "Fisici",
    "Biologici",
    "Cancerogeni",
    "Organizzazione",
    "Ergonomici",
  ],
  laboratorio: [...CATEGORIE_RISCHIO],
  esterno: [
    "Strutture",
    "Fisici",
    "Organizzazione",
    "Ergonomici",
    "Incendio",
  ],
  negozio: [
    "Strutture",
    "Elettrici",
    "Incendio",
    "Ergonomici",
    "Organizzazione",
  ],
  altro: [...CATEGORIE_RISCHIO],
};

function getCategorieForTipo(tipo: string | undefined | null): CategoriaRischio[] {
  if (!tipo) return [...CATEGORIE_RISCHIO];
  const filtered = RISCHI_PER_AMBIENTE[tipo.toLowerCase()];
  return filtered ?? [...CATEGORIE_RISCHIO];
}

// ---------------------------------------------------------------------------
// Default risk scoring matrix (US-2.3)
// Mirrors backend/app/services/reference_data.py DEFAULT_RISK_SCORES.
// Keep shapes identical between Python and TS.
// ---------------------------------------------------------------------------
const DEFAULT_RISK_SCORES: Record<string, Record<CategoriaRischio, [number, number]>> = {
  ufficio: {
    Strutture: [1, 2],
    Macchine: [1, 1],
    Elettrici: [1, 2],
    Incendio: [1, 2],
    Chimici: [1, 1],
    Fisici: [1, 2],
    Biologici: [1, 1],
    Cancerogeni: [1, 1],
    Organizzazione: [1, 1],
    Psicologici: [2, 2],
    Ergonomici: [2, 2],
  },
  magazzino: {
    Strutture: [2, 2],
    Macchine: [2, 3],
    Elettrici: [1, 2],
    Incendio: [2, 3],
    Chimici: [1, 2],
    Fisici: [2, 2],
    Biologici: [1, 1],
    Cancerogeni: [1, 1],
    Organizzazione: [2, 2],
    Psicologici: [1, 1],
    Ergonomici: [2, 3],
  },
  produzione: {
    Strutture: [2, 2],
    Macchine: [2, 3],
    Elettrici: [2, 3],
    Incendio: [2, 3],
    Chimici: [2, 3],
    Fisici: [2, 3],
    Biologici: [1, 2],
    Cancerogeni: [1, 3],
    Organizzazione: [2, 2],
    Psicologici: [1, 2],
    Ergonomici: [2, 3],
  },
  cucina: {
    Strutture: [2, 2],
    Macchine: [2, 2],
    Elettrici: [2, 2],
    Incendio: [2, 3],
    Chimici: [2, 2],
    Fisici: [2, 2],
    Biologici: [2, 2],
    Cancerogeni: [1, 1],
    Organizzazione: [2, 2],
    Psicologici: [2, 2],
    Ergonomici: [2, 2],
  },
  laboratorio: {
    Strutture: [2, 2],
    Macchine: [2, 3],
    Elettrici: [2, 3],
    Incendio: [2, 3],
    Chimici: [2, 3],
    Fisici: [2, 2],
    Biologici: [2, 3],
    Cancerogeni: [2, 3],
    Organizzazione: [2, 2],
    Psicologici: [1, 2],
    Ergonomici: [2, 2],
  },
  esterno: {
    Strutture: [2, 2],
    Macchine: [1, 2],
    Elettrici: [1, 2],
    Incendio: [2, 2],
    Chimici: [1, 1],
    Fisici: [2, 3],
    Biologici: [1, 2],
    Cancerogeni: [1, 1],
    Organizzazione: [2, 2],
    Psicologici: [1, 1],
    Ergonomici: [2, 3],
  },
  negozio: {
    Strutture: [1, 2],
    Macchine: [1, 1],
    Elettrici: [1, 2],
    Incendio: [2, 2],
    Chimici: [1, 1],
    Fisici: [1, 2],
    Biologici: [1, 1],
    Cancerogeni: [1, 1],
    Organizzazione: [1, 2],
    Psicologici: [1, 2],
    Ergonomici: [2, 2],
  },
  altro: {
    Strutture: [1, 2],
    Macchine: [1, 2],
    Elettrici: [1, 2],
    Incendio: [1, 2],
    Chimici: [1, 2],
    Fisici: [1, 2],
    Biologici: [1, 2],
    Cancerogeni: [1, 2],
    Organizzazione: [1, 2],
    Psicologici: [1, 2],
    Ergonomici: [1, 2],
  },
};

function getDefaultScores(
  tipo: string | undefined | null,
  categoria: CategoriaRischio
): [number, number] {
  const key = (tipo ?? "").toLowerCase();
  const matrix = DEFAULT_RISK_SCORES[key];
  if (!matrix) return [1, 1];
  return matrix[categoria] ?? [1, 1];
}

function calcIndice(p: number, d: number): number {
  return 2 * d + p;
}

function getLivello(
  indice: number
): "ACCETTABILE" | "MODESTO" | "GRAVE" | "GRAVISSIMO" {
  if (indice <= 4) return "ACCETTABILE";
  if (indice <= 6) return "MODESTO";
  if (indice <= 8) return "GRAVE";
  return "GRAVISSIMO";
}

function getLivelloStyle(livello: string) {
  switch (livello) {
    case "ACCETTABILE":
      return "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800";
    case "MODESTO":
      return "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800";
    case "GRAVE":
      return "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800";
    case "GRAVISSIMO":
      return "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800";
    default:
      return "";
  }
}

function getIndiceBarColor(livello: string) {
  switch (livello) {
    case "ACCETTABILE":
      return "bg-green-500";
    case "MODESTO":
      return "bg-yellow-500";
    case "GRAVE":
      return "bg-orange-500";
    case "GRAVISSIMO":
      return "bg-red-500";
    default:
      return "bg-muted";
  }
}

function initValutazioni(
  ambienteId: string,
  existing: ValutazioneRischio[]
): ValutazioneRischio[] {
  return CATEGORIE_RISCHIO.map((cat) => {
    const found = existing.find(
      (v) =>
        v.ambiente_id === ambienteId && v.categoria_rischio === cat
    );
    if (found) return found;
    return {
      id: crypto.randomUUID(),
      ambiente_id: ambienteId,
      categoria_rischio: cat,
      applicabile: true,
      pericolo: null,
      condizioni_esposizione: null,
      rischio: null,
      misure_prevenzione: null,
      probabilita_p: 1,
      danno_d: 1,
      indice_i: 3,
      livello_rischio: "ACCETTABILE" as const,
    };
  });
}

export function StepRischi({
  ambienti,
  valutazioni,
  onChange,
}: StepRischiProps) {
  const [selectedAmbienteIndex, setSelectedAmbienteIndex] = useState(0);
  const [mostraTutti, setMostraTutti] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);

  const selectedAmbiente = ambienti[selectedAmbienteIndex];

  // Ensure we have valutazioni for all ambienti
  const allValutazioni = useMemo(() => {
    const result: ValutazioneRischio[] = [];
    for (const amb of ambienti) {
      result.push(...initValutazioni(amb.id, valutazioni));
    }
    return result;
  }, [ambienti, valutazioni]);

  const currentValutazioni = useMemo(
    () =>
      selectedAmbiente
        ? allValutazioni.filter(
            (v) => v.ambiente_id === selectedAmbiente.id
          )
        : [],
    [allValutazioni, selectedAmbiente]
  );

  // Compute the subset of categories shown for this ambiente.tipo.
  const categorieVisibili = useMemo<CategoriaRischio[]>(() => {
    if (mostraTutti) return [...CATEGORIE_RISCHIO];
    return getCategorieForTipo(selectedAmbiente?.tipo);
  }, [mostraTutti, selectedAmbiente?.tipo]);

  const visibleValutazioni = useMemo(() => {
    const setVis = new Set<string>(categorieVisibili);
    return currentValutazioni.filter((v) =>
      setVis.has(v.categoria_rischio as CategoriaRischio)
    );
  }, [currentValutazioni, categorieVisibili]);

  // Summary counts over the currently visible rows.
  const summary = useMemo(() => {
    const applicabiliRows = visibleValutazioni.filter((v) => v.applicabile);
    const total = visibleValutazioni.length;
    const selected = applicabiliRows.length;

    let gravissimo = 0;
    let grave = 0;
    let modesto = 0;
    let accettabile = 0;

    for (const v of applicabiliRows) {
      const p = v.probabilita_p ?? 1;
      const d = v.danno_d ?? 1;
      const livello = getLivello(calcIndice(p, d));
      if (livello === "GRAVISSIMO") gravissimo += 1;
      else if (livello === "GRAVE") grave += 1;
      else if (livello === "MODESTO") modesto += 1;
      else accettabile += 1;
    }

    return { total, selected, gravissimo, grave, modesto, accettabile };
  }, [visibleValutazioni]);

  const updateValutazione = useCallback(
    (valId: string, fields: Partial<ValutazioneRischio>) => {
      const updated = allValutazioni.map((v) => {
        if (v.id !== valId) return v;
        const merged = { ...v, ...fields };

        // Recalculate if P or D changed
        if ("probabilita_p" in fields || "danno_d" in fields) {
          const p = merged.probabilita_p ?? 1;
          const d = merged.danno_d ?? 1;
          const indice = calcIndice(p, d);
          merged.indice_i = indice;
          merged.livello_rischio = getLivello(indice);
        }

        return merged;
      });
      onChange(updated);
    },
    [allValutazioni, onChange]
  );

  // Apply default scoring matrix to every row of the selected ambiente.
  const applyDefaults = useCallback(() => {
    if (!selectedAmbiente) return;
    const updated = allValutazioni.map((v) => {
      if (v.ambiente_id !== selectedAmbiente.id) return v;
      const [p, d] = getDefaultScores(
        selectedAmbiente.tipo,
        v.categoria_rischio as CategoriaRischio
      );
      const indice = calcIndice(p, d);
      return {
        ...v,
        probabilita_p: p,
        danno_d: d,
        indice_i: indice,
        livello_rischio: getLivello(indice),
      };
    });
    onChange(updated);
  }, [allValutazioni, onChange, selectedAmbiente]);

  if (ambienti.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <p className="text-muted-foreground">
            Aggiungi almeno un ambiente di lavoro nel passo 3 prima di
            procedere con la valutazione dei rischi.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Ambiente selector */}
      <Card>
        <CardHeader>
          <CardTitle>Valutazione Rischi</CardTitle>
          <CardDescription>
            Valuta i rischi per ogni ambiente di lavoro. Formula: I = 2D + P
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <Label>Seleziona Ambiente</Label>
            <div className="flex flex-wrap gap-2">
              {ambienti.map((amb, idx) => (
                <button
                  key={amb.id}
                  type="button"
                  onClick={() => setSelectedAmbienteIndex(idx)}
                  className={cn(
                    "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
                    idx === selectedAmbienteIndex
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-input bg-background text-foreground hover:bg-muted"
                  )}
                >
                  {amb.nome || `Ambiente ${idx + 1}`}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Risk table */}
      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base">
              {selectedAmbiente?.nome || "Ambiente"}
              {selectedAmbiente?.tipo
                ? ` (${selectedAmbiente.tipo})`
                : ""}
            </CardTitle>
            <CardDescription>
              {mostraTutti
                ? "Stai vedendo tutte le 11 categorie di rischio."
                : `Categorie filtrate per tipo "${selectedAmbiente?.tipo ?? "altro"}".`}
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-muted-foreground">
              <input
                type="checkbox"
                checked={mostraTutti}
                onChange={(e) => setMostraTutti(e.target.checked)}
                className="h-4 w-4 accent-primary"
              />
              Mostra tutti i rischi
            </label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setResetDialogOpen(true)}
            >
              Reset al default
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Summary bar */}
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/40 px-3 py-2 text-xs">
            <div className="font-medium">
              {summary.selected} di {summary.total} rischi selezionati
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant="outline"
                className={cn(
                  "font-semibold",
                  getLivelloStyle("GRAVISSIMO")
                )}
              >
                {summary.gravissimo} Gravissimo
              </Badge>
              <Badge
                variant="outline"
                className={cn(
                  "font-semibold",
                  getLivelloStyle("GRAVE")
                )}
              >
                {summary.grave} Grave
              </Badge>
              <Badge
                variant="outline"
                className={cn(
                  "font-semibold",
                  getLivelloStyle("MODESTO")
                )}
              >
                {summary.modesto} Modesto
              </Badge>
              <Badge
                variant="outline"
                className={cn(
                  "font-semibold",
                  getLivelloStyle("ACCETTABILE")
                )}
              >
                {summary.accettabile} Accettabile
              </Badge>
            </div>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[180px]">
                  Categoria Rischio
                </TableHead>
                <TableHead className="w-[80px] text-center">
                  Applicabile
                </TableHead>
                <TableHead className="w-[140px] text-center">
                  P (Probabilita)
                </TableHead>
                <TableHead className="w-[140px] text-center">
                  D (Danno)
                </TableHead>
                <TableHead className="w-[80px] text-center">
                  I (Indice)
                </TableHead>
                <TableHead className="w-[140px] text-center">
                  Livello
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleValutazioni.map((val) => {
                const p = val.probabilita_p ?? 1;
                const d = val.danno_d ?? 1;
                const indice = calcIndice(p, d);
                const livello = getLivello(indice);

                return (
                  <TableRow
                    key={val.id}
                    className={cn(
                      !val.applicabile && "opacity-40"
                    )}
                  >
                    <TableCell className="font-medium">
                      {val.categoria_rischio}
                    </TableCell>

                    {/* Applicabile toggle */}
                    <TableCell className="text-center">
                      <button
                        type="button"
                        onClick={() =>
                          updateValutazione(val.id, {
                            applicabile: !val.applicabile,
                          })
                        }
                        className={cn(
                          "inline-flex h-6 w-10 items-center rounded-full transition-colors",
                          val.applicabile
                            ? "bg-primary"
                            : "bg-muted-foreground/30"
                        )}
                      >
                        <span
                          className={cn(
                            "inline-block h-4 w-4 rounded-full bg-white transition-transform",
                            val.applicabile
                              ? "translate-x-5"
                              : "translate-x-1"
                          )}
                        />
                      </button>
                    </TableCell>

                    {/* P slider */}
                    <TableCell>
                      {val.applicabile && (
                        <div className="flex flex-col items-center gap-1">
                          <input
                            type="range"
                            min={1}
                            max={4}
                            step={1}
                            value={p}
                            onChange={(e) =>
                              updateValutazione(val.id, {
                                probabilita_p: Number(
                                  e.target.value
                                ),
                              })
                            }
                            className="w-full accent-primary"
                          />
                          <span className="text-xs font-medium text-muted-foreground">
                            {p}
                          </span>
                        </div>
                      )}
                    </TableCell>

                    {/* D slider */}
                    <TableCell>
                      {val.applicabile && (
                        <div className="flex flex-col items-center gap-1">
                          <input
                            type="range"
                            min={1}
                            max={4}
                            step={1}
                            value={d}
                            onChange={(e) =>
                              updateValutazione(val.id, {
                                danno_d: Number(
                                  e.target.value
                                ),
                              })
                            }
                            className="w-full accent-primary"
                          />
                          <span className="text-xs font-medium text-muted-foreground">
                            {d}
                          </span>
                        </div>
                      )}
                    </TableCell>

                    {/* Indice */}
                    <TableCell className="text-center">
                      {val.applicabile && (
                        <div className="flex flex-col items-center gap-1">
                          <span className="text-lg font-bold">
                            {indice}
                          </span>
                          <div className="h-1.5 w-full max-w-[60px] overflow-hidden rounded-full bg-muted">
                            <div
                              className={cn(
                                "h-full rounded-full transition-all",
                                getIndiceBarColor(livello)
                              )}
                              style={{
                                width: `${((indice - 3) / 9) * 100}%`,
                              }}
                            />
                          </div>
                        </div>
                      )}
                    </TableCell>

                    {/* Livello */}
                    <TableCell className="text-center">
                      {val.applicabile && (
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs font-semibold",
                            getLivelloStyle(livello)
                          )}
                        >
                          {livello}
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {/* Legend */}
          <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
            <span className="font-medium">Legenda:</span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-green-500" />
              Accettabile (3-4)
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-yellow-500" />
              Modesto (5-6)
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-orange-500" />
              Grave (7-8)
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500" />
              Gravissimo (9-12)
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Reset confirmation dialog */}
      <Dialog
        open={resetDialogOpen}
        onOpenChange={(open) => setResetDialogOpen(open)}
      >
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>Reset al default</DialogTitle>
            <DialogDescription>
              Sei sicuro? I valori P/D correnti verranno sovrascritti con i
              valori predefiniti per il tipo
              {selectedAmbiente?.tipo
                ? ` "${selectedAmbiente.tipo}"`
                : ""}.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setResetDialogOpen(false)}
            >
              Annulla
            </Button>
            <Button
              onClick={() => {
                applyDefaults();
                setResetDialogOpen(false);
              }}
            >
              Conferma Reset
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
