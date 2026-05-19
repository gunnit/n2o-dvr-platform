"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { Loader2, Sparkles } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
  // Feedback #31 (2026-05-18): hydrate the checklist from any persisted
  // StressValutazione before mounting the checklist component, so a
  // returning operator sees the previous run instead of an empty form.
  // The checklist reads localStorage on mount, so we have to write the
  // saved answers BEFORE it renders — gate render on `hydrated`.
  const [hydrated, setHydrated] = useState(false);
  // Timestamp of the latest persisted valutazione, for the finalize
  // banner. Null until the operator confirms at least once.
  const [savedAt, setSavedAt] = useState<string | null>(null);
  // Track the last saved text per row so we can detect dirty state on blur.
  const lastSavedTextRef = useRef<Map<string, string>>(new Map());
  // Feedback #31 (2026-05-18): bump on every successful save/delete so the
  // per-row "Salvato / Da salvare" badge re-renders. The ref alone won't
  // trigger React renders.
  const [savedTick, setSavedTick] = useState(0);

  // Load azienda metadata (best-effort — if auth not set up, we fall back to
  // the raw id so the UI still works for testing).
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

  // Hydrate checklist answers from any persisted StressValutazione. Runs
  // once on mount. We write into localStorage (the StressChecklist owns
  // its state via that key) and only then flip `hydrated` so the
  // checklist mounts with the right initial answers.
  useEffect(() => {
    let cancelled = false;
    async function hydrateFromServer() {
      if (!aziendaId) return;
      try {
        const token = await getAuthToken();
        const res = await fetch(
          `${apiUrl}/api/v1/aziende/${aziendaId}/stress/valutazione`,
          {
            headers: token
              ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
              : { "Content-Type": "application/json" },
          },
        );
        if (res.ok) {
          const data = (await res.json()) as null | {
            area_a_eventi_sentinella?: Record<string, string>;
            area_b_contenuto_lavoro?: Record<string, string>;
            area_c_contesto_lavoro?: Record<string, string>;
            updated_at?: string;
            livello_rischio?: string | null;
            punteggio_totale?: number | null;
          };
          if (data && !cancelled) {
            const merged: Record<string, string> = {
              ...(data.area_a_eventi_sentinella ?? {}),
              ...(data.area_b_contenuto_lavoro ?? {}),
              ...(data.area_c_contesto_lavoro ?? {}),
            };
            // Only overwrite the local draft if (a) there's no local
            // draft yet, or (b) the local draft is empty. We don't want
            // to clobber an in-progress edit the operator made offline.
            const existing = window.localStorage.getItem(
              `stress-draft-${aziendaId}`,
            );
            const hasLocalEdits =
              existing &&
              Object.keys(JSON.parse(existing || "{}")).length > 0;
            if (!hasLocalEdits && Object.keys(merged).length > 0) {
              window.localStorage.setItem(
                `stress-draft-${aziendaId}`,
                JSON.stringify(merged),
              );
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
    return () => {
      cancelled = true;
    };
  }, [aziendaId, apiUrl]);

  // Rebuild the measures panel whenever the risk level changes. For each
  // band we: (1) seed with defaults, (2) fetch the per-client library for
  // that band and append every library entry tagged as personalizzata.
  useEffect(() => {
    if (result.livello === misureLivello) return;
    const livello = result.livello;
    const band = LIVELLO_TO_BAND[livello];
    setMisureLivello(livello);

    let cancelled = false;

    async function hydrate() {
      // Start with default scaffolded list.
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

  // Persist a measure row to the per-client library.
  // - If it already has libraryId + the text changed, PUT it.
  // - Else if the text is non-empty and differs from the original default
  //   (or the row had no originalText, i.e. was user-added), POST it.
  const saveMisura = useCallback(
    async (id: string) => {
      const row = misure.find((m) => m.id === id);
      if (!row) return;
      const trimmed = row.text.trim();
      if (!trimmed) return;
      // Skip if unchanged since last save.
      if (lastSavedTextRef.current.get(id) === row.text) return;
      // Skip if this is a default row that hasn't actually been edited.
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
      // If the row has a library id, delete it server-side first.
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

  // Feedback #20 (2026-05-18): ask gpt-5.4-mini for misure correttive
  // tailored to the live answers. Adds each suggested line to the
  // measures list as a personalized entry — the operator still reviews,
  // edits, and saves. We never auto-persist into misure_correttive.
  const suggestWithAI = useCallback(async () => {
    setAiLoading(true);
    try {
      const raw = window.localStorage.getItem(`stress-draft-${aziendaId}`);
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

      // Split the suggestion (one measure per line). Strip any leading
      // bullet/numbering the model might add despite the prompt.
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
  }, [apiUrl, aziendaId]);

  const finalize = useCallback(async () => {
    setFinalizing(true);
    setFinalizeMessage(null);
    try {
      const token = await getAuthToken();

      // Pull answers directly from localStorage (the checklist owns the state)
      const raw = window.localStorage.getItem(`stress-draft-${aziendaId}`);
      const answers: AnswersMap = raw ? JSON.parse(raw) : {};

      // Feedback #31: PUT to the upsert endpoint so the valutazione is
      // actually archived in the fascicolo. The endpoint runs the same
      // calculator server-side, persists raw answers + scores + livello,
      // and returns the computed result so we can show the operator the
      // totale + livello immediately.
      const res = await fetch(
        `${apiUrl}/api/v1/aziende/${aziendaId}/stress/valutazione`,
        {
          method: "PUT",
          headers: token
            ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
            : { "Content-Type": "application/json" },
          body: JSON.stringify({ answers }),
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
    } catch (err) {
      setFinalizeMessage(
        err instanceof Error
          ? `Errore conferma: ${err.message}`
          : "Errore conferma sconosciuto",
      );
    } finally {
      setFinalizing(false);
    }
  }, [apiUrl, aziendaId]);

  const pageSubtitle = useMemo(() => {
    if (loadError) return `Azienda ${aziendaId} (metadati non disponibili)`;
    if (azienda) return azienda.ragione_sociale ?? `Azienda ${aziendaId}`;
    return "Caricamento…";
  }, [azienda, aziendaId, loadError]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
            <Badge variant="secondary">Allegato Stress Lavoro-Correlato</Badge>
            <span>D.Lgs. 81/2008 · INAIL Metodo Indicatori Oggettivi</span>
          </div>
          <h1 className="mt-2 type-h1">
            Valutazione Stress Lavoro-Correlato
          </h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
      </div>

      {hydrated ? (
        <StressChecklist aziendaId={aziendaId} onResultChange={setResult} />
      ) : (
        <Card>
          <CardContent className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Caricamento valutazione precedente…
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
                    Analisi…
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
                      placeholder="Descrivi la misura correttiva…"
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
                          ✓ Salvato
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
              Le misure modificate sono contrassegnate come «Personalizzato» e
              salvate nella libreria del cliente.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Finalize */}
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div>
            <p className="text-sm font-medium">Conferma valutazione</p>
            <p className="text-xs text-muted-foreground">
              {allAnswered
                ? `Tutti i ${INDICATORS.length} indicatori compilati. La valutazione sarà archiviata nel fascicolo cliente.`
                : `Mancano ${result.unanswered.length} indicatori. Completa la checklist per confermare.`}
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
              {finalizing ? "Conferma in corso…" : "Conferma valutazione"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <p className="text-[11px] text-muted-foreground">
        Conteggio indicatori: {answeredCount} / {INDICATORS.length} · bozza
        salvata in locale (chiave: <code>stress-draft-{aziendaId}</code>)
      </p>
    </div>
  );
}
