"use client";

import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  Check,
  Download,
  Loader2,
  Save,
} from "lucide-react";

import { documentTypeLabel } from "@/components/documents/document-types";
import type { OverrideSaveState } from "@/components/documents/editor/use-document-overrides";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatRelative } from "@/lib/ui/relative-time";
import type { DocumentPreviewResponse } from "@/types";

function SaveIndicator({
  saveState,
  onRetry,
}: {
  saveState: OverrideSaveState;
  onRetry: () => void;
}) {
  if (saveState === "saving") {
    return (
      <span
        role="status"
        className="inline-flex items-center gap-1.5 text-[12px] text-[#64748d]"
      >
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Salvataggio…
      </span>
    );
  }
  if (saveState === "saved") {
    return (
      <span
        role="status"
        className="inline-flex items-center gap-1.5 text-[12px] text-[#108c3d]"
      >
        <Check className="h-3.5 w-3.5" strokeWidth={2} />
        Modifiche salvate
      </span>
    );
  }
  if (saveState === "error") {
    return (
      <span
        role="alert"
        className="inline-flex items-center gap-1.5 text-[12px] text-[#b51648]"
      >
        <AlertCircle className="h-3.5 w-3.5" strokeWidth={2} />
        Salvataggio non riuscito
        <button
          type="button"
          onClick={onRetry}
          className="font-medium underline underline-offset-2 transition-colors hover:text-[#8f1038]"
        >
          Riprova
        </button>
      </span>
    );
  }
  return null;
}

export interface EditorHeaderProps {
  preview: DocumentPreviewResponse;
  saveState: OverrideSaveState;
  /** Number of blocks currently carrying an override. */
  editedCount: number;
  onRetrySave: () => void;
  onDownload: () => void;
  downloading: boolean;
  onSaveVersion: () => void;
  savingVersion: boolean;
}

export function EditorHeader({
  preview,
  saveState,
  editedCount,
  onRetrySave,
  onDownload,
  downloading,
  onSaveVersion,
  savingVersion,
}: EditorHeaderProps) {
  const canSaveVersion = editedCount > 0 && !savingVersion;

  return (
    // Bleeds into the dashboard shell's px-8/py-8 padding so the bar spans
    // the full content column and sticks to the very top of the viewport.
    <div className="sticky top-0 z-30 -mx-8 -mt-8 border-b border-[#e5edf5] bg-white/95 px-8 py-3 backdrop-blur-sm">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Link
          href="/documents"
          className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#64748d] transition-colors hover:text-[#061b31]"
        >
          <ArrowLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Documenti
        </Link>
        <span aria-hidden className="hidden h-5 w-px bg-[#e5edf5] sm:block" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="truncate font-heading text-[16px] font-semibold tracking-[-0.01em] text-[#061b31]">
              {documentTypeLabel(preview.tipo_documento)}
            </h1>
            <Badge variant="secondary" className="tnum shrink-0">
              v{preview.versione}
            </Badge>
            {editedCount > 0 && (
              <Badge className="tnum shrink-0">
                {editedCount}{" "}
                {editedCount === 1 ? "blocco modificato" : "blocchi modificati"}
              </Badge>
            )}
          </div>
          <p className="truncate text-[12px] text-[#64748d]">
            {preview.azienda_nome}
            {preview.generated_at
              ? ` · generato ${formatRelative(preview.generated_at)}`
              : ""}
          </p>
        </div>
        <SaveIndicator saveState={saveState} onRetry={onRetrySave} />
        <div className="flex shrink-0 items-center gap-2">
          {/* Disabled buttons swallow pointer events, so the tooltip lives
              on a wrapper span. */}
          <span
            className="inline-flex"
            title={
              editedCount === 0 ? "Nessuna modifica da salvare" : undefined
            }
          >
            <Button
              size="sm"
              variant="outline"
              onClick={onSaveVersion}
              disabled={!canSaveVersion}
            >
              {savingVersion ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Save strokeWidth={1.75} />
              )}
              Salva come nuova versione
            </Button>
          </span>
          <Button size="sm" onClick={onDownload} disabled={downloading}>
            {downloading ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Download strokeWidth={1.75} />
            )}
            Scarica .docx
          </Button>
        </div>
      </div>
    </div>
  );
}
