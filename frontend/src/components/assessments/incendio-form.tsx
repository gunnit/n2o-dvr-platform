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
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Domain model — mirrors backend/app/services/risk_calculator.py::calculate_fire_risk.
// Score bands: 3-4 = Basso, 5-7 = Medio, 8-9 = Alto.
// ---------------------------------------------------------------------------

export type FireLivello = "Basso" | "Medio" | "Alto";

export type FireScore = 1 | 2 | 3;

export interface FireAnswers {
  inf?: FireScore;
  si?: FireScore;
  pi?: FireScore;
}

export interface FireResult {
  inf?: FireScore;
  si?: FireScore;
  pi?: FireScore;
  totale: number | null;
  livello: FireLivello | null;
  complete: boolean;
}

export function computeFireRisk(answers: FireAnswers): FireResult {
  const { inf, si, pi } = answers;
  if (inf === undefined || si === undefined || pi === undefined) {
    return {
      inf,
      si,
      pi,
      totale: null,
      livello: null,
      complete: false,
    };
  }
  const totale = inf + si + pi;
  let livello: FireLivello;
  if (totale <= 4) livello = "Basso";
  else if (totale <= 7) livello = "Medio";
  else livello = "Alto";
  return { inf, si, pi, totale, livello, complete: true };
}

// ---------------------------------------------------------------------------
// Parameter definitions — Italian labels from REFERENCE_DATA.md section 4.1.
// ---------------------------------------------------------------------------

interface ParamOption {
  value: FireScore;
  label: string;
  hint: string;
}

interface ParamDef {
  key: "inf" | "si" | "pi";
  code: string;
  title: string;
  description: string;
  options: [ParamOption, ParamOption, ParamOption];
}

const PARAMS: ParamDef[] = [
  {
    key: "inf",
    code: "INF",
    title: "Infiammabilità delle sostanze",
    description:
      "Caratteristiche di infiammabilità delle sostanze presenti nel luogo di lavoro.",
    options: [
      {
        value: 1,
        label: "A basso tasso",
        hint: "Sostanze a basso tasso di infiammabilità o assenti.",
      },
      {
        value: 2,
        label: "Infiammabili",
        hint: "Presenza di sostanze infiammabili in quantità limitate.",
      },
      {
        value: 3,
        label: "Altamente infiammabili",
        hint: "Presenza di sostanze altamente infiammabili, esplosive o fiamme libere.",
      },
    ],
  },
  {
    key: "si",
    code: "SI",
    title: "Sorgenti di innesco",
    description:
      "Possibilità di sviluppo di un incendio per presenza di sorgenti di innesco.",
    options: [
      {
        value: 1,
        label: "Bassa",
        hint: "Sorgenti di innesco assenti o ben controllate.",
      },
      {
        value: 2,
        label: "Limitata",
        hint: "Sorgenti presenti ma limitate a specifiche lavorazioni.",
      },
      {
        value: 3,
        label: "Notevole",
        hint: "Sorgenti di innesco diffuse: fiamme libere, lavorazioni a caldo, impianti elettrici critici.",
      },
    ],
  },
  {
    key: "pi",
    code: "PI",
    title: "Propagazione dell'incendio",
    description:
      "Probabilità che un incendio possa propagarsi all'interno del luogo di lavoro.",
    options: [
      {
        value: 1,
        label: "Basso",
        hint: "Compartimentazione efficace, scarsa presenza di materiali combustibili.",
      },
      {
        value: 2,
        label: "Medio",
        hint: "Presenza di materiali combustibili ma con compartimentazioni o misure di contenimento.",
      },
      {
        value: 3,
        label: "Elevato",
        hint: "Notevole quantità di materiali combustibili, edifici in legno o ambienti senza compartimentazione.",
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Small UI atoms
// ---------------------------------------------------------------------------

const BAND_CLASS: Record<FireLivello, string> = {
  Basso:
    "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30 dark:text-emerald-400",
  Medio:
    "bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-300",
  Alto: "bg-rose-500/15 text-rose-700 ring-rose-500/30 dark:text-rose-400",
};

const BAND_BAR: Record<FireLivello, string> = {
  Basso: "bg-emerald-500",
  Medio: "bg-amber-500",
  Alto: "bg-rose-500",
};

function LivelloBadge({
  livello,
  className,
}: {
  livello: FireLivello;
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

function ScoreButton({
  label,
  value,
  active,
  onClick,
}: {
  label: string;
  value: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex-1 rounded-md px-3 py-2 text-sm font-medium ring-1 transition-colors",
        active
          ? "bg-primary/10 text-primary ring-primary/40"
          : "bg-background text-muted-foreground ring-border hover:bg-muted",
      )}
    >
      <span className="mr-1 text-[11px] uppercase tracking-wide opacity-70">
        {value}
      </span>
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface IncendioFormProps {
  aziendaId: string;
  onResultChange?: (result: FireResult) => void;
}

export function IncendioForm({ aziendaId, onResultChange }: IncendioFormProps) {
  const storageKey = `incendio-draft-${aziendaId}`;

  const [answers, setAnswers] = useState<FireAnswers>({});

  // Hydrate from localStorage
  useEffect(() => {
    try {
      const raw =
        typeof window !== "undefined"
          ? window.localStorage.getItem(storageKey)
          : null;
      if (raw) {
        const parsed = JSON.parse(raw) as FireAnswers;
        setAnswers(parsed ?? {});
      } else {
        setAnswers({});
      }
    } catch {
      setAnswers({});
    }
  }, [storageKey]);

  // Persist on change
  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(answers));
    } catch {
      // ignore
    }
  }, [answers, storageKey]);

  const result = useMemo(() => computeFireRisk(answers), [answers]);

  useEffect(() => {
    onResultChange?.(result);
  }, [result, onResultChange]);

  const setScore = useCallback(
    (key: "inf" | "si" | "pi", value: FireScore) => {
      setAnswers((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const resetDraft = useCallback(() => {
    setAnswers({});
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
  }, [storageKey]);

  const currentOption = (p: ParamDef): ParamOption | undefined => {
    const v = answers[p.key];
    return v ? p.options.find((o) => o.value === v) : undefined;
  };

  const progressPct = result.complete
    ? ((result.totale! / 9) * 100).toFixed(0)
    : "0";

  return (
    <div className="space-y-6">
      {/* Sticky live result */}
      <Card className="sticky top-4 z-10 shadow-sm">
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">Livello di rischio incendio</CardTitle>
              <CardDescription className="text-xs">
                Formula: INF + SI + PI (ciascuno 1–3) · D.M. 03/09/2021
              </CardDescription>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-2xl font-semibold tabular-nums">
                  {result.totale ?? "—"}
                </div>
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  su 9
                </div>
              </div>
              {result.livello ? (
                <LivelloBadge livello={result.livello} className="px-3 py-1 text-sm" />
              ) : (
                <Badge variant="secondary" className="px-3 py-1 text-sm">
                  incompleto
                </Badge>
              )}
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
                    result.livello ? BAND_BAR[result.livello] : "bg-muted-foreground/20",
                  )}
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <div className="mt-1 flex justify-between text-[10px] uppercase tracking-wide text-muted-foreground">
                <span>3</span>
                <span>4</span>
                <span>7</span>
                <span>9</span>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-2 pt-1 text-xs sm:grid-cols-3">
            {PARAMS.map((p) => {
              const v = answers[p.key];
              return (
                <div
                  key={p.key}
                  className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2"
                >
                  <span className="text-muted-foreground">{p.code}</span>
                  <span className="font-medium tabular-nums">
                    {v !== undefined ? `${v} / 3` : "—"}
                  </span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Parameter selectors */}
      {PARAMS.map((p) => {
        const selected = currentOption(p);
        return (
          <Card key={p.key}>
            <CardHeader className="border-b">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px]">
                      {p.code}
                    </Badge>
                    <CardTitle className="text-sm">{p.title}</CardTitle>
                  </div>
                  <CardDescription className="mt-1 text-xs">
                    {p.description}
                  </CardDescription>
                </div>
                {selected && (
                  <Badge variant="secondary" className="text-xs">
                    {selected.label}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-3 pt-4">
              <div className="flex flex-wrap gap-2">
                {p.options.map((opt) => (
                  <ScoreButton
                    key={opt.value}
                    label={opt.label}
                    value={opt.value}
                    active={answers[p.key] === opt.value}
                    onClick={() => setScore(p.key, opt.value)}
                  />
                ))}
              </div>
              {selected && (
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  {selected.hint}
                </p>
              )}
            </CardContent>
          </Card>
        );
      })}

      {/* Reset */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 p-4">
        <div className="text-xs text-muted-foreground">
          Bozza salvata automaticamente ·{" "}
          {result.complete
            ? "tutti e tre i parametri compilati"
            : "completa i parametri per ottenere il livello"}
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
