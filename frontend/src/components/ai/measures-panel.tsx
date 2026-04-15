"use client";

import { useState } from "react";
import {
  AlertCircle,
  Check,
  Loader2,
  Pencil,
  Plus,
  Sparkles,
  ThumbsDown,
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
 * Given a risk (valutazione_rischio), the user can request 2-5 AI-suggested
 * prevention/protection measures and Accept / Modify / Reject each one. The
 * accepted + modified + manually-added measures are emitted via
 * onAccept(combinedText) so the parent can persist them to
 * ValutazioneRischio.misure_prevenzione.
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

type Provenance = "ai-accepted" | "ai-modified" | "manual";

interface WorkingMeasure extends MisuraSuggerita {
  id: string;
  provenance: Provenance;
}

interface MeasuresPanelProps {
  aziendaId: string;
  rischioId: string;
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

export function MeasuresPanel({
  aziendaId,
  rischioId,
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
        context: { rischioId, suggestion },
      }),
    }).catch(() => {
      // Feedback failures are non-blocking — users already moved on.
    });
  };

  const saveEdit = (idx: number, edits: Partial<MisuraSuggerita>) => {
    setAccepted((list) =>
      list.map((m, i) =>
        i === idx ? { ...m, ...edits, provenance: "ai-modified" } : m
      )
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
      const combined = accepted.map(measureToText).join("\n");
      const payload = initialText ? `${initialText.trim()}\n\n${combined}` : combined;
      await onSave(payload);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-4 rounded-lg border border-input bg-muted/20 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <h4 className="text-sm font-medium">Misure di miglioramento (AI)</h4>
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
              {suggestions.length > 0 ? "Rigenera" : "Suggerisci misure"}
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
