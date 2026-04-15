"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileUp,
  Loader2,
  RotateCw,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { AIBadge } from "./ai-badge";
import { AIContent } from "./ai-filter-context";
import { DescriptionHistory } from "./description-history";

/**
 * AI-generated company description editor (US-2.1).
 *
 * Users can click "Genera con AI" to produce an Italian DVR Part I
 * description, then review/edit it in place. When the user edits, the
 * "AI" badge switches to "Modificato dall'utente" to preserve provenance.
 * The parent page is responsible for persisting the final text via the
 * existing PUT /aziende/{id} endpoint.
 *
 * AC1 also covers an optional visura camerale PDF upload — when present
 * its (PII-redacted) extracted snippet is added to the AI prompt. AC2
 * renders the per-azienda revision history below the editor with an
 * inline "Ripristina" action that snapshots a fresh manual revision.
 */

type Provenance = "none" | "ai" | "edited";

interface DescriptionEditorProps {
  aziendaId: string;
  value: string;
  onChange: (value: string, provenance: Provenance) => void;
  initialProvenance?: Provenance;
  /** Timestamp of last AI generation, surfaced in the badge tooltip. */
  generatedAt?: string | Date | null;
  /** Non-null ISO timestamp from `azienda.visura_uploaded_at` if a visura
   *  PDF is already on file. Renders an inline "visura caricata" hint. */
  visuraUploadedAt?: string | null;
}

export function DescriptionEditor({
  aziendaId,
  value,
  onChange,
  initialProvenance = "none",
  generatedAt = null,
  visuraUploadedAt = null,
}: DescriptionEditorProps) {
  const { apiFetch } = useApi();
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provenance, setProvenance] = useState<Provenance>(initialProvenance);
  const [lastGeneratedAt, setLastGeneratedAt] = useState<string | Date | null>(generatedAt);
  const [historyKey, setHistoryKey] = useState(0);
  const [visuraAt, setVisuraAt] = useState<string | null>(visuraUploadedAt);
  const [isUploadingVisura, setIsUploadingVisura] = useState(false);
  const [visuraNotice, setVisuraNotice] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setProvenance(initialProvenance);
  }, [initialProvenance]);

  useEffect(() => {
    setLastGeneratedAt(generatedAt);
  }, [generatedAt]);

  useEffect(() => {
    setVisuraAt(visuraUploadedAt);
  }, [visuraUploadedAt]);

  const bumpHistory = () => setHistoryKey((k) => k + 1);

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
      bumpHistory();
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

  const handleVisuraSelected = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    // Reset the input so re-uploading the same filename re-fires onChange.
    event.target.value = "";
    if (!file) return;
    setError(null);
    setVisuraNotice(null);
    setIsUploadingVisura(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      // useApi detects FormData and skips the JSON Content-Type so the
      // browser can set the multipart boundary itself.
      const res = await apiFetch<{
        visura_uploaded_at: string;
        extracted_chars: number;
        pages: number;
      }>(`/api/v1/aziende/${aziendaId}/visura`, {
        method: "POST",
        body: formData,
      });
      setVisuraAt(res.visura_uploaded_at);
      setVisuraNotice(
        `Visura caricata (${res.pages} pag., ${res.extracted_chars} caratteri estratti). ` +
          `Clicca \"Genera con AI\" per usare il contesto.`
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Caricamento visura fallito."
      );
    } finally {
      setIsUploadingVisura(false);
    }
  };

  const handleRestoreFromHistory = (descrizione: string) => {
    onChange(descrizione, "edited");
    setProvenance("edited");
    setLastGeneratedAt(new Date().toISOString());
    bumpHistory();
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
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="sr-only"
            onChange={handleVisuraSelected}
          />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploadingVisura || isGenerating}
            title={
              visuraAt
                ? "Sostituisci la visura camerale gia' caricata"
                : "Carica una visura camerale per arricchire il prompt AI"
            }
          >
            {isUploadingVisura ? (
              <>
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                Caricamento visura...
              </>
            ) : (
              <>
                <FileUp className="mr-1.5 h-3.5 w-3.5" />
                {visuraAt ? "Sostituisci visura" : "Carica visura"}
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleGenerate}
            disabled={isGenerating || isUploadingVisura}
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
      </div>
      {visuraAt && !visuraNotice && (
        <p className="flex items-center gap-1.5 text-xs text-emerald-700">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Visura camerale caricata il{" "}
          {new Date(visuraAt).toLocaleString("it-IT", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
          . Verra&apos; usata come contesto al prossimo &quot;Genera con AI&quot;.
        </p>
      )}
      {visuraNotice && (
        <p className="flex items-start gap-1.5 text-xs text-emerald-700">
          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
          <span>{visuraNotice}</span>
        </p>
      )}
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
        ambienti, ruoli e (se presente) sull&apos;estratto della visura
        camerale con CF, email e telefoni redatti — nessun dato personale viene
        inviato all&apos;AI.
      </p>
      <DescriptionHistory
        aziendaId={aziendaId}
        refreshKey={historyKey}
        onRestore={handleRestoreFromHistory}
      />
    </AIContent>
  );
}
