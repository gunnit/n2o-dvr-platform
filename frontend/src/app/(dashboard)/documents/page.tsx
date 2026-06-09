"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { toast } from "sonner";
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
  Pencil,
  CloudDownload,
  Trash2,
  ShieldAlert,
  Paperclip,
  Siren,
  Utensils,
  Handshake,
  Construction,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Monogram, type AccentKey } from "@/components/cards/Monogram";
import { formatRelative } from "@/lib/ui/relative-time";
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

type DocCategory = "dvr" | "allegati" | "emergenza" | "haccp" | "contratti";

type DocType = {
  key: string;
  name: string;
  pages: string;
  complexity: "Bassa" | "Media" | "Alta";
  category: DocCategory;
  icon: LucideIcon;
};

const CATEGORY_META: Record<DocCategory, { label: string; accent: AccentKey; rail: string }> = {
  dvr: { label: "Documento principale", accent: "navy", rail: "bg-[#003d74]" },
  allegati: { label: "Allegati DVR", accent: "sky", rail: "bg-[#0ea5e9]" },
  emergenza: { label: "Piani di emergenza", accent: "amber", rail: "bg-[#d97706]" },
  haccp: { label: "HACCP — alimentare", accent: "emerald", rail: "bg-[#059669]" },
  contratti: { label: "Appalti e cantieri", accent: "violet", rail: "bg-[#7c3aed]" },
};

const documentTypes: DocType[] = [
  { key: "dvr_master", name: "DVR Master", pages: "~187", complexity: "Alta", category: "dvr", icon: ShieldAlert },
  { key: "allegato_mmc", name: "Allegato MMC", pages: "~30", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_vdt", name: "Allegato VDT", pages: "~25", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_stress", name: "Allegato Stress", pages: "~20", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_gestanti", name: "Allegato Gestanti", pages: "~10", complexity: "Bassa", category: "allegati", icon: Paperclip },
  { key: "allegato_incendio", name: "Allegato Incendio", pages: "~15", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_microclima", name: "Microclima Moderato", pages: "~15", complexity: "Alta", category: "allegati", icon: Paperclip },
  { key: "allegato_microclima_severo", name: "Microclima Caldo Severo", pages: "~12", complexity: "Alta", category: "allegati", icon: Paperclip },
  { key: "allegato_biologico_alimentare", name: "Biologico Alimentare", pages: "~25", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_biologico_asilo", name: "Biologico Asilo", pages: "~20", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_biologico_dentisti", name: "Biologico Dentisti", pages: "~30", complexity: "Alta", category: "allegati", icon: Paperclip },
  { key: "pee_azienda", name: "PEE Aziendale", pages: "~25", complexity: "Media", category: "emergenza", icon: Siren },
  { key: "pee_comune", name: "PEE Edificio/Comune", pages: "~40", complexity: "Media", category: "emergenza", icon: Siren },
  { key: "haccp", name: "HACCP Manuale", pages: "~90", complexity: "Media", category: "haccp", icon: Utensils },
  { key: "haccp_forms", name: "HACCP Schede (16)", pages: "~25", complexity: "Bassa", category: "haccp", icon: Utensils },
  { key: "duvri", name: "DUVRI", pages: "~45", complexity: "Media", category: "contratti", icon: Handshake },
  { key: "pos", name: "POS", pages: "~110", complexity: "Alta", category: "contratti", icon: Construction },
];

const CATEGORY_ORDER: DocCategory[] = ["dvr", "allegati", "emergenza", "haccp", "contratti"];

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
  // Per-document pending states for the Google Docs round-trip flow
  // (keyed by documento_generato.id). `openingGdoc` = creating/opening the
  // editable Doc; `syncingGdoc` = pulling the edited version back;
  // `discardingGdoc` = deleting the Doc without syncing.
  const [openingGdoc, setOpeningGdoc] = useState<Set<string>>(new Set());
  const [syncingGdoc, setSyncingGdoc] = useState<Set<string>>(new Set());
  const [discardingGdoc, setDiscardingGdoc] = useState<Set<string>>(new Set());
  // Confirm dialog for "Scarta modifiche" — stores the doc whose edits
  // will be discarded, cleared on confirm/cancel.
  const [discardTarget, setDiscardTarget] = useState<DocumentoGenerato | null>(null);
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

  // Open a DVR document in Google Docs for in-browser editing. First call
  // creates the Google Doc (DOCX -> GDoc conversion ~2-5s); subsequent calls
  // return the cached edit URL immediately. Retries once on network failure
  // since Render's API service can return a transient 502 on cold-start
  // right after a redeploy.
  async function handleOpenInGoogleDocs(doc: DocumentoGenerato) {
    setOpeningGdoc((prev) => new Set(prev).add(doc.id));
    const isFirstOpen = !doc.gdoc_file_id;
    const convertingToast = isFirstOpen
      ? toast.loading("Conversione in Google Docs in corso...")
      : null;

    const openOnce = () =>
      apiCall<{ gdoc_file_id: string; edit_url: string }>(
        `/api/v1/documenti/${doc.id}/open-for-editing`,
        { method: "POST" },
      );

    try {
      let result: { gdoc_file_id: string; edit_url: string };
      try {
        result = await openOnce();
      } catch (first) {
        // Retry once after 2s for transient network / cold-start errors
        // (502/504 preflight). Surface anything that fails twice.
        const msg = first instanceof Error ? first.message : "";
        const looksTransient = /fetch|502|503|504|network/i.test(msg);
        if (!looksTransient) throw first;
        await new Promise((r) => setTimeout(r, 2000));
        result = await openOnce();
      }
      window.open(result.edit_url, "_blank", "noopener,noreferrer");
      if (convertingToast) toast.dismiss(convertingToast);
      if (isFirstOpen) toast.success("Documento aperto in Google Docs");
      await fetchDocumenti();
    } catch (err) {
      if (convertingToast) toast.dismiss(convertingToast);
      toast.error(
        err instanceof Error
          ? err.message
          : "Impossibile aprire il documento in Google Docs",
      );
    } finally {
      setOpeningGdoc((prev) => {
        const next = new Set(prev);
        next.delete(doc.id);
        return next;
      });
    }
  }

  // Pull the latest Google Doc content back into the app as a new version.
  // Backend inserts a new DocumentoGenerato row with incremented `versione`
  // and `options.edited_in_gdocs = true`. Backend rejects with 409 when no
  // edits are detected in the Google Doc — we surface the Italian message
  // from the server as a toast instead of a generic error.
  async function handleSyncFromGoogleDocs(doc: DocumentoGenerato) {
    setSyncingGdoc((prev) => new Set(prev).add(doc.id));
    const syncingToast = toast.loading("Sincronizzazione in corso...");
    try {
      const synced = await apiCall<DocumentoGenerato>(
        `/api/v1/documenti/${doc.id}/sync-from-gdoc`,
        { method: "POST" },
      );
      toast.dismiss(syncingToast);
      toast.success(`Nuova versione v${synced.versione} creata`);
      await fetchDocumenti();
    } catch (err) {
      toast.dismiss(syncingToast);
      toast.error(
        err instanceof Error
          ? err.message
          : "Sincronizzazione da Google Docs non riuscita",
      );
    } finally {
      setSyncingGdoc((prev) => {
        const next = new Set(prev);
        next.delete(doc.id);
        return next;
      });
    }
  }

  // Delete the editable Google Doc without importing its content. Used when
  // the user decides the in-browser edits aren't worth keeping — backend
  // removes the Drive file and clears gdoc_file_id so the sync/discard
  // buttons disappear.
  async function handleDiscardGdocEdits(doc: DocumentoGenerato) {
    setDiscardingGdoc((prev) => new Set(prev).add(doc.id));
    try {
      await apiCall<DocumentoGenerato>(`/api/v1/documenti/${doc.id}/gdoc`, {
        method: "DELETE",
      });
      toast.success("Modifiche in Google Docs scartate");
      await fetchDocumenti();
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Impossibile scartare le modifiche",
      );
    } finally {
      setDiscardingGdoc((prev) => {
        const next = new Set(prev);
        next.delete(doc.id);
        return next;
      });
      setDiscardTarget(null);
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
              {aziende.map((a) => {
                // #73 — show the full ragione sociale plus the sede (street +
                // city), preferring the sede operativa and falling back to the
                // sede legale, so two companies with the same name stay
                // distinguishable in the picker.
                const sede =
                  [a.sede_operativa_via, a.sede_operativa_citta]
                    .filter(Boolean)
                    .join(", ") ||
                  [a.sede_legale_via, a.sede_legale_citta]
                    .filter(Boolean)
                    .join(", ");
                return (
                  <option key={a.id} value={a.id}>
                    {a.ragione_sociale}
                    {sede ? ` — ${sede}` : ""}
                  </option>
                );
              })}
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
          <div className="space-y-8">
          {CATEGORY_ORDER.map((category) => {
            const items = documentTypes.filter((d) => d.category === category);
            if (items.length === 0) return null;
            const catMeta = CATEGORY_META[category];
            return (
              <div key={category} className="space-y-3">
                <div className="flex items-baseline gap-3 border-b border-dashed border-[#e5edf5] pb-2">
                  <span className={cn("h-2 w-2 rounded-full", catMeta.rail)} />
                  <h3 className="font-heading text-[14px] font-semibold text-[#061b31]">
                    {catMeta.label}
                  </h3>
                  <span className="tnum text-[12px] text-[#94a3b8]">
                    {items.length} document{items.length === 1 ? "o" : "i"}
                  </span>
                </div>

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {items.map((docType) => {
                    const existing = getDocStatus(docType.key);
                    const isGenerating = generatingTypes.has(docType.key);
                    const status = existing?.status;
                    const config = status ? statusConfig[status] : null;
                    const versionCount = documenti.filter(
                      (d) => d.tipo_documento === docType.key,
                    ).length;
                    // US-4.1: visually mark PEE cards as blocked when the DVR
                    // Master has not yet been generated. The generate button
                    // stays clickable so the Italian error message can still
                    // surface; the block itself is enforced by the backend.
                    const blockedByDvr =
                      DVR_DEPENDENT_TYPES.has(docType.key) && !dvrReady;
                    const ActionIcon = docType.icon;
                    const isReady =
                      existing?.status === "ready" ||
                      existing?.status === "completed";

                    return (
                      <div
                        key={docType.key}
                        className={cn(
                          "group relative overflow-hidden rounded-md border border-[#e5edf5] bg-white shadow-stripe-ambient transition-[box-shadow,border-color] hover:border-[#d1d9e3] hover:shadow-stripe-elevated",
                          blockedByDvr && "opacity-75",
                        )}
                      >
                        <span
                          className={cn(
                            "absolute inset-y-0 left-0 w-[3px]",
                            catMeta.rail,
                          )}
                          aria-hidden
                        />
                        <div className="flex flex-col gap-3 p-[18px] pl-[22px]">
                          <div className="flex items-start gap-3">
                            <Monogram accent={catMeta.accent}>
                              <ActionIcon className="h-5 w-5" strokeWidth={1.75} />
                            </Monogram>
                            <div className="min-w-0 flex-1">
                              <h4 className="font-heading text-[14.5px] font-semibold leading-[1.25] tracking-[-0.005em] text-[#061b31]">
                                {docType.name}
                              </h4>
                              <p className="mt-0.5 text-[11.5px] font-medium uppercase tracking-[0.04em] text-[#94a3b8]">
                                <span className="tnum">{docType.pages}</span>{" "}
                                pagine
                              </p>
                            </div>
                            <Badge
                              className={cn(
                                complexityColors[docType.complexity],
                                "shrink-0",
                              )}
                            >
                              {docType.complexity}
                            </Badge>
                          </div>

                          {blockedByDvr && (
                            <p className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-[11.5px] text-amber-800">
                              Genera prima il DVR Master
                            </p>
                          )}

                          {existing && config ? (
                            <div className="grid grid-cols-2 gap-3 border-t border-[#eef2f7] pt-3">
                              <div className="min-w-0">
                                <div className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[#94a3b8]">
                                  Stato
                                </div>
                                <div className="mt-0.5">
                                  <Badge
                                    className={config.color}
                                    title={
                                      status === "bozza" && existing.error_message
                                        ? existing.error_message
                                        : undefined
                                    }
                                  >
                                    {(status === "generating" ||
                                      status === "in_progress") && (
                                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                                    )}
                                    {config.label}
                                  </Badge>
                                </div>
                              </div>
                              <div className="min-w-0">
                                <div className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[#94a3b8]">
                                  Versione · aggiornato
                                </div>
                                <div className="mt-0.5 truncate text-[13px] font-semibold text-[#273951]">
                                  <span className="tnum">v{existing.versione}</span>{" "}
                                  <span className="font-normal text-[#64748d]">
                                    · {formatRelative(existing.created_at)}
                                  </span>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <p className="text-[12px] text-[#94a3b8]">
                              Mai generato
                            </p>
                          )}

                          {existing?.generated_by_name && (
                            <p className="flex items-center gap-1 text-[11.5px] text-[#64748d]">
                              <UserIcon className="h-3 w-3" strokeWidth={1.75} />
                              {existing.generated_by_name}
                            </p>
                          )}

                          {status === "bozza" && existing?.error_message && (
                            <p className="text-[11.5px] text-amber-700">
                              {existing.error_message}
                            </p>
                          )}

                          <div className="mt-auto flex flex-wrap items-center gap-1.5 border-t border-[#eef2f7] pt-3">
                            <Button
                              size="sm"
                              variant={isReady ? "outline" : "default"}
                              onClick={() => handleGenerate(docType.key)}
                              disabled={
                                isGenerating ||
                                status === "generating" ||
                                status === "in_progress"
                              }
                            >
                              {isGenerating ||
                              status === "generating" ||
                              status === "in_progress" ? (
                                <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                              ) : (
                                <RefreshCw className="mr-1.5 h-3 w-3" />
                              )}
                              {isReady
                                ? "Rigenera"
                                : existing?.status === "bozza"
                                  ? "Riprova"
                                  : "Genera"}
                            </Button>
                            {isReady && existing.file_path && (
                              <Button
                                size="icon-sm"
                                variant="ghost"
                                title="Scarica"
                                aria-label="Scarica"
                                onClick={async () => {
                                  try {
                                    await downloadFile(
                                      `/api/v1/documenti/${existing.id}/download`,
                                    );
                                  } catch (e) {
                                    alert(
                                      (e as Error).message || "Download fallito",
                                    );
                                  }
                                }}
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                            )}
                            {docType.key === "dvr_master" && isReady && (
                              <>
                                <Button
                                  size="icon-sm"
                                  variant="ghost"
                                  onClick={() => handleOpenInGoogleDocs(existing)}
                                  disabled={openingGdoc.has(existing.id)}
                                  title="Modifica in Google Docs"
                                  aria-label="Modifica in Google Docs"
                                >
                                  {openingGdoc.has(existing.id) ? (
                                    <Loader2 className="animate-spin" />
                                  ) : (
                                    <Pencil />
                                  )}
                                </Button>
                                {existing.gdoc_file_id && (
                                  <>
                                    <Button
                                      size="icon-sm"
                                      variant="ghost"
                                      onClick={() =>
                                        handleSyncFromGoogleDocs(existing)
                                      }
                                      disabled={syncingGdoc.has(existing.id)}
                                      title="Scarica modifiche da Google Docs"
                                      aria-label="Scarica modifiche da Google Docs"
                                    >
                                      {syncingGdoc.has(existing.id) ? (
                                        <Loader2 className="animate-spin" />
                                      ) : (
                                        <CloudDownload />
                                      )}
                                    </Button>
                                    <Button
                                      size="icon-sm"
                                      variant="ghost"
                                      className="text-[#ba1a1a] hover:text-[#ba1a1a]"
                                      onClick={() => setDiscardTarget(existing)}
                                      disabled={discardingGdoc.has(existing.id)}
                                      title="Scarta modifiche Google Docs"
                                      aria-label="Scarta modifiche Google Docs"
                                    >
                                      {discardingGdoc.has(existing.id) ? (
                                        <Loader2 className="animate-spin" />
                                      ) : (
                                        <Trash2 />
                                      )}
                                    </Button>
                                  </>
                                )}
                              </>
                            )}
                            {versionCount > 0 && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="ml-auto h-8 px-2"
                                onClick={() => setHistoryTipo(docType.key)}
                                title={`Storia versioni (${versionCount})`}
                                aria-label={`Storia versioni ${docType.name}`}
                              >
                                <History className="mr-1 h-4 w-4" />
                                v{versionCount}
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
          </div>
        </>
      )}

      {/* Confirm "Scarta modifiche" — destructive action (deletes the Google
          Doc on Drive and the user's in-browser edits) so a confirm dialog is
          warranted rather than a silent click. */}
      <Dialog
        open={discardTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDiscardTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Scartare le modifiche?</DialogTitle>
            <DialogDescription>
              Le modifiche fatte in Google Docs verranno eliminate
              definitivamente e il documento condiviso verrà rimosso da Drive.
              Questa azione non può essere annullata.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDiscardTarget(null)}>
              Annulla
            </Button>
            <Button
              onClick={() => {
                if (discardTarget) void handleDiscardGdocEdits(discardTarget);
              }}
              disabled={
                discardTarget !== null && discardingGdoc.has(discardTarget.id)
              }
              className="bg-[#ba1a1a] text-white hover:bg-[#9b1515]"
            >
              Scarta modifiche
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
