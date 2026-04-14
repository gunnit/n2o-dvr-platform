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
];

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
        <CardHeader>
          <CardTitle className="text-base">
            {selectedAmbiente?.nome || "Ambiente"}
            {selectedAmbiente?.tipo
              ? ` (${selectedAmbiente.tipo})`
              : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
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
              {currentValutazioni.map((val) => {
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
    </div>
  );
}
