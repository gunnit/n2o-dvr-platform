"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2, Pencil, RotateCcw, Save, X } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useApi } from "@/hooks/use-api";
import { cn } from "@/lib/utils";

/**
 * PEE emergency procedures review (US-4.2).
 *
 * Shows the five standard events × A-E procedures as a set of cards. Each
 * procedure is editable in place; edits persist per-client via PUT. A reset
 * action restores the global standard text after an explicit confirmation,
 * matching AC3.
 */

interface Procedura {
  lettera: string;
  titolo: string;
  testo: string;
  personalizzata: boolean;
}

interface EventoProcedure {
  codice: string;
  titolo: string;
  procedure: Procedura[];
}

export default function PeeProceduresPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;
  const { apiFetch } = useApi();

  const [events, setEvents] = useState<EventoProcedure[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [editKey, setEditKey] = useState<string | null>(null);
  const [draftText, setDraftText] = useState("");
  const [saving, setSaving] = useState<string | null>(null);
  const [resetTarget, setResetTarget] = useState<{
    codice: string;
    titolo: string;
    lettera: string;
  } | null>(null);
  const [resetting, setResetting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const res = await apiFetch<EventoProcedure[]>(
        `/api/v1/aziende/${aziendaId}/pee/procedure`
      );
      setEvents(res);
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : "Caricamento procedure non riuscito."
      );
    } finally {
      setLoading(false);
    }
  }, [aziendaId, apiFetch]);

  useEffect(() => {
    load();
  }, [load]);

  const key = (codice: string, lettera: string) => `${codice}:${lettera}`;

  const startEdit = (codice: string, proc: Procedura) => {
    setEditKey(key(codice, proc.lettera));
    setDraftText(proc.testo);
  };

  const cancelEdit = () => {
    setEditKey(null);
    setDraftText("");
  };

  const saveEdit = async (codice: string, lettera: string) => {
    if (!draftText.trim()) return;
    setSaving(key(codice, lettera));
    try {
      const updated = await apiFetch<Procedura>(
        `/api/v1/aziende/${aziendaId}/pee/procedure/${codice}/${lettera}`,
        {
          method: "PUT",
          body: JSON.stringify({ testo: draftText.trim() }),
        }
      );
      setEvents((prev) =>
        prev.map((e) =>
          e.codice !== codice
            ? e
            : {
                ...e,
                procedure: e.procedure.map((p) =>
                  p.lettera === lettera ? updated : p
                ),
              }
        )
      );
      cancelEdit();
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : "Salvataggio non riuscito."
      );
    } finally {
      setSaving(null);
    }
  };

  const confirmReset = async () => {
    if (!resetTarget) return;
    setResetting(true);
    try {
      const restored = await apiFetch<Procedura>(
        `/api/v1/aziende/${aziendaId}/pee/procedure/${resetTarget.codice}/${resetTarget.lettera}`,
        { method: "DELETE" }
      );
      setEvents((prev) =>
        prev.map((e) =>
          e.codice !== resetTarget.codice
            ? e
            : {
                ...e,
                procedure: e.procedure.map((p) =>
                  p.lettera === resetTarget.lettera ? restored : p
                ),
              }
        )
      );
      setResetTarget(null);
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : "Ripristino non riuscito."
      );
    } finally {
      setResetting(false);
    }
  };

  const customCount = events.reduce(
    (sum, e) => sum + e.procedure.filter((p) => p.personalizzata).length,
    0
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Procedure di emergenza (PEE)</h1>
          <p className="text-sm text-muted-foreground">
            Cinque scenari, cinque fasi A-E ciascuno. Modifica i testi dove serve
            — le modifiche vengono salvate solo per questa azienda. Il pulsante
            &quot;Ripristina standard&quot; riporta al testo predefinito.
          </p>
        </div>
        {customCount > 0 && (
          <Badge
            variant="secondary"
            className="bg-sky-100 text-sky-800 hover:bg-sky-100"
          >
            {customCount} personalizzata{customCount === 1 ? "" : "e"}
          </Badge>
        )}
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Caricamento procedure...
        </div>
      )}

      {loadError && !loading && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {loadError}
        </div>
      )}

      <div className="space-y-4">
        {events.map((evt) => (
          <Card key={evt.codice}>
            <CardHeader>
              <CardTitle>{evt.titolo}</CardTitle>
              <CardDescription>
                Procedure standard A-E per lo scenario &quot;{evt.titolo.toLowerCase()}&quot;.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {evt.procedure.map((proc) => {
                const rowKey = key(evt.codice, proc.lettera);
                const isEditing = editKey === rowKey;
                const isSaving = saving === rowKey;
                return (
                  <div
                    key={proc.lettera}
                    className={cn(
                      "rounded-md border p-3",
                      proc.personalizzata
                        ? "border-sky-300 bg-sky-50/50"
                        : "border-border bg-background"
                    )}
                  >
                    <div className="mb-2 flex items-center gap-2">
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-semibold">
                        {proc.lettera}
                      </span>
                      <span className="text-sm font-medium">{proc.titolo}</span>
                      {proc.personalizzata && (
                        <Badge
                          variant="secondary"
                          className="bg-sky-100 text-sky-800 hover:bg-sky-100 text-[11px]"
                        >
                          Personalizzata
                        </Badge>
                      )}
                    </div>
                    {isEditing ? (
                      <div className="space-y-2">
                        <textarea
                          value={draftText}
                          onChange={(e) => setDraftText(e.target.value)}
                          rows={4}
                          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                        />
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => saveEdit(evt.codice, proc.lettera)}
                            disabled={isSaving || !draftText.trim()}
                          >
                            {isSaving ? (
                              <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Save className="mr-1 h-3.5 w-3.5" />
                            )}
                            Salva
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={cancelEdit}
                            disabled={isSaving}
                          >
                            <X className="mr-1 h-3.5 w-3.5" />
                            Annulla
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <p className="whitespace-pre-line text-sm text-muted-foreground">
                          {proc.testo}
                        </p>
                        <div className="mt-2 flex gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => startEdit(evt.codice, proc)}
                          >
                            <Pencil className="mr-1 h-3.5 w-3.5" />
                            Modifica
                          </Button>
                          {proc.personalizzata && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() =>
                                setResetTarget({
                                  codice: evt.codice,
                                  titolo: evt.titolo,
                                  lettera: proc.lettera,
                                })
                              }
                            >
                              <RotateCcw className="mr-1 h-3.5 w-3.5" />
                              Ripristina standard
                            </Button>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog
        open={resetTarget !== null}
        onOpenChange={(o) => !o && setResetTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ripristinare la procedura standard?</DialogTitle>
            <DialogDescription>
              Il testo personalizzato per{" "}
              <strong>
                {resetTarget?.titolo} — procedura {resetTarget?.lettera}
              </strong>{" "}
              verra&apos; sostituito dal testo predefinito. L&apos;azione
              riguarda solo questa azienda e non puo&apos; essere annullata.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setResetTarget(null)}
              disabled={resetting}
            >
              Annulla
            </Button>
            <Button onClick={confirmReset} disabled={resetting}>
              {resetting ? (
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              ) : (
                <RotateCcw className="mr-1 h-3.5 w-3.5" />
              )}
              Ripristina
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
