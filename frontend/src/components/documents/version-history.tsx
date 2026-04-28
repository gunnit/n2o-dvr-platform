"use client";

import { useState } from "react";
import { Download, FileText, GitCompare, History, RotateCcw, Pencil } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { Azienda, DocumentoGenerato } from "@/types";
import { apiCall, downloadFile } from "@/lib/api-client";
import { AIBadge } from "@/components/ai/ai-badge";
import { AIFilterToggle, useAIFilter } from "@/components/ai/ai-filter-context";

// Subset of the rischio shape we care about for AI tagging — keeps this
// component free of a deeper schema dependency.
interface RischioWithMisure {
  id: string;
  misure_prevenzione: string | null;
}

interface VersionHistoryProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tipoDocumento: string;
  tipoDocumentoLabel: string;
  aziendaId: string;
  aziendaLabel: string;
  // Expected to be pre-sorted with highest versione first.
  versions: DocumentoGenerato[];
  onRestored?: () => void | Promise<void>;
}

// Structured text representation of a generated .docx, returned by the
// snapshot endpoint (US-2.9). Declared locally to avoid widening the
// shared types module — only this component consumes it.
interface DocumentSnapshot {
  id: string;
  versione: number;
  generated_at: string | null;
  generated_by_name: string | null;
  paragraphs: string[];
  tables: string[][][];
}

// A single diff row: either unchanged, added (only in new), or removed
// (only in old). We render both columns side-by-side.
type DiffRow =
  | { kind: "same"; left: string; right: string }
  | { kind: "added"; left: null; right: string }
  | { kind: "removed"; left: string; right: null };

const statusLabels: Record<string, { color: string; label: string }> = {
  pending: { color: "bg-gray-100 text-gray-700", label: "In attesa" },
  generating: { color: "bg-yellow-100 text-yellow-700", label: "In generazione" },
  in_progress: { color: "bg-yellow-100 text-yellow-700", label: "In generazione" },
  ready: { color: "bg-green-100 text-green-700", label: "Pronto" },
  completed: { color: "bg-green-100 text-green-700", label: "Pronto" },
  // See documents/page.tsx for the rationale on amber — bozza is a
  // recoverable rollback state, not a hard failure.
  bozza: { color: "bg-amber-100 text-amber-800", label: "Bozza" },
  error: { color: "bg-red-100 text-red-700", label: "Errore" },
  failed: { color: "bg-red-100 text-red-700", label: "Errore" },
};

function formatItalianDateTime(iso: string): string {
  return new Date(iso).toLocaleString("it-IT", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

// Returns a short Italian summary of the delta between two versions.
// Covers elapsed time and any status transition.
function buildDiffSummary(
  current: DocumentoGenerato,
  previous: DocumentoGenerato
): string {
  const currMs = new Date(current.created_at).getTime();
  const prevMs = new Date(previous.created_at).getTime();
  const diffMs = Math.max(0, currMs - prevMs);

  const minutes = Math.round(diffMs / (1000 * 60));
  const hours = Math.round(diffMs / (1000 * 60 * 60));
  const days = Math.round(diffMs / (1000 * 60 * 60 * 24));

  let gap: string;
  if (minutes < 60) {
    gap = `${minutes} ${minutes === 1 ? "minuto" : "minuti"}`;
  } else if (hours < 48) {
    gap = `${hours} ${hours === 1 ? "ora" : "ore"}`;
  } else {
    gap = `${days} ${days === 1 ? "giorno" : "giorni"}`;
  }

  const parts = [`+${gap} da v${previous.versione}`];

  if (current.status !== previous.status) {
    const prevStatus = statusLabels[previous.status]?.label ?? previous.status;
    const currStatus = statusLabels[current.status]?.label ?? current.status;
    parts.push(`stato: ${prevStatus} -> ${currStatus}`);
  }

  return parts.join(" \u00b7 ");
}

async function triggerDownload(id: string): Promise<void> {
  try {
    await downloadFile(`/api/v1/documenti/${id}/download`);
  } catch (e) {
    toast.error((e as Error).message || "Download fallito");
  }
}

// US-5.3: build the list of known AI-originated text snippets for an
// azienda — currently the AI-drafted descrizione_attivita and any
// improvement-measure rows that came from the AI suggestion endpoint.
// Snippets shorter than MIN_AI_LEN are dropped to avoid false positives
// (a 5-character measure like "DPI" would match every paragraph).
const MIN_AI_LEN = 24;

async function fetchAITexts(aziendaId: string): Promise<string[]> {
  const [azienda, rischi] = await Promise.all([
    apiCall<Azienda>(`/api/v1/aziende/${aziendaId}`).catch(() => null),
    apiCall<RischioWithMisure[]>(`/api/v1/aziende/${aziendaId}/rischi`).catch(
      () => [] as RischioWithMisure[]
    ),
  ]);

  const out = new Set<string>();
  if (azienda?.descrizione_attivita) {
    const desc = azienda.descrizione_attivita.trim();
    if (desc.length >= MIN_AI_LEN) out.add(desc.toLowerCase());
  }
  for (const r of rischi ?? []) {
    const m = (r.misure_prevenzione ?? "").trim();
    if (m.length >= MIN_AI_LEN) out.add(m.toLowerCase());
  }
  return Array.from(out);
}

// True when `line` overlaps with any known AI snippet enough that the
// reviewer should treat it as AI-originated. We try both directions
// (line includes snippet, or snippet includes line) so generator-added
// boilerplate around a quoted AI block still flags. Matching is
// case-insensitive and ignores trivial padding.
function isAIText(line: string | null, aiTexts: string[]): boolean {
  if (!line) return false;
  const norm = line.trim().toLowerCase();
  if (norm.length < MIN_AI_LEN) return false;
  for (const snippet of aiTexts) {
    if (snippet.includes(norm) || norm.includes(snippet)) return true;
  }
  return false;
}

// Flatten a snapshot into a single ordered list of "lines". Paragraphs
// become one line each; table cells are prefixed with "[T{i} R{j} C{k}]"
// so rearranged tables surface as both a removal and an addition rather
// than silently matching across table boundaries.
function snapshotToLines(snap: DocumentSnapshot): string[] {
  const lines: string[] = [];
  for (const p of snap.paragraphs) {
    lines.push(p);
  }
  snap.tables.forEach((table, ti) => {
    table.forEach((row, ri) => {
      row.forEach((cell, ci) => {
        if (cell) lines.push(`[T${ti + 1} R${ri + 1} C${ci + 1}] ${cell}`);
      });
    });
  });
  return lines;
}

// Naive line-level diff — classic LCS-based. Keeps the component free of
// a new npm dependency. For DVR-scale docs (~2k paragraphs) this is
// O(n*m) in memory but runs client-side on demand, which is acceptable
// for a single-user review surface.
function diffLines(oldLines: string[], newLines: string[]): DiffRow[] {
  const n = oldLines.length;
  const m = newLines.length;
  // Build LCS length table.
  const dp: number[][] = Array.from({ length: n + 1 }, () =>
    new Array<number>(m + 1).fill(0)
  );
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      if (oldLines[i] === newLines[j]) {
        dp[i][j] = dp[i + 1][j + 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
  }
  // Walk the table to emit the diff.
  const out: DiffRow[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (oldLines[i] === newLines[j]) {
      out.push({ kind: "same", left: oldLines[i], right: newLines[j] });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      out.push({ kind: "removed", left: oldLines[i], right: null });
      i++;
    } else {
      out.push({ kind: "added", left: null, right: newLines[j] });
      j++;
    }
  }
  while (i < n) {
    out.push({ kind: "removed", left: oldLines[i++], right: null });
  }
  while (j < m) {
    out.push({ kind: "added", left: null, right: newLines[j++] });
  }
  return out;
}

export function VersionHistory({
  open,
  onOpenChange,
  tipoDocumentoLabel,
  aziendaId,
  aziendaLabel,
  versions,
  onRestored,
}: VersionHistoryProps) {
  const latestVersione = versions[0]?.versione;

  const [diffOpen, setDiffOpen] = useState(false);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffError, setDiffError] = useState<string | null>(null);
  const [diffTitle, setDiffTitle] = useState<string>("");
  const [diffRows, setDiffRows] = useState<DiffRow[]>([]);
  const [restoringId, setRestoringId] = useState<string | null>(null);
  // US-5.3: known AI-originated text snippets for the current azienda.
  // Cached for the lifetime of the component so flipping between
  // adjacent version comparisons does not refetch.
  const [aiTexts, setAITexts] = useState<string[] | null>(null);

  // US-5.3: subscribe to the global AI filter so the diff table can dim
  // non-AI rows when the operator activates "Mostra solo contenuto AI"
  // from the header (or the dialog-local toggle).
  const { active: aiFilterActive } = useAIFilter();

  async function handleCompareWithPrevious(
    current: DocumentoGenerato,
    previous: DocumentoGenerato
  ): Promise<void> {
    setDiffOpen(true);
    setDiffLoading(true);
    setDiffError(null);
    setDiffRows([]);
    setDiffTitle(`Differenze: v${previous.versione} vs v${current.versione}`);
    try {
      const aiPromise =
        aiTexts === null ? fetchAITexts(aziendaId) : Promise.resolve(aiTexts);
      const [oldSnap, newSnap, aiList] = await Promise.all([
        apiCall<DocumentSnapshot>(
          `/api/v1/aziende/${aziendaId}/documents/${previous.id}/snapshot`
        ),
        apiCall<DocumentSnapshot>(
          `/api/v1/aziende/${aziendaId}/documents/${current.id}/snapshot`
        ),
        aiPromise,
      ]);
      if (aiTexts === null) setAITexts(aiList);
      const rows = diffLines(snapshotToLines(oldSnap), snapshotToLines(newSnap));
      setDiffRows(rows);
    } catch (e) {
      setDiffError(
        (e as Error).message ||
          "Impossibile caricare gli snapshot per il confronto"
      );
    } finally {
      setDiffLoading(false);
    }
  }

  async function handleRestore(version: DocumentoGenerato): Promise<void> {
    setRestoringId(version.id);
    try {
      const restored = await apiCall<DocumentoGenerato>(
        `/api/v1/aziende/${aziendaId}/documents/${version.id}/restore`,
        { method: "POST" }
      );
      toast.success(`Ripristinata come v${restored.versione}`);
      if (onRestored) await onRestored();
    } catch (e) {
      toast.error((e as Error).message || "Ripristino fallito");
    } finally {
      setRestoringId(null);
    }
  }

  const addedCount = diffRows.filter((r) => r.kind === "added").length;
  const removedCount = diffRows.filter((r) => r.kind === "removed").length;
  // US-5.3: precompute per-row AI flag once so the renderer doesn't
  // re-scan the snippet list on every cell. Both sides count — if the
  // old or new side carried AI text, the row is an AI row.
  const aiList = aiTexts ?? [];
  const rowIsAI = diffRows.map(
    (r) => isAIText(r.left, aiList) || isAIText(r.right, aiList)
  );
  const aiRowCount = rowIsAI.filter(Boolean).length;

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent side="right" className="w-full sm:max-w-xl">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <History className="h-4 w-4 text-muted-foreground" />
              Cronologia versioni &mdash; {tipoDocumentoLabel}
            </SheetTitle>
            <SheetDescription>{aziendaLabel}</SheetDescription>
          </SheetHeader>

          <Separator />

          <div className="flex-1 overflow-y-auto px-4 pb-6">
            {versions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <FileText className="mb-3 h-10 w-10 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  Nessuna versione disponibile per questo documento.
                </p>
              </div>
            ) : (
              <ol className="relative space-y-5 border-l border-border pl-5">
                {versions.map((version, idx) => {
                  const isCurrent = version.versione === latestVersione;
                  const statusInfo =
                    statusLabels[version.status] ?? {
                      color: "bg-gray-100 text-gray-700",
                      label: version.status,
                    };
                  const previous = versions[idx + 1];
                  const diffSummary = previous
                    ? buildDiffSummary(version, previous)
                    : null;
                  const canCompare =
                    !!previous &&
                    !!version.file_path &&
                    !!previous.file_path &&
                    (version.status === "completed" ||
                      version.status === "ready") &&
                    (previous.status === "completed" ||
                      previous.status === "ready");
                  const canRestore =
                    !isCurrent &&
                    !!version.file_path &&
                    (version.status === "completed" ||
                      version.status === "ready");

                  return (
                    <li key={version.id} className="relative">
                      <span
                        className={
                          "absolute -left-[29px] top-1.5 flex h-4 w-4 items-center justify-center rounded-full border-2 border-background " +
                          (isCurrent ? "bg-primary" : "bg-muted")
                        }
                        aria-hidden
                      />
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge
                            className={
                              isCurrent
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted text-muted-foreground"
                            }
                          >
                            v{version.versione}
                          </Badge>
                          <Badge className={statusInfo.color}>
                            {statusInfo.label}
                          </Badge>
                          {isCurrent && (
                            <span className="text-xs font-medium text-primary">
                              Versione corrente
                            </span>
                          )}
                          {/* Distinguish human-edited versions (synced from
                              Google Docs) from the AI-generated originals.
                              Reviewers reviewing a run need to know at a
                              glance which versions had hand corrections. */}
                          {version.edited_in_gdocs && (
                            <Badge
                              className="bg-[rgba(66,100,251,0.1)] text-[#2e48b0] border border-[rgba(66,100,251,0.3)]"
                              title="Versione importata dopo modifiche in Google Docs"
                            >
                              <Pencil className="mr-1 h-2.5 w-2.5" />
                              Modificato in Google Docs
                            </Badge>
                          )}
                        </div>

                        <p className="text-xs text-muted-foreground">
                          Creato il {formatItalianDateTime(version.created_at)}
                          {version.generated_by_name
                            ? ` da ${version.generated_by_name}`
                            : ""}
                        </p>

                        {diffSummary && (
                          <p className="text-xs text-muted-foreground">
                            {diffSummary}
                          </p>
                        )}

                        {version.status === "bozza" && version.error_message && (
                          <p className="text-xs text-amber-700 dark:text-amber-400">
                            {version.error_message}
                          </p>
                        )}

                        <div className="flex flex-wrap gap-2 pt-1">
                          {(version.status === "ready" ||
                            version.status === "completed") &&
                            version.file_path && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  void triggerDownload(version.id);
                                }}
                              >
                                <Download className="mr-1.5 h-3 w-3" />
                                Scarica
                              </Button>
                            )}
                          {canCompare && previous && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                void handleCompareWithPrevious(version, previous);
                              }}
                            >
                              <GitCompare className="mr-1.5 h-3 w-3" />
                              Confronta con precedente
                            </Button>
                          )}
                          {canRestore && (
                            <Button
                              size="sm"
                              variant="ghost"
                              disabled={restoringId === version.id}
                              onClick={() => {
                                void handleRestore(version);
                              }}
                            >
                              <RotateCcw className="mr-1.5 h-3 w-3" />
                              {restoringId === version.id
                                ? "Ripristino..."
                                : "Ripristina"}
                            </Button>
                          )}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ol>
            )}
          </div>
        </SheetContent>
      </Sheet>

      <Dialog open={diffOpen} onOpenChange={setDiffOpen}>
        <DialogContent className="max-w-[min(1100px,calc(100%-2rem))] sm:max-w-[min(1100px,calc(100%-2rem))]">
          <DialogHeader>
            <DialogTitle>{diffTitle}</DialogTitle>
            <DialogDescription>
              {diffLoading
                ? "Caricamento snapshot..."
                : diffError
                ? diffError
                : `${addedCount} righe aggiunte, ${removedCount} righe rimosse${
                    aiRowCount > 0
                      ? ` - ${aiRowCount} ${
                          aiRowCount === 1 ? "sezione" : "sezioni"
                        } generata da AI`
                      : ""
                  }`}
            </DialogDescription>
            {/* US-5.3 AC3: in-dialog mirror of the global AI filter so
                the operator can dim non-AI paragraphs without leaving
                the diff view. */}
            {!diffLoading && !diffError && aiRowCount > 0 && (
              <div className="flex items-center justify-end pt-1">
                <AIFilterToggle />
              </div>
            )}
          </DialogHeader>

          <div className="max-h-[65vh] overflow-auto rounded-md border">
            {diffLoading ? (
              <div className="p-6 text-center text-sm text-muted-foreground">
                Caricamento...
              </div>
            ) : diffError ? (
              <div className="p-6 text-center text-sm text-red-600">
                {diffError}
              </div>
            ) : diffRows.length === 0 ? (
              <div className="p-6 text-center text-sm text-muted-foreground">
                Nessuna differenza rilevata.
              </div>
            ) : (
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-muted">
                  <tr>
                    <th className="w-1/2 border-b px-2 py-1.5 text-left font-medium">
                      Precedente
                    </th>
                    <th className="w-1/2 border-b px-2 py-1.5 text-left font-medium">
                      Nuovo
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {diffRows.map((row, i) => {
                    const isAI = rowIsAI[i];
                    // US-5.3 AC1: AI sections get a subtle violet tint
                    // overlay on top of the diff add/remove colour, plus
                    // a small AI badge in the leading non-empty cell so
                    // the reviewer knows which paragraphs the AI wrote.
                    // AC3: when the global AI filter is active, non-AI
                    // rows are dimmed and made non-interactive.
                    const dimmed = aiFilterActive && !isAI;
                    return (
                      <tr
                        key={i}
                        data-ai-block={isAI ? "ai" : "non-ai"}
                        className={
                          "align-top transition-opacity " +
                          (isAI ? "ring-1 ring-inset ring-violet-200 " : "") +
                          (dimmed ? "pointer-events-none opacity-40 " : "")
                        }
                      >
                        <td
                          className={
                            "whitespace-pre-wrap break-words border-b px-2 py-1 " +
                            (isAI ? "bg-violet-100 " : "") +
                            (row.kind === "removed"
                              ? "bg-red-50 text-red-900"
                              : "")
                          }
                        >
                          {isAI && row.left && (
                            <AIBadge
                              provenance="ai"
                              size="xs"
                              className="mb-1 mr-1"
                            />
                          )}
                          {row.left ?? ""}
                        </td>
                        <td
                          className={
                            "whitespace-pre-wrap break-words border-b px-2 py-1 " +
                            (isAI ? "bg-violet-100 " : "") +
                            (row.kind === "added"
                              ? "bg-green-50 text-green-900"
                              : "")
                          }
                        >
                          {isAI && row.right && !row.left && (
                            <AIBadge
                              provenance="ai"
                              size="xs"
                              className="mb-1 mr-1"
                            />
                          )}
                          {row.right ?? ""}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
