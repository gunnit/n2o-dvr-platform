"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  FormProvider,
  useFieldArray,
  useForm,
  useFormContext,
  type UseFormReturn,
} from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { IncendioAreaCard } from "./incendio-area-card";

// ---------------------------------------------------------------------------
// Domain model — mirrors backend/app/services/risk_calculator.py::calculate_fire_risk.
// Score bands: 3-4 = Basso, 5-7 = Medio, 8-9 = Alto.
// ---------------------------------------------------------------------------

export type FireLivello = "Basso" | "Medio" | "Alto";
export type FireScore = 1 | 2 | 3;

export interface AreaResult {
  nome: string;
  inf?: FireScore;
  si?: FireScore;
  pi?: FireScore;
  totale: number | null;
  livello: FireLivello | null;
  complete: boolean;
}

export interface IncendioResult {
  areas: AreaResult[];
  maxLivello: FireLivello | null;
  allComplete: boolean;
}

export function livelloFor(totale: number): FireLivello {
  if (totale <= 4) return "Basso";
  if (totale <= 7) return "Medio";
  return "Alto";
}

export function computeArea(values: {
  nome: string;
  inf?: number;
  si?: number;
  pi?: number;
}): AreaResult {
  const { nome, inf, si, pi } = values;
  if (inf === undefined || si === undefined || pi === undefined) {
    return {
      nome,
      inf: inf as FireScore | undefined,
      si: si as FireScore | undefined,
      pi: pi as FireScore | undefined,
      totale: null,
      livello: null,
      complete: false,
    };
  }
  const totale = inf + si + pi;
  return {
    nome,
    inf: inf as FireScore,
    si: si as FireScore,
    pi: pi as FireScore,
    totale,
    livello: livelloFor(totale),
    complete: true,
  };
}

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

const RANGE_MSG = "Valore consentito: 1-3";

export const areaSchema = z.object({
  nome: z.string().min(1, "Nome area richiesto"),
  inf: z
    .number({ message: RANGE_MSG })
    .int(RANGE_MSG)
    .min(1, RANGE_MSG)
    .max(3, RANGE_MSG),
  si: z
    .number({ message: RANGE_MSG })
    .int(RANGE_MSG)
    .min(1, RANGE_MSG)
    .max(3, RANGE_MSG),
  pi: z
    .number({ message: RANGE_MSG })
    .int(RANGE_MSG)
    .min(1, RANGE_MSG)
    .max(3, RANGE_MSG),
});

export const incendioFormSchema = z.object({
  areas: z.array(areaSchema).min(1, "Almeno un'area è richiesta"),
});

export type IncendioFormValues = z.infer<typeof incendioFormSchema>;

export const DEFAULT_AREA: IncendioFormValues["areas"][number] = {
  nome: "",
  inf: 1,
  si: 1,
  pi: 1,
};

// ---------------------------------------------------------------------------
// Band color tokens (shared across page/measures/banner — keep in sync with
// cross-cutting palette emerald/amber/rose).
// ---------------------------------------------------------------------------

export const BAND_CLASS: Record<FireLivello, string> = {
  Basso:
    "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30",
  Medio:
    "bg-amber-500/15 text-amber-800 ring-amber-500/30",
  Alto: "bg-rose-500/15 text-rose-700 ring-rose-500/30",
};

// ---------------------------------------------------------------------------
// Hook helper — exposes the typed form so the page can build buttons + submit.
// ---------------------------------------------------------------------------

export interface UseIncendioFormOptions {
  initial?: IncendioFormValues;
}

export function useIncendioForm(
  options: UseIncendioFormOptions = {},
): UseFormReturn<IncendioFormValues> {
  const { initial } = options;
  return useForm<IncendioFormValues>({
    resolver: zodResolver(incendioFormSchema),
    defaultValues: initial ?? { areas: [{ ...DEFAULT_AREA }] },
    mode: "onChange",
  });
}

// ---------------------------------------------------------------------------
// Compute helpers for external consumers (page owns max livello badge, VVF
// banner, etc.).
// ---------------------------------------------------------------------------

export function computeIncendioResult(values: IncendioFormValues): IncendioResult {
  const areas = values.areas.map((a) => computeArea(a));
  const levels = areas
    .map((a) => a.livello)
    .filter((l): l is FireLivello => l !== null);
  let maxLivello: FireLivello | null = null;
  if (levels.includes("Alto")) maxLivello = "Alto";
  else if (levels.includes("Medio")) maxLivello = "Medio";
  else if (levels.includes("Basso")) maxLivello = "Basso";
  return {
    areas,
    maxLivello,
    allComplete: areas.length > 0 && areas.every((a) => a.complete),
  };
}

// ---------------------------------------------------------------------------
// Main form
// ---------------------------------------------------------------------------

export interface IncendioFormProps {
  form: UseFormReturn<IncendioFormValues>;
  onResultChange?: (result: IncendioResult) => void;
}

export function IncendioForm({ form, onResultChange }: IncendioFormProps) {
  const { control, watch } = form;
  const { fields, append, remove } = useFieldArray({
    control,
    name: "areas",
  });

  const watched = watch();
  const result = useMemo(() => computeIncendioResult(watched), [watched]);

  // H-02 (US-3.12): `computeIncendioResult` always returns a fresh object,
  // and the parent's setState tends to land in a state object that — even
  // when shallow-equal — looks different to React by reference. That tripped
  // an infinite render loop (48+ "Maximum update depth exceeded" logs on
  // every interaction). Key the effect off a stable content-hash instead of
  // the object reference so the parent is only notified when the result
  // actually changes.
  const lastHashRef = useRef<string>("");
  const resultHash = useMemo(() => {
    const parts = [
      result.maxLivello ?? "",
      result.allComplete ? "1" : "0",
      ...result.areas.map(
        (a) =>
          `${a.nome}|${a.inf ?? ""}|${a.si ?? ""}|${a.pi ?? ""}|${a.totale ?? ""}|${a.livello ?? ""}`,
      ),
    ];
    return parts.join("§");
  }, [result]);

  useEffect(() => {
    if (lastHashRef.current === resultHash) return;
    lastHashRef.current = resultHash;
    onResultChange?.(result);
    // `result` is intentionally excluded — the hash captures its content,
    // and including `result` would re-fire the effect on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resultHash, onResultChange]);

  const handleAdd = () => {
    append({ ...DEFAULT_AREA, nome: "" });
  };

  const handleDuplicate = (index: number) => {
    const current = watched.areas[index];
    if (!current) return;
    append({
      nome: "",
      inf: current.inf,
      si: current.si,
      pi: current.pi,
    });
  };

  const handleRemove = (index: number) => {
    if (fields.length <= 1) return;
    const areaName = watched.areas[index]?.nome || `#${index + 1}`;
    const ok = window.confirm(
      `Rimuovere l'area "${areaName}"? L'operazione non può essere annullata.`,
    );
    if (ok) remove(index);
  };

  return (
    <FormProvider {...form}>
      <div className="space-y-6">
        <IncendioOverview result={result} />

        <div className="space-y-4">
          {fields.map((field, index) => {
            const area = result.areas[index];
            return (
              <IncendioAreaCard
                key={field.id}
                index={index}
                totalAreas={fields.length}
                result={area}
                onDuplicate={() => handleDuplicate(index)}
                onRemove={() => handleRemove(index)}
              />
            );
          })}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 p-4">
          <div className="text-xs text-muted-foreground">
            {result.allComplete
              ? `${fields.length} area/e compilate · livello massimo ${result.maxLivello ?? "-"}.`
              : "Completa INF, SI e PI per ciascuna area per ottenere il livello."}
          </div>
          <Button type="button" variant="outline" onClick={handleAdd}>
            Aggiungi area
          </Button>
        </div>
      </div>
    </FormProvider>
  );
}

// ---------------------------------------------------------------------------
// Overview card (sticky summary) — reads via useFormContext so children can
// still trigger rerenders without prop-drilling.
// ---------------------------------------------------------------------------

function IncendioOverview({ result }: { result: IncendioResult }) {
  useFormContext<IncendioFormValues>(); // ensure the hook is mounted

  return (
    <Card className="sticky top-4 z-10 shadow-sm">
      <CardHeader className="border-b">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base">Livello di rischio incendio</CardTitle>
            <p className="text-xs text-muted-foreground">
              Formula: INF + SI + PI (ciascuno 1-3) · D.M. 03/09/2021
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-2xl font-semibold tabular-nums">
                {result.areas.length}
              </div>
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                aree
              </div>
            </div>
            {result.maxLivello ? (
              <span
                className={cn(
                  "inline-flex items-center rounded-md px-3 py-1 text-sm font-medium ring-1",
                  BAND_CLASS[result.maxLivello],
                )}
              >
                livello massimo: {result.maxLivello}
              </span>
            ) : (
              <Badge variant="secondary" className="px-3 py-1 text-sm">
                incompleto
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <ul className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
          {result.areas.map((a, i) => (
            <li
              key={i}
              className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2"
            >
              <span className="truncate text-muted-foreground">
                {a.nome || `Area ${i + 1}`}
              </span>
              {a.livello ? (
                <span
                  className={cn(
                    "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium ring-1",
                    BAND_CLASS[a.livello],
                  )}
                >
                  {a.livello} · {a.totale}/9
                </span>
              ) : (
                <span className="text-muted-foreground">incompleta</span>
              )}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
