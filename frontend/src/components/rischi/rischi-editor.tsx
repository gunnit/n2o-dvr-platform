"use client";

/**
 * Standalone Rischi editor — extracted from the (now-removed) Step 6 of the
 * survey wizard so admins / N2O staff can run the risk-evaluation pass on a
 * full-width page without the wizard chrome (feedback 2026-04-30 #2 + #5).
 *
 * The editor is data-decoupled: it loads its own valutazioni from the
 * backend via `apiFetch` and posts them through the same /rischi/batch
 * endpoint the wizard used. Just pass `aziendaId` + `ambienti[]` and
 * (optionally) `attrezzature[]` for the equipment-driven category surfacing.
 */
import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
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
import {
  AlertTriangle,
  Check,
  CloudOff,
  Loader2,
  Sparkles,
  Wrench,
} from "lucide-react";
import { HelpTooltip } from "@/components/ui/help-tooltip";
import { cn } from "@/lib/utils";
import {
  canonicalTipoLabel,
  normalizeAmbienteTipo,
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
// Contextual filtering per ambiente.tipo
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

function getCategorieForTipo(
  tipo: string | undefined | null,
): CategoriaRischio[] {
  const bucket = normalizeAmbienteTipo(tipo);
  return RISCHI_PER_AMBIENTE[bucket] ?? [...CATEGORIE_RISCHIO];
}

// Categories that are pre-flagged "applicabile" for a given environment.
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

const DEFAULT_APPLICABLE_FALLBACK: ReadonlyArray<CategoriaRischio> = [
  "Strutture",
  "Elettrici",
  "Incendio",
  "Fisici",
  "Organizzazione",
  "Ergonomici",
];

function getDefaultApplicable(
  tipo: string | undefined | null,
): Set<CategoriaRischio> {
  const bucket = normalizeAmbienteTipo(tipo);
  return new Set(
    DEFAULT_APPLICABLE_PER_AMBIENTE[bucket] ?? DEFAULT_APPLICABLE_FALLBACK,
  );
}

// ---------------------------------------------------------------------------
// Attrezzature-driven risk override
// ---------------------------------------------------------------------------
const EQUIPMENT_RISK_KEYWORDS: ReadonlyArray<{
  keywords: readonly string[];
  categorie: readonly CategoriaRischio[];
}> = [
  {
    keywords: ["saldatrice", "saldatura"],
    categorie: ["Macchine", "Chimici", "Cancerogeni", "Fisici", "Incendio"],
  },
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
  {
    keywords: ["muletto", "carrello elevatore", "transpallet elettrico"],
    categorie: ["Macchine", "Fisici"],
  },
  {
    keywords: ["forno", "piano cottura", "fornello", "friggitrice"],
    categorie: ["Incendio", "Fisici"],
  },
  {
    keywords: ["affettatrice", "tritacarne", "impastatrice"],
    categorie: ["Macchine"],
  },
  {
    keywords: ["cappa aspirante", "cappa estrazione"],
    categorie: ["Chimici"],
  },
  { keywords: ["cappa chimica"], categorie: ["Chimici", "Cancerogeni"] },
  { keywords: ["centrifuga"], categorie: ["Macchine", "Fisici"] },
  { keywords: ["autoclave"], categorie: ["Biologici", "Fisici"] },
  {
    keywords: ["ponteggio", "trabattello", "scala portatile"],
    categorie: ["Strutture"],
  },
  {
    keywords: ["escavatore", "gru", "betoniera", "martello demolitore"],
    categorie: ["Macchine", "Fisici", "Strutture"],
  },
  { keywords: ["compressore"], categorie: ["Fisici", "Macchine"] },
  {
    keywords: ["lavastoviglie industriale"],
    categorie: ["Chimici", "Macchine"],
  },
  {
    keywords: [
      "frigorifero industriale",
      "abbattitore",
      "frigorifero espositore",
    ],
    categorie: ["Chimici", "Macchine"],
  },
] as const;

function categoriesImpliedByAttrezzature(
  attrezzature: ReadonlyArray<Attrezzatura>,
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
// Ambienti signature (US-1.5 AC3 — kept exported for any caller still
// tracking acknowledgement state).
// ---------------------------------------------------------------------------
export function ambientiSignature(
  ambienti: ReadonlyArray<Ambiente>,
): string {
  return JSON.stringify(
    ambienti
      .map((a) => ({ id: a.id, tipo: (a.tipo ?? "").toLowerCase() }))
      .sort((x, y) => x.id.localeCompare(y.id)),
  );
}

// ---------------------------------------------------------------------------
// Default risk scoring matrix
// Mirrors backend/app/services/reference_data.py DEFAULT_RISK_SCORES.
// ---------------------------------------------------------------------------
const DEFAULT_RISK_SCORES: Record<
  string,
  Record<CategoriaRischio, [number, number]>
> = {
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
  categoria: CategoriaRischio,
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
  indice: number,
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
  existing: ValutazioneRischio[],
): ValutazioneRischio[] {
  const defaultApplicable = getDefaultApplicable(ambienteTipo);
  return CATEGORIE_RISCHIO.map((cat) => {
    const found = existing.find(
      (v) => v.ambiente_id === ambienteId && v.categoria_rischio === cat,
    );
    if (found) return found;
    const [p, d] = getDefaultScores(ambienteTipo, cat);
    const indice = calcIndice(p, d);
    return {
      id: crypto.randomUUID(),
      ambiente_id: ambienteId,
      categoria_rischio: cat,
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

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

export interface RischiEditorProps {
  aziendaId: string;
  ambienti: Ambiente[];
  /** Optional — used to surface equipment-driven risk categories. */
  attrezzature?: Attrezzatura[];
  /** Optional initial valutazioni — e.g. when the parent page already
   *  fetched them. When omitted the editor loads them from the API. */
  initialValutazioni?: ValutazioneRischio[];
  /** Optional change hook so a parent (e.g. wizard) can mirror local edits
   *  into its own state. The editor still drives its own persistence. */
  onChange?: (valutazioni: ValutazioneRischio[]) => void;
}

export function RischiEditor({
  aziendaId,
  ambienti,
  attrezzature = [],
  initialValutazioni,
  onChange,
}: RischiEditorProps) {
  const { apiFetch } = useApi();
  const [selectedAmbienteIndex, setSelectedAmbienteIndex] = useState(0);
  const [mostraTutti, setMostraTutti] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [valutazioni, setValutazioni] = useState<ValutazioneRischio[]>(
    initialValutazioni ?? [],
  );
  const [loadingInitial, setLoadingInitial] = useState(
    initialValutazioni === undefined,
  );

  // Phase 8.3 — AI rischi suggester. Per-ambiente loading flag + last sintesi.
  const [aiLoadingByAmbiente, setAiLoadingByAmbiente] = useState<
    Record<string, boolean>
  >({});
  const [aiSintesiByAmbiente, setAiSintesiByAmbiente] = useState<
    Record<string, string>
  >({});

  const saveTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map(),
  );
  const pendingPayloadsRef = useRef<
    Map<string, { items: Array<Record<string, unknown>> }>
  >(new Map());

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

  type SaveStatus =
    | { kind: "idle" }
    | { kind: "pending" }
    | { kind: "saving" }
    | { kind: "saved"; at: number }
    | { kind: "error"; message: string };
  const [saveStatus, setSaveStatus] = useState<SaveStatus>({ kind: "idle" });

  // Load valutazioni from the backend on mount when the parent didn't
  // supply them. Parent-supplied lists win and skip the network round-trip.
  useEffect(() => {
    if (initialValutazioni !== undefined) return;
    let cancelled = false;
    setLoadingInitial(true);
    apiFetch<ValutazioneRischio[]>(`/api/v1/aziende/${aziendaId}/rischi`)
      .then((rows) => {
        if (cancelled) return;
        setValutazioni(rows);
      })
      .catch(() => {
        // Non-fatal — the editor will seed defaults from the matrix.
      })
      .finally(() => {
        if (!cancelled) setLoadingInitial(false);
      });
    return () => {
      cancelled = true;
    };
    // initialValutazioni only matters at mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aziendaId, apiFetch]);

  const selectedAmbiente = ambienti[selectedAmbienteIndex];

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
        ? allValutazioni.filter((v) => v.ambiente_id === selectedAmbiente.id)
        : [],
    [allValutazioni, selectedAmbiente],
  );

  const impliedByAttrezzature = useMemo(
    () => categoriesImpliedByAttrezzature(attrezzature),
    [attrezzature],
  );

  const categorieVisibili = useMemo<CategoriaRischio[]>(() => {
    if (mostraTutti) return [...CATEGORIE_RISCHIO];
    const ambienteSubset = getCategorieForTipo(selectedAmbiente?.tipo);
    const merged = new Set<CategoriaRischio>(ambienteSubset);
    for (const cat of impliedByAttrezzature.keys()) {
      merged.add(cat);
    }
    return CATEGORIE_RISCHIO.filter((c) => merged.has(c));
  }, [mostraTutti, selectedAmbiente?.tipo, impliedByAttrezzature]);

  const visibleValutazioni = useMemo(() => {
    const setVis = new Set<string>(categorieVisibili);
    return currentValutazioni.filter((v) =>
      setVis.has(v.categoria_rischio as CategoriaRischio),
    );
  }, [currentValutazioni, categorieVisibili]);

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

  // BUG-1 — refs let the debounced save's reconciliation read the latest
  // state instead of a stale closure (see step-rischi.tsx commit history).
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

  const updateLocalValutazioni = useCallback(
    (next: ValutazioneRischio[]) => {
      setValutazioni(next);
      onChangeRef.current?.(next);
    },
    [],
  );

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
          const byCat = new Map(saved.map((s) => [s.categoria_rischio, s]));
          const reconciled = allValutazioniRef.current.map((v) => {
            if (v.ambiente_id !== ambienteId) return v;
            const s = byCat.get(v.categoria_rischio);
            return s ? { ...v, id: s.id } : v;
          });
          setValutazioni(reconciled);
          onChangeRef.current?.(reconciled);
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
    [],
  );

  // Flush pending saves on unmount so navigating away doesn't drop edits.
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
            { method: "POST", body: JSON.stringify(payload) },
          )
          .catch(() => {
            /* fire-and-forget */
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
        if ("probabilita_p" in fields || "danno_d" in fields) {
          const p = merged.probabilita_p ?? 1;
          const d = merged.danno_d ?? 1;
          const indice = calcIndice(p, d);
          merged.indice_i = indice;
          merged.livello_rischio = getLivello(indice);
        }
        return merged;
      });
      updateLocalValutazioni(updated);

      const touched = updated.find((v) => v.id === valId);
      if (touched) {
        const ambienteRows = updated.filter(
          (v) => v.ambiente_id === touched.ambiente_id,
        );
        scheduleAmbienteSave(touched.ambiente_id, ambienteRows);
      }
    },
    [allValutazioni, scheduleAmbienteSave, updateLocalValutazioni],
  );

  /**
   * Persist `misure_prevenzione` for a single ValutazioneRischio.
   *
   * Called by the AI MeasuresPanel mounted inside PericoliPanel. We bypass
   * the debounced batch save here because the user just clicked "Salva
   * misure" — they expect synchronous, observable persistence (and the
   * MeasuresPanel awaits this Promise to flip its loading state).
   */
  const handleSaveMisure = useCallback(
    async (rischioId: string, combinedText: string) => {
      const target = allValutazioni.find((v) => v.id === rischioId);
      if (!target) return;
      try {
        await apiFetch(
          `/api/v1/aziende/${aziendaId}/ambienti/${target.ambiente_id}/rischi/${rischioId}`,
          {
            method: "PUT",
            body: JSON.stringify({ misure_prevenzione: combinedText }),
          },
        );
        const updated = allValutazioni.map((v) =>
          v.id === rischioId ? { ...v, misure_prevenzione: combinedText } : v,
        );
        updateLocalValutazioni(updated);
        toast.success("Misure salvate.");
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Errore nel salvataggio delle misure";
        toast.error(message);
        throw err;
      }
    },
    [allValutazioni, apiFetch, aziendaId, updateLocalValutazioni],
  );

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
          pericolo:
            v.pericolo && v.pericolo.trim().length > 0
              ? v.pericolo
              : ai.pericolo || null,
          probabilita_p: p,
          danno_d: d,
          indice_i: indice,
          livello_rischio: getLivello(indice),
        };
      });
      updateLocalValutazioni(updated);
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
    scheduleAmbienteSave,
    updateLocalValutazioni,
  ]);

  const applyDefaults = useCallback(() => {
    if (!selectedAmbiente) return;
    const updated = allValutazioni.map((v) => {
      if (v.ambiente_id !== selectedAmbiente.id) return v;
      const [p, d] = getDefaultScores(
        selectedAmbiente.tipo,
        v.categoria_rischio as CategoriaRischio,
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
    updateLocalValutazioni(updated);
    const ambienteRows = updated.filter(
      (v) => v.ambiente_id === selectedAmbiente.id,
    );
    scheduleAmbienteSave(selectedAmbiente.id, ambienteRows);
  }, [
    allValutazioni,
    selectedAmbiente,
    scheduleAmbienteSave,
    updateLocalValutazioni,
  ]);

  if (ambienti.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-input bg-muted/30 py-12">
        <AlertTriangle className="mb-2 h-6 w-6 text-muted-foreground" />
        <p className="text-sm text-on-surface-variant">
          Aggiungi almeno un ambiente di lavoro prima di procedere con la
          valutazione dei rischi.
        </p>
      </div>
    );
  }

  if (loadingInitial) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        <span className="text-sm text-muted-foreground">
          Caricamento valutazioni…
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Ambiente selector */}
      <div>
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
                    : "border-input bg-background text-foreground hover:bg-muted",
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
              {selectedAmbiente?.tipo ? ` (${selectedAmbiente.tipo})` : ""}
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
        {/* Drop the inner CardContent padding so the table stretches edge-to-
            edge on the standalone page (feedback #5). The header above keeps
            its standard padding, so the toolbar still breathes. */}
        <CardContent className="p-0 sm:p-0">
          <div className="space-y-4 px-6 pb-6">
            {/* Phase 8.3 — AI sintesi banner for the current ambiente */}
            {selectedAmbiente && aiSintesiByAmbiente[selectedAmbiente.id] && (
              <div className="flex items-start gap-2 rounded-lg border border-violet-300 bg-violet-100 px-3 py-2 text-xs text-violet-900">
                <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-600" />
                <p>{aiSintesiByAmbiente[selectedAmbiente.id]}</p>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/40 px-3 py-2 text-xs">
              <div className="font-medium">
                {summary.selected} di {summary.total} rischi selezionati
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <SummaryChip count={summary.gravissimo} livello="GRAVISSIMO" />
                <SummaryChip count={summary.grave} livello="GRAVE" />
                <SummaryChip count={summary.modesto} livello="MODESTO" />
                <SummaryChip
                  count={summary.accettabile}
                  livello="ACCETTABILE"
                />
              </div>
            </div>
          </div>

          <div className="overflow-x-auto px-6 pb-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[180px]">
                    <span className="inline-flex items-center gap-1.5">
                      Categoria Rischio
                      <HelpTooltip text="Macro-categoria del pericolo (es. Macchine, Elettrici, Chimici). Selezionata dalla libreria N2O in base al tipo di ambiente e alle attrezzature presenti." />
                    </span>
                  </TableHead>
                  <TableHead className="w-[80px] text-center">
                    <span className="inline-flex items-center gap-1.5">
                      Applicabile
                      <HelpTooltip text="Spunta se la categoria di rischio è presente in questo ambiente. Se non spuntata, la riga viene esclusa dal DVR." />
                    </span>
                  </TableHead>
                  <TableHead className="w-[140px] text-center">
                    <span className="inline-flex items-center justify-center gap-1.5">
                      P (Probabilita)
                      <HelpTooltip text="Probabilità del danno (1-4): 1 Bassa, 2 Medio-Bassa, 3 Medio-Alta, 4 Elevata. Considera frequenza di esposizione e misure già in atto." />
                    </span>
                  </TableHead>
                  <TableHead className="w-[140px] text-center">
                    <span className="inline-flex items-center justify-center gap-1.5">
                      D (Danno)
                      <HelpTooltip text="Magnitudo del danno (1-4): 1 Trascurabile, 2 Modesta, 3 Notevole, 4 Ingente. Valuta la gravità del peggior infortunio plausibile." />
                    </span>
                  </TableHead>
                  <TableHead className="w-[80px] text-center">
                    <span className="inline-flex items-center justify-center gap-1.5">
                      I (Indice)
                      <HelpTooltip text="Indice di rischio: I = 2·D + P (formula N2O, non standard P×D). Range 3-12. Il danno pesa il doppio della probabilità." />
                    </span>
                  </TableHead>
                  <TableHead className="w-[140px] text-center">
                    <span className="inline-flex items-center justify-center gap-1.5">
                      Livello
                      <HelpTooltip text="Bande dell'indice: 3-4 Accettabile, 5-6 Modesto, 7-8 Grave, 9-12 Gravissimo. Determina la priorità delle misure di prevenzione." />
                    </span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visibleValutazioni.map((val) => {
                  const p = val.probabilita_p ?? 1;
                  const d = val.danno_d ?? 1;
                  const childSummary = pericoliSummaries[val.id];
                  const hasChildren =
                    !!childSummary && childSummary.applicableCount > 0;
                  const { indice, livello } = getEffective(val);
                  const long = CATEGORIA_LONG[val.categoria_rischio];
                  const showPericoli =
                    val.applicabile && Boolean(val.id) && Boolean(long);

                  return (
                    <Fragment key={val.id}>
                      <TableRow className={cn(!val.applicabile && "opacity-40")}>
                        <TableCell className="font-medium">
                          <div className="flex flex-col gap-1">
                            <span>{val.categoria_rischio}</span>
                            {(() => {
                              const reasons = impliedByAttrezzature.get(
                                val.categoria_rischio as CategoriaRischio,
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
                                : "bg-muted-foreground/30",
                            )}
                          >
                            <span
                              className={cn(
                                "inline-block h-4 w-4 rounded-full bg-white transition-transform",
                                val.applicabile
                                  ? "translate-x-5"
                                  : "translate-x-1",
                              )}
                            />
                          </button>
                        </TableCell>

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
                              onSaveMisure={handleSaveMisure}
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
              {selectedAmbiente?.tipo ? ` "${selectedAmbiente.tipo}"` : ""}.
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
// Local helpers
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

function DashCell() {
  return <div className="text-center text-xs text-muted-foreground">—</div>;
}

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
