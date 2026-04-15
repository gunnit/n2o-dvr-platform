"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Loader2, RotateCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { AIBadge } from "./ai-badge";
import { AIContent } from "./ai-filter-context";

/**
 * AI-generated company description editor (US-2.1).
 *
 * Users can click "Genera con AI" to produce an Italian DVR Part I
 * description, then review/edit it in place. When the user edits, the
 * "AI" badge switches to "Modificato dall'utente" to preserve provenance.
 * The parent page is responsible for persisting the final text via the
 * existing PUT /aziende/{id} endpoint.
 */

type Provenance = "none" | "ai" | "edited";

interface DescriptionEditorProps {
  aziendaId: string;
  value: string;
  onChange: (value: string, provenance: Provenance) => void;
  initialProvenance?: Provenance;
  /** Timestamp of last AI generation, surfaced in the badge tooltip. */
  generatedAt?: string | Date | null;
}

export function DescriptionEditor({
  aziendaId,
  value,
  onChange,
  initialProvenance = "none",
  generatedAt = null,
}: DescriptionEditorProps) {
  const { apiFetch } = useApi();
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provenance, setProvenance] = useState<Provenance>(initialProvenance);
  const [lastGeneratedAt, setLastGeneratedAt] = useState<string | Date | null>(generatedAt);

  useEffect(() => {
    setProvenance(initialProvenance);
  }, [initialProvenance]);

  useEffect(() => {
    setLastGeneratedAt(generatedAt);
  }, [generatedAt]);

  const handleGenerate = async () => {
    setError(null);
    setIsGenerating(true);
    try {
      const res = await apiFetch<{ description: string }>(
        `/api/v1/aziende/${aziendaId}/genera-descrizione`,
        { method: "POST" }
      );
      onChange(res.description, "ai");
      setProvenance("ai");
      setLastGeneratedAt(new Date().toISOString());
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Generazione fallita. Riprova o inserisci manualmente."
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleManualEdit = (text: string) => {
    onChange(text, provenance === "ai" ? "edited" : provenance);
    if (provenance === "ai") setProvenance("edited");
  };

  return (
    <AIContent isAI={provenance === "ai"} className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-medium">Descrizione attivita&apos;</h4>
          {provenance === "ai" && <AIBadge provenance="ai" timestamp={lastGeneratedAt} />}
          {provenance === "edited" && (
            <AIBadge provenance="edited" timestamp={lastGeneratedAt} />
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleGenerate}
          disabled={isGenerating}
        >
          {isGenerating ? (
            <>
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              Generazione...
            </>
          ) : (
            <>
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              {value ? "Rigenera con AI" : "Genera con AI"}
            </>
          )}
        </Button>
      </div>
      <textarea
        value={value}
        onChange={(e) => handleManualEdit(e.target.value)}
        placeholder="Clicca 'Genera con AI' per produrre automaticamente una descrizione basata sui dati del sopralluogo, oppure scrivi qui."
        rows={10}
        className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm leading-relaxed transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50"
        disabled={isGenerating}
      />
      {error && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span className="flex-1">{error}</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleGenerate}
            disabled={isGenerating}
            className="h-7 px-2 text-destructive hover:text-destructive"
          >
            <RotateCw className="mr-1 h-3 w-3" />
            Riprova
          </Button>
        </div>
      )}
      <p className="text-xs text-muted-foreground">
        La descrizione generata e&apos; basata solo sui dati anagrafici, ATECO,
        ambienti e ruoli — nessun dato personale viene inviato all&apos;AI.
      </p>
    </AIContent>
  );
}
