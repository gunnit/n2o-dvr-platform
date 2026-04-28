"use client";

import {
  useCallback,
  useEffect,
  useMemo,
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
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types & constants — mirror backend/app/services/document_generator/
// reference_data_biologico.py so the UI can render and classify instantly.
// The server endpoint GET /api/v1/calculate/biologico-checklist is the source
// of truth and is re-fetched whenever the sector changes.
// ---------------------------------------------------------------------------

export type Settore = "alimentare" | "asilo" | "dentisti";
export type Risposta = "SI" | "NO" | "NA";
export type Criticita = "alta" | "media" | "bassa";
export type LivelloRischio = "BASSO" | "MEDIO" | "ALTO";

export interface ChecklistItem {
  id: string;
  descrizione: string;
  criticita: Criticita;
}

export interface RispostaEntry {
  id: string;
  risposta: Risposta;
}

export interface BiologicoState {
  settore: Settore;
  risposte: Record<string, Risposta>;
  protocolloSanitario: string;
}

export interface BiologicoResult {
  noWeight: number;
  maxWeight: number;
  ratio: number;
  livello: LivelloRischio;
  unanswered: string[];
}

const CRITICITA_WEIGHTS: Record<Criticita, number> = {
  alta: 3,
  media: 2,
  bassa: 1,
};

const SETTORE_META: Record<Settore, { label: string; normativa: string }> = {
  alimentare: {
    label: "Alimentare",
    normativa: "Reg. CE 852/2004 + HACCP",
  },
  asilo: {
    label: "Asilo nido / scuola infanzia",
    normativa: "D.Lgs. 81/2008 Titolo X + linee guida ISS",
  },
  dentisti: {
    label: "Studio odontoiatrico",
    normativa: "D.Lgs. 81/2008 Titolo X + precauzioni standard",
  },
};

const CRITICITA_BADGE: Record<Criticita, string> = {
  alta: "bg-rose-500/15 text-rose-700 ring-rose-500/30 dark:text-rose-400",
  media: "bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-300",
  bassa: "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30 dark:text-emerald-400",
};

const CRITICITA_LABEL: Record<Criticita, string> = {
  alta: "Alta",
  media: "Media",
  bassa: "Bassa",
};

const BAND_CLASS: Record<LivelloRischio, string> = {
  BASSO: "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30 dark:text-emerald-400",
  MEDIO: "bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-300",
  ALTO: "bg-rose-500/15 text-rose-700 ring-rose-500/30 dark:text-rose-400",
};

// ---------------------------------------------------------------------------
// Scoring — same thresholds as backend/reference_data_biologico.py
// ---------------------------------------------------------------------------

export function computeBiologico(
  items: ChecklistItem[],
  risposte: Record<string, Risposta>,
): BiologicoResult {
  let noWeight = 0;
  let maxWeight = 0;
  const unanswered: string[] = [];

  for (const item of items) {
    const weight = CRITICITA_WEIGHTS[item.criticita];
    const answer = risposte[item.id];
    if (!answer) {
      unanswered.push(item.id);
      maxWeight += weight;
      continue;
    }
    if (answer === "NA") continue; // Excluded from denominator
    maxWeight += weight;
    if (answer === "NO") noWeight += weight;
  }

  const ratio = maxWeight > 0 ? noWeight / maxWeight : 0;
  let livello: LivelloRischio;
  if (ratio >= 0.4) livello = "ALTO";
  else if (ratio >= 0.15) livello = "MEDIO";
  else livello = "BASSO";

  return {
    noWeight,
    maxWeight,
    ratio: Math.round(ratio * 10000) / 10000,
    livello,
    unanswered,
  };
}

// ---------------------------------------------------------------------------
// API fetch — checklist catalog
// ---------------------------------------------------------------------------

async function fetchChecklist(settore: Settore): Promise<ChecklistItem[]> {
  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  let token: string | null = null;
  try {
    const s = await fetch("/api/auth/session");
    const session = await s.json();
    token = session?.accessToken ?? null;
  } catch {
    /* unauth fallback */
  }
  const res = await fetch(
    `${apiUrl}/api/v1/calculate/biologico-checklist?settore=${settore}`,
    {
      headers: token
        ? { Authorization: `Bearer ${token}` }
        : undefined,
    },
  );
  if (!res.ok) throw new Error(`Checklist non disponibile (HTTP ${res.status})`);
  const body = (await res.json()) as {
    settore: Settore;
    items: ChecklistItem[];
  };
  return body.items;
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

function LivelloBadge({
  livello,
  className,
}: {
  livello: LivelloRischio;
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

function CriticitaBadge({ criticita }: { criticita: Criticita }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ring-1",
        CRITICITA_BADGE[criticita],
      )}
    >
      {CRITICITA_LABEL[criticita]}
    </span>
  );
}

function AnswerButton({
  label,
  active,
  onClick,
  tone,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  tone?: "danger" | "neutral" | "muted";
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
            : tone === "muted"
            ? "bg-muted text-muted-foreground ring-border"
            : "bg-emerald-500/15 text-emerald-700 ring-emerald-500/40 dark:text-emerald-400"
          : "bg-background text-muted-foreground ring-border hover:bg-muted",
      )}
    >
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface BiologicoFormProps {
  aziendaId: string;
  initialSettore?: Settore;
  initialRisposte?: Record<string, Risposta>;
  initialProtocollo?: string;
  onStateChange?: (state: BiologicoState) => void;
  onResultChange?: (result: BiologicoResult) => void;
  onDirtyChange?: (dirty: boolean) => void;
}

export function BiologicoForm({
  aziendaId,
  initialSettore = "alimentare",
  initialRisposte,
  initialProtocollo = "",
  onStateChange,
  onResultChange,
  onDirtyChange,
}: BiologicoFormProps) {
  const storageKey = `biologico-draft-${aziendaId}`;

  const [settore, setSettore] = useState<Settore>(initialSettore);
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [risposteBySettore, setRisposteBySettore] = useState<
    Record<Settore, Record<string, Risposta>>
  >({
    alimentare: {},
    asilo: {},
    dentisti: {},
  });
  const [protocollo, setProtocollo] = useState<string>(initialProtocollo);
  const [hydrated, setHydrated] = useState(false);

  // ------------------------------------------------------------------ Draft
  // Hydrate draft from localStorage on mount.
  useEffect(() => {
    try {
      const raw =
        typeof window !== "undefined"
          ? window.localStorage.getItem(storageKey)
          : null;
      if (raw) {
        const parsed = JSON.parse(raw) as {
          settore?: Settore;
          risposteBySettore?: Record<Settore, Record<string, Risposta>>;
          protocollo?: string;
        };
        if (parsed.settore) setSettore(parsed.settore);
        if (parsed.risposteBySettore) {
          setRisposteBySettore((prev) => ({
            ...prev,
            ...parsed.risposteBySettore,
          }));
        }
        if (typeof parsed.protocollo === "string") setProtocollo(parsed.protocollo);
      } else if (initialRisposte) {
        setRisposteBySettore((prev) => ({
          ...prev,
          [initialSettore]: { ...initialRisposte },
        }));
      }
    } catch {
      /* ignore parse errors */
    }
    setHydrated(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storageKey]);

  // Persist on any change.
  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(
        storageKey,
        JSON.stringify({ settore, risposteBySettore, protocollo }),
      );
    } catch {
      /* ignore quota */
    }
  }, [hydrated, settore, risposteBySettore, protocollo, storageKey]);

  // ------------------------------------------------------------------ Load
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    fetchChecklist(settore)
      .then((items) => {
        if (!cancelled) setItems(items);
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(
            err instanceof Error ? err.message : "Errore di caricamento",
          );
          setItems([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [settore]);

  // ------------------------------------------------------------------ Scoring
  const risposte = useMemo(
    () => risposteBySettore[settore] ?? {},
    [risposteBySettore, settore],
  );
  const result = useMemo(
    () => computeBiologico(items, risposte),
    [items, risposte],
  );

  useEffect(() => {
    onResultChange?.(result);
  }, [result, onResultChange]);

  useEffect(() => {
    onStateChange?.({
      settore,
      risposte,
      protocolloSanitario: protocollo,
    });
  }, [settore, risposte, protocollo, onStateChange]);

  // Dirty tracking — anything entered for this sector counts as dirty.
  useEffect(() => {
    if (!hydrated) return;
    const hasAnswers = Object.keys(risposte).length > 0;
    const hasProtocollo = protocollo.trim().length > 0;
    onDirtyChange?.(hasAnswers || hasProtocollo);
  }, [hydrated, risposte, protocollo, onDirtyChange]);

  // ------------------------------------------------------------------ Callbacks
  const setAnswer = useCallback(
    (itemId: string, value: Risposta) => {
      setRisposteBySettore((prev) => {
        const current = prev[settore] ?? {};
        // Clicking the active answer again clears it (toggle off).
        const next = { ...current };
        if (next[itemId] === value) {
          delete next[itemId];
        } else {
          next[itemId] = value;
        }
        return { ...prev, [settore]: next };
      });
    },
    [settore],
  );

  const resetDraft = useCallback(() => {
    setRisposteBySettore((prev) => ({ ...prev, [settore]: {} }));
  }, [settore]);

  // ------------------------------------------------------------------ Render
  const answeredCount = items.length - result.unanswered.length;
  const progressPct =
    items.length > 0 ? Math.round((answeredCount / items.length) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Sector selector */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Settore di riferimento</CardTitle>
          <CardDescription className="text-xs">
            Il settore determina la checklist tecnica e gli agenti biologici
            pre-popolati nel documento.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="settore">Settore</Label>
            <div className="grid gap-2 sm:grid-cols-3">
              {(Object.keys(SETTORE_META) as Settore[]).map((key) => {
                const active = key === settore;
                const meta = SETTORE_META[key];
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSettore(key)}
                    className={cn(
                      "rounded-lg border p-3 text-left transition-colors",
                      active
                        ? "border-primary bg-primary/5 ring-1 ring-primary/40"
                        : "border-border hover:bg-muted",
                    )}
                    aria-pressed={active}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{meta.label}</span>
                      {active && <Badge variant="secondary">Attivo</Badge>}
                    </div>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      {meta.normativa}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Risk summary */}
      <Card className="sticky top-4 z-10 shadow-sm">
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">Classificazione rischio</CardTitle>
              <CardDescription className="text-xs">
                Calcolo live: somma pesata delle risposte NO / peso massimo
                applicabile (criticità alta=3, media=2, bassa=1)
              </CardDescription>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-2xl font-semibold tabular-nums">
                  {result.noWeight}/{result.maxWeight || 0}
                </div>
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  rapporto {(result.ratio * 100).toFixed(0)}%
                </div>
              </div>
              <LivelloBadge
                livello={result.livello}
                className="px-3 py-1 text-sm"
              />
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
                    result.livello === "BASSO" && "bg-emerald-500",
                    result.livello === "MEDIO" && "bg-amber-500",
                    result.livello === "ALTO" && "bg-rose-500",
                  )}
                  style={{
                    width: `${Math.min(100, result.ratio * 100)}%`,
                  }}
                />
              </div>
              <div className="mt-1 flex justify-between text-[10px] uppercase tracking-wide text-muted-foreground">
                <span>Basso</span>
                <span>15%</span>
                <span>40%</span>
                <span>Alto</span>
              </div>
            </div>
            <Badge variant="secondary" className="gap-1 text-xs">
              <span className="tabular-nums">
                {answeredCount}/{items.length || 0}
              </span>
              risposte ({progressPct}%)
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Checklist card */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="text-sm">
                Checklist {SETTORE_META[settore].label}
              </CardTitle>
              <CardDescription className="text-xs">
                {items.length} controlli · {SETTORE_META[settore].normativa}
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={resetDraft}
              disabled={Object.keys(risposte).length === 0}
              className="h-7 px-2 text-xs"
            >
              Azzera risposte settore
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-3">
          {loading && (
            <p className="text-sm text-muted-foreground">Caricamento…</p>
          )}
          {loadError && (
            <div
              role="alert"
              className="rounded-md border border-rose-300 bg-rose-100 px-4 py-3 text-sm text-rose-900 dark:border-rose-700 dark:bg-rose-950/40 dark:text-rose-200"
            >
              <strong className="font-medium">Errore:</strong> {loadError}
            </div>
          )}
          {!loading && !loadError && items.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Nessun controllo disponibile per il settore selezionato.
            </p>
          )}
          {!loading && items.length > 0 && (
            <ul className="divide-y">
              {items.map((item) => {
                const current = risposte[item.id];
                return (
                  <li
                    key={item.id}
                    data-id={item.id}
                    className="flex flex-wrap items-start justify-between gap-3 py-2.5"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          variant="outline"
                          className="text-[10px] tabular-nums"
                        >
                          {item.id}
                        </Badge>
                        <CriticitaBadge criticita={item.criticita} />
                        <span className="text-sm">{item.descrizione}</span>
                      </div>
                    </div>
                    <div
                      className="flex shrink-0 items-center gap-1.5"
                      role="radiogroup"
                      aria-label={`Risposta per ${item.id}`}
                    >
                      <AnswerButton
                        label="SI"
                        active={current === "SI"}
                        onClick={() => setAnswer(item.id, "SI")}
                        tone="neutral"
                      />
                      <AnswerButton
                        label="NO"
                        active={current === "NO"}
                        onClick={() => setAnswer(item.id, "NO")}
                        tone="danger"
                      />
                      <AnswerButton
                        label="N/A"
                        active={current === "NA"}
                        onClick={() => setAnswer(item.id, "NA")}
                        tone="muted"
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Protocollo sanitario */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Protocollo sanitario aziendale</CardTitle>
          <CardDescription className="text-xs">
            Descrivi visite mediche, esami periodici, vaccinazioni e gestione
            delle esposizioni accidentali. Appare nella sezione Sorveglianza
            sanitaria del documento generato.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <textarea
            id="protocollo"
            value={protocollo}
            onChange={(e) => setProtocollo(e.target.value)}
            rows={5}
            placeholder="Es. Sorveglianza annuale per personale esposto, verifica vaccinazioni HBV per il personale clinico, protocollo post-esposizione attivabile entro 1 ora…"
            className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </CardContent>
      </Card>
    </div>
  );
}
