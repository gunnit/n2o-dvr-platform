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
// NIOSH reference data — mirrors backend/app/services/reference_data.py
// so the UI can score instantly. The backend is the source of truth: we
// re-POST on finalize to confirm.
// ---------------------------------------------------------------------------

// Factor A -- Fattore Altezza (height from floor, cm at start of lift)
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

// Factor B -- Fattore Dislocazione Verticale (vertical displacement, cm)
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

// Factor C -- Fattore Orizzontale (horizontal distance, cm)
export const NIOSH_FACTOR_C: Array<[number, number]> = [
  [25, 1.0],
  [30, 0.83],
  [40, 0.63],
  [50, 0.5],
  [55, 0.45],
  [60, 0.42],
  [63, 0.0],
];

// Factor D -- Fattore Dislocazione Angolare (asymmetry, degrees)
export const NIOSH_FACTOR_D: Array<[number, number]> = [
  [0, 1.0],
  [30, 0.9],
  [60, 0.81],
  [90, 0.71],
  [120, 0.62],
  [135, 0.57],
  [180, 0.0],
];

// Factor E -- Fattore Presa (grip quality)
export type GripQuality = "Buona" | "Sufficiente" | "Scarsa";
export const NIOSH_FACTOR_E: Record<GripQuality, number> = {
  Buona: 1.0,
  Sufficiente: 0.95,
  Scarsa: 0.9,
};

// Factor F -- Fattore Frequenza (lifts/min × duration bucket)
export type DurationBucket = "breve" | "media" | "lunga";
export const NIOSH_FACTOR_F_BREAKS: number[] = [
  0.2, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
];
export const NIOSH_FACTOR_F: Record<number, Record<DurationBucket, number>> = {
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
  16: { breve: 0.0, media: 0.0, lunga: 0.0 },
};

// CP -- Costante di Peso
export type Sex = "M" | "F";
export type AgeBucket = ">18" | "15-18";
export const NIOSH_CP: Record<AgeBucket, Record<Sex, number>> = {
  ">18": { M: 25.0, F: 20.0 },
  "15-18": { M: 15.0, F: 10.0 },
};

// ---------------------------------------------------------------------------
// Lookup / interpolation helpers
// ---------------------------------------------------------------------------

/**
 * Linear interpolation over a sorted [x, y] table, clamped at ends.
 */
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

function lookupFactorF(freq: number, duration: DurationBucket): number {
  if (!isFinite(freq) || freq < 0) return 0;
  // Snap to the nearest breakpoint at or above the input frequency.
  // Values below 0.2 are treated as 0.2 (minimum), values above 16 return 0.
  if (freq <= NIOSH_FACTOR_F_BREAKS[0]) {
    return NIOSH_FACTOR_F[NIOSH_FACTOR_F_BREAKS[0]][duration];
  }
  for (const brk of NIOSH_FACTOR_F_BREAKS) {
    if (freq <= brk) {
      return NIOSH_FACTOR_F[brk][duration];
    }
  }
  return 0;
}

// ---------------------------------------------------------------------------
// Form state + derived result
// ---------------------------------------------------------------------------

export interface MmcInputs {
  sex: Sex;
  age: AgeBucket;
  peso_sollevato: number | null;
  altezza_cm: number | null;
  dislocazione_cm: number | null;
  distanza_cm: number | null;
  angolo_deg: number | null;
  presa: GripQuality;
  frequenza: number | null;
  durata: DurationBucket;
}

export const DEFAULT_INPUTS: MmcInputs = {
  sex: "M",
  age: ">18",
  peso_sollevato: null,
  altezza_cm: null,
  dislocazione_cm: null,
  distanza_cm: null,
  angolo_deg: null,
  presa: "Buona",
  frequenza: null,
  durata: "breve",
};

export type Livello = "VERDE" | "GIALLA" | "ROSSA";

export interface MmcResult {
  cp: number;
  a: number;
  b: number;
  c: number;
  d: number;
  e: number;
  f: number;
  plr: number;
  ir: number;
  livello: Livello;
  unanswered: string[];
}

export function computeMmc(inputs: MmcInputs): MmcResult {
  const cp = NIOSH_CP[inputs.age][inputs.sex];
  const a = inputs.altezza_cm != null ? interp(NIOSH_FACTOR_A, inputs.altezza_cm) : 0;
  const b =
    inputs.dislocazione_cm != null ? interp(NIOSH_FACTOR_B, inputs.dislocazione_cm) : 0;
  const c = inputs.distanza_cm != null ? interp(NIOSH_FACTOR_C, inputs.distanza_cm) : 0;
  const d = inputs.angolo_deg != null ? interp(NIOSH_FACTOR_D, inputs.angolo_deg) : 0;
  const e = NIOSH_FACTOR_E[inputs.presa];
  const f = inputs.frequenza != null ? lookupFactorF(inputs.frequenza, inputs.durata) : 0;

  const unanswered: string[] = [];
  if (inputs.peso_sollevato == null) unanswered.push("peso_sollevato");
  if (inputs.altezza_cm == null) unanswered.push("altezza_cm");
  if (inputs.dislocazione_cm == null) unanswered.push("dislocazione_cm");
  if (inputs.distanza_cm == null) unanswered.push("distanza_cm");
  if (inputs.angolo_deg == null) unanswered.push("angolo_deg");
  if (inputs.frequenza == null) unanswered.push("frequenza");

  const plr = cp * a * b * c * d * e * f;
  const peso = inputs.peso_sollevato ?? 0;
  const ir = plr > 0 ? peso / plr : peso > 0 ? Infinity : 0;

  let livello: Livello;
  if (plr <= 0 && peso > 0) livello = "ROSSA";
  else if (ir <= 0.75) livello = "VERDE";
  else if (ir <= 1.0) livello = "GIALLA";
  else livello = "ROSSA";

  return { cp, a, b, c, d, e, f, plr, ir, livello, unanswered };
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

const BAND_CLASS: Record<Livello, string> = {
  VERDE: "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30 dark:text-emerald-400",
  GIALLA: "bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-300",
  ROSSA: "bg-rose-500/15 text-rose-700 ring-rose-500/30 dark:text-rose-400",
};

const BAND_TITLE: Record<Livello, string> = {
  VERDE: "Accettabile",
  GIALLA: "Da ridurre",
  ROSSA: "Non accettabile",
};

const BAND_DESCRIPTION: Record<Livello, string> = {
  VERDE: "Situazione accettabile.",
  GIALLA:
    "Situazione si avvicina ai limiti; 1-10% della popolazione potrebbe essere a rischio.",
  ROSSA: "Rischio per quote crescenti di popolazione.",
};

const BAND_ACTION: Record<Livello, string> = {
  VERDE: "Nessun intervento specifico richiesto.",
  GIALLA:
    "Attivare sorveglianza sanitaria, formazione specifica, interventi strutturali.",
  ROSSA:
    "Intervento di prevenzione primaria: riprogettazione postazioni, riduzione carichi, ausili meccanici.",
};

function LivelloBadge({
  livello,
  className,
}: {
  livello: Livello;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 transition-colors",
        BAND_CLASS[livello],
        className,
      )}
    >
      {livello}
    </span>
  );
}

function ChoiceButton({
  label,
  active,
  onClick,
  tone,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  tone?: "danger" | "neutral";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-md px-2.5 py-1 text-xs font-medium ring-1 transition-colors",
        active
          ? tone === "danger"
            ? "bg-rose-500/15 text-rose-700 ring-rose-500/40 dark:text-rose-400"
            : "bg-primary/10 text-primary ring-primary/40"
          : "bg-background text-muted-foreground ring-border hover:bg-muted",
      )}
    >
      {label}
    </button>
  );
}

// Numeric field with live derived factor readout
function NumericField({
  label,
  suffix,
  value,
  onChange,
  placeholder,
  factorLabel,
  factorValue,
  hint,
  step,
  min,
  max,
}: {
  label: string;
  suffix: string;
  value: number | null;
  onChange: (v: number | null) => void;
  placeholder?: string;
  factorLabel: string;
  factorValue: number;
  hint?: string;
  step?: string;
  min?: number;
  max?: number;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <Label className="text-xs">
          {label}
          <span className="ml-1 font-normal text-muted-foreground">({suffix})</span>
        </Label>
        <span className="text-[11px] text-muted-foreground tabular-nums">
          {factorLabel}{" "}
          <span
            className={cn(
              "font-medium",
              value == null
                ? "text-muted-foreground"
                : factorValue === 0
                ? "text-rose-600 dark:text-rose-400"
                : "text-foreground",
            )}
          >
            {value == null ? "—" : factorValue.toFixed(2)}
          </span>
        </span>
      </div>
      <Input
        type="number"
        inputMode="decimal"
        step={step ?? "0.1"}
        min={min}
        max={max}
        placeholder={placeholder}
        value={value ?? ""}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") {
            onChange(null);
          } else {
            const n = Number(raw);
            onChange(isNaN(n) ? null : n);
          }
        }}
      />
      {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface MmcFormProps {
  aziendaId: string;
  onResultChange?: (result: MmcResult) => void;
  onInputsChange?: (inputs: MmcInputs) => void;
}

export function MmcForm({ aziendaId, onResultChange, onInputsChange }: MmcFormProps) {
  const storageKey = `mmc-draft-${aziendaId}`;

  const [inputs, setInputs] = useState<MmcInputs>(DEFAULT_INPUTS);

  // Hydrate from localStorage on mount or aziendaId change
  useEffect(() => {
    try {
      const raw =
        typeof window !== "undefined" ? window.localStorage.getItem(storageKey) : null;
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<MmcInputs>;
        setInputs({ ...DEFAULT_INPUTS, ...parsed });
      } else {
        setInputs(DEFAULT_INPUTS);
      }
    } catch {
      setInputs(DEFAULT_INPUTS);
    }
  }, [storageKey]);

  // Persist on change
  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(inputs));
    } catch {
      // ignore quota / privacy mode errors
    }
  }, [inputs, storageKey]);

  const result = useMemo(() => computeMmc(inputs), [inputs]);

  useEffect(() => {
    onResultChange?.(result);
  }, [result, onResultChange]);

  useEffect(() => {
    onInputsChange?.(inputs);
  }, [inputs, onInputsChange]);

  const setField = useCallback(
    <K extends keyof MmcInputs>(key: K, value: MmcInputs[K]) => {
      setInputs((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const resetDraft = useCallback(() => {
    setInputs(DEFAULT_INPUTS);
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
  }, [storageKey]);

  const peso = inputs.peso_sollevato ?? 0;
  const pesoForDisplay = peso > 0 ? peso : null;
  const allAnswered = result.unanswered.length === 0;

  return (
    <div className="space-y-6">
      {/* Sticky result widget */}
      <Card className="sticky top-4 z-10 shadow-sm">
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">
                Indice di Sollevamento (IR)
              </CardTitle>
              <CardDescription className="text-xs">
                NIOSH ISO 11228-1 · PLR = CP × A × B × C × D × E × F · IR = Peso / PLR
              </CardDescription>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-2xl font-semibold tabular-nums">
                  {pesoForDisplay == null || result.plr <= 0
                    ? "—"
                    : isFinite(result.ir)
                    ? result.ir.toFixed(2)
                    : "∞"}
                </div>
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  IR
                </div>
              </div>
              <LivelloBadge livello={result.livello} className="px-3 py-1 text-sm" />
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex-1 min-w-[180px]">
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className={cn(
                    "h-full transition-all duration-500",
                    result.livello === "VERDE" && "bg-emerald-500",
                    result.livello === "GIALLA" && "bg-amber-500",
                    result.livello === "ROSSA" && "bg-rose-500",
                  )}
                  style={{
                    width: `${Math.min(
                      100,
                      isFinite(result.ir) ? (result.ir / 1.5) * 100 : 100,
                    )}%`,
                  }}
                />
              </div>
              <div className="mt-1 flex justify-between text-[10px] uppercase tracking-wide text-muted-foreground">
                <span>0</span>
                <span>0.75</span>
                <span>1.00</span>
                <span>≥1.5</span>
              </div>
            </div>
            <Badge variant="secondary" className="gap-1 text-xs">
              <span className="tabular-nums">
                {pesoForDisplay == null || result.plr <= 0
                  ? "—"
                  : `PLR ${result.plr.toFixed(2)} kg`}
              </span>
            </Badge>
          </div>
          <div className="grid grid-cols-2 gap-2 pt-1 text-xs sm:grid-cols-4">
            <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
              <span className="text-muted-foreground">CP</span>
              <span className="font-medium tabular-nums">
                {result.cp.toFixed(2)} kg
              </span>
            </div>
            <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
              <span className="text-muted-foreground">A × B</span>
              <span className="font-medium tabular-nums">
                {(result.a * result.b).toFixed(2)}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
              <span className="text-muted-foreground">C × D</span>
              <span className="font-medium tabular-nums">
                {(result.c * result.d).toFixed(2)}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
              <span className="text-muted-foreground">E × F</span>
              <span className="font-medium tabular-nums">
                {(result.e * result.f).toFixed(2)}
              </span>
            </div>
          </div>
          <div
            className={cn(
              "rounded-md border p-3 text-xs",
              result.livello === "VERDE" &&
                "border-emerald-500/30 bg-emerald-500/5 text-emerald-900 dark:text-emerald-200",
              result.livello === "GIALLA" &&
                "border-amber-500/30 bg-amber-500/5 text-amber-900 dark:text-amber-200",
              result.livello === "ROSSA" &&
                "border-rose-500/30 bg-rose-500/5 text-rose-900 dark:text-rose-200",
            )}
          >
            <div className="font-medium">{BAND_TITLE[result.livello]}</div>
            <p className="mt-0.5">{BAND_DESCRIPTION[result.livello]}</p>
            <p className="mt-1 text-muted-foreground">{BAND_ACTION[result.livello]}</p>
          </div>
        </CardContent>
      </Card>

      {/* Worker + CP */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="text-sm">Lavoratore e Costante di Peso (CP)</CardTitle>
              <CardDescription className="text-xs">
                CP deriva da sesso e fascia d&apos;età secondo NIOSH ISO 11228-1.
              </CardDescription>
            </div>
            <Badge variant="outline" className="tabular-nums">
              CP {result.cp.toFixed(2)} kg
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 pt-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label className="text-xs">Sesso</Label>
            <div className="flex gap-1.5">
              <ChoiceButton
                label="Maschio"
                active={inputs.sex === "M"}
                onClick={() => setField("sex", "M")}
              />
              <ChoiceButton
                label="Femmina"
                active={inputs.sex === "F"}
                onClick={() => setField("sex", "F")}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-xs">Fascia d&apos;età</Label>
            <div className="flex gap-1.5">
              <ChoiceButton
                label="Adulto (>18)"
                active={inputs.age === ">18"}
                onClick={() => setField("age", ">18")}
              />
              <ChoiceButton
                label="Giovane (15-18)"
                active={inputs.age === "15-18"}
                onClick={() => setField("age", "15-18")}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Lifting parameters */}
      <Card>
        <CardHeader className="border-b">
          <CardTitle className="text-sm">Parametri di sollevamento</CardTitle>
          <CardDescription className="text-xs">
            Ogni parametro è convertito in un moltiplicatore (0.00 — 1.00) tramite
            le tabelle NIOSH. I valori 0.00 indicano una condizione fuori soglia.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-x-6 gap-y-4 pt-4 md:grid-cols-2">
          <NumericField
            label="Peso sollevato"
            suffix="kg"
            placeholder="es. 12"
            value={inputs.peso_sollevato}
            onChange={(v) => setField("peso_sollevato", v)}
            factorLabel="peso reale"
            factorValue={peso}
            min={0}
            step="0.1"
          />
          <NumericField
            label="Altezza inizio presa"
            suffix="cm dal suolo"
            placeholder="es. 75"
            value={inputs.altezza_cm}
            onChange={(v) => setField("altezza_cm", v)}
            factorLabel="fattore A ="
            factorValue={result.a}
            hint="Ottimale a 75 cm. Oltre 175 cm il fattore è nullo."
            min={0}
            max={200}
            step="1"
          />
          <NumericField
            label="Dislocazione verticale"
            suffix="cm"
            placeholder="es. 40"
            value={inputs.dislocazione_cm}
            onChange={(v) => setField("dislocazione_cm", v)}
            factorLabel="fattore B ="
            factorValue={result.b}
            hint="|altezza fine − altezza inizio|. Oltre 175 cm il fattore è nullo."
            min={0}
            max={200}
            step="1"
          />
          <NumericField
            label="Distanza orizzontale"
            suffix="cm caviglie-carico"
            placeholder="es. 30"
            value={inputs.distanza_cm}
            onChange={(v) => setField("distanza_cm", v)}
            factorLabel="fattore C ="
            factorValue={result.c}
            hint="Oltre 63 cm il fattore è nullo."
            min={0}
            max={100}
            step="1"
          />
          <NumericField
            label="Angolo di asimmetria"
            suffix="° torsione busto"
            placeholder="es. 0"
            value={inputs.angolo_deg}
            onChange={(v) => setField("angolo_deg", v)}
            factorLabel="fattore D ="
            factorValue={result.d}
            hint="Oltre 135° il fattore è nullo."
            min={0}
            max={180}
            step="5"
          />
          <NumericField
            label="Frequenza"
            suffix="atti/min"
            placeholder="es. 1"
            value={inputs.frequenza}
            onChange={(v) => setField("frequenza", v)}
            factorLabel="fattore F ="
            factorValue={result.f}
            hint="Combinato con la durata sotto."
            min={0}
            max={20}
            step="0.1"
          />

          {/* Grip quality */}
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between gap-2">
              <Label className="text-xs">Qualità della presa</Label>
              <span className="text-[11px] text-muted-foreground tabular-nums">
                fattore E ={" "}
                <span className="font-medium text-foreground">
                  {result.e.toFixed(2)}
                </span>
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {(["Buona", "Sufficiente", "Scarsa"] as GripQuality[]).map((g) => (
                <ChoiceButton
                  key={g}
                  label={g}
                  active={inputs.presa === g}
                  onClick={() => setField("presa", g)}
                  tone={g === "Scarsa" ? "danger" : "neutral"}
                />
              ))}
            </div>
          </div>

          {/* Duration bucket */}
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between gap-2">
              <Label className="text-xs">Durata del compito</Label>
              <span className="text-[11px] text-muted-foreground">
                modula il fattore F
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <ChoiceButton
                label="Breve (<1h)"
                active={inputs.durata === "breve"}
                onClick={() => setField("durata", "breve")}
              />
              <ChoiceButton
                label="Media (1-2h)"
                active={inputs.durata === "media"}
                onClick={() => setField("durata", "media")}
              />
              <ChoiceButton
                label="Lunga (>2h)"
                active={inputs.durata === "lunga"}
                onClick={() => setField("durata", "lunga")}
                tone="danger"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 p-4">
        <div className="text-xs text-muted-foreground">
          Bozza salvata automaticamente ·{" "}
          {allAnswered ? "tutti i parametri inseriti" : `mancano ${result.unanswered.length} parametri`}
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={resetDraft}>
            Azzera bozza
          </Button>
        </div>
      </div>
    </div>
  );
}
