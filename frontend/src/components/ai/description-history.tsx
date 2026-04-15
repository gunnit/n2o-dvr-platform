"use client";

import { useEffect, useState } from "react";
import { Loader2, RotateCcw, Sparkles, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";

/**
 * Per-azienda revision history of the company description (US-2.1 AC2).
 *
 * Renders newest-first list of every AI generation + every manual save.
 * Each row exposes a "Ripristina" button that snapshots a fresh manual
 * revision server-side (mirrors the US-2.9 document restore semantics —
 * restoring never destroys existing history).
 *
 * Designed as a self-contained inline panel so it can sit next to the
 * `<DescriptionEditor>` without pulling in a Sheet/Drawer dependency.
 */

export interface DescriptionRevision {
  id: string;
  azienda_id: string;
  source: "ai" | "manual" | string;
  content: string;
  generated_by: string | null;
  generated_by_name: string | null;
  created_at: string;
}

interface DescriptionHistoryProps {
  aziendaId: string;
  /** Bumped by the parent every time a new revision is created so the list
   *  refetches without needing a separate websocket / polling layer. */
  refreshKey?: number;
  /** Called when the user restores a revision — the parent should sync
   *  the editor's value with the returned descrizione. */
  onRestore: (descrizione: string) => void;
}

function formatTs(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function preview(content: string, max = 180): string {
  const trimmed = content.trim().replace(/\s+/g, " ");
  if (trimmed.length <= max) return trimmed;
  return trimmed.slice(0, max).trimEnd() + "…";
}

export function DescriptionHistory({
  aziendaId,
  refreshKey = 0,
  onRestore,
}: DescriptionHistoryProps) {
  const { apiFetch } = useApi();
  const [revisions, setRevisions] = useState<DescriptionRevision[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [restoringId, setRestoringId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiFetch<DescriptionRevision[]>(
      `/api/v1/aziende/${aziendaId}/description-revisions`
    )
      .then((rows) => {
        if (!cancelled) setRevisions(rows);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Errore caricamento");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [aziendaId, open, refreshKey, apiFetch]);

  const handleRestore = async (rev: DescriptionRevision) => {
    if (
      !window.confirm(
        "Ripristinare questa revisione? La descrizione corrente sara' sostituita ma resta nella cronologia."
      )
    )
      return;
    setRestoringId(rev.id);
    try {
      const out = await apiFetch<{
        descrizione_attivita: string;
        revision: DescriptionRevision;
      }>(
        `/api/v1/aziende/${aziendaId}/description-revisions/${rev.id}/restore`,
        { method: "POST" }
      );
      onRestore(out.descrizione_attivita);
      // Optimistic prepend so the user immediately sees the new manual row.
      setRevisions((prev) => [out.revision, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ripristino fallito");
    } finally {
      setRestoringId(null);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          {open ? "Nascondi cronologia" : "Mostra cronologia descrizione"}
        </button>
        {open && revisions.length > 0 && (
          <span className="text-xs text-muted-foreground">
            {revisions.length} revision{revisions.length === 1 ? "e" : "i"}
          </span>
        )}
      </div>

      {open && (
        <div className="rounded-md border border-input bg-muted/30 p-2">
          {loading && (
            <div className="flex items-center justify-center py-4 text-xs text-muted-foreground">
              <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
              Caricamento cronologia...
            </div>
          )}
          {error && (
            <p className="px-2 py-1 text-xs text-destructive">{error}</p>
          )}
          {!loading && !error && revisions.length === 0 && (
            <p className="px-2 py-3 text-center text-xs text-muted-foreground">
              Nessuna revisione registrata. Le modifiche future saranno tracciate.
            </p>
          )}
          {!loading && !error && revisions.length > 0 && (
            <ul className="divide-y divide-border/60">
              {revisions.map((rev) => (
                <li
                  key={rev.id}
                  className="flex items-start gap-3 px-2 py-2.5"
                >
                  <span
                    className={
                      "mt-0.5 inline-flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full " +
                      (rev.source === "ai"
                        ? "bg-violet-100 text-violet-700"
                        : "bg-slate-100 text-slate-700")
                    }
                    aria-hidden
                  >
                    {rev.source === "ai" ? (
                      <Sparkles className="h-3 w-3" />
                    ) : (
                      <User className="h-3 w-3" />
                    )}
                  </span>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>
                        {rev.source === "ai" ? "AI" : "Manuale"} ·{" "}
                        {formatTs(rev.created_at)}
                      </span>
                      {rev.generated_by_name && (
                        <span className="text-muted-foreground/80">
                          · {rev.generated_by_name}
                        </span>
                      )}
                    </div>
                    <p className="text-xs leading-snug text-foreground">
                      {preview(rev.content)}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs"
                    onClick={() => handleRestore(rev)}
                    disabled={restoringId === rev.id}
                  >
                    {restoringId === rev.id ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <>
                        <RotateCcw className="mr-1 h-3 w-3" />
                        Ripristina
                      </>
                    )}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
