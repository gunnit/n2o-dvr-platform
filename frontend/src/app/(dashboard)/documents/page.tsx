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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  Alta: "bg-[rgba(186,26,26,0.1)] text-[#ba1a1a] border border-[rgba(186,26,26,0.3)]",
  Media:
    "bg-[rgba(245,158,11,0.12)] text-[#9b6829] border border-[rgba(245,158,11,0.3)]",
  Bassa:
    "bg-[rgba(21,190,83,0.2)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
};

const statusConfig: Record<string, { color: string; label: string; icon: typeof Clock }> = {
  pending: {
    color: "bg-[#f6f9fc] text-[#273951] border border-[#e5edf5]",
    label: "In attesa",
    icon: Clock,
  },
  in_progress: {
    color:
      "bg-[rgba(245,158,11,0.12)] text-[#9b6829] border border-[rgba(245,158,11,0.3)]",
    label: "In generazione",
    icon: Loader2,
  },
  generating: {
    color:
      "bg-[rgba(245,158,11,0.12)] text-[#9b6829] border border-[rgba(245,158,11,0.3)]",
    label: "In generazione",
    icon: Loader2,
  },
  completed: {
    color:
      "bg-[rgba(21,190,83,0.2)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
    label: "Pronto",
    icon: CheckCircle2,
  },
  ready: {
    color:
      "bg-[rgba(21,190,83,0.2)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
    label: "Pronto",
    icon: CheckCircle2,
  },
  // US-2.8 AC3: a failed attempt is rolled back to "bozza" — partial
  // file discarded, record retained so the operator can retry without
  // starting from scratch. Amber rather than red because the record is
  // still usable (retry is available); red is reserved for non-recoverable
  // legacy "failed" rows that predate the rollback logic.
  bozza: {
    color:
      "bg-[rgba(245,158,11,0.12)] text-[#9b6829] border border-[rgba(245,158,11,0.3)]",
    label: "Bozza",
    icon: AlertCircle,
  },
  failed: {
    color:
      "bg-[rgba(186,26,26,0.1)] text-[#ba1a1a] border border-[rgba(186,26,26,0.3)]",
    label: "Errore",
    icon: AlertCircle,
  },
  error: {
    color:
      "bg-[rgba(186,26,26,0.1)] text-[#ba1a1a] border border-[rgba(186,26,26,0.3)]",
    label: "Errore",
    icon: AlertCircle,
  },
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

  // US-4.4: HACCP forms subset selection dialog. Renders once when the
  // operator clicks "Genera" on the haccp_forms card. Default = all 16
  // selected so "OK" with no edits matches the legacy behaviour.
  const HACCP_FORM_CODES: { code: string; title: string }[] = [
    { code: "SA-01", title: "Pulizia e sanificazione" },
    { code: "SA-02", title: "Controllo temperature frigoriferi" },
    { code: "SA-03", title: "Controllo temperature congelatori" },
    { code: "SA-04", title: "Controllo cottura alimenti" },
    { code: "SA-05", title: "Controllo scongelamento" },
    { code: "SA-06", title: "Controllo ricevimento merci" },
    { code: "SA-07", title: "Conservazione e stoccaggio" },
    { code: "SA-08", title: "Controllo derattizzazione e disinfestazione" },
    { code: "SA-09", title: "Manutenzione attrezzature e impianti" },
    { code: "SA-10", title: "Acqua potabile" },
    { code: "SA-11", title: "Formazione del personale" },
    { code: "SA-12", title: "Stato di salute degli operatori" },
    { code: "SA-13", title: "Tracciabilità e rintracciabilità" },
    { code: "SA-14", title: "Gestione non conformità" },
    { code: "SA-15", title: "Allergeni" },
    { code: "SA-16", title: "Riesame del piano HACCP" },
  ];
  const [haccpDialogOpen, setHaccpDialogOpen] = useState(false);
  const [haccpSelected, setHaccpSelected] = useState<Set<string>>(
    new Set(HACCP_FORM_CODES.map((f) => f.code)),
  );

  async function postGenerate(typeKey: string, options?: Record<string, unknown>) {
    setGenerateError(null);
    setGeneratingTypes((prev) => new Set(prev).add(typeKey));
    try {
      await apiCall(`/api/v1/aziende/${selectedAziendaId}/documents/generate`, {
        method: "POST",
        body: JSON.stringify({
          tipo_documento: typeKey,
          ...(options ? { options } : {}),
        }),
      });
      await fetchDocumenti();
    } catch (err) {
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

  async function handleGenerate(typeKey: string) {
    if (!selectedAziendaId) return;
    // Short-circuit on DVR-dependent types so we surface the Italian message
    // immediately without a round-trip. Backend guard is still authoritative.
    if (DVR_DEPENDENT_TYPES.has(typeKey) && !dvrReady) {
      setGenerateError("Genera prima il DVR Master");
      return;
    }
    // US-4.4: open the subset dialog instead of firing immediately.
    if (typeKey === "haccp_forms") {
      // Default to all selected each time the dialog opens so the operator
      // never starts in a "nothing selected" state by accident.
      setHaccpSelected(new Set(HACCP_FORM_CODES.map((f) => f.code)));
      setHaccpDialogOpen(true);
      return;
    }
    await postGenerate(typeKey);
  }

  function toggleHaccpForm(code: string) {
    setHaccpSelected((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  async function confirmHaccpGenerate() {
    const codes = HACCP_FORM_CODES
      .map((f) => f.code)
      .filter((c) => haccpSelected.has(c));
    setHaccpDialogOpen(false);
    if (codes.length === 0) {
      setGenerateError("Seleziona almeno una scheda da generare");
      return;
    }
    await postGenerate("haccp_forms", { selected_codes: codes });
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
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="type-h1">Documenti</h1>
          <p className="type-body mt-2">
            Genera i documenti di sicurezza per le aziende clienti
          </p>
        </div>
        {selectedAziendaId && (
          <button
            type="button"
            onClick={handleGenerateAll}
            disabled={generatingAll}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {generatingAll ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" strokeWidth={2.5} />
            )}
            Genera Tutti
          </button>
        )}
      </div>

      {/* Azienda Selector */}
      <div className="rounded-md border border-[#e5edf5] bg-white p-6 shadow-stripe-ambient">
        <div className="space-y-2">
          <Label htmlFor="azienda-select">Seleziona Azienda</Label>
          {loadingAziende ? (
            <p className="text-sm text-[#64748d]">Caricamento aziende...</p>
          ) : aziende.length === 0 ? (
            <p className="text-sm text-[#64748d]">
              Nessuna azienda registrata. Aggiungi un&apos;azienda per iniziare.
            </p>
          ) : (
            <select
              id="azienda-select"
              value={selectedAziendaId}
              onChange={(e) => setSelectedAziendaId(e.target.value)}
              className="w-full max-w-md rounded-xl border-none bg-surface-low px-4 py-3 text-sm outline-none transition-all focus:ring-2 focus:ring-primary-container"
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
      </div>

      {/* Document Grid */}
      {!selectedAziendaId ? (
        <div className="flex flex-col items-center justify-center rounded-xl bg-white py-12 ambient-shadow">
          <FileText className="mb-3 h-10 w-10 text-[#64748d] opacity-40" />
          <p className="text-[#64748d]">
            Seleziona un&apos;azienda per visualizzare e generare i documenti
          </p>
        </div>
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

      {/* US-4.4: HACCP forms subset selection. Defaults to all 16 + index. */}
      <Dialog open={haccpDialogOpen} onOpenChange={setHaccpDialogOpen}>
        <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Schede HACCP da generare</DialogTitle>
            <DialogDescription>
              Seleziona le schede da includere nel pacchetto .zip. Tutte le
              schede sono pre-selezionate; deseleziona quelle non necessarie.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {haccpSelected.size} di {HACCP_FORM_CODES.length} selezionate
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    setHaccpSelected(
                      new Set(HACCP_FORM_CODES.map((f) => f.code)),
                    )
                  }
                >
                  Seleziona tutte
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setHaccpSelected(new Set())}
                >
                  Deseleziona tutte
                </Button>
              </div>
            </div>
            <div className="grid gap-1.5 sm:grid-cols-2">
              {HACCP_FORM_CODES.map((f) => {
                const checked = haccpSelected.has(f.code);
                return (
                  <label
                    key={f.code}
                    className="flex items-start gap-2 rounded-md border border-input p-2 text-xs transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleHaccpForm(f.code)}
                      className="mt-0.5 accent-primary"
                    />
                    <span>
                      <span className="font-mono font-semibold">{f.code}</span>{" "}
                      <span className="text-muted-foreground">— {f.title}</span>
                    </span>
                  </label>
                );
              })}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setHaccpDialogOpen(false)}>
              Annulla
            </Button>
            <Button
              onClick={confirmHaccpGenerate}
              disabled={haccpSelected.size === 0}
            >
              Genera ({haccpSelected.size})
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
