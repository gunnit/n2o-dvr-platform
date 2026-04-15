"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  FileText,
  RefreshCw,
  Download,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  History,
  User as UserIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { VersionHistory } from "@/components/documents/version-history";
import type { Azienda, DocumentoGenerato } from "@/types";
import { apiCall, downloadFile } from "@/lib/api-client";
import { cn } from "@/lib/utils";

const documentTypes = [
  { key: "dvr_master", name: "DVR Master", pages: "~187", complexity: "Alta" },
  { key: "allegato_mmc", name: "Allegato MMC", pages: "~30", complexity: "Media" },
  { key: "allegato_vdt", name: "Allegato VDT", pages: "~25", complexity: "Media" },
  { key: "allegato_stress", name: "Allegato Stress", pages: "~20", complexity: "Media" },
  { key: "allegato_gestanti", name: "Allegato Gestanti", pages: "~10", complexity: "Bassa" },
  { key: "allegato_incendio", name: "Allegato Incendio", pages: "~15", complexity: "Media" },
  { key: "allegato_microclima", name: "Microclima Moderato", pages: "~15", complexity: "Alta" },
  { key: "allegato_microclima_severo", name: "Microclima Caldo Severo", pages: "~12", complexity: "Alta" },
  { key: "allegato_biologico_alimentare", name: "Biologico Alimentare", pages: "~25", complexity: "Media" },
  { key: "allegato_biologico_asilo", name: "Biologico Asilo", pages: "~20", complexity: "Media" },
  { key: "allegato_biologico_dentisti", name: "Biologico Dentisti", pages: "~30", complexity: "Alta" },
  { key: "pee_azienda", name: "PEE Aziendale", pages: "~25", complexity: "Media" },
  { key: "pee_comune", name: "PEE Edificio/Comune", pages: "~40", complexity: "Media" },
  { key: "haccp", name: "HACCP Manuale", pages: "~90", complexity: "Media" },
  { key: "haccp_forms", name: "HACCP Schede (16)", pages: "~25", complexity: "Bassa" },
  { key: "duvri", name: "DUVRI", pages: "~45", complexity: "Media" },
  { key: "pos", name: "POS", pages: "~110", complexity: "Alta" },
];

const complexityColors: Record<string, string> = {
  Alta: "bg-red-100 text-red-700",
  Media: "bg-yellow-100 text-yellow-700",
  Bassa: "bg-green-100 text-green-700",
};

const statusConfig: Record<string, { color: string; label: string; icon: typeof Clock }> = {
  pending: { color: "bg-gray-100 text-gray-700", label: "In attesa", icon: Clock },
  in_progress: { color: "bg-yellow-100 text-yellow-700", label: "In generazione", icon: Loader2 },
  generating: { color: "bg-yellow-100 text-yellow-700", label: "In generazione", icon: Loader2 },
  completed: { color: "bg-green-100 text-green-700", label: "Pronto", icon: CheckCircle2 },
  ready: { color: "bg-green-100 text-green-700", label: "Pronto", icon: CheckCircle2 },
  // US-2.8 AC3: a failed attempt is rolled back to "bozza" — partial
  // file discarded, record retained so the operator can retry without
  // starting from scratch. Amber rather than red because the record is
  // still usable (retry is available); red is reserved for non-recoverable
  // legacy "failed" rows that predate the rollback logic.
  bozza: { color: "bg-amber-100 text-amber-800", label: "Bozza", icon: AlertCircle },
  failed: { color: "bg-red-100 text-red-700", label: "Errore", icon: AlertCircle },
  error: { color: "bg-red-100 text-red-700", label: "Errore", icon: AlertCircle },
};

export default function DocumentsPage() {
  const [aziende, setAziende] = useState<Azienda[]>([]);
  const [selectedAziendaId, setSelectedAziendaId] = useState<string>("");
  const [documenti, setDocumenti] = useState<DocumentoGenerato[]>([]);
  const [loadingAziende, setLoadingAziende] = useState(true);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [generatingAll, setGeneratingAll] = useState(false);
  const [generatingTypes, setGeneratingTypes] = useState<Set<string>>(new Set());
  const [historyTipo, setHistoryTipo] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch aziende list
  useEffect(() => {
    apiCall<Azienda[]>("/api/v1/aziende")
      .then(setAziende)
      .catch(() => {})
      .finally(() => setLoadingAziende(false));
  }, []);

  // Fetch documents for selected azienda
  const fetchDocumenti = useCallback(async () => {
    if (!selectedAziendaId) {
      setDocumenti([]);
      return;
    }
    setLoadingDocs(true);
    try {
      const docs = await apiCall<DocumentoGenerato[]>(
        `/api/v1/aziende/${selectedAziendaId}/documents`
      );
      setDocumenti(docs);
    } catch {
      setDocumenti([]);
    } finally {
      setLoadingDocs(false);
    }
  }, [selectedAziendaId]);

  useEffect(() => {
    fetchDocumenti();
  }, [fetchDocumenti]);

  // Poll for status when documents are generating
  useEffect(() => {
    const hasGenerating = documenti.some(
      (d) => d.status === "pending" || d.status === "generating" || d.status === "in_progress"
    );

    if (hasGenerating && selectedAziendaId) {
      pollRef.current = setInterval(() => {
        apiCall<DocumentoGenerato[]>(
          `/api/v1/aziende/${selectedAziendaId}/documents`
        )
          .then(setDocumenti)
          .catch(() => {});
      }, 3000);
    }

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [documenti, selectedAziendaId]);

  function getDocStatus(typeKey: string): DocumentoGenerato | undefined {
    return documenti
      .filter((d) => d.tipo_documento === typeKey)
      .sort((a, b) => b.versione - a.versione)[0];
  }

  // US-4.1 AC2: PEE cards are blocked until the DVR Master has a successful
  // generation. We derive the flag from the latest DVR row's status.
  const DVR_DEPENDENT_TYPES = new Set(["pee_azienda", "pee_comune"]);
  const latestDvr = getDocStatus("dvr_master");
  const dvrReady =
    latestDvr?.status === "completed" || latestDvr?.status === "ready";

  const [generateError, setGenerateError] = useState<string | null>(null);

  async function handleGenerate(typeKey: string) {
    if (!selectedAziendaId) return;
    // Short-circuit on DVR-dependent types so we surface the Italian message
    // immediately without a round-trip. Backend guard is still authoritative.
    if (DVR_DEPENDENT_TYPES.has(typeKey) && !dvrReady) {
      setGenerateError("Genera prima il DVR Master");
      return;
    }
    setGenerateError(null);
    setGeneratingTypes((prev) => new Set(prev).add(typeKey));
    try {
      await apiCall(`/api/v1/aziende/${selectedAziendaId}/documents/generate`, {
        method: "POST",
        body: JSON.stringify({ tipo_documento: typeKey }),
      });
      await fetchDocumenti();
    } catch (err) {
      // Surface the backend Italian error (e.g. "Genera prima il DVR Master")
      // so the operator knows what to do next.
      setGenerateError(
        err instanceof Error ? err.message : "Generazione non riuscita",
      );
    } finally {
      setGeneratingTypes((prev) => {
        const next = new Set(prev);
        next.delete(typeKey);
        return next;
      });
    }
  }

  async function handleGenerateAll() {
    if (!selectedAziendaId) return;
    setGeneratingAll(true);
    try {
      await apiCall(`/api/v1/aziende/${selectedAziendaId}/documents/batch`, {
        method: "POST",
        body: JSON.stringify({
          tipi_documento: documentTypes.map((d) => d.key),
        }),
      });
      await fetchDocumenti();
    } catch {
      // silently handle
    } finally {
      setGeneratingAll(false);
    }
  }

  const selectedAzienda = aziende.find((a) => a.id === selectedAziendaId);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Documenti</h1>
          <p className="text-muted-foreground">
            Genera i documenti di sicurezza per le aziende clienti
          </p>
        </div>
        {selectedAziendaId && (
          <Button onClick={handleGenerateAll} disabled={generatingAll}>
            {generatingAll ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Genera Tutti
          </Button>
        )}
      </div>

      {/* Azienda Selector */}
      <Card>
        <CardContent className="pt-4">
          <div className="space-y-2">
            <Label htmlFor="azienda-select">Seleziona Azienda</Label>
            {loadingAziende ? (
              <p className="text-sm text-muted-foreground">Caricamento aziende...</p>
            ) : aziende.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Nessuna azienda registrata. Aggiungi un&apos;azienda per iniziare.
              </p>
            ) : (
              <select
                id="azienda-select"
                value={selectedAziendaId}
                onChange={(e) => setSelectedAziendaId(e.target.value)}
                className="h-8 w-full max-w-md rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <option value="">-- Seleziona un&apos;azienda --</option>
                {aziende.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.ragione_sociale}
                    {a.sede_operativa_citta ? ` - ${a.sede_operativa_citta}` : ""}
                  </option>
                ))}
              </select>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Document Grid */}
      {!selectedAziendaId ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FileText className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="text-muted-foreground">
              Seleziona un&apos;azienda per visualizzare e generare i documenti
            </p>
          </CardContent>
        </Card>
      ) : loadingDocs ? (
        <p className="text-muted-foreground">Caricamento documenti...</p>
      ) : (
        <>
          {selectedAzienda && (
            <p className="text-sm text-muted-foreground">
              Documenti per <span className="font-medium text-foreground">{selectedAzienda.ragione_sociale}</span>
            </p>
          )}
          {generateError && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {generateError}
              <button
                type="button"
                onClick={() => setGenerateError(null)}
                className="ml-2 underline"
              >
                Chiudi
              </button>
            </div>
          )}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {documentTypes.map((docType) => {
              const existing = getDocStatus(docType.key);
              const isGenerating = generatingTypes.has(docType.key);
              const status = existing?.status;
              const config = status ? statusConfig[status] : null;
              const versionCount = documenti.filter(
                (d) => d.tipo_documento === docType.key
              ).length;
              // US-4.1: visually mark PEE cards as blocked when the DVR
              // Master has not yet been generated. The generate button stays
              // clickable so the Italian error message can still surface; the
              // block itself is enforced by the backend.
              const blockedByDvr =
                DVR_DEPENDENT_TYPES.has(docType.key) && !dvrReady;

              return (
                <Card
                  key={docType.key}
                  className={cn(blockedByDvr && "opacity-75")}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <CardTitle className="text-sm">{docType.name}</CardTitle>
                      </div>
                      <Badge className={complexityColors[docType.complexity]}>
                        {docType.complexity}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <p className="text-xs text-muted-foreground">{docType.pages} pagine</p>
                    {blockedByDvr && (
                      <p className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                        Genera prima il DVR Master
                      </p>
                    )}
                    {existing && config && (
                      <div className="flex items-center gap-2">
                        <Badge
                          className={config.color}
                          // Surface the short Italian error line from the
                          // worker (US-2.8 AC3) via native tooltip rather
                          // than wiring a Popover — single-line content.
                          title={
                            status === "bozza" && existing.error_message
                              ? existing.error_message
                              : undefined
                          }
                        >
                          {(status === "generating" || status === "in_progress") && (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                          )}
                          {config.label}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          v{existing.versione} &middot;{" "}
                          {new Date(existing.created_at).toLocaleDateString("it-IT")}
                        </span>
                      </div>
                    )}
                    {existing?.generated_by_name && (
                      <p className="flex items-center gap-1 text-xs text-muted-foreground">
                        <UserIcon className="h-3 w-3" />
                        Generato da {existing.generated_by_name}
                      </p>
                    )}
                    {status === "bozza" && existing?.error_message && (
                      <p className="text-xs text-amber-700 dark:text-amber-400">
                        {existing.error_message}
                      </p>
                    )}
                  </CardContent>
                  <CardFooter className="gap-2">
                    <Button
                      size="sm"
                      variant={(existing?.status === "ready" || existing?.status === "completed") ? "outline" : "default"}
                      onClick={() => handleGenerate(docType.key)}
                      disabled={isGenerating || status === "generating" || status === "in_progress"}
                    >
                      {isGenerating || status === "generating" || status === "in_progress" ? (
                        <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                      ) : (
                        <RefreshCw className="mr-1.5 h-3 w-3" />
                      )}
                      {existing?.status === "ready" || existing?.status === "completed"
                        ? "Rigenera"
                        : existing?.status === "bozza"
                        ? "Riprova"
                        : "Genera"}
                    </Button>
                    {(existing?.status === "ready" || existing?.status === "completed") && existing.file_path && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={async () => {
                          try {
                            await downloadFile(`/api/v1/documenti/${existing.id}/download`);
                          } catch (e) {
                            alert((e as Error).message || "Download fallito");
                          }
                        }}
                      >
                        <Download className="mr-1.5 h-3 w-3" />
                        Scarica
                      </Button>
                    )}
                    {versionCount > 0 && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setHistoryTipo(docType.key)}
                        aria-label={`Storia versioni ${docType.name}`}
                      >
                        <History className="mr-1.5 h-3 w-3" />
                        Storia (v{versionCount})
                      </Button>
                    )}
                  </CardFooter>
                </Card>
              );
            })}
          </div>
        </>
      )}

      <VersionHistory
        open={historyTipo !== null}
        onOpenChange={(open) => {
          if (!open) setHistoryTipo(null);
        }}
        tipoDocumento={historyTipo ?? ""}
        tipoDocumentoLabel={
          (historyTipo && documentTypes.find((d) => d.key === historyTipo)?.name) ||
          ""
        }
        aziendaId={selectedAziendaId}
        aziendaLabel={selectedAzienda?.ragione_sociale ?? ""}
        versions={
          historyTipo
            ? documenti
                .filter((d) => d.tipo_documento === historyTipo)
                .sort((a, b) => b.versione - a.versione)
            : []
        }
        onRestored={fetchDocumenti}
      />
    </div>
  );
}
