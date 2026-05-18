"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useApi } from "@/hooks/use-api";
import { AIBadge } from "@/components/ai/ai-badge";
import { AIContent, AIFilterToggle } from "@/components/ai/ai-filter-context";
import type {
  BatchStatusResponse,
  BatchUploadFileResult,
  BatchUploadResponse,
  SostanzaChimica,
} from "@/types";

interface StepSostanzeProps {
  aziendaId: string;
  sostanze: SostanzaChimica[];
  onChange: (sostanze: SostanzaChimica[]) => void;
}

const PITTOGRAMMI_GHS = [
  { code: "GHS01", label: "Esplosivo" },
  { code: "GHS02", label: "Infiammabile" },
  { code: "GHS03", label: "Comburente" },
  { code: "GHS04", label: "Gas compresso" },
  { code: "GHS05", label: "Corrosivo" },
  { code: "GHS06", label: "Tossicita acuta" },
  { code: "GHS07", label: "Irritante" },
  { code: "GHS08", label: "Pericolo per la salute" },
  { code: "GHS09", label: "Pericolo per l'ambiente" },
];

const STATI_MISCELA = [
  "solido",
  "liquido",
  "gassoso",
  "aerosol",
  "polvere",
  "pasta",
  "altro",
];

// US-1.8 hard limits
const MAX_FILES_PER_BATCH = 20;
const MAX_FILE_SIZE_MB = 10;
const POLL_INTERVAL_MS = 2000;

function createEmptySostanza(aziendaId: string): SostanzaChimica {
  return {
    id: crypto.randomUUID(),
    azienda_id: aziendaId,
    nome_prodotto: "",
    produttore: null,
    destinazione_uso: null,
    pittogrammi: [],
    stato_miscela: null,
    frasi_h: [],
    frasi_p: [],
  };
}

// ---------------------------------------------------------------------------
// Drag-and-drop SDS upload (US-1.8, US-1.9)
// ---------------------------------------------------------------------------

type UploadRow =
  | { kind: "rejected"; filename: string; reason: string }
  | {
      kind: "tracked";
      sostanza_id: string;
      filename: string;
      status: "queued" | "processing" | "completed" | "failed";
      error?: string | null;
      confidence?: number | null;
    };

function SDSUploadZone({
  aziendaId,
  onExtracted,
}: {
  aziendaId: string;
  onExtracted: () => void;
}) {
  const { apiFetch } = useApi();
  const [rows, setRows] = useState<UploadRow[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const activeIds = rows
    .filter(
      (r) =>
        r.kind === "tracked" &&
        (r.status === "queued" || r.status === "processing")
    )
    .map((r) => (r as Extract<UploadRow, { kind: "tracked" }>).sostanza_id);

  // Poll /batch-status while any row is still queued/processing.
  useEffect(() => {
    if (activeIds.length === 0) {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      return;
    }

    let cancelled = false;
    const poll = async () => {
      try {
        const res = await apiFetch<BatchStatusResponse>(
          `/api/v1/aziende/${aziendaId}/sostanze-chimiche/batch-status`
        );
        if (cancelled) return;
        setRows((prev) =>
          prev.map((r) => {
            if (r.kind !== "tracked") return r;
            const item = res.items.find(
              (i) => i.sostanza_id === r.sostanza_id
            );
            if (!item) return r;
            return {
              ...r,
              status:
                (item.extraction_status as UploadRow extends {
                  kind: "tracked";
                  status: infer S;
                }
                  ? S
                  : never) ?? r.status,
              error: item.extraction_error,
              confidence: item.ai_confidence,
            };
          })
        );
      } catch (err) {
        console.warn("batch-status poll failed", err);
      }
      if (!cancelled) {
        pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
      }
    };
    pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, [activeIds.length, aziendaId, apiFetch]);

  // When all active rows become terminal, pull the updated sostanze list.
  const prevActiveCount = useRef(activeIds.length);
  useEffect(() => {
    if (prevActiveCount.current > 0 && activeIds.length === 0) {
      onExtracted();
    }
    prevActiveCount.current = activeIds.length;
  }, [activeIds.length, onExtracted]);

  const uploadFiles = useCallback(
    async (files: File[]) => {
      if (files.length === 0) return;

      // Client-side validation matching the backend limits
      if (files.length > MAX_FILES_PER_BATCH) {
        setRows((r) => [
          ...r,
          {
            kind: "rejected",
            filename: `(${files.length} file)`,
            reason: `Massimo ${MAX_FILES_PER_BATCH} file per caricamento`,
          },
        ]);
        return;
      }

      const accepted: File[] = [];
      const rejected: UploadRow[] = [];
      for (const f of files) {
        if (
          f.type !== "application/pdf" &&
          !f.name.toLowerCase().endsWith(".pdf")
        ) {
          rejected.push({
            kind: "rejected",
            filename: f.name,
            reason: "Solo file PDF ammessi",
          });
          continue;
        }
        if (f.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
          rejected.push({
            kind: "rejected",
            filename: f.name,
            reason: `Dimensione > ${MAX_FILE_SIZE_MB} MB`,
          });
          continue;
        }
        if (f.size === 0) {
          rejected.push({
            kind: "rejected",
            filename: f.name,
            reason: "File vuoto",
          });
          continue;
        }
        accepted.push(f);
      }

      if (rejected.length > 0) {
        setRows((r) => [...r, ...rejected]);
      }
      if (accepted.length === 0) return;

      setIsUploading(true);
      try {
        const fd = new FormData();
        for (const f of accepted) fd.append("files", f);
        // Note: don't set Content-Type — browser adds the boundary.
        const res = await apiFetch<BatchUploadResponse>(
          `/api/v1/aziende/${aziendaId}/sostanze-chimiche/batch-upload`,
          { method: "POST", body: fd, headers: {} }
        );
        const mapped: UploadRow[] = res.results.map(
          (r: BatchUploadFileResult) =>
            r.status === "failed" || !r.sostanza_id
              ? {
                  kind: "rejected",
                  filename: r.filename,
                  reason: r.reason ?? "Errore upload",
                }
              : {
                  kind: "tracked",
                  sostanza_id: r.sostanza_id,
                  filename: r.filename,
                  status: "queued",
                }
        );
        setRows((r) => [...r, ...mapped]);
      } catch (err) {
        console.error("batch-upload failed", err);
        setRows((r) => [
          ...r,
          {
            kind: "rejected",
            filename: "(upload)",
            reason: err instanceof Error ? err.message : "Errore di rete",
          },
        ]);
      } finally {
        setIsUploading(false);
      }
    },
    [aziendaId, apiFetch]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(false);
      const files = Array.from(e.dataTransfer.files ?? []);
      void uploadFiles(files);
    },
    [uploadFiles]
  );

  const handlePick = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? []);
      void uploadFiles(files);
      e.target.value = "";
    },
    [uploadFiles]
  );

  const dismissRow = (idx: number) =>
    setRows((r) => r.filter((_, i) => i !== idx));

  return (
    <div>
      <div className="mb-6">
        <h3 className="flex items-center gap-2 font-heading text-xl font-bold text-on-surface">
          <Sparkles className="h-5 w-5 text-primary" />
          Carica schede di sicurezza delle sostanze chimiche (SDS)
        </h3>
        <p className="mt-1 text-sm text-on-surface-variant">
          Trascina fino a {MAX_FILES_PER_BATCH} PDF (max {MAX_FILE_SIZE_MB} MB
          l&apos;uno). L&apos;AI estrarra&apos; automaticamente nome, produttore,
          pittogrammi e frasi H/P. Potrai revisionare tutto prima di confermare.
        </p>
      </div>
      <div className="space-y-4">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
            isDragOver
              ? "border-primary bg-primary/5"
              : "border-input hover:border-primary/50 hover:bg-muted/50"
          }`}
        >
          <Upload className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm font-medium">
            Trascina i PDF qui o clicca per selezionare
          </p>
          <p className="text-xs text-muted-foreground">
            {isUploading ? "Caricamento in corso..." : "Max 20 file, 10 MB l'uno"}
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            multiple
            className="hidden"
            onChange={handlePick}
          />
        </div>

        {rows.length > 0 && (
          <ul className="space-y-1.5">
            {rows.map((r, idx) => (
              <li
                key={idx}
                className="flex items-center gap-3 rounded-md border border-input px-3 py-2 text-sm"
              >
                <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                <span className="flex-1 truncate font-medium">
                  {r.filename}
                </span>
                {r.kind === "rejected" && (
                  <>
                    <Badge variant="destructive" className="text-xs">
                      <AlertCircle className="mr-1 h-3 w-3" />
                      {r.reason}
                    </Badge>
                    <button
                      type="button"
                      onClick={() => dismissRow(idx)}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </>
                )}
                {r.kind === "tracked" && r.status === "queued" && (
                  <Badge variant="secondary" className="text-xs">
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                    In coda
                  </Badge>
                )}
                {r.kind === "tracked" && r.status === "processing" && (
                  <Badge variant="secondary" className="text-xs">
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                    Estrazione in corso
                  </Badge>
                )}
                {r.kind === "tracked" && r.status === "completed" && (
                  <>
                    <Badge
                      variant="default"
                      className="bg-emerald-600 text-xs hover:bg-emerald-700"
                    >
                      <CheckCircle2 className="mr-1 h-3 w-3" />
                      Completata{" "}
                      {typeof r.confidence === "number" &&
                        `(${Math.round(r.confidence * 100)}%)`}
                    </Badge>
                    <button
                      type="button"
                      onClick={() => dismissRow(idx)}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </>
                )}
                {r.kind === "tracked" && r.status === "failed" && (
                  <>
                    <Badge variant="destructive" className="text-xs">
                      <AlertCircle className="mr-1 h-3 w-3" />
                      Estrazione fallita
                    </Badge>
                    {r.error && (
                      <span
                        className="text-xs text-muted-foreground"
                        title={r.error}
                      >
                        {r.error.slice(0, 40)}
                        {r.error.length > 40 ? "..." : ""}
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => dismissRow(idx)}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared tag input (frasi H / P)
// ---------------------------------------------------------------------------

function TagInput({
  label,
  value,
  onChange,
  placeholder,
  id,
}: {
  label: string;
  value: string[];
  onChange: (val: string[]) => void;
  placeholder: string;
  id: string;
}) {
  // Split a raw input string into deduped, uppercase, trimmed tags and
  // append any new ones to `value`. Empty input is a no-op.
  const flushInput = (input: HTMLInputElement) => {
    const raw = input.value;
    if (!raw.trim()) return;
    const parts = raw
      .split(",")
      .map((p) => p.trim().toUpperCase())
      .filter(Boolean);
    if (parts.length === 0) return;
    const merged = [...value];
    for (const p of parts) {
      if (!merged.includes(p)) merged.push(p);
    }
    onChange(merged);
    input.value = "";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      flushInput(e.currentTarget);
    }
  };
  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    flushInput(e.currentTarget);
  };
  const removeTag = (tag: string) =>
    onChange(value.filter((v) => v !== tag));

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex flex-wrap gap-1.5 rounded-lg border border-input p-2">
        {value.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs font-medium"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          id={id}
          type="text"
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          placeholder={value.length === 0 ? placeholder : ""}
          className="min-w-[120px] flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />
      </div>
      <p className="text-xs text-muted-foreground">
        Premi Invio, virgola o esci dal campo per aggiungere
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main step component
// ---------------------------------------------------------------------------

export function StepSostanze({
  aziendaId,
  sostanze,
  onChange,
}: StepSostanzeProps) {
  const { apiFetch, isAuthenticated } = useApi();

  const refreshFromServer = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const items = await apiFetch<SostanzaChimica[]>(
        `/api/v1/aziende/${aziendaId}/sostanze-chimiche`
      );
      // M2 fix: merge. A sostanza is considered "server-side" iff its id
      // appears in the fetched list. Any local-only rows (manual entries
      // the user is still editing, before first save) are preserved so the
      // newly-AI-extracted sostanze from a PDF upload don't overwrite them.
      const serverIds = new Set(items.map((s) => s.id));
      const localOnly = sostanze.filter((s) => !serverIds.has(s.id));
      onChange([...items, ...localOnly]);
    } catch (err) {
      console.error("refresh sostanze failed", err);
    }
  }, [aziendaId, apiFetch, isAuthenticated, onChange, sostanze]);

  // Pull persisted sostanze on mount so AI-extracted rows appear even after
  // a page refresh mid-batch.
  useEffect(() => {
    void refreshFromServer();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  // Track which manual rows exist on the server. AI-extracted rows are
  // already persisted when they arrive. Manual rows start local and flip
  // to persisted after the first PUT/POST succeeds.
  const [persistedManualIds, setPersistedManualIds] = useState<Set<string>>(
    () => new Set()
  );
  const saveTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map()
  );
  const inFlightSavesRef = useRef<Set<string>>(new Set());

  // Refs mirroring the latest `sostanze` and `persistedManualIds` so the
  // debounced autosave callback never reads stale snapshots when it fires
  // (root cause of cards being clobbered on rapid creation / pittogrammi
  // toggles being overwritten by stale POST-success merges).
  const sostanzeRef = useRef(sostanze);
  useEffect(() => {
    sostanzeRef.current = sostanze;
  }, [sostanze]);
  const persistedManualIdsRef = useRef(persistedManualIds);
  useEffect(() => {
    persistedManualIdsRef.current = persistedManualIds;
  }, [persistedManualIds]);
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  const addSostanza = useCallback(() => {
    onChange([...sostanze, createEmptySostanza(aziendaId)]);
  }, [sostanze, onChange, aziendaId]);

  const removeSostanza = useCallback(
    async (index: number) => {
      const s = sostanze[index];
      const isPersisted =
        !!s && (s.ai_extracted || persistedManualIds.has(s.id));
      onChange(sostanze.filter((_, i) => i !== index));
      if (isPersisted) {
        try {
          await apiFetch(
            `/api/v1/aziende/${aziendaId}/sostanze-chimiche/${s.id}`,
            { method: "DELETE" }
          );
          setPersistedManualIds((prev) => {
            const n = new Set(prev);
            n.delete(s.id);
            return n;
          });
        } catch (err) {
          console.error("delete sostanza failed", err);
        }
      }
    },
    [sostanze, onChange, apiFetch, aziendaId, persistedManualIds]
  );

  const scheduleSostanzaSave = useCallback(
    (rowId: string) => {
      const timers = saveTimersRef.current;
      const prev = timers.get(rowId);
      if (prev) clearTimeout(prev);
      const handle = setTimeout(async () => {
        timers.delete(rowId);
        // Coalesce: skip if a save for this row is already in flight; the
        // next keystroke will reschedule once the prior request resolves.
        if (inFlightSavesRef.current.has(rowId)) {
          const latest = sostanzeRef.current.find((r) => r.id === rowId);
          if (latest) scheduleSostanzaSave(rowId);
          return;
        }
        // Read latest row from the ref so newly-typed values, freshly
        // toggled pittogrammi, and just-added cards aren't lost.
        const row = sostanzeRef.current.find((r) => r.id === rowId);
        if (!row) return;
        if (!row.nome_prodotto?.trim()) return;
        const payload = {
          nome_prodotto: row.nome_prodotto,
          produttore: row.produttore ?? null,
          destinazione_uso: row.destinazione_uso ?? null,
          stato_miscela: row.stato_miscela ?? null,
          pittogrammi: row.pittogrammi ?? [],
          frasi_h: row.frasi_h ?? [],
          frasi_p: row.frasi_p ?? [],
        };
        const isPersisted =
          row.ai_extracted || persistedManualIdsRef.current.has(row.id);
        inFlightSavesRef.current.add(rowId);
        try {
          if (isPersisted) {
            await apiFetch<SostanzaChimica>(
              `/api/v1/aziende/${aziendaId}/sostanze-chimiche/${row.id}`,
              { method: "PUT", body: JSON.stringify(payload) }
            );
          } else {
            const created = await apiFetch<SostanzaChimica>(
              `/api/v1/aziende/${aziendaId}/sostanze-chimiche`,
              { method: "POST", body: JSON.stringify(payload) }
            );
            // Merge against the latest sostanze (not a stale closure) and
            // preserve any user edits made while the POST was in flight by
            // overlaying server fields under the local row, not over it.
            const current = sostanzeRef.current;
            const next = current.map((s) =>
              s.id === row.id
                ? {
                    ...created,
                    nome_prodotto: s.nome_prodotto,
                    produttore: s.produttore,
                    destinazione_uso: s.destinazione_uso ?? created.destinazione_uso ?? null,
                    stato_miscela: s.stato_miscela,
                    pittogrammi: s.pittogrammi ?? created.pittogrammi ?? [],
                    frasi_h: s.frasi_h ?? created.frasi_h ?? [],
                    frasi_p: s.frasi_p ?? created.frasi_p ?? [],
                  }
                : s
            );
            onChangeRef.current(next);
            setPersistedManualIds((prev) => {
              const n = new Set(prev);
              n.delete(row.id);
              n.add(created.id);
              return n;
            });
          }
        } catch (err) {
          toast.error(
            err instanceof Error
              ? err.message
              : "Errore nel salvataggio della sostanza"
          );
        } finally {
          inFlightSavesRef.current.delete(rowId);
        }
      }, 800);
      timers.set(rowId, handle);
    },
    [apiFetch, aziendaId]
  );

  useEffect(() => {
    const timers = saveTimersRef.current;
    return () => {
      for (const h of timers.values()) clearTimeout(h);
    };
  }, []);

  const updateSostanza = useCallback(
    (index: number, fields: Partial<SostanzaChimica>) => {
      const updated = sostanze.map((s, i) =>
        i === index ? { ...s, ...fields } : s
      );
      onChange(updated);
      const row = updated[index];
      if (row) scheduleSostanzaSave(row.id);
    },
    [sostanze, onChange, scheduleSostanzaSave]
  );

  const togglePittogramma = useCallback(
    (index: number, code: string) => {
      const sostanza = sostanze[index];
      // Backend can return pittogrammi=null while extraction is in-flight
      // (US-1.9 B-02), so guard before calling array methods.
      const current = sostanza.pittogrammi ?? [];
      const pitt = current.includes(code)
        ? current.filter((p) => p !== code)
        : [...current, code];
      updateSostanza(index, { pittogrammi: pitt });
    },
    [sostanze, updateSostanza]
  );

  const confirmReview = useCallback(
    async (index: number) => {
      const s = sostanze[index];
      if (!s?.ai_extracted) return;
      try {
        const updated = await apiFetch<SostanzaChimica>(
          `/api/v1/aziende/${aziendaId}/sostanze-chimiche/${s.id}/review`,
          { method: "PATCH" }
        );
        updateSostanza(index, updated);
      } catch (err) {
        console.error("review sostanza failed", err);
      }
    },
    [sostanze, aziendaId, apiFetch, updateSostanza]
  );

  return (
    <div className="space-y-6">
      <SDSUploadZone
        aziendaId={aziendaId}
        onExtracted={refreshFromServer}
      />

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Revisione sostanze</CardTitle>
              <CardDescription>
                Verifica e correggi i dati estratti dall&apos;AI. Le sostanze
                inserite manualmente non hanno badge.
              </CardDescription>
            </div>
            {sostanze.some((s) => s.ai_extracted) && <AIFilterToggle />}
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {sostanze.length === 0 && (
            <p className="py-8 text-center text-muted-foreground">
              Nessuna sostanza chimica. Carica delle SDS sopra oppure usa
              &quot;Aggiungi Sostanza&quot; per l&apos;inserimento manuale.
            </p>
          )}

          {sostanze.map((sost, index) => {
            const isProcessing =
              sost.extraction_status === "pending" ||
              sost.extraction_status === "processing";
            const hasFailed = sost.extraction_status === "failed";
            const confidencePct =
              typeof sost.ai_confidence === "number"
                ? Math.round(sost.ai_confidence * 100)
                : null;

            // US-5.3 provenance mapping:
            //   ai_extracted && !human_reviewed  -> "ai"      (violet)
            //   ai_extracted &&  human_reviewed  -> "edited"  (sky)
            //   !ai_extracted                    -> "manual"  (slate, hidden)
            // "Estrazione fallita" keeps its destructive chip because it is
            // a lifecycle state, not a provenance — the row is usable as a
            // manual fallback once the operator fills it in.
            const provenance = sost.ai_extracted
              ? sost.human_reviewed
                ? "edited"
                : "ai"
              : "manual";
            const showAiBadge = provenance !== "manual";
            const isAiBlock = provenance === "ai";

            return (
              <AIContent key={sost.id} isAI={isAiBlock}>
                {index > 0 && <Separator className="mb-6" />}
                <div className="space-y-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-sm font-medium">
                        Sostanza {index + 1}
                        {sost.nome_prodotto ? ` - ${sost.nome_prodotto}` : ""}
                      </h3>
                      {showAiBadge && (
                        <AIBadge
                          provenance={provenance}
                          timestamp={sost.created_at}
                          label={
                            provenance === "ai" && confidencePct !== null
                              ? `AI ${confidencePct}%`
                              : provenance === "edited"
                              ? "Revisionato"
                              : undefined
                          }
                        />
                      )}
                      {hasFailed && (
                        <Badge variant="destructive">
                          <AlertCircle className="mr-1 h-3 w-3" />
                          Estrazione fallita
                        </Badge>
                      )}
                    </div>
                    <div className="flex gap-2">
                      {sost.ai_extracted && !sost.human_reviewed && !isProcessing && (
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => confirmReview(index)}
                        >
                          Conferma
                        </Button>
                      )}
                      <Button
                        variant="destructive"
                        size="icon-sm"
                        onClick={() => removeSostanza(index)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>

                  {isProcessing && (
                    <div className="flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Estrazione in corso...
                    </div>
                  )}
                  {hasFailed && sost.extraction_error && (
                    <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                      {sost.extraction_error}. Puoi comunque inserire i dati
                      manualmente sotto.
                    </div>
                  )}

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor={`sost-nome-${index}`}>
                        Nome Prodotto *
                      </Label>
                      <Input
                        id={`sost-nome-${index}`}
                        value={sost.nome_prodotto}
                        onChange={(e) =>
                          updateSostanza(index, {
                            nome_prodotto: e.target.value,
                          })
                        }
                        placeholder="Es. Detergente industriale"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor={`sost-prod-${index}`}>Produttore</Label>
                      <Input
                        id={`sost-prod-${index}`}
                        value={sost.produttore ?? ""}
                        onChange={(e) =>
                          updateSostanza(index, {
                            produttore: e.target.value || null,
                          })
                        }
                        placeholder="Es. ChemCo S.r.l."
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor={`sost-stato-${index}`}>
                        Stato / Miscela
                      </Label>
                      <select
                        id={`sost-stato-${index}`}
                        value={sost.stato_miscela ?? ""}
                        onChange={(e) =>
                          updateSostanza(index, {
                            stato_miscela: e.target.value || null,
                          })
                        }
                        className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                      >
                        <option value="">Seleziona stato</option>
                        {STATI_MISCELA.map((stato) => (
                          <option key={stato} value={stato}>
                            {stato.charAt(0).toUpperCase() + stato.slice(1)}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor={`sost-dest-${index}`}>
                        Destinazione d&apos;uso
                      </Label>
                      <Input
                        id={`sost-dest-${index}`}
                        value={sost.destinazione_uso ?? ""}
                        onChange={(e) =>
                          updateSostanza(index, {
                            destinazione_uso: e.target.value || null,
                          })
                        }
                        placeholder="Es. Detergente professionale per superfici dure"
                      />
                      <p className="text-[11px] text-muted-foreground">
                        Uso identificato dal produttore (SDS § 1.2). Compilato
                        automaticamente dall&apos;estrazione AI quando
                        disponibile.
                      </p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Pittogrammi GHS</Label>
                    <div className="flex flex-wrap gap-2">
                      {PITTOGRAMMI_GHS.map((p) => (
                        <button
                          key={p.code}
                          type="button"
                          onClick={() => togglePittogramma(index, p.code)}
                          className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                            (sost.pittogrammi ?? []).includes(p.code)
                              ? "border-primary bg-primary/10 text-primary"
                              : "border-input text-muted-foreground hover:bg-muted"
                          }`}
                        >
                          {p.code} - {p.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <TagInput
                    id={`sost-h-${index}`}
                    label="Frasi H (Pericolo)"
                    // Backend may return null while extraction is in-flight
                    // (same B-02 family of bugs as pittogrammi above).
                    value={sost.frasi_h ?? []}
                    onChange={(frasi_h) =>
                      updateSostanza(index, { frasi_h })
                    }
                    placeholder="Es. H302, H315"
                  />

                  <TagInput
                    id={`sost-p-${index}`}
                    label="Frasi P (Precauzione)"
                    value={sost.frasi_p ?? []}
                    onChange={(frasi_p) =>
                      updateSostanza(index, { frasi_p })
                    }
                    placeholder="Es. P264, P280"
                  />
                </div>
              </AIContent>
            );
          })}

          <Button variant="outline" onClick={addSostanza} className="w-full">
            <Plus className="mr-2 h-4 w-4" />
            Aggiungi Sostanza (manuale)
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
