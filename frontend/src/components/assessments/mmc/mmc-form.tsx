"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  useForm,
  useFieldArray,
  useWatch,
  type UseFormReturn,
} from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

import { MmcCpOverride } from "./mmc-cp-override";
import { MmcLiftRow } from "./mmc-lift-row";
import { MmcMeasures } from "./mmc-measures";

// ---------------------------------------------------------------------------
// NIOSH multi-lift form — US-3.1 / US-3.2 / US-3.3
// The backend `POST /api/v1/calculate/niosh` remains the source of truth.
// `computeLift` below is a local echo used while the network is quiet.
// ---------------------------------------------------------------------------

// Factor A -- Fattore Altezza
export const NIOSH_FACTOR_A: Array<[number, number]> = [
  [0, 0.78],
  [25, 0.85],
  [50, 0.93],
  [75, 1.0],
  [100, 0.93],
  [125, 0.85],
  [150, 0.78],
  [175, 0.0],
];

// Factor B -- Fattore Dislocazione Verticale
export const NIOSH_FACTOR_B: Array<[number, number]> = [
  [25, 1.0],
  [30, 0.97],
  [40, 0.93],
  [50, 0.91],
  [70, 0.88],
  [100, 0.87],
  [170, 0.85],
  [175, 0.0],
];

// Factor C -- Fattore Orizzontale
export const NIOSH_FACTOR_C: Array<[number, number]> = [
  [25, 1.0],
  [30, 0.83],
  [40, 0.63],
  [50, 0.5],
  [55, 0.45],
  [60, 0.42],
  [63, 0.0],
];

// Factor D -- Fattore Dislocazione Angolare
export const NIOSH_FACTOR_D: Array<[number, number]> = [
  [0, 1.0],
  [30, 0.9],
  [60, 0.81],
  [90, 0.71],
  [120, 0.62],
  [135, 0.57],
  [180, 0.0],
];

type GripKey = "buona" | "discreta" | "scarsa";
const NIOSH_FACTOR_E: Record<GripKey, number> = {
  buona: 1.0,
  discreta: 0.95,
  scarsa: 0.9,
};

type DurationKey = "breve" | "media" | "lunga";
const NIOSH_FACTOR_F_BREAKS = [
  0.2, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
];
const NIOSH_FACTOR_F: Record<number, Record<DurationKey, number>> = {
  0.2: { breve: 1.0, media: 0.95, lunga: 0.85 },
  0.5: { breve: 0.97, media: 0.92, lunga: 0.81 },
  1: { breve: 0.94, media: 0.88, lunga: 0.75 },
  2: { breve: 0.91, media: 0.84, lunga: 0.65 },
  3: { breve: 0.88, media: 0.79, lunga: 0.55 },
  4: { breve: 0.84, media: 0.72, lunga: 0.45 },
  5: { breve: 0.8, media: 0.6, lunga: 0.35 },
  6: { breve: 0.75, media: 0.5, lunga: 0.27 },
  7: { breve: 0.7, media: 0.42, lunga: 0.22 },
  8: { breve: 0.6, media: 0.35, lunga: 0.18 },
  9: { breve: 0.52, media: 0.3, lunga: 0.15 },
  10: { breve: 0.45, media: 0.26, lunga: 0.13 },
  11: { breve: 0.41, media: 0.23, lunga: 0.0 },
  12: { breve: 0.37, media: 0.21, lunga: 0.0 },
  13: { breve: 0.34, media: 0.0, lunga: 0.0 },
  14: { breve: 0.31, media: 0.0, lunga: 0.0 },
  15: { breve: 0.28, media: 0.0, lunga: 0.0 },
};

function interp(table: Array<[number, number]>, x: number): number {
  if (!isFinite(x)) return 0;
  if (x <= table[0][0]) return table[0][1];
  if (x >= table[table.length - 1][0]) return table[table.length - 1][1];
  for (let i = 0; i < table.length - 1; i++) {
    const [x0, y0] = table[i];
    const [x1, y1] = table[i + 1];
    if (x >= x0 && x <= x1) {
      if (x1 === x0) return y0;
      return y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
    }
  }
  return 0;
}

function lookupFactorF(freq: number, duration: DurationKey): number {
  if (!isFinite(freq) || freq < 0) return 0;
  if (freq <= NIOSH_FACTOR_F_BREAKS[0]) {
    return NIOSH_FACTOR_F[NIOSH_FACTOR_F_BREAKS[0]][duration];
  }
  for (const brk of NIOSH_FACTOR_F_BREAKS) {
    if (freq <= brk) return NIOSH_FACTOR_F[brk][duration];
  }
  return 0;
}

// ---------------------------------------------------------------------------
// Schema + types
// ---------------------------------------------------------------------------

const liftSchema = z.object({
  name: z.string(),
  altezza: z
    .number({ message: "Valore consentito: 0-175 cm" })
    .min(0, "Valore consentito: 0-175 cm")
    .max(175, "Valore consentito: 0-175 cm"),
  dislocazione: z
    .number({ message: "Valore consentito: 0-175 cm" })
    .min(0, "Valore consentito: 0-175 cm")
    .max(175, "Valore consentito: 0-175 cm"),
  distanza: z
    .number({ message: "Valore consentito: 25-63 cm" })
    .min(25, "Valore consentito: 25-63 cm")
    .max(63, "Valore consentito: 25-63 cm"),
  angolo: z
    .number({ message: "Valore consentito: 0-135 gradi" })
    .min(0, "Valore consentito: 0-135 gradi")
    .max(135, "Valore consentito: 0-135 gradi"),
  presa: z.enum(["buona", "discreta", "scarsa"]),
  frequenza: z
    .number({ message: "Valore consentito: 0.2-15 atti/min" })
    .min(0.2, "Valore consentito: 0.2-15 atti/min")
    .max(15, "Valore consentito: 0.2-15 atti/min"),
  durata: z.enum(["breve", "media", "lunga"]),
  peso_reale: z
    .number({ message: "Il peso deve essere > 0 kg" })
    .positive("Il peso deve essere > 0 kg"),
});

export const mmcFormSchema = z.object({
  worker_sesso: z.enum(["M", "F"]),
  worker_eta: z
    .number({ message: "Eta non valida (15-70)" })
    .int("Eta non valida (15-70)")
    .min(15, "Eta non valida (15-70)")
    .max(70, "Eta non valida (15-70)"),
  cp_override: z.number().positive("CP deve essere > 0").optional(),
  cp_motivazione: z.string().optional(),
  lifts: z.array(liftSchema).min(1, "Almeno un sollevamento e richiesto"),
  measures: z.array(z.string()).optional(),
});

/**
 * Cross-field validation: when cp_override is set the motivazione must be
 * at least 5 characters. Called from the submit handler so we can set a
 * field-level error on cp_motivazione when the guard fails.
 */
export function validateCpOverride(v: MmcFormValues): string | null {
  if (v.cp_override === undefined) return null;
  if ((v.cp_motivazione?.length ?? 0) >= 5) return null;
  return "Motivazione richiesta (min. 5 caratteri) per modificare il CP";
}

export type MmcFormValues = z.infer<typeof mmcFormSchema>;
export type LiftValues = z.infer<typeof liftSchema>;

export type Zona = "VERDE" | "GIALLA" | "ROSSA";

export interface LiftResult {
  plr: number;
  ir: number;
  zona: Zona;
  a: number;
  b: number;
  c: number;
  d: number;
  e: number;
  f: number;
}

export interface MmcResult {
  perLift: LiftResult[];
  worst: LiftResult | null;
  unanswered: string[];
  cp: number;
}

// Legacy alias kept for the page component until Task A1.7 rewrites it.
export type MmcInputs = MmcFormValues;

function bandFor(ir: number, plr: number, peso: number): Zona {
  if (plr <= 0 && peso > 0) return "ROSSA";
  if (ir <= 0.75) return "VERDE";
  if (ir <= 1.0) return "GIALLA";
  return "ROSSA";
}

export function computeLift(cp: number, l: LiftValues): LiftResult {
  const a = interp(NIOSH_FACTOR_A, l.altezza);
  const b = interp(NIOSH_FACTOR_B, l.dislocazione);
  const c = interp(NIOSH_FACTOR_C, l.distanza);
  const d = interp(NIOSH_FACTOR_D, l.angolo);
  const e = NIOSH_FACTOR_E[l.presa];
  const f = lookupFactorF(l.frequenza, l.durata);
  const plr = cp * a * b * c * d * e * f;
  const ir = plr > 0 ? l.peso_reale / plr : l.peso_reale > 0 ? Infinity : 0;
  return { a, b, c, d, e, f, plr, ir, zona: bandFor(ir, plr, l.peso_reale) };
}

export function computeMmc(values: MmcFormValues, effectiveCp?: number): MmcResult {
  const cp = effectiveCp ?? values.cp_override ?? 0;
  const perLift = (values.lifts ?? []).map((l) => computeLift(cp, l));
  let worst: LiftResult | null = null;
  for (const r of perLift) {
    if (!worst || r.ir > worst.ir) worst = r;
  }
  return { perLift, worst, unanswered: [], cp };
}

export const DEFAULT_LIFT: LiftValues = {
  name: "",
  altezza: 75,
  dislocazione: 25,
  distanza: 40,
  angolo: 0,
  presa: "buona",
  frequenza: 1,
  durata: "breve",
  peso_reale: 15,
};

export const DEFAULT_INPUTS: MmcFormValues = {
  worker_sesso: "M",
  worker_eta: 30,
  cp_override: undefined,
  cp_motivazione: "",
  lifts: [DEFAULT_LIFT],
  measures: [],
};

// ---------------------------------------------------------------------------
// Main form
// ---------------------------------------------------------------------------

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const h = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(h);
  }, [value, delayMs]);
  return debounced;
}

function LiftWatcher({
  form,
  index,
  cp,
  onResult,
}: {
  form: UseFormReturn<MmcFormValues>;
  index: number;
  cp: number | null;
  onResult: (index: number, r: LiftResult | null) => void;
}) {
  const lift = useWatch({ control: form.control, name: `lifts.${index}` });
  const debounced = useDebouncedValue(lift, 350);

  useEffect(() => {
    if (cp == null || cp <= 0 || !debounced) {
      onResult(index, null);
      return;
    }
    const local = computeLift(cp, debounced as LiftValues);
    const anyZero =
      local.a <= 0 ||
      local.b <= 0 ||
      local.c <= 0 ||
      local.d <= 0 ||
      local.e <= 0 ||
      local.f <= 0 ||
      (debounced as LiftValues).peso_reale <= 0;
    if (anyZero) {
      onResult(index, local);
      return;
    }
    const ctrl = new AbortController();
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${apiUrl}/api/v1/calculate/niosh`, {
      method: "POST",
      signal: ctrl.signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        peso_sollevato: (debounced as LiftValues).peso_reale,
        cp,
        fattore_a: local.a,
        fattore_b: local.b,
        fattore_c: local.c,
        fattore_d: local.d,
        fattore_e: local.e,
        fattore_f: local.f,
      }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d: { plr: number; ir: number; livello: string }) => {
        const zona: Zona =
          d.livello === "GREEN"
            ? "VERDE"
            : d.livello === "YELLOW"
            ? "GIALLA"
            : "ROSSA";
        onResult(index, { ...local, plr: d.plr, ir: d.ir, zona });
      })
      .catch(() => onResult(index, local));
    return () => ctrl.abort();
  }, [cp, debounced, index, onResult]);

  return null;
}

export interface MmcFormProps {
  aziendaId?: string;
  initialValues?: Partial<MmcFormValues>;
  finalizing?: boolean;
  onResult?: (r: MmcResult) => void;
  onFinalize?: (v: MmcFormValues, r: MmcResult) => void;
  // Legacy listeners kept for existing page — invoked on each change.
  onResultChange?: (r: MmcResult) => void;
  onInputsChange?: (v: MmcFormValues) => void;
}

export function MmcForm({
  initialValues,
  finalizing = false,
  onResult,
  onFinalize,
  onResultChange,
  onInputsChange,
}: MmcFormProps) {
  const form = useForm<MmcFormValues>({
    resolver: zodResolver(mmcFormSchema),
    defaultValues: { ...DEFAULT_INPUTS, ...(initialValues ?? {}) },
    mode: "onBlur",
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "lifts",
  });

  const [autoCp, setAutoCp] = useState<number | null>(null);
  const cpOverride = form.watch("cp_override");
  const effectiveCp = cpOverride ?? autoCp;

  const [perLiftResults, setPerLiftResults] = useState<(LiftResult | null)[]>([]);

  const handleLiftResult = useCallback(
    (index: number, r: LiftResult | null) => {
      setPerLiftResults((prev) => {
        const next = [...prev];
        while (next.length <= index) next.push(null);
        next[index] = r;
        return next;
      });
    },
    [],
  );

  useEffect(() => {
    setPerLiftResults((prev) => prev.slice(0, fields.length));
  }, [fields.length]);

  const worst = useMemo<LiftResult | null>(() => {
    let w: LiftResult | null = null;
    for (const r of perLiftResults) {
      if (!r) continue;
      if (!w || r.ir > w.ir) w = r;
    }
    return w;
  }, [perLiftResults]);

  const aggregate = useMemo<MmcResult>(
    () => ({
      perLift: perLiftResults.filter((r): r is LiftResult => r !== null),
      worst,
      unanswered: [],
      cp: effectiveCp ?? 0,
    }),
    [perLiftResults, worst, effectiveCp],
  );

  useEffect(() => {
    onResult?.(aggregate);
    onResultChange?.(aggregate);
  }, [aggregate, onResult, onResultChange]);

  const watchedValues = form.watch();
  const watchedSerialized = JSON.stringify(watchedValues);
  useEffect(() => {
    onInputsChange?.(watchedValues);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchedSerialized]);

  const onSubmit = form.handleSubmit((v) => {
    const cpErr = validateCpOverride(v);
    if (cpErr) {
      form.setError("cp_motivazione", { type: "manual", message: cpErr });
      return;
    }
    onFinalize?.(v, aggregate);
  });

  const isDirty = form.formState.isDirty;

  return (
    <form onSubmit={onSubmit} className="space-y-6" noValidate>
      <Card className="sticky top-4 z-10 shadow-sm">
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">
                Indice di Sollevamento (IR)
              </CardTitle>
              <CardDescription className="text-xs">
                NIOSH ISO 11228-1 · PLR = CP x A x B x C x D x E x F · IR = Peso / PLR
              </CardDescription>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-2xl font-semibold tabular-nums">
                  {worst == null
                    ? "—"
                    : isFinite(worst.ir)
                    ? worst.ir.toFixed(2)
                    : "∞"}
                </div>
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  IR peggiore
                </div>
              </div>
              {worst && (
                <Badge
                  className={cn(
                    "px-3 py-1 text-sm ring-1",
                    worst.zona === "VERDE" &&
                      "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30",
                    worst.zona === "GIALLA" &&
                      "bg-amber-500/15 text-amber-800 ring-amber-500/30",
                    worst.zona === "ROSSA" &&
                      "bg-rose-500/15 text-rose-700 ring-rose-500/30",
                  )}
                >
                  {worst.zona}
                </Badge>
              )}
              {isDirty && (
                <Badge variant="outline" className="text-xs">
                  Modifiche non salvate
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
      </Card>

      <MmcCpOverride form={form} onAutoCpChange={setAutoCp} />

      {fields.map((f, i) => (
        <LiftWatcher
          key={`${f.id}-watch`}
          form={form}
          index={i}
          cp={effectiveCp}
          onResult={handleLiftResult}
        />
      ))}

      <div className="space-y-4">
        {fields.map((f, i) => (
          <MmcLiftRow
            key={f.id}
            index={i}
            control={form.control}
            register={form.register}
            errors={form.formState.errors}
            result={perLiftResults[i] ?? undefined}
            onRemove={() => remove(i)}
            canRemove={fields.length > 1}
          />
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={() => append({ ...DEFAULT_LIFT })}
        >
          <Plus className="mr-2 h-4 w-4" /> Aggiungi sollevamento
        </Button>
        {form.formState.errors.lifts?.message && (
          <p className="text-xs text-rose-600">
            {form.formState.errors.lifts.message}
          </p>
        )}
      </div>

      <MmcMeasures form={form} visible={worst?.zona === "ROSSA"} />

      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div>
            <p className="text-sm font-medium">Conferma valutazione</p>
            <p className="text-xs text-muted-foreground">
              {worst
                ? `IR peggiore ${
                    isFinite(worst.ir) ? worst.ir.toFixed(2) : "∞"
                  } · zona ${worst.zona}`
                : "Compila i parametri e salva la valutazione."}
            </p>
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={finalizing}>
              {finalizing ? "Salvataggio in corso..." : "Salva valutazione"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </form>
  );
}
