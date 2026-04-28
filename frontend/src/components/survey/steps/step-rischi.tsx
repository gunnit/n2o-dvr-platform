"use client";

import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { useApi } from "@/hooks/use-api";
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
import { AlertTriangle, Check, CloudOff, Loader2, Sparkles, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  canonicalTipoLabel,
  normalizeAmbienteTipo,
  type CanonicalTipo,
} from "@/lib/ambiente-tipo";
import type {
  Ambiente,
  Attrezzatura,
  LivelloRischio,
  ValutazioneRischio,
} from "@/types";
import {
  PericoliPanel,
  type PericoliSummary,
} from "@/components/survey/pericoli-panel";

// Map short category name (DB) → canonical long form used by the catalog
// API (PericoloLibreria.categoria). Mirrors backend
// reference_data.CATEGORIA_SHORT_TO_LONG.
const CATEGORIA_LONG: Record<string, string> = {
  Strutture: "Strutture",
  Macchine: "Macchine",
  Elettrici: "Impianti Elettrici",
  Incendio: "Incendio-Esplosioni",
  Chimici: "Agenti Chimici",
  Fisici: "Agenti Fisici",
  Biologici: "Agenti Biologici",
  Cancerogeni: "Agenti Cancerogeni",
  Organizzazione: "Organizzazione del Lavoro",
  Psicologici: "Fattori Psicologici",
  Ergonomici: "Fattori Ergonomici",
};

interface StepRischiProps {
  aziendaId: string;
  ambienti: Ambiente[];
  attrezzature: Attrezzatura[];
  valutazioni: ValutazioneRischio[];
  onChange: (valutazioni: ValutazioneRischio[]) => void;
  // US-1.5 AC3: signature of the ambienti list the operator last
  // acknowledged on Step 5. Owned by the wizard so it survives Step 5
  // unmount/remount under <AnimatePresence mode="wait">. When this
  // diverges from the current ambienti sig the banner appears and
  // clicking "Ho rivisto" calls onAcknowledgeAmbienti with the live sig.
  acknowledgedAmbientiSig: string;
  onAcknowledgeAmbienti: (sig: string) => void;
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
  // Normalize free-text tipo (e.g. "Open space", "Officina meccanica") to
  // one of the 9 canonical buckets the lookup tables key off — without
  // this, every tipo not exactly in the dict fell back to "all 11
  // categories visible" and useless 1/1 defaults.
  const bucket = normalizeAmbienteTipo(tipo);
  return RISCHI_PER_AMBIENTE[bucket] ?? [...CATEGORIE_RISCHIO];
}

// ---------------------------------------------------------------------------
// Phase 2.4 / bug B3 — categories that are pre-flagged "applicabile" for a
// given environment. This is *narrower* than what's visible: a category can
// show up for review (RISCHI_PER_AMBIENTE) without being auto-checked.
// Cancerogeni in particular must stay opt-in everywhere except laboratorio
// — Luca surfaced "Cancerogeno default in sala consumazione" as a real
// confused-the-client bug. Same protective treatment for high-impact rows
// that should never be defaulted on for retail / food-service environments.
// ---------------------------------------------------------------------------
const DEFAULT_APPLICABLE_PER_AMBIENTE: Record<string, CategoriaRischio[]> = {
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
    "Organizzazione",
    "Ergonomici",
  ],
  // Only place Cancerogeni / Biologici are auto-on by default.
  laboratorio: [
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
};

// Conservative fallback for unknown ambiente tipos (operator-entered values
// like "Sala consumazione", "Bar", "Reception"). Notably excludes
// Cancerogeni, Biologici, Chimici, Macchine — those need explicit opt-in.
const DEFAULT_APPLICABLE_FALLBACK: ReadonlyArray<CategoriaRischio> = [
  "Strutture",
  "Elettrici",
  "Incendio",
  "Fisici",
  "Organizzazione",
  "Ergonomici",
];

function getDefaultApplicable(
  tipo: string | undefined | null
): Set<CategoriaRischio> {
  const bucket = normalizeAmbienteTipo(tipo);
  return new Set(
    DEFAULT_APPLICABLE_PER_AMBIENTE[bucket] ?? DEFAULT_APPLICABLE_FALLBACK,
  );
}

// ---------------------------------------------------------------------------
// Attrezzature-driven risk override (US-1.5 AC1 — second half)
//
// When a declared attrezzatura implies a risk category that the ambiente
// subset would normally hide (e.g., a "Saldatrice" in an Ufficio adds
// Chimici / Cancerogeni / Incendio / Fisici that the ufficio filter
// otherwise drops), surface that category anyway and tell the operator
// which attrezzatura caused it. Keyword matching is case-insensitive
// substring against the descrizione so custom variants like "Tornio CNC
// 5 assi" still hit "tornio".
// ---------------------------------------------------------------------------
const EQUIPMENT_RISK_KEYWORDS: ReadonlyArray<{
  keywords: readonly string[];
  categorie: readonly CategoriaRischio[];
}> = [
  // Welding — fumes, UV/heat, fire, IARC-listed
  {
    keywords: ["saldatrice", "saldatura"],
    categorie: ["Macchine", "Chimici", "Cancerogeni", "Fisici", "Incendio"],
  },
  // Industrial machine tools — moving parts, noise
  {
    keywords: [
      "tornio",
      "fresa",
      "pressa",
      "trapano a colonna",
      "trapano colonna",
      "carroponte",
      "rettificatrice",
    ],
    categorie: ["Macchine", "Fisici"],
  },
  { keywords: ["nastro trasportatore"], categorie: ["Macchine"] },
  // Forklift / pallet trucks — vehicle + noise/vibration
  {
    keywords: ["muletto", "carrello elevatore", "transpallet elettrico"],
    categorie: ["Macchine", "Fisici"],
  },
  // Cooking heat sources — fire, burns
  {
    keywords: ["forno", "piano cottura", "fornello", "friggitrice"],
    categorie: ["Incendio", "Fisici"],
  },
  // Cooking machinery — moving blades / mixers
  {
    keywords: ["affettatrice", "tritacarne", "impastatrice"],
    categorie: ["Macchine"],
  },
  // Cooking ventilation — chemical fume control
  {
    keywords: ["cappa aspirante", "cappa estrazione"],
    categorie: ["Chimici"],
  },
  // Lab fume hood
  { keywords: ["cappa chimica"], categorie: ["Chimici", "Cancerogeni"] },
  { keywords: ["centrifuga"], categorie: ["Macchine", "Fisici"] },
  { keywords: ["autoclave"], categorie: ["Biologici", "Fisici"] },
  // Working at height
  {
    keywords: ["ponteggio", "trabattello", "scala portatile"],
    categorie: ["Strutture"],
  },
  // Heavy construction machinery
  {
    keywords: ["escavatore", "gru", "betoniera", "martello demolitore"],
    categorie: ["Macchine", "Fisici", "Strutture"],
  },
  // Compressor — noise + pressure
  { keywords: ["compressore"], categorie: ["Fisici", "Macchine"] },
  // Industrial dishwasher — caustic detergents + heat
  {
    keywords: ["lavastoviglie industriale"],
    categorie: ["Chimici", "Macchine"],
  },
  // Refrigeration — refrigerant gas + machinery
  {
    keywords: [
      "frigorifero industriale",
      "abbattitore",
      "frigorifero espositore",
    ],
    categorie: ["Chimici", "Macchine"],
  },
] as const;

/**
 * Returns a map: categoria → list of attrezzatura descriptions that
 * caused that categoria to surface. Empty map when no attrezzature match
 * any keyword. Used by the visibility filter and the per-row reason chip.
 */
function categoriesImpliedByAttrezzature(
  attrezzature: ReadonlyArray<Attrezzatura>
): Map<CategoriaRischio, string[]> {
  const result = new Map<CategoriaRischio, string[]>();
  for (const att of attrezzature) {
    const desc = (att.descrizione ?? "").toLowerCase();
    if (!desc) continue;
    for (const rule of EQUIPMENT_RISK_KEYWORDS) {
      if (!rule.keywords.some((k) => desc.includes(k))) continue;
      for (const cat of rule.categorie) {
        const list = result.get(cat) ?? [];
        if (!list.includes(att.descrizione)) list.push(att.descrizione);
        result.set(cat, list);
      }
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Ambienti-changed banner (US-1.5 AC3)
//
// When step 2 ambienti changed since the operator last reviewed step 6,
// show an amber banner prompting them to reconfirm. Signature is
// {id, tipo} sorted by id — only changes that actually move the visible
// risk subset count (added/removed ambienti, or tipo edits) flip it.
// Renames or surface-area edits do not trigger the banner.
// ---------------------------------------------------------------------------
export function ambientiSignature(
  ambienti: ReadonlyArray<Ambiente>
): string {
  return JSON.stringify(
    ambienti
      .map((a) => ({ id: a.id, tipo: (a.tipo ?? "").toLowerCase() }))
      .sort((x, y) => x.id.localeCompare(y.id))
  );
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
  // L2 fix — Officina was defaulting to "altro" (all 1,2 → I=3 Accettabile)
  // which is unrealistic for a workshop. These defaults mirror "produzione"
  // with minor tweaks for a mechanical shop context.
  officina: {
    Strutture: [2, 2],
    Macchine: [2, 3],
    Elettrici: [2, 3],
    Incendio: [2, 3],
    Chimici: [2, 2],
    Fisici: [2, 3],
    Biologici: [1, 1],
    Cancerogeni: [1, 2],
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
  const bucket = normalizeAmbienteTipo(tipo);
  const matrix = DEFAULT_RISK_SCORES[bucket];
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
      return "bg-green-100 text-green-800 border-green-200";
    case "MODESTO":
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    case "GRAVE":
      return "bg-orange-100 text-orange-800 border-orange-200";
    case "GRAVISSIMO":
      return "bg-red-100 text-red-800 border-red-200";
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
  ambienteTipo: string | null | undefined,
  existing: ValutazioneRischio[]
): ValutazioneRischio[] {
  // US-2.3 AC1: when the Rischi step first loads, every row must be
  // pre-populated with the default P/D from the scoring matrix — not
  // the generic 1/1 placeholder — so the operator reviews, not enters.
  // Rows that already exist in `existing` (loaded from the backend or
  // authored in a previous session) are preserved as-is.
  const defaultApplicable = getDefaultApplicable(ambienteTipo);
  return CATEGORIE_RISCHIO.map((cat) => {
    const found = existing.find(
      (v) =>
        v.ambiente_id === ambienteId && v.categoria_rischio === cat
    );
    if (found) return found;
    const [p, d] = getDefaultScores(ambienteTipo, cat);
    const indice = calcIndice(p, d);
    return {
      id: crypto.randomUUID(),
      ambiente_id: ambienteId,
      categoria_rischio: cat,
      // Phase 2.4: only pre-flag categories appropriate for the env type.
      // Unknown tipos use the conservative fallback (no Cancerogeni etc.).
      applicabile: defaultApplicable.has(cat),
      pericolo: null,
      condizioni_esposizione: null,
      rischio: null,
      misure_prevenzione: null,
      probabilita_p: p,
      danno_d: d,
      indice_i: indice,
      livello_rischio: getLivello(indice),
    };
  });
}

export function StepRischi({
  aziendaId,
  ambienti,
  attrezzature,
  valutazioni,
  onChange,
  acknowledgedAmbientiSig,
  onAcknowledgeAmbienti,
}: StepRischiProps) {
  const { apiFetch } = useApi();
  const [selectedAmbienteIndex, setSelectedAmbienteIndex] = useState(0);
  const [mostraTutti, setMostraTutti] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  // Phase 8.3 — AI rischi suggester. Per-ambiente loading flag + last sintesi.
  const [aiLoadingByAmbiente, setAiLoadingByAmbiente] = useState<
    Record<string, boolean>
  >({});
  const [aiSintesiByAmbiente, setAiSintesiByAmbiente] = useState<
    Record<string, string>
  >({});

  // Debounced batch-save per ambiente. When the operator changes a slider we
  // schedule a POST to /rischi/batch 800ms later so rapid drag-updates coalesce.
  // This replaces the implicit "bozza salvata" label (which was a lie for
  // this step — see QA H5/B3 notes in the report) with an actual round-trip.
  const saveTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map()
  );
  // Phase 2.2 / bug B2 — flush-on-unmount needs the latest pending payload
  // per ambiente, otherwise toggling "disabilita" and immediately stepping
  // forward would silently drop the change. Mirrors saveTimersRef so the
  // unmount handler can dispatch one final POST per pending ambiente.
  const pendingPayloadsRef = useRef<
    Map<string, { items: Array<Record<string, unknown>> }>
  >(new Map());

  // BUG-3 — per-rischio summary published by each PericoliPanel (max
  // child indice + applicable count). When a rischio has children, its
  // displayed I/Livello and the top summary banner derive from the
  // children, not the parent's own P/D. Without this the parent could
  // read "ACCETTABILE 3" while 12 GRAVE pericoli sat underneath.
  const [pericoliSummaries, setPericoliSummaries] = useState<
    Record<string, PericoliSummary>
  >({});
  const handlePericoliSummary = useCallback(
    (rischioId: string, summary: PericoliSummary) => {
      setPericoliSummaries((prev) => {
        const existing = prev[rischioId];
        if (
          existing &&
          existing.applicableCount === summary.applicableCount &&
          existing.maxIndice === summary.maxIndice &&
          existing.maxLivello === summary.maxLivello &&
          existing.totalCount === summary.totalCount
        ) {
          return prev;
        }
        return { ...prev, [rischioId]: summary };
      });
    },
    [],
  );

  // UX-4 — real save status. The wizard footer's "bozza salvata" string
  // was static; here we track per-step pending/saving/saved/error and
  // render a small badge in the card header. State machine:
  //   idle    → no edits this session
  //   pending → debounce window open (operator just edited)
  //   saving  → POST in flight
  //   saved   → last POST returned 2xx (carries the timestamp)
  //   error   → last POST threw (toast already raised; badge stays red
  //             until next successful save)
  type SaveStatus =
    | { kind: "idle" }
    | { kind: "pending" }
    | { kind: "saving" }
    | { kind: "saved"; at: number }
    | { kind: "error"; message: string };
  const [saveStatus, setSaveStatus] = useState<SaveStatus>({ kind: "idle" });

  // US-1.5 AC3: ack-sig is owned by the wizard so it survives this
  // component's unmount/remount across step navigation. A fresh
  // page-load initialises the wizard's ack-sig from the initial
  // ambienti, so the banner does NOT show until the operator actually
  // edits Step 2 during this session.
  const currentAmbientiSig = useMemo(
    () => ambientiSignature(ambienti),
    [ambienti]
  );
  const ambientiChanged = currentAmbientiSig !== acknowledgedAmbientiSig;

  const selectedAmbiente = ambienti[selectedAmbienteIndex];

  // Ensure we have valutazioni for all ambienti — seeded from the
  // default P/D matrix so AC1 ("risks pre-filled from a default scoring
  // matrix") holds the first time the step opens.
  const allValutazioni = useMemo(() => {
    const result: ValutazioneRischio[] = [];
    for (const amb of ambienti) {
      result.push(...initValutazioni(amb.id, amb.tipo, valutazioni));
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

  // US-1.5 AC1 second half: categories implied by the declared
  // attrezzature (azienda-wide — equipment is shared across ambienti).
  const impliedByAttrezzature = useMemo(
    () => categoriesImpliedByAttrezzature(attrezzature),
    [attrezzature]
  );

  // Compute the subset of categories shown for this ambiente.tipo,
  // augmented by anything an attrezzatura implies.
  const categorieVisibili = useMemo<CategoriaRischio[]>(() => {
    if (mostraTutti) return [...CATEGORIE_RISCHIO];
    const ambienteSubset = getCategorieForTipo(selectedAmbiente?.tipo);
    const merged = new Set<CategoriaRischio>(ambienteSubset);
    for (const cat of impliedByAttrezzature.keys()) {
      merged.add(cat);
    }
    // Preserve canonical order of CATEGORIE_RISCHIO so the table doesn't
    // reflow when a new attrezzatura surfaces a category mid-session.
    return CATEGORIE_RISCHIO.filter((c) => merged.has(c));
  }, [mostraTutti, selectedAmbiente?.tipo, impliedByAttrezzature]);

  const visibleValutazioni = useMemo(() => {
    const setVis = new Set<string>(categorieVisibili);
    return currentValutazioni.filter((v) =>
      setVis.has(v.categoria_rischio as CategoriaRischio)
    );
  }, [currentValutazioni, categorieVisibili]);

  // BUG-3 — derive a row's *effective* indice/livello: when a row has
  // catalog/custom pericoli children, the parent's own P/D becomes a
  // summary-of-summaries — we render the max-of-children instead so the
  // parent badge can't lie about its own contents.
  const getEffective = useCallback(
    (val: ValutazioneRischio): { indice: number; livello: LivelloRischio } => {
      const childSummary = pericoliSummaries[val.id];
      if (
        childSummary &&
        childSummary.applicableCount > 0 &&
        childSummary.maxIndice != null &&
        childSummary.maxLivello != null
      ) {
        return {
          indice: childSummary.maxIndice,
          livello: childSummary.maxLivello,
        };
      }
      const p = val.probabilita_p ?? 1;
      const d = val.danno_d ?? 1;
      const indice = calcIndice(p, d);
      return { indice, livello: getLivello(indice) };
    },
    [pericoliSummaries],
  );

  // Summary counts over the currently visible rows. Counts use the
  // *effective* livello so the chips agree with what the operator sees
  // in each row (and what will end up in the DVR).
  const summary = useMemo(() => {
    const applicabiliRows = visibleValutazioni.filter((v) => v.applicabile);
    const total = visibleValutazioni.length;
    const selected = applicabiliRows.length;

    let gravissimo = 0;
    let grave = 0;
    let modesto = 0;
    let accettabile = 0;

    for (const v of applicabiliRows) {
      const { livello } = getEffective(v);
      if (livello === "GRAVISSIMO") gravissimo += 1;
      else if (livello === "GRAVE") grave += 1;
      else if (livello === "MODESTO") modesto += 1;
      else accettabile += 1;
    }

    return { total, selected, gravissimo, grave, modesto, accettabile };
  }, [visibleValutazioni, getEffective]);

  // BUG-1 — refs let the debounced save's reconciliation read the
  // *latest* state instead of a stale closure. Previously the timeout
  // body did `onChange(allValutazioni.map(...))` with `allValutazioni`
  // captured when the save was scheduled. After fetchAIRischi flipped
  // every row to AI values and then scheduled the save, the timeout
  // would fire 800ms later with the pre-AI snapshot and overwrite the
  // parent state — so the AI's P/D vanished from the UI even though
  // the server had persisted them. Reads via refs always see the
  // post-AI state.
  const apiFetchRef = useRef(apiFetch);
  const aziendaIdRef = useRef(aziendaId);
  const allValutazioniRef = useRef(allValutazioni);
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    apiFetchRef.current = apiFetch;
    aziendaIdRef.current = aziendaId;
    allValutazioniRef.current = allValutazioni;
    onChangeRef.current = onChange;
  });

  const scheduleAmbienteSave = useCallback(
    (ambienteId: string, rows: ValutazioneRischio[]) => {
      const timers = saveTimersRef.current;
      const pending = pendingPayloadsRef.current;
      const existing = timers.get(ambienteId);
      if (existing) clearTimeout(existing);

      const payload = {
        items: rows.map((r) => ({
          id: r.id,
          categoria_rischio: r.categoria_rischio,
          applicabile: r.applicabile,
          pericolo: r.pericolo ?? null,
          condizioni_esposizione: r.condizioni_esposizione ?? null,
          rischio: r.rischio ?? null,
          misure_prevenzione: r.misure_prevenzione ?? null,
          probabilita_p: r.probabilita_p ?? null,
          danno_d: r.danno_d ?? null,
        })),
      };
      pending.set(ambienteId, payload);
      setSaveStatus({ kind: "pending" });

      const handle = setTimeout(async () => {
        timers.delete(ambienteId);
        pending.delete(ambienteId);
        setSaveStatus({ kind: "saving" });
        try {
          const saved = await apiFetchRef.current<ValutazioneRischio[]>(
            `/api/v1/aziende/${aziendaIdRef.current}/ambienti/${ambienteId}/rischi/batch`,
            { method: "POST", body: JSON.stringify(payload) },
          );
          // Merge server-returned ids back into local state so subsequent
          // PUTs use the persisted id, not the client-side placeholder.
          // Read latest state from the ref — `allValutazioni` captured at
          // schedule time is stale by the time this resolves.
          const byCat = new Map(saved.map((s) => [s.categoria_rischio, s]));
          onChangeRef.current(
            allValutazioniRef.current.map((v) => {
              if (v.ambiente_id !== ambienteId) return v;
              const s = byCat.get(v.categoria_rischio);
              return s ? { ...v, id: s.id } : v;
            }),
          );
          setSaveStatus({ kind: "saved", at: Date.now() });
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Errore nel salvataggio delle valutazioni rischio";
          toast.error(message);
          setSaveStatus({ kind: "error", message });
        }
      }, 800);
      timers.set(ambienteId, handle);
    },
    // No `allValutazioni` / `onChange` / `apiFetch` deps — the timeout
    // body always reads the latest values via refs, and capturing them
    // here would cancel + reschedule debounces on every parent render.
    [],
  );

  // Phase 2.2 / bug B2 — flush (not cancel) any pending saves when the
  // component unmounts. Without this, toggling a rischio's "applicabile"
  // and immediately stepping forward dropped the change: the disabled
  // rischio would still appear in the generated DVR. We keep latest
  // payloads in pendingPayloadsRef and dispatch them fire-and-forget;
  // the request stays in the network stack across the unmount.
  useEffect(() => {
    const timers = saveTimersRef.current;
    const pending = pendingPayloadsRef.current;
    return () => {
      for (const [ambienteId, payload] of pending) {
        const handle = timers.get(ambienteId);
        if (handle) clearTimeout(handle);
        void apiFetchRef
          .current(
            `/api/v1/aziende/${aziendaIdRef.current}/ambienti/${ambienteId}/rischi/batch`,
            { method: "POST", body: JSON.stringify(payload) }
          )
          .catch(() => {
            // Fire-and-forget on unmount — no UI to notify.
          });
      }
      pending.clear();
      timers.clear();
    };
  }, []);

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

      // Persist the whole ambiente's valutazioni (debounced).
      const touched = updated.find((v) => v.id === valId);
      if (touched) {
        const ambienteRows = updated.filter(
          (v) => v.ambiente_id === touched.ambiente_id
        );
        scheduleAmbienteSave(touched.ambiente_id, ambienteRows);
      }
    },
    [allValutazioni, onChange, scheduleAmbienteSave]
  );

  // Phase 8.3 — fetch AI rischi suggestions for the selected ambiente.
  // Merges into existing valutazioni (does NOT replace): AI sets applicabile,
  // pericolo, P, D — operator-edited fields like misure_prevenzione and
  // condizioni_esposizione are preserved untouched.
  const fetchAIRischi = useCallback(async () => {
    if (!selectedAmbiente) return;
    const ambienteId = selectedAmbiente.id;
    setAiLoadingByAmbiente((prev) => ({ ...prev, [ambienteId]: true }));
    try {
      const response = await apiFetch<{
        items: Array<{
          categoria_rischio: string;
          applicabile: boolean;
          pericolo: string;
          probabilita_p: number;
          danno_d: number;
          motivazione: string;
        }>;
        sintesi: string;
      }>(
        `/api/v1/aziende/${aziendaId}/ambienti/${ambienteId}/rischi/suggerisci`,
        { method: "POST" },
      );
      const byCat = new Map(
        response.items.map((s) => [s.categoria_rischio, s]),
      );
      let mergedCount = 0;
      const updated = allValutazioni.map((v) => {
        if (v.ambiente_id !== ambienteId) return v;
        const ai = byCat.get(v.categoria_rischio);
        if (!ai) return v;
        const p = ai.probabilita_p;
        const d = ai.danno_d;
        const indice = calcIndice(p, d);
        mergedCount += 1;
        return {
          ...v,
          applicabile: ai.applicabile,
          // Only overwrite pericolo when the operator hasn't authored one
          // — protects manual edits from being clobbered by re-runs.
          pericolo: v.pericolo && v.pericolo.trim().length > 0
            ? v.pericolo
            : (ai.pericolo || null),
          probabilita_p: p,
          danno_d: d,
          indice_i: indice,
          livello_rischio: getLivello(indice),
        };
      });
      onChange(updated);
      const ambienteRows = updated.filter(
        (v) => v.ambiente_id === ambienteId,
      );
      scheduleAmbienteSave(ambienteId, ambienteRows);
      setAiSintesiByAmbiente((prev) => ({
        ...prev,
        [ambienteId]: response.sintesi,
      }));
      const applicabili = response.items.filter((i) => i.applicabile).length;
      toast.success(
        `AI: ${applicabili} categorie applicabili, ${mergedCount} righe aggiornate.`,
      );
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Errore nella generazione AI",
      );
    } finally {
      setAiLoadingByAmbiente((prev) => ({ ...prev, [ambienteId]: false }));
    }
  }, [
    apiFetch,
    aziendaId,
    selectedAmbiente,
    allValutazioni,
    onChange,
    scheduleAmbienteSave,
  ]);

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
    const ambienteRows = updated.filter(
      (v) => v.ambiente_id === selectedAmbiente.id
    );
    scheduleAmbienteSave(selectedAmbiente.id, ambienteRows);
  }, [allValutazioni, onChange, selectedAmbiente, scheduleAmbienteSave]);

  if (ambienti.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-on-surface-variant">
          Aggiungi almeno un ambiente di lavoro nel passo 3 prima di
          procedere con la valutazione dei rischi.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* US-1.5 AC3: ambienti changed since last visit — prompt the
          operator to reconfirm. Dismiss-only (acknowledgement, not a
          mutation) — the row data is already up-to-date thanks to the
          allValutazioni reseed, so no destructive action is offered. */}
      {ambientiChanged && (
        <div className="flex flex-col gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">Ambienti modificati</p>
              <p className="text-xs">
                Hai modificato la lista degli ambienti dal passo 3.
                Rivedi le selezioni di rischio per i nuovi ambienti o
                quelli con tipologia cambiata.
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="border-amber-400 text-amber-900 hover:bg-amber-100"
            onClick={() => onAcknowledgeAmbienti(currentAmbientiSig)}
          >
            Ho rivisto
          </Button>
        </div>
      )}

      {/* Ambiente selector */}
      <div>
        <div className="mb-4">
          <h3 className="font-heading text-xl font-bold text-on-surface">
            Valutazione Rischi
          </h3>
          <p className="mt-1 text-sm text-on-surface-variant">
            Valuta i rischi per ogni ambiente di lavoro. Formula: I = 2D + P
          </p>
        </div>
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
      </div>

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
            <CardDescription className="flex flex-wrap items-center gap-2">
              <span>
                {mostraTutti
                  ? "Stai vedendo tutte le 11 categorie di rischio."
                  : `Categorie filtrate per ${canonicalTipoLabel(
                      normalizeAmbienteTipo(selectedAmbiente?.tipo),
                    )}.`}
              </span>
              <SaveStatusBadge status={saveStatus} />
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
              onClick={fetchAIRischi}
              disabled={
                !selectedAmbiente ||
                aiLoadingByAmbiente[selectedAmbiente.id] === true
              }
              className="border-violet-300 text-violet-700 hover:bg-violet-100"
            >
              {selectedAmbiente &&
              aiLoadingByAmbiente[selectedAmbiente.id] ? (
                <>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  Analisi...
                </>
              ) : (
                <>
                  <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                  Suggerisci con AI
                </>
              )}
            </Button>
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
          {/* Phase 8.3 — AI sintesi banner for the current ambiente */}
          {selectedAmbiente && aiSintesiByAmbiente[selectedAmbiente.id] && (
            <div className="mb-4 flex items-start gap-2 rounded-lg border border-violet-300 bg-violet-100 px-3 py-2 text-xs text-violet-900">
              <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-600" />
              <p>{aiSintesiByAmbiente[selectedAmbiente.id]}</p>
            </div>
          )}
          {/* UX-1 — summary bar. Chips with count = 0 render muted so a
              red "0 Gravissimo" badge can't mislead the eye into thinking
              there's an alert; the highest non-zero livello carries the
              colored treatment so the operator sees at-a-glance whether
              this ambiente is dominated by GRAVISSIMO/GRAVE/MODESTO. */}
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/40 px-3 py-2 text-xs">
            <div className="font-medium">
              {summary.selected} di {summary.total} rischi selezionati
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <SummaryChip count={summary.gravissimo} livello="GRAVISSIMO" />
              <SummaryChip count={summary.grave} livello="GRAVE" />
              <SummaryChip count={summary.modesto} livello="MODESTO" />
              <SummaryChip count={summary.accettabile} livello="ACCETTABILE" />
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
                // BUG-3 — when this rischio has children pericoli, the
                // displayed I/Livello come from max-of-children. The own
                // P/D sliders still drive the *parent* row (used as the
                // fallback when there are no children), but the badge
                // column shows the truth.
                const childSummary = pericoliSummaries[val.id];
                const hasChildren =
                  !!childSummary && childSummary.applicableCount > 0;
                const { indice, livello } = getEffective(val);
                // Phase 3 (1:N): for every applicable categoria we render
                // the expandable per-pericolo editor as a sibling row
                // immediately under the categoria row, so the sub-rows
                // visually belong to their parent group instead of piling
                // up at the bottom of the table.
                const long = CATEGORIA_LONG[val.categoria_rischio];
                const showPericoli = val.applicabile && Boolean(val.id) && Boolean(long);

                return (
                  <Fragment key={val.id}>
                    <TableRow
                      className={cn(
                        !val.applicabile && "opacity-40"
                      )}
                    >
                      <TableCell className="font-medium">
                        <div className="flex flex-col gap-1">
                          <span>{val.categoria_rischio}</span>
                          {(() => {
                            const reasons = impliedByAttrezzature.get(
                              val.categoria_rischio as CategoriaRischio
                            );
                            if (!reasons || reasons.length === 0) return null;
                            const tooltip = `Aggiunto perche hai dichiarato: ${reasons.join(", ")}`;
                            return (
                              <span
                                title={tooltip}
                                className="inline-flex w-fit items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-800"
                              >
                                <Wrench className="h-3 w-3" />
                                Suggerito da attrezzature
                              </span>
                            );
                          })()}
                        </div>
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

                      {/* P — UX-2 segmented 1/2/3/4 (replaces unstyled
                          range slider). BUG-5: when row is not
                          applicable, render an em-dash placeholder
                          instead of an empty cell. */}
                      <TableCell>
                        {val.applicabile ? (
                          <PDSegmented
                            value={p}
                            onChange={(next) =>
                              updateValutazione(val.id, {
                                probabilita_p: next,
                              })
                            }
                            ariaLabel={`Probabilita ${val.categoria_rischio}`}
                            disabledByChildren={hasChildren}
                          />
                        ) : (
                          <DashCell />
                        )}
                      </TableCell>

                      {/* D — same treatment as P */}
                      <TableCell>
                        {val.applicabile ? (
                          <PDSegmented
                            value={d}
                            onChange={(next) =>
                              updateValutazione(val.id, {
                                danno_d: next,
                              })
                            }
                            ariaLabel={`Danno ${val.categoria_rischio}`}
                            disabledByChildren={hasChildren}
                          />
                        ) : (
                          <DashCell />
                        )}
                      </TableCell>

                      {/* Indice — derived (children-aware) */}
                      <TableCell className="text-center">
                        {val.applicabile ? (
                          <div className="flex flex-col items-center gap-1">
                            <span className="text-lg font-bold">{indice}</span>
                            <div className="h-1.5 w-full max-w-[60px] overflow-hidden rounded-full bg-muted">
                              <div
                                className={cn(
                                  "h-full rounded-full transition-all",
                                  getIndiceBarColor(livello),
                                )}
                                style={{
                                  width: `${((indice - 3) / 9) * 100}%`,
                                }}
                              />
                            </div>
                            {hasChildren && (
                              <span
                                title="Calcolato come massimo dei pericoli di dettaglio"
                                className="text-[9px] uppercase tracking-wide text-muted-foreground"
                              >
                                da pericoli
                              </span>
                            )}
                          </div>
                        ) : (
                          <DashCell />
                        )}
                      </TableCell>

                      {/* Livello */}
                      <TableCell className="text-center">
                        {val.applicabile ? (
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-xs font-semibold",
                              getLivelloStyle(livello),
                            )}
                          >
                            {livello}
                          </Badge>
                        ) : (
                          <DashCell />
                        )}
                      </TableCell>
                    </TableRow>
                    {showPericoli && (
                      <TableRow className="hover:bg-transparent">
                        <TableCell colSpan={6} className="p-0">
                          <PericoliPanel
                            aziendaId={aziendaId}
                            ambienteId={val.ambiente_id}
                            valutazione={val}
                            categoriaLong={long as string}
                            onSummaryChange={handlePericoliSummary}
                          />
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
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

// ---------------------------------------------------------------------------
// UX-2 — segmented 1/2/3/4 control replacing the unstyled <input type=range>
// for P (probabilita) and D (danno). Each value is a discrete pip the
// operator can hit directly on tablets in the field; the active pip uses
// the brand primary so the choice is unmistakable. When the rischio has
// children pericoli, the parent slider is greyed out — the value still
// renders but editing it would mislead since the displayed I/Livello come
// from the children, not from this control.
// ---------------------------------------------------------------------------
interface PDSegmentedProps {
  value: number;
  onChange: (next: number) => void;
  ariaLabel: string;
  disabledByChildren?: boolean;
}

function PDSegmented({
  value,
  onChange,
  ariaLabel,
  disabledByChildren,
}: PDSegmentedProps) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cn(
        "mx-auto flex w-fit items-center gap-0.5 rounded-md border bg-background p-0.5",
        disabledByChildren && "opacity-50",
      )}
    >
      {[1, 2, 3, 4].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          onClick={() => onChange(n)}
          className={cn(
            "h-6 w-6 rounded text-xs font-semibold transition-colors",
            value === n
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-muted",
          )}
        >
          {n}
        </button>
      ))}
    </div>
  );
}

// BUG-5 — placeholder for cells whose row is not applicable. Renders an
// em-dash centered in the cell so the table doesn't appear broken. We
// keep the full muted opacity treatment on the parent <TableRow> so the
// whole row reads as "off".
function DashCell() {
  return (
    <div className="text-center text-xs text-muted-foreground">—</div>
  );
}

// UX-1 — summary chip. count = 0 falls back to a muted style so a red
// "0 Gravissimo" badge can't be misread as an alert; non-zero counts
// keep the per-livello color treatment.
interface SummaryChipProps {
  count: number;
  livello: LivelloRischio;
}

function SummaryChip({ count, livello }: SummaryChipProps) {
  const label = (() => {
    switch (livello) {
      case "GRAVISSIMO":
        return "Gravissimo";
      case "GRAVE":
        return "Grave";
      case "MODESTO":
        return "Modesto";
      case "ACCETTABILE":
        return "Accettabile";
    }
  })();
  return (
    <Badge
      variant="outline"
      className={cn(
        "font-semibold",
        count === 0
          ? "border-muted bg-muted/30 text-muted-foreground"
          : getLivelloStyle(livello),
      )}
    >
      {count} {label}
    </Badge>
  );
}

// UX-4 — small status pill rendered next to the card description.
// Mirrors the saveStatus state machine in StepRischi. Hidden in the
// idle state to avoid noise on the first paint.
type SaveStatus =
  | { kind: "idle" }
  | { kind: "pending" }
  | { kind: "saving" }
  | { kind: "saved"; at: number }
  | { kind: "error"; message: string };

function SaveStatusBadge({ status }: { status: SaveStatus }) {
  if (status.kind === "idle") return null;
  if (status.kind === "pending" || status.kind === "saving") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
        <Loader2 className="h-2.5 w-2.5 animate-spin" />
        Salvataggio…
      </span>
    );
  }
  if (status.kind === "error") {
    return (
      <span
        title={status.message}
        className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700"
      >
        <CloudOff className="h-2.5 w-2.5" />
        Salvataggio fallito
      </span>
    );
  }
  // saved
  const time = new Date(status.at).toLocaleTimeString("it-IT", {
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
      <Check className="h-2.5 w-2.5" />
      Salvato {time}
    </span>
  );
}
