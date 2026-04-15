"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  Check,
  Loader2,
  Pencil,
  Plus,
  Sparkles,
  ThumbsDown,
  Trash2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useApi } from "@/hooks/use-api";
import { AIBadge } from "./ai-badge";
import { AIContent } from "./ai-filter-context";

/**
 * AI improvement measures panel (US-2.6).
 *
 * Given a risk (valutazione_rischio), the user can:
 *   1. Pick from the per-client reusable measures library (AC2)
 *      — previously saved measures for the same categoria, surfaced on top
 *   2. Request 2-5 AI-suggested prevention/protection measures
 *   3. Accept / Modify / Reject each AI suggestion or type one from scratch
 *
 * Accepted / modified / manually-added measures are:
 *   - emitted via onSave(combinedText) so the parent can persist them to
 *     ValutazioneRischio.misure_prevenzione, and
 *   - auto-persisted to the per-client library keyed by categoria_rischio
 *     so they surface on future risks of the same category.
 */

type Priorita = "bassa" | "media" | "alta" | "urgente";
type TipoMisura =
  | "tecnica"
  | "organizzativa"
  | "dpi"
  | "formazione"
  | "sorveglianza_sanitaria";

interface MisuraSuggerita {
  titolo: string;
  descrizione: string;
  tipo: TipoMisura;
  priorita: Priorita;
  tempistica: string;
  riferimento_normativo: string | null;
}

type Provenance = "ai-accepted" | "ai-modified" | "manual" | "library";

interface WorkingMeasure extends MisuraSuggerita {
  id: string;
  provenance: Provenance;
  /** If present, this measure is already persisted in the library (don't duplicate). */
  libraryId?: string;
}

interface LibraryEntry extends MisuraSuggerita {
  id: string;
  azienda_id: string;
  categoria_rischio: string;
  provenance: "ai-accepted" | "ai-modified" | "manual";
  created_at: string;
  updated_at: string;
}

interface MeasuresPanelProps {
  aziendaId: string;
  rischioId: string;
  categoriaRischio: string;
  /** Current misure_prevenzione text, used to seed the text area on first load. */
  initialText?: string;
  onSave: (combinedText: string) => void | Promise<void>;
}

const priorityColors: Record<Priorita, string> = {
  bassa: "bg-slate-100 text-slate-700",
  media: "bg-amber-100 text-amber-800",
  alta: "bg-orange-100 text-orange-800",
  urgente: "bg-red-100 text-red-800",
};

const tipoLabels: Record<TipoMisura, string> = {
  tecnica: "Tecnica",
  organizzativa: "Organizzativa",
  dpi: "DPI",
  formazione: "Formazione",
  sorveglianza_sanitaria: "Sorv. sanitaria",
};

function measureToText(m: WorkingMeasure): string {
  const parts: string[] = [`- ${m.titolo}: ${m.descrizione}`];
  parts.push(
    `  [${tipoLabels[m.tipo]}, priorita ${m.priorita}, tempistica ${m.tempistica}${
      m.riferimento_normativo ? `, rif. ${m.riferimento_normativo}` : ""
    }]`
  );
  return parts.join("\n");
}

/** Maps our ai-accepted/ai-modified/manual UI provenance to library provenance. */
function libraryProvenanceFor(p: Provenance): "ai-accepted" | "ai-modified" | "manual" {
  if (p === "ai-accepted") return "ai-accepted";
  if (p === "ai-modified") return "ai-modified";
  return "manual";
}

export function MeasuresPanel({
  aziendaId,
  rischioId,
  categoriaRischio,
  initialText,
  onSave,
}: MeasuresPanelProps) {
  const { apiFetch } = useApi();
  const [suggestions, setSuggestions] = useState<MisuraSuggerita[]>([]);
  const [accepted, setAccepted] = useState<WorkingMeasure[]>([]);
  const [rejected, setRejected] = useState<Set<number>>(new Set());
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [library, setLibrary] = useState<LibraryEntry[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [libraryError, setLibraryError] = useState<string | null>(null);

  const libraryUrl = `/api/v1/aziende/${aziendaId}/rischi/misure-libreria?categoria_rischio=${encodeURIComponent(categoriaRischio)}`;

  const fetchLibrary = useCallback(async () => {
    if (!categoriaRischio) return;
    setLibraryLoading(true);
    setLibraryError(null);
    try {
      const res = await apiFetch<LibraryEntry[]>(libraryUrl, { method: "GET" });
      setLibrary(res);
    } catch (err) {
      setLibraryError(
        err instanceof Error ? err.message : "Errore nel caricamento della libreria"
      );
    } finally {
      setLibraryLoading(false);
    }
  }, [apiFetch, libraryUrl, categoriaRischio]);

  useEffect(() => {
    fetchLibrary();
  }, [fetchLibrary]);

  const persistToLibrary = useCallback(
    async (m: WorkingMeasure): Promise<string | null> => {
      // Skip if this is already a library entry — the UI surfaces it but
      // a second POST would create a duplicate row.
      if (m.libraryId || m.provenance === "library") return m.libraryId ?? null;
      try {
        const created = await apiFetch<LibraryEntry>(
          `/api/v1/aziende/${aziendaId}/rischi/misure-libreria`,
          {
            method: "POST",
            body: JSON.stringify({
              categoria_rischio: categoriaRischio,
              titolo: m.titolo,
              descrizione: m.descrizione,
              tipo: m.tipo,
              priorita: m.priorita,
              tempistica: m.tempistica,
              riferimento_normativo: m.riferimento_normativo,
              provenance: libraryProvenanceFor(m.provenance),
            }),
          }
        );
        // Refresh so new entry appears in the library panel next time the
        // page is revisited (and on the same risk after save).
        setLibrary((prev) => [...prev, created]);
        return created.id;
      } catch {
        // Non-fatal — the measure still gets saved to misure_prevenzione
        // via onSave; library persistence is a nice-to-have.
        return null;
      }
    },
    [apiFetch, aziendaId, categoriaRischio]
  );

  const fetchSuggestions = async () => {
    setError(null);
    setIsLoading(true);
    try {
      const res = await apiFetch<{ misure: MisuraSuggerita[] }>(
        `/api/v1/aziende/${aziendaId}/rischi/${rischioId}/suggerisci-misure`,
        { method: "POST" }
      );
      setSuggestions(res.misure);
      setRejected(new Set());
      setGeneratedAt(new Date().toISOString());
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Errore nella generazione"
      );
    } finally {
      setIsLoading(false);
    }
  };

  const acceptSuggestion = (idx: number) => {
    const s = suggestions[idx];
    if (!s) return;
    setAccepted((a) => [
      ...a,
      { ...s, id: crypto.randomUUID(), provenance: "ai-accepted" },
    ]);
    setRejected((r) => new Set(r).add(idx));
  };

  const rejectSuggestion = (idx: number) => {
    setRejected((r) => new Set(r).add(idx));
    // Fire-and-forget thumbs-down signal (US-2.6 AC3).
    // Don't await — the user rejection should feel instant; feedback is advisory.
    const suggestion = suggestions[idx];
    if (!suggestion) return;
    apiFetch("/api/v1/ai-feedback", {
      method: "POST",
      body: JSON.stringify({
        entity_type: "misura_suggerita",
        entity_id: `${rischioId}:${idx}`,
        signal: "thumbs_down",
        azienda_id: aziendaId,
        context: { rischioId, categoriaRischio, suggestion },
      }),
    }).catch(() => {
      // Feedback failures are non-blocking — users already moved on.
    });
  };

  const useLibraryEntry = (entry: LibraryEntry) => {
    setAccepted((a) => [
      ...a,
      {
        id: crypto.randomUUID(),
        libraryId: entry.id,
        titolo: entry.titolo,
        descrizione: entry.descrizione,
        tipo: entry.tipo,
        priorita: entry.priorita,
        tempistica: entry.tempistica,
        riferimento_normativo: entry.riferimento_normativo,
        provenance: "library",
      },
    ]);
  };

  const deleteLibraryEntry = async (entry: LibraryEntry) => {
    if (!confirm(`Rimuovere "${entry.titolo}" dalla libreria?`)) return;
    try {
      await apiFetch(
        `/api/v1/aziende/${aziendaId}/rischi/misure-libreria/${entry.id}`,
        { method: "DELETE" }
      );
      setLibrary((prev) => prev.filter((e) => e.id !== entry.id));
    } catch {
      // silent — user can retry
    }
  };

  const saveEdit = (idx: number, edits: Partial<MisuraSuggerita>) => {
    setAccepted((list) =>
      list.map((m, i) => {
        if (i !== idx) return m;
        // If the user edits a library-sourced measure, we treat it as a fresh
        // manual entry (AI-modified if it came from an AI suggestion) so it
        // will be re-saved to the library on next Save.
        const nextProvenance: Provenance =
          m.provenance === "ai-accepted" ? "ai-modified" : m.provenance === "library" ? "manual" : m.provenance;
        const next: WorkingMeasure = { ...m, ...edits, provenance: nextProvenance };
        if (m.provenance === "library") {
          // The edited version is semantically new; don't link back to the
          // original library row so it won't overwrite.
          delete next.libraryId;
        }
        return next;
      })
    );
    setEditingIdx(null);
  };

  const removeAccepted = (idx: number) => {
    setAccepted((list) => list.filter((_, i) => i !== idx));
  };

  const addManual = () => {
    setAccepted((a) => [
      ...a,
      {
        id: crypto.randomUUID(),
        titolo: "",
        descrizione: "",
        tipo: "tecnica",
        priorita: "media",
        tempistica: "",
        riferimento_normativo: null,
        provenance: "manual",
      },
    ]);
    setEditingIdx(accepted.length);
  };

  const handleSave = async () => {
    if (accepted.length === 0) return;
    setIsSaving(true);
    try {
      // 1. Persist to the per-client library so these measures resurface
      //    on future risks of the same categoria (US-2.6 AC2).
      await Promise.all(accepted.map((m) => persistToLibrary(m)));

      // 2. Emit combined text up to parent to store on the risk itself.
      const combined = accepted.map(measureToText).join("\n");
      const payload = initialText ? `${initialText.trim()}\n\n${combined}` : combined;
      await onSave(payload);
    } finally {
      setIsSaving(false);
    }
  };

  // Library entries that haven't already been added to the working list.
  const alreadyUsedLibraryIds = new Set(
    accepted.map((m) => m.libraryId).filter(Boolean) as string[]
  );
  const availableLibrary = library.filter(
    (e) => !alreadyUsedLibraryIds.has(e.id)
  );

  return (
    <div className="space-y-4 rounded-lg border border-input bg-muted/20 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <h4 className="text-sm font-medium">Misure di miglioramento</h4>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchSuggestions}
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              Analisi...
            </>
          ) : (
            <>
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              {suggestions.length > 0 ? "Rigenera" : "Suggerisci con AI"}
            </>
          )}
        </Button>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Per-client library — reusable measures previously saved for this categoria (AC2) */}
      {(availableLibrary.length > 0 || libraryLoading || libraryError) && (
        <div className="space-y-2">
          <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            <BookOpen className="h-3 w-3" />
            Libreria cliente ({categoriaRischio})
            {libraryLoading && <Loader2 className="h-3 w-3 animate-spin" />}
          </p>
          {libraryError && (
            <p className="text-xs text-destructive">{libraryError}</p>
          )}
          {availableLibrary.map((entry) => (
            <div
              key={entry.id}
              className="rounded-md border border-emerald-200 bg-emerald-50/50 p-3"
            >
              <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                <span className="text-sm font-medium">{entry.titolo}</span>
                <Badge
                  variant="secondary"
                  className={`${priorityColors[entry.priorita]} text-xs`}
                >
                  {entry.priorita}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {tipoLabels[entry.tipo]}
                </Badge>
                <Badge
                  variant="secondary"
                  className="bg-emerald-100 text-emerald-800 text-xs"
                >
                  Libreria
                </Badge>
              </div>
              <p className="mb-2 text-sm text-muted-foreground">
                {entry.descrizione}
              </p>
              <p className="mb-2 text-xs text-muted-foreground">
                Tempistica: {entry.tempistica || "n/d"}
                {entry.riferimento_normativo &&
                  ` · Rif. ${entry.riferimento_normativo}`}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => useLibraryEntry(entry)}
                >
                  <Check className="mr-1 h-3.5 w-3.5" />
                  Usa
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteLibraryEntry(entry)}
                  title="Rimuovi dalla libreria cliente"
                >
                  <Trash2 className="mr-1 h-3.5 w-3.5" />
                  Rimuovi
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* AI suggestions awaiting Accept / Reject */}
      {suggestions.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">
            Suggerimenti AI
          </p>
          {suggestions.map((s, idx) => {
            if (rejected.has(idx)) return null;
            return (
              <div
                key={idx}
                className="rounded-md border border-input bg-background p-3"
              >
                <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                  <span className="text-sm font-medium">{s.titolo}</span>
                  <Badge
                    variant="secondary"
                    className={`${priorityColors[s.priorita]} text-xs`}
                  >
                    {s.priorita}
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    {tipoLabels[s.tipo]}
                  </Badge>
                </div>
                <p className="mb-2 text-sm text-muted-foreground">
                  {s.descrizione}
                </p>
                <p className="mb-2 text-xs text-muted-foreground">
                  Tempistica: {s.tempistica}
                  {s.riferimento_normativo &&
                    ` · Rif. ${s.riferimento_normativo}`}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => acceptSuggestion(idx)}
                  >
                    <Check className="mr-1 h-3.5 w-3.5" />
                    Accetta
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => rejectSuggestion(idx)}
                    title="Rifiuta questa proposta e invia un segnale 'non utile' all'AI"
                  >
                    <ThumbsDown className="mr-1 h-3.5 w-3.5" />
                    Rifiuta
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Accepted / modified / manual — editable list */}
      {accepted.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">
            Misure selezionate ({accepted.length})
          </p>
          {accepted.map((m, idx) => {
            const isEditing = editingIdx === idx;
            const isAI = m.provenance === "ai-accepted" || m.provenance === "ai-modified";
            return (
              <AIContent
                key={m.id}
                isAI={isAI}
                className="rounded-md border border-input bg-background p-3"
              >
                {isEditing ? (
                  <EditForm
                    measure={m}
                    onSave={(edits) => saveEdit(idx, edits)}
                    onCancel={() => setEditingIdx(null)}
                  />
                ) : (
                  <>
                    <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                      <span className="text-sm font-medium">
                        {m.titolo || "(senza titolo)"}
                      </span>
                      <Badge
                        variant="secondary"
                        className={`${priorityColors[m.priorita]} text-xs`}
                      >
                        {m.priorita}
                      </Badge>
                      {m.provenance === "ai-accepted" && (
                        <AIBadge
                          provenance="ai"
                          label="AI - accettato"
                          timestamp={generatedAt}
                          size="xs"
                        />
                      )}
                      {m.provenance === "ai-modified" && (
                        <AIBadge
                          provenance="edited"
                          label="AI - modificato"
                          timestamp={generatedAt}
                          size="xs"
                        />
                      )}
                      {m.provenance === "manual" && (
                        <AIBadge provenance="manual" size="xs" />
                      )}
                      {m.provenance === "library" && (
                        <Badge
                          variant="secondary"
                          className="bg-emerald-100 text-emerald-800 text-xs"
                        >
                          <BookOpen className="mr-1 h-2.5 w-2.5" />
                          Libreria
                        </Badge>
                      )}
                    </div>
                    <p className="mb-2 text-sm text-muted-foreground">
                      {m.descrizione || "(nessuna descrizione)"}
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setEditingIdx(idx)}
                      >
                        <Pencil className="mr-1 h-3.5 w-3.5" />
                        Modifica
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeAccepted(idx)}
                      >
                        <X className="mr-1 h-3.5 w-3.5" />
                        Rimuovi
                      </Button>
                    </div>
                  </>
                )}
              </AIContent>
            );
          })}
        </div>
      )}

      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={addManual}>
          <Plus className="mr-1 h-3.5 w-3.5" />
          Aggiungi misura personalizzata
        </Button>
        {accepted.length > 0 && (
          <Button
            size="sm"
            onClick={handleSave}
            disabled={isSaving}
            className="ml-auto"
          >
            {isSaving ? (
              <>
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                Salvataggio...
              </>
            ) : (
              "Salva misure"
            )}
          </Button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function EditForm({
  measure,
  onSave,
  onCancel,
}: {
  measure: WorkingMeasure;
  onSave: (edits: Partial<MisuraSuggerita>) => void;
  onCancel: () => void;
}) {
  const [titolo, setTitolo] = useState(measure.titolo);
  const [descrizione, setDescrizione] = useState(measure.descrizione);
  const [priorita, setPriorita] = useState<Priorita>(measure.priorita);
  const [tipo, setTipo] = useState<TipoMisura>(measure.tipo);
  const [tempistica, setTempistica] = useState(measure.tempistica);
  const [rif, setRif] = useState(measure.riferimento_normativo ?? "");

  return (
    <div className="space-y-2">
      <input
        value={titolo}
        onChange={(e) => setTitolo(e.target.value)}
        placeholder="Titolo"
        className="h-8 w-full rounded-md border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
      />
      <textarea
        value={descrizione}
        onChange={(e) => setDescrizione(e.target.value)}
        placeholder="Descrizione operativa"
        rows={3}
        className="w-full rounded-md border border-input bg-transparent px-2 py-1.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
      />
      <div className="grid grid-cols-2 gap-2">
        <select
          value={priorita}
          onChange={(e) => setPriorita(e.target.value as Priorita)}
          className="h-8 rounded-md border border-input bg-transparent px-2 text-sm"
        >
          <option value="bassa">Priorita bassa</option>
          <option value="media">Priorita media</option>
          <option value="alta">Priorita alta</option>
          <option value="urgente">Priorita urgente</option>
        </select>
        <select
          value={tipo}
          onChange={(e) => setTipo(e.target.value as TipoMisura)}
          className="h-8 rounded-md border border-input bg-transparent px-2 text-sm"
        >
          <option value="tecnica">Tecnica</option>
          <option value="organizzativa">Organizzativa</option>
          <option value="dpi">DPI</option>
          <option value="formazione">Formazione</option>
          <option value="sorveglianza_sanitaria">Sorv. sanitaria</option>
        </select>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <input
          value={tempistica}
          onChange={(e) => setTempistica(e.target.value)}
          placeholder="Tempistica"
          className="h-8 rounded-md border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        />
        <input
          value={rif}
          onChange={(e) => setRif(e.target.value)}
          placeholder="Rif. normativo"
          className="h-8 rounded-md border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        />
      </div>
      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={() =>
            onSave({
              titolo,
              descrizione,
              priorita,
              tipo,
              tempistica,
              riferimento_normativo: rif || null,
            })
          }
        >
          <Check className="mr-1 h-3.5 w-3.5" />
          Salva
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>
          Annulla
        </Button>
      </div>
    </div>
  );
}
