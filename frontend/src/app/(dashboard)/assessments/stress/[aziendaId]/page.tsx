"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { Loader2, Plus, Sparkles, Users, X } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import {
  StressChecklist,
  computeStress,
  INDICATORS,
  type AnswersMap,
  type Livello,
  type StressResult,
} from "@/components/assessments/stress-checklist";
import type { Azienda } from "@/types";

// Inline copy of the library type. The orchestrator wires the canonical
// definition into `frontend/src/types/index.ts`; keeping this declared
// locally means the page compiles even before that merge lands.
interface StressMisuraLibreria {
  id: string;
  azienda_id: string;
  livello_rischio: "Basso" | "Medio" | "Alto";
  testo: string;
  personalizzato: boolean;
  created_at: string;
}

// Persisted valutazione shape from the API
interface PersistedValutazione {
  id: string;
  mansione: string | null;
  area_a_eventi_sentinella?: Record<string, string>;
  area_b_contenuto_lavoro?: Record<string, string>;
  area_c_contesto_lavoro?: Record<string, string>;
  updated_at?: string;
  livello_rischio?: string | null;
  punteggio_totale?: number | null;
}

const DEFAULT_MANSIONI = [
  "Operaio",
  "Impiegato",
  "Dirigente",
  "Preposto",
];

const DEFAULT_MEASURES: Record<Livello, string[]> = {
  BASSO: [
    "Proseguire con le attività di monitoraggio periodico dei principali indicatori aziendali (infortuni, assenteismo, turnover).",
    "Mantenere attive le procedure di comunicazione interna esistenti.",
    "Programmare la rivalutazione dello stress lavoro-correlato entro 2 anni.",
  ],
  MEDIO: [
    "Istituire incontri periodici (trimestrali) tra dirigenti e lavoratori per raccogliere segnalazioni di disagio.",
    "Rivedere e diffondere procedure aziendali e organigramma, assicurandone la comprensione da parte di tutti i lavoratori.",
    "Introdurre o rafforzare strumenti di partecipazione decisionale (riunioni di team, suggerimenti strutturati).",
    "Pianificare formazione specifica su gestione del carico di lavoro e conciliazione vita-lavoro.",
    "Ripetere la valutazione oggettiva entro 12 mesi; se non migliora, procedere alla valutazione di percezione (2º livello).",
  ],
  ALTO: [
    "Avviare immediatamente la valutazione di percezione dello stress (2º livello) tramite questionari anonimi ai lavoratori.",
    "Coinvolgere medico competente, RLS e RSPP in un piano straordinario di riduzione dello stress.",
    "Ridefinire compiti, ritmi e turnazione per abbattere le fonti di sovraccarico identificate nella checklist.",
    "Rafforzare i canali di segnalazione di conflitti e comportamenti prevaricatori e garantirne la gestione tempestiva.",
    "Verificare efficacia delle azioni correttive entro 12 mesi; monitoraggio continuo degli indicatori aziendali.",
  ],
};

const AZIONE_PER_LIVELLO: Record<Livello, string> = {
  BASSO:
    "Nessun approfondimento richiesto. Monitoraggio periodico. Ripetere valutazione entro 2 anni.",
  MEDIO:
    "Adottare azioni di miglioramento mirate. Se non si rileva miglioramento entro 1 anno, procedere al 2º livello (questionari di percezione lavoratori). Ripetere entro 2 anni.",
  ALTO:
    "Procedere al 2º livello (valutazione percezione lavoratori). Verificare efficacia delle azioni entro 1 anno. Ripetere entro 2 anni.",
};

// The backend library stores the band title-cased (Basso/Medio/Alto) while
// the UI uses the uppercase Livello variant. Map both directions.
const LIVELLO_TO_BAND: Record<Livello, "Basso" | "Medio" | "Alto"> = {
  BASSO: "Basso",
  MEDIO: "Medio",
  ALTO: "Alto",
};

interface Misura {
  id: string;
  text: string;
  personalizzata: boolean;
  // Library row id — present only for measures persisted server-side.
  libraryId?: string;
  // The original default text (if this row started as a default). Used to
  // detect whether the user actually edited the suggestion before saving.
  originalText?: string;
}

function makeId(): string {
  return `m-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

async function getAuthToken(): Promise<string | null> {
  try {
    const s = await fetch("/api/auth/session");
    const session = await s.json();
    return session?.accessToken ?? null;
  } catch {
    return null;
  }
}

/** Build the localStorage key for a mansione draft. NULL mansione = "Generale". */
function draftKey(aziendaId: string, mansione: string | null): string {
  const suffix = mansione ?? "__generale__";
  return `stress-draft-${aziendaId}-${suffix}`;
}

// ---------------------------------------------------------------------------
// Mansione summary badge for the tab list
// ---------------------------------------------------------------------------

interface MansioneSummary {
  mansione: string | null;
  livello: string | null;
  punteggio: number | null;
}

// ---------------------------------------------------------------------------

export default function StressAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [result, setResult] = useState<StressResult>(() => computeStress({}));
  const [misure, setMisure] = useState<Misura[]>([]);
  const [misureLivello, setMisureLivello] = useState<Livello | null>(null);
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeMessage, setFinalizeMessage] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const lastSavedTextRef = useRef<Map<string, string>>(new Map());
  const [savedTick, setSavedTick] = useState(0);

  // Feedback #17: per-mansione state
  const [mansioni, setMansioni] = useState<string[]>([]);
  const [activeMansione, setActiveMansione] = useState<string | null>(null);
  const [addingMansione, setAddingMansione] = useState(false);
  const [newMansioneName, setNewMansioneName] = useState("");
  const [summaries, setSummaries] = useState<MansioneSummary[]>([]);

  // The tab value string: null mansione maps to "__generale__"
  const activeTabValue = activeMansione ?? "__generale__";

  // Load azienda metadata (best-effort)
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const token = await getAuthToken();
        const res = await fetch(`${apiUrl}/api/v1/aziende/${aziendaId}`, {
          headers: token
            ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
            : { "Content-Type": "application/json" },
        });
        if (!res.ok) throw new Error(`Errore ${res.status}`);
        const data = (await res.json()) as Azienda;
        if (!cancelled) setAzienda(data);
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error ? err.message : "Impossibile caricare l'azienda",
          );
        }
      }
    }
    if (aziendaId) load();
    return () => {
      cancelled = true;
    };
  }, [aziendaId, apiUrl]);

  // Fetch all existing valutazioni to build mansioni list + summaries
  const refreshSummaries = useCallback(async () => {
    try {
      const token = await getAuthToken();
      const res = await fetch(
        `${apiUrl}/api/v1/aziende/${aziendaId}/stress/valutazione/all`,
        {
          headers: token
            ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
            : { "Content-Type": "application/json" },
        },
      );
      if (res.ok) {
        const data = (await res.json()) as PersistedValutazione[];
        const sums: MansioneSummary[] = data.map((v) => ({
          mansione: v.mansione,
          livello: v.livello_rischio ?? null,
          punteggio: v.punteggio_totale ?? null,
        }));
        setSummaries(sums);
        // Merge saved mansioni into the mansioni list
        const saved = data
          .map((v) => v.mansione)
          .filter((m): m is string => m !== null);
        setMansioni((prev) => {
          const set = new Set([...prev, ...saved]);
          return Array.from(set);
        });
      }
    } catch {
      // non-critical
    }
  }, [apiUrl, aziendaId]);

  // Hydrate checklist answers from persisted StressValutazione for the
  // active mansione. Runs on mount and when mansione changes.
  useEffect(() => {
    let cancelled = false;
    async function hydrateFromServer() {
      if (!aziendaId) return;
      setHydrated(false);
      setFinalizeMessage(null);
      setSavedAt(null);
      // Reset measures so they reload for the new mansione's livello
      setMisureLivello(null);
      try {
        const token = await getAuthToken();
        const url = new URL(
          `${apiUrl}/api/v1/aziende/${aziendaId}/stress/valutazione`,
        );
        if (activeMansione !== null) {
          url.searchParams.set("mansione", activeMansione);
        }
        const res = await fetch(url.toString(), {
          headers: token
            ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
            : { "Content-Type": "application/json" },
        });
        if (res.ok) {
          const data = (await res.json()) as PersistedValutazione | null;
          if (data && !cancelled) {
            const merged: Record<string, string> = {
              ...(data.area_a_eventi_sentinella ?? {}),
              ...(data.area_b_contenuto_lavoro ?? {}),
              ...(data.area_c_contesto_lavoro ?? {}),
            };
            const key = draftKey(aziendaId, activeMansione);
            const existing = window.localStorage.getItem(key);
            const hasLocalEdits =
              existing &&
              Object.keys(JSON.parse(existing || "{}")).length > 0;
            if (!hasLocalEdits && Object.keys(merged).length > 0) {
              window.localStorage.setItem(key, JSON.stringify(merged));
            }
            if (data.updated_at) setSavedAt(data.updated_at);
            if (data.livello_rischio && data.punteggio_totale !== undefined) {
              setFinalizeMessage(
                `Ultima valutazione archiviata: totale ${data.punteggio_totale ?? "—"} — livello ${data.livello_rischio}`,
              );
            }
          }
        }
      } catch {
        // Swallow — the checklist still works without a server-side row.
      } finally {
        if (!cancelled) setHydrated(true);
      }
    }
    hydrateFromServer();
    // Also refresh summaries on mount
    refreshSummaries();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aziendaId, apiUrl, activeMansione]);

  // Fetch saved mansioni from the server on mount
  useEffect(() => {
    let cancelled = false;
    async function fetchMansioni() {
      try {
        const token = await getAuthToken();
        const res = await fetch(
          `${apiUrl}/api/v1/aziende/${aziendaId}/stress/valutazione/mansioni`,
          {
            headers: token
              ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
              : { "Content-Type": "application/json" },
          },
        );
        if (res.ok && !cancelled) {
          const data = (await res.json()) as string[];
          setMansioni((prev) => {
            const set = new Set([...prev, ...data]);
            return Array.from(set);
          });
        }
      } catch {
        // non-critical
      }
    }
    fetchMansioni();
    return () => {
      cancelled = true;
    };
  }, [apiUrl, aziendaId]);

  // Rebuild the measures panel whenever the risk level changes.
  useEffect(() => {
    if (result.livello === misureLivello) return;
    const livello = result.livello;
    const band = LIVELLO_TO_BAND[livello];
    setMisureLivello(livello);

    let cancelled = false;

    async function hydrate() {
      const defaults: Misura[] = DEFAULT_MEASURES[livello].map((text) => ({
        id: makeId(),
        text,
        personalizzata: false,
        originalText: text,
      }));

      try {
        const token = await getAuthToken();
        const res = await fetch(
          `${apiUrl}/api/v1/aziende/${aziendaId}/stress/misure?livello_rischio=${encodeURIComponent(band)}`,
          {
            headers: token
              ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
              : { "Content-Type": "application/json" },
          },
        );
        if (res.ok) {
          const rows = (await res.json()) as StressMisuraLibreria[];
          const fromLibrary: Misura[] = rows.map((row) => ({
            id: makeId(),
            text: row.testo,
            personalizzata: row.personalizzato,
            libraryId: row.id,
          }));
          if (!cancelled) {
            const merged = [...defaults, ...fromLibrary];
            lastSavedTextRef.current = new Map(
              fromLibrary.map((m) => [m.id, m.text]),
            );
            setSavedTick((t) => t + 1);
            setMisure(merged);
          }
        } else if (!cancelled) {
          setMisure(defaults);
          lastSavedTextRef.current = new Map();
          setSavedTick((t) => t + 1);
        }
      } catch {
        if (!cancelled) {
          setMisure(defaults);
          lastSavedTextRef.current = new Map();
          setSavedTick((t) => t + 1);
        }
      }
    }

    hydrate();
    return () => {
      cancelled = true;
    };
  }, [result.livello, misureLivello, apiUrl, aziendaId]);

  const answeredCount = INDICATORS.length - result.unanswered.length;
  const allAnswered = result.unanswered.length === 0;

  const updateMisuraText = useCallback((id: string, text: string) => {
    setMisure((prev) => prev.map((m) => (m.id === id ? { ...m, text } : m)));
  }, []);

  const saveMisura = useCallback(
    async (id: string) => {
      const row = misure.find((m) => m.id === id);
      if (!row) return;
      const trimmed = row.text.trim();
      if (!trimmed) return;
      if (lastSavedTextRef.current.get(id) === row.text) return;
      if (
        row.originalText !== undefined &&
        row.originalText === row.text &&
        !row.libraryId
      ) {
        return;
      }

      const band = LIVELLO_TO_BAND[result.livello];
      const token = await getAuthToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers.Authorization = `Bearer ${token}`;

      try {
        if (row.libraryId) {
          const res = await fetch(
            `${apiUrl}/api/v1/aziende/${aziendaId}/stress/misure/${row.libraryId}`,
            {
              method: "PUT",
              headers,
              body: JSON.stringify({ testo: row.text }),
            },
          );
          if (!res.ok) throw new Error(`Errore ${res.status}`);
          const saved = (await res.json()) as StressMisuraLibreria;
          lastSavedTextRef.current.set(id, saved.testo);
          setSavedTick((t) => t + 1);
          setMisure((prev) =>
            prev.map((m) =>
              m.id === id
                ? { ...m, personalizzata: true, text: saved.testo }
                : m,
            ),
          );
          toast.success("Misura aggiornata nella libreria cliente");
        } else {
          const res = await fetch(
            `${apiUrl}/api/v1/aziende/${aziendaId}/stress/misure`,
            {
              method: "POST",
              headers,
              body: JSON.stringify({
                azienda_id: aziendaId,
                livello_rischio: band,
                testo: row.text,
              }),
            },
          );
          if (!res.ok) throw new Error(`Errore ${res.status}`);
          const saved = (await res.json()) as StressMisuraLibreria;
          lastSavedTextRef.current.set(id, saved.testo);
          setSavedTick((t) => t + 1);
          setMisure((prev) =>
            prev.map((m) =>
              m.id === id
                ? {
                    ...m,
                    personalizzata: true,
                    libraryId: saved.id,
                    text: saved.testo,
                  }
                : m,
            ),
          );
          toast.success("Misura salvata nella libreria cliente");
        }
      } catch (err) {
        toast.error(
          err instanceof Error
            ? `Salvataggio fallito: ${err.message}`
            : "Salvataggio fallito",
        );
      }
    },
    [apiUrl, aziendaId, misure, result.livello],
  );

  const removeMisura = useCallback(
    async (id: string) => {
      const row = misure.find((m) => m.id === id);
      if (!row) return;
      if (row.libraryId) {
        try {
          const token = await getAuthToken();
          const headers: Record<string, string> = {
            "Content-Type": "application/json",
          };
          if (token) headers.Authorization = `Bearer ${token}`;
          const res = await fetch(
            `${apiUrl}/api/v1/aziende/${aziendaId}/stress/misure/${row.libraryId}`,
            { method: "DELETE", headers },
          );
          if (!res.ok && res.status !== 204) {
            throw new Error(`Errore ${res.status}`);
          }
          toast.success("Misura rimossa dalla libreria cliente");
        } catch (err) {
          toast.error(
            err instanceof Error
              ? `Rimozione fallita: ${err.message}`
              : "Rimozione fallita",
          );
          return;
        }
      }
      lastSavedTextRef.current.delete(id);
      setSavedTick((t) => t + 1);
      setMisure((prev) => prev.filter((m) => m.id !== id));
    },
    [apiUrl, aziendaId, misure],
  );

  const addMisura = useCallback(() => {
    setMisure((prev) => [
      ...prev,
      { id: makeId(), text: "", personalizzata: true },
    ]);
  }, []);

  const suggestWithAI = useCallback(async () => {
    setAiLoading(true);
    try {
      const raw = window.localStorage.getItem(draftKey(aziendaId, activeMansione));
      const answers: AnswersMap = raw ? JSON.parse(raw) : {};
      if (Object.keys(answers).length === 0) {
        toast.error(
          "Compila almeno alcuni indicatori prima di chiedere suggerimenti AI",
        );
        return;
      }

      const token = await getAuthToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers.Authorization = `Bearer ${token}`;

      const res = await fetch(
        `${apiUrl}/api/v1/aziende/${aziendaId}/stress/ai-misure`,
        {
          method: "POST",
          headers,
          body: JSON.stringify({ answers }),
        },
      );
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `Errore ${res.status}`);
      }
      const data = (await res.json()) as { suggestion: string };

      const lines = data.suggestion
        .split(/\r?\n/)
        .map((s) => s.replace(/^\s*[-*•]\s*/, "").replace(/^\s*\d+[.)]\s*/, "").trim())
        .filter((s) => s.length > 0);

      if (lines.length === 0) {
        toast.error("L'AI non ha prodotto suggerimenti utilizzabili");
        return;
      }

      setMisure((prev) => [
        ...prev,
        ...lines.map((text) => ({
          id: makeId(),
          text,
          personalizzata: true,
        })),
      ]);
      toast.success(
        `${lines.length} misure suggerite dall'AI. Rivedile e clicca «Salva» per archiviarle.`,
      );
    } catch (err) {
      toast.error(
        err instanceof Error
          ? `Suggerimento AI fallito: ${err.message}`
          : "Suggerimento AI fallito",
      );
    } finally {
      setAiLoading(false);
    }
  }, [apiUrl, aziendaId, activeMansione]);

  const finalize = useCallback(async () => {
    setFinalizing(true);
    setFinalizeMessage(null);
    try {
      const token = await getAuthToken();

      const raw = window.localStorage.getItem(draftKey(aziendaId, activeMansione));
      const answers: AnswersMap = raw ? JSON.parse(raw) : {};

      const res = await fetch(
        `${apiUrl}/api/v1/aziende/${aziendaId}/stress/valutazione`,
        {
          method: "PUT",
          headers: token
            ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
            : { "Content-Type": "application/json" },
          body: JSON.stringify({
            answers,
            mansione: activeMansione,
          }),
        },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API error ${res.status}`);
      }
      const data = (await res.json()) as {
        punteggio_totale: number | null;
        livello_rischio: string | null;
        updated_at: string;
      };
      if (data.updated_at) setSavedAt(data.updated_at);
      toast.success("Valutazione archiviata nel fascicolo cliente");
      setFinalizeMessage(
        `Valutazione archiviata: totale ${data.punteggio_totale ?? "—"} — livello ${data.livello_rischio ?? "—"}`,
      );
      // Refresh the summaries panel
      refreshSummaries();
    } catch (err) {
      setFinalizeMessage(
        err instanceof Error
          ? `Errore conferma: ${err.message}`
          : "Errore conferma sconosciuto",
      );
    } finally {
      setFinalizing(false);
    }
  }, [apiUrl, aziendaId, activeMansione, refreshSummaries]);

  const pageSubtitle = useMemo(() => {
    if (loadError) return `Azienda ${aziendaId} (metadati non disponibili)`;
    if (azienda) return azienda.ragione_sociale ?? `Azienda ${aziendaId}`;
    return "Caricamento...";
  }, [azienda, aziendaId, loadError]);

  // Handle adding a new custom mansione
  const handleAddMansione = useCallback(() => {
    const trimmed = newMansioneName.trim();
    if (!trimmed) return;
    if (mansioni.includes(trimmed)) {
      toast.error("Questa mansione esiste già");
      return;
    }
    setMansioni((prev) => [...prev, trimmed]);
    setActiveMansione(trimmed);
    setNewMansioneName("");
    setAddingMansione(false);
  }, [newMansioneName, mansioni]);

  // Handle removing a mansione tab (only custom ones)
  const handleRemoveMansione = useCallback(
    (m: string) => {
      setMansioni((prev) => prev.filter((x) => x !== m));
      if (activeMansione === m) {
        setActiveMansione(null);
      }
    },
    [activeMansione],
  );

  // Handle tab change
  const handleTabChange = useCallback((value: string | number | null) => {
    if (value === null) return;
    const strValue = String(value);
    if (strValue === "__generale__") {
      setActiveMansione(null);
    } else {
      setActiveMansione(strValue);
    }
  }, []);

  // The mansione label shown in the UI
  const mansioneLabel = activeMansione ?? "Generale";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
            <Badge variant="secondary">Allegato Stress Lavoro-Correlato</Badge>
            <span>D.Lgs. 81/2008 - INAIL Metodo Indicatori Oggettivi</span>
          </div>
          <h1 className="mt-2 type-h1">
            Valutazione Stress Lavoro-Correlato
          </h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
      </div>

      {/* Mansione selector */}
      <Card>
        <CardHeader className="border-b pb-3">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm">Valutazione per mansione</CardTitle>
          </div>
          <CardDescription className="text-xs">
            Compila una checklist separata per ogni mansione. La valutazione
            &laquo;Generale&raquo; copre l'azienda intera.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4">
          <Tabs value={activeTabValue} onValueChange={handleTabChange}>
            <div className="flex flex-wrap items-center gap-2">
              <TabsList className="flex-wrap h-auto gap-1">
                <TabsTrigger value="__generale__" className="gap-1.5">
                  Generale
                  {summaries.find((s) => s.mansione === null)?.livello && (
                    <LivelloMicroBadge livello={summaries.find((s) => s.mansione === null)!.livello!} />
                  )}
                </TabsTrigger>
                {mansioni.map((m) => (
                  <TabsTrigger key={m} value={m} className="gap-1.5 group/tab">
                    {m}
                    {summaries.find((s) => s.mansione === m)?.livello && (
                      <LivelloMicroBadge livello={summaries.find((s) => s.mansione === m)!.livello!} />
                    )}
                    <button
                      type="button"
                      className="ml-0.5 rounded-sm p-0.5 opacity-0 hover:bg-destructive/10 hover:text-destructive group-hover/tab:opacity-100 transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveMansione(m);
                      }}
                      title={`Rimuovi ${m}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </TabsTrigger>
                ))}
              </TabsList>

              {addingMansione ? (
                <div className="flex items-center gap-1.5">
                  <Input
                    className="h-8 w-40 text-sm"
                    placeholder="Nome mansione..."
                    value={newMansioneName}
                    onChange={(e) => setNewMansioneName((e.target as HTMLInputElement).value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleAddMansione();
                      if (e.key === "Escape") {
                        setAddingMansione(false);
                        setNewMansioneName("");
                      }
                    }}
                    autoFocus
                  />
                  <Button size="sm" variant="outline" className="h-8" onClick={handleAddMansione}>
                    Aggiungi
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8"
                    onClick={() => {
                      setAddingMansione(false);
                      setNewMansioneName("");
                    }}
                  >
                    Annulla
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5">
                  {DEFAULT_MANSIONI.filter((m) => !mansioni.includes(m)).length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {DEFAULT_MANSIONI.filter((m) => !mansioni.includes(m)).map((m) => (
                        <Button
                          key={m}
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs"
                          onClick={() => {
                            setMansioni((prev) => [...prev, m]);
                          }}
                        >
                          + {m}
                        </Button>
                      ))}
                    </div>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 text-xs gap-1"
                    onClick={() => setAddingMansione(true)}
                  >
                    <Plus className="h-3 w-3" />
                    Altra mansione
                  </Button>
                </div>
              )}
            </div>

            {/* Summary of all mansioni with persisted assessments */}
            {summaries.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {summaries.map((s, i) => (
                  <div
                    key={i}
                    className={cn(
                      "flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs cursor-pointer transition-colors",
                      (s.mansione ?? "__generale__") === activeTabValue
                        ? "border-primary/40 bg-primary/5"
                        : "border-border bg-background hover:bg-muted/50",
                    )}
                    onClick={() => handleTabChange(s.mansione ?? "__generale__")}
                  >
                    <span className="font-medium">{s.mansione ?? "Generale"}</span>
                    <span className="text-muted-foreground">
                      {s.punteggio !== null ? `${s.punteggio}/67` : "--"}
                    </span>
                    {s.livello && <LivelloMicroBadge livello={s.livello} />}
                  </div>
                ))}
              </div>
            )}

          </Tabs>
        </CardContent>
      </Card>

      {/* Active mansione banner */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Badge variant="outline" className="text-xs">
          Mansione: {mansioneLabel}
        </Badge>
        <span>
          Compilazione checklist INAIL per{" "}
          <strong className="text-foreground">{mansioneLabel}</strong>
        </span>
      </div>

      {hydrated ? (
        <StressChecklist
          key={activeTabValue}
          aziendaId={aziendaId}
          mansione={activeMansione}
          onResultChange={setResult}
        />
      ) : (
        <Card>
          <CardContent className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Caricamento valutazione precedente...
          </CardContent>
        </Card>
      )}

      {/* Corrective measures — US-3.8 */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-sm">Misure correttive suggerite</CardTitle>
              <CardDescription className="text-xs">
                {AZIONE_PER_LIVELLO[result.livello]}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={suggestWithAI}
                disabled={aiLoading}
                title="Genera misure correttive con AI (gpt-5.4-mini) basate sulle risposte INAIL compilate"
              >
                {aiLoading ? (
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
              <span className="text-xs uppercase tracking-wide text-muted-foreground">
                livello attuale
              </span>
              <span
                className={cn(
                  "inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium ring-1",
                  result.livello === "BASSO" &&
                    "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30",
                  result.livello === "MEDIO" &&
                    "bg-amber-500/15 text-amber-800 ring-amber-500/30",
                  result.livello === "ALTO" &&
                    "bg-rose-500/15 text-rose-700 ring-rose-500/30",
                )}
              >
                {result.livello}
              </span>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          {misure.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Nessuna misura. Aggiungine una personalizzata qui sotto.
            </p>
          )}
          <ul className="space-y-2">
            {misure.map((m, idx) => {
              // savedTick keeps this dependent on lastSavedTextRef mutations
              void savedTick;
              const lastSaved = lastSavedTextRef.current.get(m.id);
              const trimmed = m.text.trim();
              const isDefaultUntouched =
                m.originalText !== undefined &&
                m.originalText === m.text &&
                !m.libraryId;
              const persisted = lastSaved !== undefined;
              const dirty =
                !!trimmed && !isDefaultUntouched && lastSaved !== m.text;
              return (
                <li
                  key={m.id}
                  className={cn(
                    "group rounded-md border p-3 transition-colors",
                    dirty
                      ? "border-amber-300 bg-amber-50/40"
                      : persisted
                        ? "border-emerald-300/60 bg-emerald-50/30"
                        : "border-border bg-background",
                  )}
                >
                  <div className="flex flex-wrap items-start gap-2">
                    <Badge variant="outline" className="mt-0.5 shrink-0 text-[10px]">
                      {idx + 1}
                    </Badge>
                    <textarea
                      className="flex-1 min-w-0 resize-none bg-transparent text-sm leading-relaxed outline-none focus:outline-none"
                      rows={Math.max(2, Math.ceil((m.text.length || 20) / 90))}
                      value={m.text}
                      placeholder="Descrivi la misura correttiva..."
                      onChange={(e) => updateMisuraText(m.id, e.target.value)}
                      onBlur={() => saveMisura(m.id)}
                    />
                    <div className="flex shrink-0 items-center gap-2">
                      {m.personalizzata && (
                        <Badge variant="secondary">Personalizzato</Badge>
                      )}
                      {dirty ? (
                        <Badge
                          variant="outline"
                          className="border-amber-400/70 text-amber-700"
                        >
                          Da salvare
                        </Badge>
                      ) : persisted ? (
                        <Badge
                          variant="outline"
                          className="border-emerald-400/70 text-emerald-700"
                        >
                          Salvato
                        </Badge>
                      ) : null}
                      <Button
                        variant={dirty ? "default" : "ghost"}
                        size="sm"
                        className="h-7 px-2 text-xs"
                        onClick={() => saveMisura(m.id)}
                        disabled={!dirty}
                      >
                        Salva
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive"
                        onClick={() => removeMisura(m.id)}
                      >
                        Rimuovi
                      </Button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <Button variant="outline" size="sm" onClick={addMisura}>
              + Aggiungi misura
            </Button>
            <p className="text-[11px] text-muted-foreground">
              Le misure modificate sono contrassegnate come &laquo;Personalizzato&raquo; e
              salvate nella libreria del cliente.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Finalize */}
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div>
            <p className="text-sm font-medium">
              Conferma valutazione{activeMansione ? ` — ${activeMansione}` : ""}
            </p>
            <p className="text-xs text-muted-foreground">
              {allAnswered
                ? `Tutti i ${INDICATORS.length} indicatori compilati per ${mansioneLabel}. La valutazione sarà archiviata nel fascicolo cliente.`
                : `Mancano ${result.unanswered.length} indicatori per ${mansioneLabel}. Completa la checklist per confermare.`}
            </p>
            {savedAt && (
              <p className="mt-1 text-[11px] text-muted-foreground">
                Ultimo salvataggio: {new Date(savedAt).toLocaleString("it-IT")}
              </p>
            )}
            {finalizeMessage && (
              <p
                className={cn(
                  "mt-1 text-xs",
                  finalizeMessage.startsWith("Errore")
                    ? "text-destructive"
                    : "text-emerald-700",
                )}
              >
                {finalizeMessage}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              disabled={!allAnswered || finalizing}
              onClick={finalize}
            >
              {finalizing ? "Conferma in corso..." : "Conferma valutazione"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <p className="text-[11px] text-muted-foreground">
        Conteggio indicatori: {answeredCount} / {INDICATORS.length} - bozza
        salvata in locale (mansione: {mansioneLabel})
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small livello badge for tab headers and summaries
// ---------------------------------------------------------------------------

function LivelloMicroBadge({ livello }: { livello: string }) {
  const upper = livello.toUpperCase();
  return (
    <span
      className={cn(
        "inline-flex h-4 items-center rounded px-1 text-[10px] font-medium ring-1",
        upper === "BASSO" && "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30",
        upper === "MEDIO" && "bg-amber-500/15 text-amber-800 ring-amber-500/30",
        upper === "ALTO" && "bg-rose-500/15 text-rose-700 ring-rose-500/30",
      )}
    >
      {livello}
    </span>
  );
}
