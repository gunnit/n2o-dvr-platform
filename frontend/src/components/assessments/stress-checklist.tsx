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
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Indicator catalog — mirrors backend/app/services/stress_calculator.py
// so the UI can render + score instantly without waiting for the API. The
// backend is the source of truth: we re-POST on finalize to confirm.
// ---------------------------------------------------------------------------

export type ScoringMode =
  | "tripartite"
  | "binary_heavy"
  | "binary"
  | "binary_inverted";

export type AreaCode =
  | "A"
  | "B1"
  | "B2"
  | "B3"
  | "B4"
  | "B5"
  | "B6"
  | "C1"
  | "C2"
  | "C3"
  | "C4";

export interface Indicator {
  id: string;
  area: AreaCode;
  text: string;
  scoring: ScoringMode;
  note: string;
}

// Keep in sync with stress_calculator.py::INDICATORS
export const INDICATORS: Indicator[] = [
  { id: "A.1",  area: "A",  scoring: "tripartite",   note: "Se INALTERATO = 0 eventi, marcare DIMINUITO", text: "Indici infortunistici" },
  { id: "A.2",  area: "A",  scoring: "tripartite",   note: "", text: "Assenteismo (% ore assenza / ore lavorative)" },
  { id: "A.3",  area: "A",  scoring: "tripartite",   note: "", text: "Assenza per malattia (escluso maternità, allattamento, congedo matrimoniale)" },
  { id: "A.4",  area: "A",  scoring: "tripartite",   note: "", text: "% Ferie non godute" },
  { id: "A.5",  area: "A",  scoring: "tripartite",   note: "", text: "% Rotazione del personale non programmata" },
  { id: "A.6",  area: "A",  scoring: "tripartite",   note: "Se INALTERATO = 0 eventi, marcare DIMINUITO", text: "Cessazione rapporti di lavoro / turnover" },
  { id: "A.7",  area: "A",  scoring: "tripartite",   note: "Se INALTERATO = 0 eventi, marcare DIMINUITO", text: "Procedimenti / sanzioni disciplinari" },
  { id: "A.8",  area: "A",  scoring: "tripartite",   note: "Se INALTERATO = 0 eventi, marcare DIMINUITO", text: "Richieste visite mediche straordinarie dal medico competente" },
  { id: "A.9",  area: "A",  scoring: "binary_heavy", note: "", text: "Segnalazioni scritte medico competente di condizioni stress al lavoro" },
  { id: "A.10", area: "A",  scoring: "binary_heavy", note: "", text: "Istanze giudiziarie per licenziamento / demansionamento" },

  { id: "B1.1",  area: "B1", scoring: "binary", note: "", text: "Diffusione organigramma aziendale" },
  { id: "B1.2",  area: "B1", scoring: "binary", note: "", text: "Presenza di procedure aziendali" },
  { id: "B1.3",  area: "B1", scoring: "binary", note: "", text: "Diffusione delle procedure aziendali ai lavoratori" },
  { id: "B1.4",  area: "B1", scoring: "binary", note: "", text: "Diffusione degli obiettivi aziendali ai lavoratori" },
  { id: "B1.5",  area: "B1", scoring: "binary", note: "", text: "Sistema di gestione della sicurezza aziendale (certificazioni SA8000, BS OHSAS 18001:2007)" },
  { id: "B1.6",  area: "B1", scoring: "binary", note: "", text: "Presenza di un sistema di comunicazione aziendale (bacheca, internet, busta paga, volantini)" },
  { id: "B1.7",  area: "B1", scoring: "binary", note: "", text: "Effettuazione riunioni / incontri tra dirigenti e lavoratori" },
  { id: "B1.8",  area: "B1", scoring: "binary", note: "", text: "Presenza di un piano formativo per la crescita professionale dei lavoratori" },
  { id: "B1.9",  area: "B1", scoring: "binary", note: "", text: "Presenza di momenti di comunicazione dell'azienda a tutto il personale" },
  { id: "B1.10", area: "B1", scoring: "binary", note: "", text: "Presenza di codice etico e di comportamento" },
  { id: "B1.11", area: "B1", scoring: "binary", note: "", text: "Presenza di sistemi per il recepimento e la gestione dei casi di disagio lavorativo" },

  { id: "B2.1", area: "B2", scoring: "binary",          note: "", text: "I lavoratori conoscono la linea gerarchica aziendale" },
  { id: "B2.2", area: "B2", scoring: "binary",          note: "", text: "I ruoli sono chiaramente definiti" },
  { id: "B2.3", area: "B2", scoring: "binary_inverted", note: "", text: "Vi è una sovrapposizione di ruoli differenti sulle stesse persone" },
  { id: "B2.4", area: "B2", scoring: "binary_inverted", note: "", text: "Accade di frequente che dirigenti / preposti forniscano informazioni contrastanti" },

  { id: "B3.1", area: "B3", scoring: "binary", note: "", text: "Sono definiti i criteri per l'avanzamento di carriera" },
  { id: "B3.2", area: "B3", scoring: "binary", note: "", text: "Esistono sistemi premianti in relazione alla corretta gestione del personale" },
  { id: "B3.3", area: "B3", scoring: "binary", note: "", text: "Esistono sistemi premianti in relazione al raggiungimento degli obiettivi di sicurezza" },

  { id: "B4.1", area: "B4", scoring: "binary_inverted", note: "", text: "Il lavoro dipende da compiti precedentemente svolti da altri" },
  { id: "B4.2", area: "B4", scoring: "binary",          note: "", text: "I lavoratori hanno sufficiente autonomia per l'esecuzione dei compiti" },
  { id: "B4.3", area: "B4", scoring: "binary",          note: "", text: "I lavoratori hanno a disposizione le informazioni sulle decisioni aziendali" },
  { id: "B4.4", area: "B4", scoring: "binary",          note: "", text: "Sono predisposti strumenti di partecipazione decisionale dei lavoratori" },
  { id: "B4.5", area: "B4", scoring: "binary_inverted", note: "", text: "Sono presenti rigidi protocolli di supervisione sul lavoro svolto" },

  { id: "B5.1", area: "B5", scoring: "binary",          note: "", text: "Possibilità di comunicare con i dirigenti di grado superiore" },
  { id: "B5.2", area: "B5", scoring: "binary",          note: "", text: "Vengono gestiti eventuali comportamenti prevaricatori o illeciti" },
  { id: "B5.3", area: "B5", scoring: "binary_inverted", note: "", text: "Vi è la segnalazione frequente di conflitti / litigi" },

  { id: "B6.1", area: "B6", scoring: "binary", note: "", text: "Possibilità di effettuare la pausa pasto in luogo adeguato / mensa aziendale" },
  { id: "B6.2", area: "B6", scoring: "binary", note: "", text: "Possibilità di orario flessibile" },
  { id: "B6.3", area: "B6", scoring: "binary", note: "", text: "Possibilità di raggiungere il posto di lavoro con mezzi pubblici / navetta" },
  { id: "B6.4", area: "B6", scoring: "binary", note: "", text: "Possibilità di svolgere lavoro part-time verticale / orizzontale" },

  { id: "C1.1",  area: "C1", scoring: "binary_inverted", note: "", text: "Esposizione a rumore superiore al secondo livello d'azione" },
  { id: "C1.2",  area: "C1", scoring: "binary_inverted", note: "", text: "Inadeguato comfort acustico (ambiente non industriale)" },
  { id: "C1.3",  area: "C1", scoring: "binary_inverted", note: "", text: "Rischio cancerogeno / chimico non irrilevante" },
  { id: "C1.4",  area: "C1", scoring: "binary",          note: "", text: "Microclima adeguato" },
  { id: "C1.5",  area: "C1", scoring: "binary",          note: "", text: "Adeguato illuminamento (specie per attività ad elevato impegno visivo)" },
  { id: "C1.6",  area: "C1", scoring: "binary_inverted", note: "", text: "Rischio movimentazione manuale dei carichi" },
  { id: "C1.7",  area: "C1", scoring: "binary",          note: "Se DPI non previsti, marcare SI", text: "Disponibilità di adeguati e confortevoli DPI" },
  { id: "C1.8",  area: "C1", scoring: "binary_inverted", note: "", text: "Lavoro a rischio di aggressione fisica / lavoro solitario" },
  { id: "C1.9",  area: "C1", scoring: "binary",          note: "", text: "Segnaletica di sicurezza chiara, immediata e pertinente ai rischi" },
  { id: "C1.10", area: "C1", scoring: "binary_inverted", note: "", text: "Esposizione a vibrazione superiore al limite d'azione" },
  { id: "C1.11", area: "C1", scoring: "binary",          note: "", text: "Adeguata manutenzione macchine ed attrezzature" },
  { id: "C1.12", area: "C1", scoring: "binary_inverted", note: "", text: "Esposizione a radiazioni ionizzanti" },
  { id: "C1.13", area: "C1", scoring: "binary_inverted", note: "", text: "Esposizione a rischio biologico" },

  { id: "C2.1", area: "C2", scoring: "binary_inverted", note: "", text: "Il lavoro subisce frequenti interruzioni" },
  { id: "C2.2", area: "C2", scoring: "binary",          note: "", text: "Adeguatezza delle risorse strumentali necessarie" },
  { id: "C2.3", area: "C2", scoring: "binary_inverted", note: "", text: "È presente un lavoro caratterizzato da alta monotonia" },
  { id: "C2.4", area: "C2", scoring: "binary_inverted", note: "", text: "Lo svolgimento della mansione richiede di eseguire più compiti contemporaneamente" },
  { id: "C2.5", area: "C2", scoring: "binary",          note: "", text: "Chiara definizione dei compiti" },
  { id: "C2.6", area: "C2", scoring: "binary",          note: "", text: "Adeguatezza delle risorse umane necessarie" },

  { id: "C3.1", area: "C3", scoring: "binary",          note: "", text: "I lavoratori hanno autonomia nella esecuzione dei compiti" },
  { id: "C3.2", area: "C3", scoring: "binary_inverted", note: "", text: "Ci sono variazioni imprevedibili della quantità di lavoro" },
  { id: "C3.3", area: "C3", scoring: "binary_inverted", note: "", text: "Vi è assenza di compiti per lunghi periodi nel turno lavorativo" },
  { id: "C3.4", area: "C3", scoring: "binary_inverted", note: "", text: "È presente un lavoro caratterizzato da alta ripetitività" },
  { id: "C3.5", area: "C3", scoring: "binary_inverted", note: "", text: "Il ritmo lavorativo per l'esecuzione del compito è prefissato" },
  { id: "C3.6", area: "C3", scoring: "binary_inverted", note: "Se macchine non previste, marcare NO", text: "Il lavoratore non può agire sul ritmo della macchina" },
  { id: "C3.7", area: "C3", scoring: "binary_inverted", note: "", text: "I lavoratori devono prendere decisioni rapide" },
  { id: "C3.8", area: "C3", scoring: "binary_inverted", note: "", text: "Lavoro con utilizzo di macchine ed attrezzature ad alto rischio" },
  { id: "C3.9", area: "C3", scoring: "binary_inverted", note: "", text: "Lavoro con elevata responsabilità per terzi, impianti e produzione" },

  { id: "C4.1", area: "C4", scoring: "binary_inverted", note: "", text: "È presente regolarmente un orario lavorativo superiore alle 8 ore" },
  { id: "C4.2", area: "C4", scoring: "binary_inverted", note: "", text: "Viene abitualmente svolto lavoro straordinario" },
  { id: "C4.3", area: "C4", scoring: "binary_inverted", note: "", text: "È presente orario di lavoro rigido (non flessibile)" },
  { id: "C4.4", area: "C4", scoring: "binary_inverted", note: "", text: "La programmazione dell'orario varia frequentemente" },
  { id: "C4.5", area: "C4", scoring: "binary",          note: "", text: "Le pause di lavoro non sono chiaramente definite" },
  { id: "C4.6", area: "C4", scoring: "binary_inverted", note: "", text: "È presente il lavoro a turni" },
  { id: "C4.7", area: "C4", scoring: "binary_inverted", note: "", text: "È presente il lavoro a turni notturni" },
  { id: "C4.8", area: "C4", scoring: "binary_inverted", note: "", text: "È presente il turno notturno fisso o a rotazione" },
];

// ---------------------------------------------------------------------------
// Scoring — mirrors stress_calculator.py
// ---------------------------------------------------------------------------

type TripartiteAnswer = "DIMINUITO" | "INALTERATO" | "AUMENTATO";
type BinaryAnswer = "SI" | "NO";
export type StressAnswer = TripartiteAnswer | BinaryAnswer;

export type AnswersMap = Record<string, StressAnswer | undefined>;

const SUBAREA_THRESHOLDS: Record<string, [number, number, number]> = {
  B1: [4, 7, 11],
  B2: [1, 3, 4],
  B3: [1, 2, 3],
  B4: [1, 3, 5],
  B5: [1, 2, 3],
  C1: [5, 9, 13],
  C2: [2, 4, 6],
  C3: [4, 7, 9],
  C4: [2, 5, 8],
};

const TOTALE_B_THRESHOLDS: [number, number, number] = [8, 17, 26];
const TOTALE_C_THRESHOLDS: [number, number, number] = [13, 25, 36];
const FINAL_THRESHOLDS: [number, number, number] = [17, 34, 67];

export type Livello = "BASSO" | "MEDIO" | "ALTO";

function band(score: number, t: [number, number, number]): Livello {
  if (score <= t[0]) return "BASSO";
  if (score <= t[1]) return "MEDIO";
  return "ALTO";
}

function scoreIndicator(ind: Indicator, ans: StressAnswer | undefined): number {
  if (!ans) return 0;
  switch (ind.scoring) {
    case "tripartite":
      return { DIMINUITO: 0, INALTERATO: 1, AUMENTATO: 4 }[ans as TripartiteAnswer] ?? 0;
    case "binary_heavy":
      return { NO: 0, SI: 4 }[ans as BinaryAnswer] ?? 0;
    case "binary":
      return { SI: 0, NO: 1 }[ans as BinaryAnswer] ?? 0;
    case "binary_inverted":
      return { SI: 1, NO: 0 }[ans as BinaryAnswer] ?? 0;
  }
}

export interface StressResult {
  areaA: { raw: number; converted: number; livello: Livello };
  subB: Record<string, { score: number; max: number; livello: Livello }>;
  totalB: number;
  livelloB: Livello;
  subC: Record<string, { score: number; max: number; livello: Livello }>;
  totalC: number;
  livelloC: Livello;
  totale: number;
  livello: Livello;
  unanswered: string[];
}

export function computeStress(answers: AnswersMap): StressResult {
  const unanswered: string[] = [];
  const scoreFor = (id: string, ind: Indicator) => {
    const a = answers[id];
    if (!a) {
      unanswered.push(id);
      return 0;
    }
    return scoreIndicator(ind, a);
  };

  // Area A
  let areaARaw = 0;
  for (const ind of INDICATORS) if (ind.area === "A") areaARaw += scoreFor(ind.id, ind);
  let areaAConv = 0;
  let areaALiv: Livello = "BASSO";
  if (areaARaw <= 10) {
    areaAConv = 0;
    areaALiv = "BASSO";
  } else if (areaARaw <= 20) {
    areaAConv = 2;
    areaALiv = "MEDIO";
  } else {
    areaAConv = 5;
    areaALiv = "ALTO";
  }

  // Sub-areas B / C
  const subB: StressResult["subB"] = {};
  for (const sub of ["B1", "B2", "B3", "B4", "B5", "B6"] as const) {
    const inds = INDICATORS.filter((i) => i.area === sub);
    const score = inds.reduce((acc, ind) => acc + scoreFor(ind.id, ind), 0);
    const max = inds.length;
    const livello: Livello =
      sub === "B6"
        ? score === 0
          ? "BASSO"
          : score < max
          ? "MEDIO"
          : "ALTO"
        : band(score, SUBAREA_THRESHOLDS[sub]);
    subB[sub] = { score, max, livello };
  }
  // B6 special rule: reward (-1) only when all 4 items are answered and all
  // positive. Otherwise contribute 0 so incomplete assessments don't show a
  // negative total.
  const b6Ids = INDICATORS.filter((i) => i.area === "B6").map((i) => i.id);
  const b6FullyAnswered = b6Ids.every((id) => !!answers[id]);
  const b6Contribution = b6FullyAnswered && subB.B6.score === 0 ? -1 : 0;
  const totalB =
    subB.B1.score + subB.B2.score + subB.B3.score + subB.B4.score + subB.B5.score + b6Contribution;
  const livelloB = band(Math.max(totalB, 0), TOTALE_B_THRESHOLDS);

  const subC: StressResult["subC"] = {};
  for (const sub of ["C1", "C2", "C3", "C4"] as const) {
    const inds = INDICATORS.filter((i) => i.area === sub);
    const score = inds.reduce((acc, ind) => acc + scoreFor(ind.id, ind), 0);
    const max = inds.length;
    subC[sub] = { score, max, livello: band(score, SUBAREA_THRESHOLDS[sub]) };
  }
  const totalC = subC.C1.score + subC.C2.score + subC.C3.score + subC.C4.score;
  const livelloC = band(totalC, TOTALE_C_THRESHOLDS);

  const totale = areaAConv + totalB + totalC;
  const livello = band(Math.max(totale, 0), FINAL_THRESHOLDS);

  return {
    areaA: { raw: areaARaw, converted: areaAConv, livello: areaALiv },
    subB,
    totalB,
    livelloB,
    subC,
    totalC,
    livelloC,
    totale,
    livello,
    unanswered,
  };
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

const AREA_LABELS: Record<AreaCode, string> = {
  A: "A — Indicatori Aziendali",
  B1: "B1 — Funzione e Cultura Organizzativa",
  B2: "B2 — Ruolo nell'Ambito dell'Organizzazione",
  B3: "B3 — Evoluzione della Carriera",
  B4: "B4 — Autonomia Decisionale / Controllo del Lavoro",
  B5: "B5 — Rapporti Interpersonali sul Lavoro",
  B6: "B6 — Interfaccia Casa-Lavoro / Conciliazione",
  C1: "C1 — Ambiente di Lavoro e Attrezzature",
  C2: "C2 — Pianificazione dei Compiti",
  C3: "C3 — Carico e Ritmo di Lavoro",
  C4: "C4 — Orario di Lavoro",
};

const BAND_CLASS: Record<Livello, string> = {
  BASSO: "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30 dark:text-emerald-400",
  MEDIO: "bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-300",
  ALTO: "bg-rose-500/15 text-rose-700 ring-rose-500/30 dark:text-rose-400",
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

function AnswerButton({
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

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface StressChecklistProps {
  aziendaId: string;
  onResultChange?: (result: StressResult) => void;
}

type AreaGroup = { code: string; label: string; indicators: Indicator[] };

function groupIndicators(): AreaGroup[] {
  const ordering: AreaCode[] = [
    "A",
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "C1",
    "C2",
    "C3",
    "C4",
  ];
  return ordering.map((code) => ({
    code,
    label: AREA_LABELS[code],
    indicators: INDICATORS.filter((ind) => ind.area === code),
  }));
}

export function StressChecklist({ aziendaId, onResultChange }: StressChecklistProps) {
  const storageKey = `stress-draft-${aziendaId}`;

  const [answers, setAnswers] = useState<AnswersMap>({});
  const [showUnanswered, setShowUnanswered] = useState(false);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  // Hydrate from localStorage on mount or aziendaId change
  useEffect(() => {
    try {
      const raw = typeof window !== "undefined" ? window.localStorage.getItem(storageKey) : null;
      if (raw) {
        const parsed = JSON.parse(raw) as AnswersMap;
        setAnswers(parsed ?? {});
      } else {
        setAnswers({});
      }
    } catch {
      setAnswers({});
    }
    setShowUnanswered(false);
  }, [storageKey]);

  // Persist on change
  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(answers));
    } catch {
      // ignore quota / privacy mode errors
    }
  }, [answers, storageKey]);

  const result = useMemo(() => computeStress(answers), [answers]);

  useEffect(() => {
    onResultChange?.(result);
  }, [result, onResultChange]);

  const setAnswer = useCallback((id: string, value: StressAnswer) => {
    setAnswers((prev) => ({ ...prev, [id]: value }));
  }, []);

  const toggleCollapse = useCallback((code: string) => {
    setCollapsed((prev) => ({ ...prev, [code]: !prev[code] }));
  }, []);

  const resetDraft = useCallback(() => {
    setAnswers({});
    setShowUnanswered(false);
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
  }, [storageKey]);

  const groups = useMemo(groupIndicators, []);
  const answeredCount = INDICATORS.length - result.unanswered.length;
  const progressPct = Math.round((answeredCount / INDICATORS.length) * 100);
  const unansweredSet = useMemo(
    () => new Set(showUnanswered ? result.unanswered : []),
    [showUnanswered, result.unanswered],
  );

  const areaScore = (code: string): { label: string; badge: Livello } => {
    if (code === "A")
      return { label: `${result.areaA.raw}/40 (conv. ${result.areaA.converted})`, badge: result.areaA.livello };
    if (code.startsWith("B"))
      return { label: `${result.subB[code].score}/${result.subB[code].max}`, badge: result.subB[code].livello };
    return { label: `${result.subC[code].score}/${result.subC[code].max}`, badge: result.subC[code].livello };
  };

  return (
    <div className="space-y-6">
      {/* Sticky score widget */}
      <Card className="sticky top-4 z-10 shadow-sm">
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">Punteggio complessivo</CardTitle>
              <CardDescription className="text-xs">
                INAIL — Metodo Indicatori Oggettivi · formula: A conv. + B tot. + C tot.
              </CardDescription>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-2xl font-semibold tabular-nums">{result.totale}</div>
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  su 67
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
                    "h-full transition-all duration-200",
                    result.livello === "BASSO" && "bg-emerald-500",
                    result.livello === "MEDIO" && "bg-amber-500",
                    result.livello === "ALTO" && "bg-rose-500",
                  )}
                  style={{ width: `${(Math.max(result.totale, 0) / 67) * 100}%` }}
                />
              </div>
              <div className="mt-1 flex justify-between text-[10px] uppercase tracking-wide text-muted-foreground">
                <span>0</span>
                <span>17</span>
                <span>34</span>
                <span>67</span>
              </div>
            </div>
            <Badge variant="secondary" className="gap-1 text-xs">
              <span className="tabular-nums">{answeredCount}/{INDICATORS.length}</span>
              risposte ({progressPct}%)
            </Badge>
          </div>
          <div className="grid grid-cols-1 gap-2 pt-1 text-xs sm:grid-cols-3">
            <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
              <span className="text-muted-foreground">Area A (conv.)</span>
              <span className="flex items-center gap-2 font-medium">
                {result.areaA.converted}/5
                <LivelloBadge livello={result.areaA.livello} />
              </span>
            </div>
            <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
              <span className="text-muted-foreground">Area B</span>
              <span className="flex items-center gap-2 font-medium">
                {result.totalB}/26
                <LivelloBadge livello={result.livelloB} />
              </span>
            </div>
            <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
              <span className="text-muted-foreground">Area C</span>
              <span className="flex items-center gap-2 font-medium">
                {result.totalC}/36
                <LivelloBadge livello={result.livelloC} />
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Unanswered banner */}
      {showUnanswered && result.unanswered.length > 0 && (
        <div
          role="alert"
          className="rounded-md border border-amber-300 bg-amber-100 px-4 py-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200"
        >
          <strong className="font-medium">Valutazione incompleta</strong> — rispondi a tutti gli{" "}
          {result.unanswered.length} indicatori evidenziati prima di confermare.
        </div>
      )}

      {/* Area groups */}
      {groups.map((group) => {
        const isCollapsed = !!collapsed[group.code];
        const score = areaScore(group.code);
        const hasUnanswered = group.indicators.some((ind) => unansweredSet.has(ind.id));
        return (
          <Card
            key={group.code}
            className={cn(
              "transition-shadow",
              hasUnanswered && "ring-2 ring-amber-500/40",
            )}
          >
            <CardHeader className="border-b">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle className="text-sm">{group.label}</CardTitle>
                  <CardDescription className="text-xs">
                    {group.indicators.length} indicatori · punteggio {score.label}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <LivelloBadge livello={score.badge} />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleCollapse(group.code)}
                    className="h-7 px-2 text-xs"
                  >
                    {isCollapsed ? "Espandi" : "Comprimi"}
                  </Button>
                </div>
              </div>
            </CardHeader>
            {!isCollapsed && (
              <CardContent className="pt-3">
                <ul className="divide-y">
                  {group.indicators.map((ind) => {
                    const current = answers[ind.id];
                    const flagged = unansweredSet.has(ind.id);
                    return (
                      <li
                        key={ind.id}
                        data-id={ind.id}
                        className={cn(
                          "flex flex-wrap items-center justify-between gap-3 py-2.5",
                          flagged && "bg-amber-100 -mx-3 rounded-md px-3 dark:bg-amber-950/40",
                        )}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-[10px]">
                              {ind.id}
                            </Badge>
                            <span className="text-sm">{ind.text}</span>
                          </div>
                          {ind.note && (
                            <p className="mt-0.5 text-[11px] text-muted-foreground">
                              {ind.note}
                            </p>
                          )}
                        </div>
                        <div className="flex shrink-0 items-center gap-1.5">
                          {ind.scoring === "tripartite" ? (
                            <>
                              <AnswerButton
                                label="Diminuito"
                                active={current === "DIMINUITO"}
                                onClick={() => setAnswer(ind.id, "DIMINUITO")}
                              />
                              <AnswerButton
                                label="Inalterato"
                                active={current === "INALTERATO"}
                                onClick={() => setAnswer(ind.id, "INALTERATO")}
                              />
                              <AnswerButton
                                label="Aumentato"
                                active={current === "AUMENTATO"}
                                onClick={() => setAnswer(ind.id, "AUMENTATO")}
                                tone="danger"
                              />
                            </>
                          ) : (
                            <>
                              <AnswerButton
                                label="SI"
                                active={current === "SI"}
                                onClick={() => setAnswer(ind.id, "SI")}
                                tone={
                                  ind.scoring === "binary_inverted" ||
                                  ind.scoring === "binary_heavy"
                                    ? "danger"
                                    : "neutral"
                                }
                              />
                              <AnswerButton
                                label="NO"
                                active={current === "NO"}
                                onClick={() => setAnswer(ind.id, "NO")}
                                tone={ind.scoring === "binary" ? "danger" : "neutral"}
                              />
                            </>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </CardContent>
            )}
          </Card>
        );
      })}

      {/* Actions */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 p-4">
        <div className="text-xs text-muted-foreground">
          Bozza salvata automaticamente · {answeredCount}/{INDICATORS.length} risposte
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={resetDraft}>
            Azzera bozza
          </Button>
          <Button
            onClick={() => {
              if (result.unanswered.length > 0) {
                setShowUnanswered(true);
                const first = document.querySelector(
                  `[data-id="${result.unanswered[0]}"]`,
                );
                first?.scrollIntoView({ behavior: "smooth", block: "center" });
              }
            }}
            disabled={result.unanswered.length === 0}
            variant={result.unanswered.length === 0 ? "ghost" : "default"}
            size="sm"
          >
            Evidenzia {result.unanswered.length} mancanti
          </Button>
        </div>
      </div>
    </div>
  );
}
