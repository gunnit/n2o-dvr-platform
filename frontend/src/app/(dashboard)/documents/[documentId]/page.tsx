"use client";

/**
 * In-browser document preview + inline text editing.
 *
 * Renders the JSON model served by GET /documenti/{id}/preview as A4-like
 * sheets; clicking any editable paragraph (top-level or table cell) opens a
 * plain-text contentEditable whose commits autosave as content overrides
 * (PATCH /documenti/{id}/overrides). "Scarica .docx" streams the document
 * with overrides applied; "Salva come nuova versione" mints a new
 * DocumentoGenerato row and clears the source's overrides.
 *
 * Client component: the dynamic [documentId] segment is read with
 * useParams() (Next 16 made the server-side `params` prop a Promise).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import {
  ParagraphBlockView,
  TableBlockView,
  groupIntoSheets,
} from "@/components/documents/editor/block-renderer";
import { EditorHeader } from "@/components/documents/editor/editor-header";
import {
  EditorToc,
  buildTocEntries,
} from "@/components/documents/editor/editor-toc";
import { useDocumentOverrides } from "@/components/documents/editor/use-document-overrides";
import { apiCall, downloadFile } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { DocumentPreviewResponse, DocumentoGenerato } from "@/types";

// Stable empty slice so tables without overrides keep memo equality.
const EMPTY_OVERRIDES: Record<string, string> = {};

export default function DocumentEditorPage() {
  const params = useParams<{ documentId: string }>();
  const documentId = params.documentId;
  const router = useRouter();

  const [preview, setPreview] = useState<DocumentPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [savingVersion, setSavingVersion] = useState(false);

  const { overrides, saveState, initialize, setOverride, retrySave, flushAll } =
    useDocumentOverrides(documentId);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    setPreview(null);
    apiCall<DocumentPreviewResponse>(`/api/v1/documenti/${documentId}/preview`)
      .then((data) => {
        if (cancelled) return;
        setPreview(data);
        initialize(data.overrides);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadError(
          err instanceof Error
            ? err.message
            : "Impossibile caricare l'anteprima del documento",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [documentId, initialize]);

  const sheets = useMemo(
    () => (preview ? groupIntoSheets(preview.blocks) : []),
    [preview],
  );

  const tocEntries = useMemo(
    () => (preview ? buildTocEntries(preview.blocks, overrides) : []),
    [preview, overrides],
  );

  // Per-table slices of the overrides map, so a keystroke in one paragraph
  // doesn't re-render every table (see TableBlockView's memo comparator).
  const tableOverrideSlices = useMemo(() => {
    const slices: Record<string, Record<string, string>> = {};
    for (const [addr, value] of Object.entries(overrides)) {
      const sep = addr.indexOf(":");
      if (sep === -1) continue; // top-level paragraph override
      const tableAddr = addr.slice(0, sep);
      (slices[tableAddr] ??= {})[addr] = value;
    }
    return slices;
  }, [overrides]);

  const editedCount = Object.keys(overrides).length;

  const handleDownload = useCallback(async () => {
    setDownloading(true);
    try {
      // Push any pending edit first — the download applies the overrides
      // saved on the row, not the ones still sitting in the debounce queue.
      const flushed = await flushAll();
      if (!flushed) {
        toast.error("Alcune modifiche non sono ancora salvate. Riprova.");
        return;
      }
      await downloadFile(`/api/v1/documenti/${documentId}/download`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Download fallito");
    } finally {
      setDownloading(false);
    }
  }, [documentId, flushAll]);

  const handleSaveVersion = useCallback(async () => {
    setSavingVersion(true);
    try {
      const flushed = await flushAll();
      if (!flushed) {
        toast.error(
          "Alcune modifiche non sono ancora salvate. Riprova prima di creare la nuova versione.",
        );
        return;
      }
      const created = await apiCall<DocumentoGenerato>(
        `/api/v1/documenti/${documentId}/save-edited-version`,
        { method: "POST" },
      );
      toast.success(`Versione ${created.versione} salvata`);
      router.push(`/documents/${created.id}`);
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Impossibile salvare la nuova versione",
      );
    } finally {
      setSavingVersion(false);
    }
  }, [documentId, flushAll, router]);

  if (loading) {
    return (
      <div className="space-y-6" aria-busy="true">
        <p className="sr-only">Caricamento anteprima…</p>
        <div className="h-9 w-72 animate-pulse rounded-md bg-[#eef2f7]" />
        <div className="flex justify-center rounded-md bg-[#f6f9fc] px-4 py-10">
          <div className="w-full max-w-[794px] space-y-4 rounded-sm bg-white p-12 shadow-stripe-standard sm:p-[94px]">
            {Array.from({ length: 14 }).map((_, i) => (
              <div
                key={i}
                className={cn(
                  "h-4 animate-pulse rounded bg-[#eef2f7]",
                  i % 5 === 0 ? "w-1/2" : i % 3 === 0 ? "w-5/6" : "w-full",
                )}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (loadError || !preview) {
    return (
      <div className="space-y-6">
        <Link
          href="/documents"
          className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#64748d] transition-colors hover:text-[#061b31]"
        >
          <ArrowLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Torna ai documenti
        </Link>
        <div className="rounded-md border border-[rgba(234,34,97,0.25)] bg-[rgba(234,34,97,0.04)] p-10 text-center shadow-stripe-ambient">
          <p className="text-[14px] text-[#b51648]">
            {loadError || "Documento non trovato"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <EditorHeader
        preview={preview}
        saveState={saveState}
        editedCount={editedCount}
        onRetrySave={retrySave}
        onDownload={handleDownload}
        downloading={downloading}
        onSaveVersion={handleSaveVersion}
        savingVersion={savingVersion}
      />

      <div className="mt-6 space-y-4">
        {preview.stale_snapshot && (
          <div
            role="status"
            className="flex items-start gap-2 rounded-md border border-[rgba(155,104,41,0.3)] bg-[rgba(155,104,41,0.06)] px-3 py-2.5 text-[13px] text-[#9b6829]"
          >
            <ShieldAlert className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>
              I dati del sopralluogo sono cambiati dopo la generazione di
              questo documento — i contenuti potrebbero essere disallineati.
              Rigenera il documento per aggiornarli.
            </span>
          </div>
        )}

        <div className="flex items-start gap-6">
          <aside className="sticky top-[76px] hidden max-h-[calc(100vh-100px)] w-64 shrink-0 overflow-y-auto rounded-md border border-[#e5edf5] bg-white p-3 shadow-stripe-ambient lg:block">
            <EditorToc entries={tocEntries} />
          </aside>

          <div className="min-w-0 flex-1 rounded-md bg-[#f6f9fc] px-3 py-6 sm:px-6">
            <div className="mx-auto flex w-full max-w-[794px] flex-col gap-6">
              {sheets.map((sheet, sheetIdx) => (
                <section
                  key={sheet[0].addr}
                  aria-label={`Pagina ${sheetIdx + 1}`}
                  className="min-h-[1123px] w-full rounded-sm bg-white px-10 py-12 text-neutral-900 shadow-stripe-standard sm:px-[94px] sm:py-[94px]"
                  style={{
                    contentVisibility: "auto",
                    containIntrinsicSize: "auto 1123px",
                  }}
                >
                  {sheet.map((block) =>
                    block.kind === "paragraph" ? (
                      <ParagraphBlockView
                        key={block.addr}
                        block={block}
                        documentId={documentId}
                        override={overrides[block.addr]}
                        onOverrideChange={setOverride}
                      />
                    ) : (
                      <TableBlockView
                        key={block.addr}
                        block={block}
                        documentId={documentId}
                        overrides={
                          tableOverrideSlices[block.addr] ?? EMPTY_OVERRIDES
                        }
                        onOverrideChange={setOverride}
                      />
                    ),
                  )}
                </section>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
