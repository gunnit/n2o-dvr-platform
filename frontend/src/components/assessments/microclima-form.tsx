"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
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
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Threshold (in minutes) below which PHS exposure triggers the mandatory-
 * measures banner per US-3.14. The backend classifies `d_lim < 60` as
 * CRITICO, but the acceptance criterion is stricter: at `d_lim < 30` the
 * shift is physiologically unsustainable and a red banner must be surfaced
 * above the result so the operator cannot overlook it.
 */
const PHS_CRITICAL_DLIM_MIN = 30;

// ---------------------------------------------------------------------------
// Types — mirrors backend PmvPpdRequest/PmvPpdResponse.
// ---------------------------------------------------------------------------

export interface PmvInputs {
  air_temp: number;
  mean_radiant_temp: number;
  air_velocity: number;
  humidity: number;
  metabolic_rate: number;
  clothing_insulation: number;
}

export interface PmvResult {
  pmv: number;
  ppd: number;
  sensation: string;
  category: string; // "A" | "B" | "C" | "FUORI_SOGLIA"
  compliant: boolean;
}

// ---------------------------------------------------------------------------
// Presets — plausible office/industrial scenarios.
// ---------------------------------------------------------------------------

interface Preset {
  id: string;
  label: string;
  hint: string;
  inputs: PmvInputs;
}

const PRESETS: Preset[] = [
  {
    id: "ufficio-inverno",
    label: "Ufficio inverno",
    hint: "20 °C, 50 % RH, attività sedentaria, abbigliamento pesante.",
    inputs: {
      air_temp: 20,
      mean_radiant_temp: 20,
      air_velocity: 0.1,
      humidity: 50,
      metabolic_rate: 1.2,
      clothing_insulation: 1.0,
    },
  },
  {
    id: "ufficio-estate",
    label: "Ufficio estate",
    hint: "26 °C, 55 % RH, attività sedentaria, abbigliamento leggero.",
    inputs: {
      air_temp: 26,
      mean_radiant_temp: 26,
      air_velocity: 0.15,
      humidity: 55,
      metabolic_rate: 1.2,
      clothing_insulation: 0.5,
    },
  },
  {
    id: "industria-leggera",
    label: "Industria leggera",
    hint: "22 °C, attività moderata, tuta da lavoro.",
    inputs: {
      air_temp: 22,
      mean_radiant_temp: 22,
      air_velocity: 0.2,
      humidity: 50,
      metabolic_rate: 1.6,
      clothing_insulation: 0.8,
    },
  },
];

export const DEFAULT_PMV_INPUTS: PmvInputs = PRESETS[0].inputs;

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

function CategoryBadge({
  category,
  compliant,
}: {
  category: string;
  compliant: boolean;
}) {
  if (category === "FUORI_SOGLIA") {
    return (
      <span className="inline-flex items-center rounded-md bg-rose-500/15 px-2.5 py-1 text-xs font-medium text-rose-700 ring-1 ring-rose-500/30 dark:text-rose-400">
        Fuori soglia
      </span>
    );
  }
  const tone = compliant
    ? category === "A"
      ? "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30 dark:text-emerald-400"
      : category === "B"
      ? "bg-emerald-500/10 text-emerald-700 ring-emerald-500/25 dark:text-emerald-400"
      : "bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-300"
    : "bg-rose-500/15 text-rose-700 ring-rose-500/30 dark:text-rose-400";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium ring-1",
        tone,
      )}
    >
      Categoria {category}
    </span>
  );
}

function NumericField({
  label,
  unit,
  value,
  onChange,
  min,
  max,
  step,
  hint,
}: {
  label: string;
  unit: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
  hint?: string;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <Label className="text-xs">
          {label}
          <span className="ml-1 font-normal text-muted-foreground">({unit})</span>
        </Label>
        <span className="text-[11px] tabular-nums text-muted-foreground">
          {value.toFixed(unit === "clo" || unit === "met" || unit === "m/s" ? 2 : 1)}
        </span>
      </div>
      <Input
        type="number"
        inputMode="decimal"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") return;
          const n = Number(raw);
          if (!isNaN(n)) onChange(n);
        }}
      />
      {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface MicroclimaFormProps {
  aziendaId: string;
  onResultChange?: (result: PmvResult | null) => void;
}

export function MicroclimaPmvForm({
  aziendaId,
  onResultChange,
}: MicroclimaFormProps) {
  const storageKey = `microclima-pmv-draft-${aziendaId}`;

  const [inputs, setInputs] = useState<PmvInputs>(DEFAULT_PMV_INPUTS);
  const [result, setResult] = useState<PmvResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Hydrate from localStorage
  useEffect(() => {
    try {
      const raw =
        typeof window !== "undefined"
          ? window.localStorage.getItem(storageKey)
          : null;
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<PmvInputs>;
        setInputs({ ...DEFAULT_PMV_INPUTS, ...parsed });
      } else {
        setInputs(DEFAULT_PMV_INPUTS);
      }
    } catch {
      setInputs(DEFAULT_PMV_INPUTS);
    }
  }, [storageKey]);

  // Persist on change
  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(inputs));
    } catch {
      // ignore
    }
  }, [inputs, storageKey]);

  // Debounced live compute via the backend — the formula is iterative.
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const controller = new AbortController();
      (async () => {
        setLoading(true);
        setError(null);
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
          const res = await fetch(`${apiUrl}/api/v1/calculate/microclima/pmv`, {
            method: "POST",
            headers: token
              ? {
                  Authorization: `Bearer ${token}`,
                  "Content-Type": "application/json",
                }
              : { "Content-Type": "application/json" },
            body: JSON.stringify(inputs),
            signal: controller.signal,
          });
          if (!res.ok) throw new Error(`API error ${res.status}`);
          const data = (await res.json()) as PmvResult;
          setResult(data);
        } catch (err) {
          if (err instanceof DOMException && err.name === "AbortError") return;
          setError(
            err instanceof Error ? err.message : "Errore di calcolo",
          );
          setResult(null);
        } finally {
          setLoading(false);
        }
      })();
      return () => controller.abort();
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [inputs]);

  useEffect(() => {
    onResultChange?.(result);
  }, [result, onResultChange]);

  const setField = useCallback(<K extends keyof PmvInputs>(key: K, value: PmvInputs[K]) => {
    setInputs((prev) => ({ ...prev, [key]: value }));
  }, []);

  const applyPreset = useCallback((preset: Preset) => {
    setInputs(preset.inputs);
  }, []);

  const resetDraft = useCallback(() => {
    setInputs(DEFAULT_PMV_INPUTS);
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
  }, [storageKey]);

  // PMV bar position (−3..+3 → 0..100 %)
  const pmvPct = useMemo(() => {
    if (!result) return 50;
    const clamped = Math.max(-3, Math.min(3, result.pmv));
    return ((clamped + 3) / 6) * 100;
  }, [result]);

  return (
    <div className="space-y-6">
      {/* Sticky live result */}
      <Card className="sticky top-4 z-10 shadow-sm">
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">Comfort termico (PMV/PPD)</CardTitle>
              <CardDescription className="text-xs">
                ISO 7730:2006 · scala −3 (molto freddo) … +3 (molto caldo)
              </CardDescription>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-2xl font-semibold tabular-nums">
                  {result ? result.pmv.toFixed(2) : "—"}
                </div>
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  PMV
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-semibold tabular-nums">
                  {result ? `${result.ppd.toFixed(1)}%` : "—"}
                </div>
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  PPD
                </div>
              </div>
              {result ? (
                <CategoryBadge
                  category={result.category}
                  compliant={result.compliant}
                />
              ) : (
                <Badge variant="secondary" className="text-xs">
                  {loading ? "…" : "—"}
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          {/* PMV scale bar: gradient from blue (cold) to red (hot), marker at PMV */}
          <div className="space-y-1">
            <div className="relative h-3 overflow-hidden rounded-full bg-gradient-to-r from-blue-500 via-emerald-500 to-rose-500">
              <div
                className="absolute top-0 h-3 w-0.5 bg-foreground shadow"
                style={{ left: `calc(${pmvPct}% - 1px)` }}
              />
            </div>
            <div className="flex justify-between text-[10px] uppercase tracking-wide text-muted-foreground">
              <span>−3 freddo</span>
              <span>−1</span>
              <span>0 neutro</span>
              <span>+1</span>
              <span>+3 caldo</span>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Badge variant="outline" className="tabular-nums">
              Sensazione: {result ? result.sensation : "—"}
            </Badge>
            <Badge
              variant="outline"
              className={cn(
                "tabular-nums",
                result?.compliant
                  ? "border-emerald-500/40 text-emerald-700 dark:text-emerald-400"
                  : "border-rose-500/40 text-rose-700 dark:text-rose-400",
              )}
            >
              {result
                ? result.compliant
                  ? "Conforme ISO 7730"
                  : "Non conforme"
                : "—"}
            </Badge>
            {error && (
              <span className="text-[11px] text-destructive">{error}</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Presets */}
      <Card>
        <CardHeader className="border-b">
          <CardTitle className="text-sm">Scenari predefiniti</CardTitle>
          <CardDescription className="text-xs">
            Applica valori plausibili per una tipologia di ambiente, poi modifica.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2 pt-4">
          {PRESETS.map((p) => (
            <Button
              key={p.id}
              variant="outline"
              size="sm"
              onClick={() => applyPreset(p)}
              title={p.hint}
            >
              {p.label}
            </Button>
          ))}
        </CardContent>
      </Card>

      {/* Inputs */}
      <Card>
        <CardHeader className="border-b">
          <CardTitle className="text-sm">Parametri microclimatici</CardTitle>
          <CardDescription className="text-xs">
            Sei parametri per il calcolo PMV/PPD. Il calcolo server-side è
            iterativo (ISO 7730) e si aggiorna automaticamente.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-x-6 gap-y-4 pt-4 md:grid-cols-2">
          <NumericField
            label="Temperatura aria (Ta)"
            unit="°C"
            value={inputs.air_temp}
            onChange={(v) => setField("air_temp", v)}
            min={10}
            max={40}
            step={0.1}
            hint="Limiti applicabilità ISO 7730: 10–30 °C."
          />
          <NumericField
            label="Temperatura radiante media (Tr)"
            unit="°C"
            value={inputs.mean_radiant_temp}
            onChange={(v) => setField("mean_radiant_temp", v)}
            min={10}
            max={40}
            step={0.1}
            hint="Limiti ISO 7730: 10–40 °C. Spesso ≈ Ta in ambienti senza superfici calde/fredde."
          />
          <NumericField
            label="Velocità aria (Va)"
            unit="m/s"
            value={inputs.air_velocity}
            onChange={(v) => setField("air_velocity", v)}
            min={0}
            max={2}
            step={0.05}
            hint="Tipicamente 0.1–0.2 m/s in ambienti chiusi."
          />
          <NumericField
            label="Umidità relativa (Ur)"
            unit="%"
            value={inputs.humidity}
            onChange={(v) => setField("humidity", v)}
            min={0}
            max={100}
            step={1}
          />
          <NumericField
            label="Tasso metabolico (M)"
            unit="met"
            value={inputs.metabolic_rate}
            onChange={(v) => setField("metabolic_rate", v)}
            min={0.7}
            max={4.0}
            step={0.1}
            hint="1.0 riposo · 1.2 ufficio · 1.6 attività moderata · 2.0+ lavoro pesante."
          />
          <NumericField
            label="Isolamento abbigliamento (Icl)"
            unit="clo"
            value={inputs.clothing_insulation}
            onChange={(v) => setField("clothing_insulation", v)}
            min={0}
            max={2.0}
            step={0.05}
            hint="0.5 estivo · 1.0 invernale tipico · 1.5 molto caldo."
          />
        </CardContent>
      </Card>

      {/* Reset */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 p-4">
        <div className="text-xs text-muted-foreground">
          Bozza salvata automaticamente
        </div>
        <button
          type="button"
          onClick={resetDraft}
          className="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          Ripristina valori predefiniti
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PHS form (ISO 7933) — severe heat only.
// ---------------------------------------------------------------------------

export interface PhsInputs {
  air_temp: number;
  mean_radiant_temp: number;
  air_velocity: number;
  humidity: number;
  metabolic_rate: number;
  clothing_insulation: number;
  posture: "sitting" | "standing" | "crouching";
  acclimatized: boolean;
  drink_free: boolean;
  duration_min: number;
}

export interface PhsResult {
  t_re: number;
  t_sk: number;
  d_lim_t_re: number;
  d_lim_loss_50: number;
  d_lim_loss_95: number;
  sweat_loss_g: number;
  d_lim: number;
  livello: string;
}

export const DEFAULT_PHS_INPUTS: PhsInputs = {
  air_temp: 35,
  mean_radiant_temp: 35,
  air_velocity: 0.3,
  humidity: 50,
  metabolic_rate: 2.5,
  clothing_insulation: 0.5,
  posture: "standing",
  acclimatized: true,
  drink_free: true,
  duration_min: 480,
};

function LivelloBadge({ livello }: { livello: string }) {
  const tone =
    livello === "ACCETTABILE"
      ? "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30 dark:text-emerald-400"
      : livello === "LIMITE"
      ? "bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-300"
      : "bg-rose-500/15 text-rose-700 ring-rose-500/30 dark:text-rose-400";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium ring-1",
        tone,
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
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-md px-2.5 py-1 text-xs font-medium ring-1 transition-colors",
        active
          ? "bg-primary/10 text-primary ring-primary/40"
          : "bg-background text-muted-foreground ring-border hover:bg-muted",
      )}
    >
      {label}
    </button>
  );
}

export interface MicroclimaPhsFormProps {
  aziendaId: string;
  onResultChange?: (result: PhsResult | null) => void;
}

export function MicroclimaPhsForm({
  aziendaId,
  onResultChange,
}: MicroclimaPhsFormProps) {
  const storageKey = `microclima-phs-draft-${aziendaId}`;

  const [inputs, setInputs] = useState<PhsInputs>(DEFAULT_PHS_INPUTS);
  const [result, setResult] = useState<PhsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw =
        typeof window !== "undefined"
          ? window.localStorage.getItem(storageKey)
          : null;
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<PhsInputs>;
        setInputs({ ...DEFAULT_PHS_INPUTS, ...parsed });
      } else {
        setInputs(DEFAULT_PHS_INPUTS);
      }
    } catch {
      setInputs(DEFAULT_PHS_INPUTS);
    }
  }, [storageKey]);

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(inputs));
    } catch {
      // ignore
    }
  }, [inputs, storageKey]);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const controller = new AbortController();
      (async () => {
        setLoading(true);
        setError(null);
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
          const res = await fetch(`${apiUrl}/api/v1/calculate/microclima/phs`, {
            method: "POST",
            headers: token
              ? {
                  Authorization: `Bearer ${token}`,
                  "Content-Type": "application/json",
                }
              : { "Content-Type": "application/json" },
            body: JSON.stringify(inputs),
            signal: controller.signal,
          });
          if (!res.ok) throw new Error(`API error ${res.status}`);
          const data = (await res.json()) as PhsResult;
          setResult(data);
        } catch (err) {
          if (err instanceof DOMException && err.name === "AbortError") return;
          setError(err instanceof Error ? err.message : "Errore di calcolo");
          setResult(null);
        } finally {
          setLoading(false);
        }
      })();
      return () => controller.abort();
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [inputs]);

  useEffect(() => {
    onResultChange?.(result);
  }, [result, onResultChange]);

  const setField = useCallback(<K extends keyof PhsInputs>(key: K, value: PhsInputs[K]) => {
    setInputs((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetDraft = useCallback(() => {
    setInputs(DEFAULT_PHS_INPUTS);
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
  }, [storageKey]);

  return (
    <div className="space-y-6">
      {/* Scope note */}
      <div className="rounded-md border border-amber-300 bg-amber-100 p-3 text-xs text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
        <div className="font-medium">Ambito di applicazione</div>
        <p className="mt-0.5 leading-relaxed">
          Applicabile solo per esposizioni a caldo severo (es. fonderie,
          cantieri estivi con temperature &gt;30 °C, panetterie industriali,
          vetrerie). Per ambienti di comfort normale usare la scheda PMV/PPD.
        </p>
      </div>

      {/* Critical-exposure banner (US-3.14 AC3): Dlim < 30 min */}
      {result && result.d_lim < PHS_CRITICAL_DLIM_MIN && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-md border border-rose-400/60 bg-rose-50 p-3 text-rose-900 shadow-sm dark:border-rose-500/40 dark:bg-rose-950/30 dark:text-rose-100"
        >
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">Esposizione critica – misure obbligatorie</p>
            <p className="text-sm">
              Dlim = {result.d_lim.toFixed(0)}&prime; (&lt; {PHS_CRITICAL_DLIM_MIN}&prime;).
              Interrompere l&apos;esposizione, predisporre rotazione/cicli di
              recupero in area climatizzata e attivare la sorveglianza sanitaria
              rinforzata ai sensi dell&apos;art. 181 D.Lgs. 81/2008.
            </p>
          </div>
        </div>
      )}

      {/* Live result */}
      <Card className="sticky top-4 z-10 shadow-sm">
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">Stress termico (PHS)</CardTitle>
              <CardDescription className="text-xs">
                ISO 7933:2023 · Dlim = tempo massimo di esposizione
              </CardDescription>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-2xl font-semibold tabular-nums">
                  {result ? `${result.d_lim.toFixed(0)}′` : "—"}
                </div>
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  Dlim
                </div>
              </div>
              {result ? (
                <LivelloBadge livello={result.livello} />
              ) : (
                <Badge variant="secondary" className="text-xs">
                  {loading ? "…" : "—"}
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-2 pt-4 text-xs sm:grid-cols-4">
          <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
            <span className="text-muted-foreground">T rettale</span>
            <span className="font-medium tabular-nums">
              {result ? `${result.t_re.toFixed(1)} °C` : "—"}
            </span>
          </div>
          <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
            <span className="text-muted-foreground">T cute</span>
            <span className="font-medium tabular-nums">
              {result ? `${result.t_sk.toFixed(1)} °C` : "—"}
            </span>
          </div>
          <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
            <span className="text-muted-foreground">Dlim T_re</span>
            <span className="font-medium tabular-nums">
              {result ? `${result.d_lim_t_re.toFixed(0)}′` : "—"}
            </span>
          </div>
          <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
            <span className="text-muted-foreground">Sudore</span>
            <span className="font-medium tabular-nums">
              {result ? `${result.sweat_loss_g.toFixed(0)} g` : "—"}
            </span>
          </div>
        </CardContent>
        {error && (
          <div className="border-t px-6 py-2 text-[11px] text-destructive">
            {error}
          </div>
        )}
      </Card>

      {/* Inputs */}
      <Card>
        <CardHeader className="border-b">
          <CardTitle className="text-sm">Parametri ambientali</CardTitle>
          <CardDescription className="text-xs">
            Range ISO 7933: Ta 15–50 °C, Tr 15–60 °C, Va 0–3 m/s, M 1.0–7.5 met,
            Icl 0.1–1.0 clo.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-x-6 gap-y-4 pt-4 md:grid-cols-2">
          <NumericField
            label="Temperatura aria (Ta)"
            unit="°C"
            value={inputs.air_temp}
            onChange={(v) => setField("air_temp", v)}
            min={15}
            max={50}
            step={0.5}
          />
          <NumericField
            label="Temperatura radiante (Tr)"
            unit="°C"
            value={inputs.mean_radiant_temp}
            onChange={(v) => setField("mean_radiant_temp", v)}
            min={15}
            max={60}
            step={0.5}
          />
          <NumericField
            label="Velocità aria (Va)"
            unit="m/s"
            value={inputs.air_velocity}
            onChange={(v) => setField("air_velocity", v)}
            min={0}
            max={3}
            step={0.05}
          />
          <NumericField
            label="Umidità relativa"
            unit="%"
            value={inputs.humidity}
            onChange={(v) => setField("humidity", v)}
            min={0}
            max={100}
            step={1}
          />
          <NumericField
            label="Tasso metabolico (M)"
            unit="met"
            value={inputs.metabolic_rate}
            onChange={(v) => setField("metabolic_rate", v)}
            min={1.0}
            max={7.5}
            step={0.1}
            hint="Lavoro moderato 2.0 · pesante 3.0 · molto pesante 4.0+."
          />
          <NumericField
            label="Isolamento abbigliamento"
            unit="clo"
            value={inputs.clothing_insulation}
            onChange={(v) => setField("clothing_insulation", v)}
            min={0.1}
            max={1.0}
            step={0.05}
          />
          <NumericField
            label="Durata esposizione"
            unit="min"
            value={inputs.duration_min}
            onChange={(v) => setField("duration_min", Math.round(v))}
            min={1}
            max={480}
            step={30}
            hint="Durata turno o sessione valutata. Max 480 min."
          />
          <div className="space-y-1.5">
            <Label className="text-xs">Postura</Label>
            <div className="flex flex-wrap gap-1.5">
              <ChoiceButton
                label="In piedi"
                active={inputs.posture === "standing"}
                onClick={() => setField("posture", "standing")}
              />
              <ChoiceButton
                label="Seduto"
                active={inputs.posture === "sitting"}
                onClick={() => setField("posture", "sitting")}
              />
              <ChoiceButton
                label="Accovacciato"
                active={inputs.posture === "crouching"}
                onClick={() => setField("posture", "crouching")}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Condizioni del lavoratore</Label>
            <div className="flex flex-wrap gap-1.5">
              <ChoiceButton
                label={inputs.acclimatized ? "Acclimatato" : "Non acclimatato"}
                active={inputs.acclimatized}
                onClick={() => setField("acclimatized", !inputs.acclimatized)}
              />
              <ChoiceButton
                label={
                  inputs.drink_free ? "Accesso libero a bere" : "Accesso limitato"
                }
                active={inputs.drink_free}
                onClick={() => setField("drink_free", !inputs.drink_free)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Reset */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 p-4">
        <div className="text-xs text-muted-foreground">
          Bozza salvata automaticamente
        </div>
        <button
          type="button"
          onClick={resetDraft}
          className="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          Ripristina valori predefiniti
        </button>
      </div>
    </div>
  );
}
