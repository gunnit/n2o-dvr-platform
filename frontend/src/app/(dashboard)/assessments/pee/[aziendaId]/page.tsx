"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2, Pencil, Plus, RotateCcw, Save, Trash2, X } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
 * PEE review (US-4.1 + US-4.2).
 *
 * Top card: PEE plan config — coordinator, punto di raccolta, vie di fuga,
 * squadra di emergenza, numeri telefonici. All persisted per-client. (US-4.1)
 *
 * Bottom: the five standard events × A-E procedures as a set of cards. Each
 * procedure is editable in place; edits persist per-client via PUT. A reset
 * action restores the global standard text after an explicit confirmation.
 * (US-4.2)
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

interface SquadraMember {
  nome: string;
  ruolo: string;
}

interface PeePlanConfig {
  coordinatore_emergenza: string | null;
  punto_raccolta: string | null;
  vie_fuga: string | null;
  tempo_evacuazione_stimato_min: number | null;
  frequenza_prove: string;
  squadra_emergenza: SquadraMember[];
  telefoni_emergenza: Record<string, string>;
}

const emptyPlan: PeePlanConfig = {
  coordinatore_emergenza: null,
  punto_raccolta: null,
  vie_fuga: null,
  tempo_evacuazione_stimato_min: null,
  frequenza_prove: "annuale",
  squadra_emergenza: [],
  telefoni_emergenza: {},
};

export default function PeeProceduresPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;
  const { apiFetch } = useApi();

  const [events, setEvents] = useState<EventoProcedure[]>([]);
  const [plan, setPlan] = useState<PeePlanConfig>(emptyPlan);
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
  // Plan card: buffer the draft so we can save it atomically and reset on
  // cancel. The backing `plan` state is the "saved" copy.
  const [planDraft, setPlanDraft] = useState<PeePlanConfig>(emptyPlan);
  const [planEditing, setPlanEditing] = useState(false);
  const [planSaving, setPlanSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [proceduresRes, planRes] = await Promise.all([
        apiFetch<EventoProcedure[]>(
          `/api/v1/aziende/${aziendaId}/pee/procedure`
        ),
        apiFetch<PeePlanConfig>(`/api/v1/aziende/${aziendaId}/pee/plan`),
      ]);
      setEvents(proceduresRes);
      setPlan(planRes);
      setPlanDraft(planRes);
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

  const startPlanEdit = () => {
    setPlanDraft(plan);
    setPlanEditing(true);
  };

  const cancelPlanEdit = () => {
    setPlanDraft(plan);
    setPlanEditing(false);
  };

  const updateSquadraMember = (index: number, patch: Partial<SquadraMember>) => {
    setPlanDraft((prev) => ({
      ...prev,
      squadra_emergenza: prev.squadra_emergenza.map((m, i) =>
        i === index ? { ...m, ...patch } : m,
      ),
    }));
  };

  const addSquadraMember = () => {
    setPlanDraft((prev) => ({
      ...prev,
      squadra_emergenza: [...prev.squadra_emergenza, { nome: "", ruolo: "" }],
    }));
  };

  const removeSquadraMember = (index: number) => {
    setPlanDraft((prev) => ({
      ...prev,
      squadra_emergenza: prev.squadra_emergenza.filter((_, i) => i !== index),
    }));
  };

  const updateTelefono = (key: string, value: string) => {
    setPlanDraft((prev) => ({
      ...prev,
      telefoni_emergenza: { ...prev.telefoni_emergenza, [key]: value },
    }));
  };

  const removeTelefono = (key: string) => {
    setPlanDraft((prev) => {
      const next = { ...prev.telefoni_emergenza };
      delete next[key];
      return { ...prev, telefoni_emergenza: next };
    });
  };

  const addTelefono = () => {
    // Start with a placeholder key so the row renders; user can rename it.
    let idx = 1;
    while (
      Object.prototype.hasOwnProperty.call(
        planDraft.telefoni_emergenza,
        `Contatto ${idx}`,
      )
    ) {
      idx += 1;
    }
    updateTelefono(`Contatto ${idx}`, "");
  };

  const savePlan = async () => {
    // Drop empty squadra rows and any empty-phone keys so we don't persist
    // junk. Cleanup matches what the backend's minimal validation expects.
    const cleanedSquadra = planDraft.squadra_emergenza.filter(
      (m) => m.nome.trim() && m.ruolo.trim(),
    );
    const cleanedTelefoni: Record<string, string> = {};
    for (const [k, v] of Object.entries(planDraft.telefoni_emergenza)) {
      if (k.trim() && v.trim()) cleanedTelefoni[k.trim()] = v.trim();
    }
    setPlanSaving(true);
    try {
      const saved = await apiFetch<PeePlanConfig>(
        `/api/v1/aziende/${aziendaId}/pee/plan`,
        {
          method: "PUT",
          body: JSON.stringify({
            coordinatore_emergenza:
              planDraft.coordinatore_emergenza?.trim() || null,
            punto_raccolta: planDraft.punto_raccolta?.trim() || null,
            vie_fuga: planDraft.vie_fuga?.trim() || null,
            tempo_evacuazione_stimato_min:
              planDraft.tempo_evacuazione_stimato_min ?? null,
            frequenza_prove: planDraft.frequenza_prove || "annuale",
            squadra_emergenza: cleanedSquadra,
            telefoni_emergenza: cleanedTelefoni,
          }),
        },
      );
      setPlan(saved);
      setPlanDraft(saved);
      setPlanEditing(false);
    } catch (err) {
      setLoadError(
        err instanceof Error
          ? err.message
          : "Salvataggio configurazione PEE non riuscito.",
      );
    } finally {
      setPlanSaving(false);
    }
  };

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
          <h1 className="type-h1">Procedure di emergenza (PEE)</h1>
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

      {/* US-4.1: PEE plan config card — coordinator, punto raccolta, vie
          fuga, squadra, numeri di emergenza. Feeds the generated .docx. */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <div>
              <CardTitle>Configurazione piano di emergenza</CardTitle>
              <CardDescription>
                Coordinatore, squadra, punto di raccolta, vie di fuga e numeri
                telefonici utilizzati al momento della generazione del PEE.
              </CardDescription>
            </div>
            {!planEditing && (
              <Button size="sm" variant="outline" onClick={startPlanEdit}>
                <Pencil className="mr-1 h-3.5 w-3.5" />
                Modifica
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Coordinatore emergenza</Label>
              {planEditing ? (
                <Input
                  value={planDraft.coordinatore_emergenza ?? ""}
                  onChange={(e) =>
                    setPlanDraft((p) => ({
                      ...p,
                      coordinatore_emergenza: e.target.value || null,
                    }))
                  }
                  placeholder="Nome e cognome"
                />
              ) : (
                <p className="text-sm text-muted-foreground">
                  {plan.coordinatore_emergenza || "—"}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label>Punto di raccolta</Label>
              {planEditing ? (
                <Input
                  value={planDraft.punto_raccolta ?? ""}
                  onChange={(e) =>
                    setPlanDraft((p) => ({
                      ...p,
                      punto_raccolta: e.target.value || null,
                    }))
                  }
                  placeholder="Es. Parcheggio esterno, lato nord"
                />
              ) : (
                <p className="text-sm text-muted-foreground">
                  {plan.punto_raccolta || "—"}
                </p>
              )}
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label>Vie di fuga</Label>
              {planEditing ? (
                <textarea
                  value={planDraft.vie_fuga ?? ""}
                  onChange={(e) =>
                    setPlanDraft((p) => ({
                      ...p,
                      vie_fuga: e.target.value || null,
                    }))
                  }
                  rows={2}
                  placeholder="Descrizione percorsi di esodo"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                />
              ) : (
                <p className="whitespace-pre-line text-sm text-muted-foreground">
                  {plan.vie_fuga || "—"}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label>Tempo evacuazione stimato (minuti)</Label>
              {planEditing ? (
                <Input
                  type="number"
                  min={0}
                  value={planDraft.tempo_evacuazione_stimato_min ?? ""}
                  onChange={(e) =>
                    setPlanDraft((p) => ({
                      ...p,
                      tempo_evacuazione_stimato_min: e.target.value
                        ? Number(e.target.value)
                        : null,
                    }))
                  }
                />
              ) : (
                <p className="text-sm text-muted-foreground">
                  {plan.tempo_evacuazione_stimato_min ?? "—"}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label>Frequenza prove</Label>
              {planEditing ? (
                <Input
                  value={planDraft.frequenza_prove}
                  onChange={(e) =>
                    setPlanDraft((p) => ({
                      ...p,
                      frequenza_prove: e.target.value,
                    }))
                  }
                  placeholder="annuale"
                />
              ) : (
                <p className="text-sm text-muted-foreground">
                  {plan.frequenza_prove}
                </p>
              )}
            </div>
          </div>

          {/* Squadra di emergenza */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Squadra di emergenza</Label>
              {planEditing && (
                <Button size="sm" variant="ghost" onClick={addSquadraMember}>
                  <Plus className="mr-1 h-3.5 w-3.5" />
                  Aggiungi membro
                </Button>
              )}
            </div>
            {(planEditing
              ? planDraft.squadra_emergenza
              : plan.squadra_emergenza
            ).length === 0 ? (
              <p className="text-xs text-muted-foreground italic">
                Nessun membro configurato.
              </p>
            ) : (
              <div className="space-y-2">
                {(planEditing
                  ? planDraft.squadra_emergenza
                  : plan.squadra_emergenza
                ).map((m, i) =>
                  planEditing ? (
                    <div key={i} className="flex gap-2">
                      <Input
                        value={m.nome}
                        onChange={(e) =>
                          updateSquadraMember(i, { nome: e.target.value })
                        }
                        placeholder="Nome e cognome"
                      />
                      <Input
                        value={m.ruolo}
                        onChange={(e) =>
                          updateSquadraMember(i, { ruolo: e.target.value })
                        }
                        placeholder="Ruolo (antincendio, primo soccorso...)"
                      />
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        onClick={() => removeSquadraMember(i)}
                        aria-label="Rimuovi"
                      >
                        <Trash2 className="h-3.5 w-3.5 text-destructive" />
                      </Button>
                    </div>
                  ) : (
                    <div
                      key={i}
                      className="flex items-center justify-between rounded-md border border-border bg-background px-3 py-1.5 text-sm"
                    >
                      <span>{m.nome}</span>
                      <Badge variant="secondary">{m.ruolo}</Badge>
                    </div>
                  ),
                )}
              </div>
            )}
          </div>

          {/* Telefoni emergenza */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Numeri telefonici di emergenza</Label>
              {planEditing && (
                <Button size="sm" variant="ghost" onClick={addTelefono}>
                  <Plus className="mr-1 h-3.5 w-3.5" />
                  Aggiungi numero
                </Button>
              )}
            </div>
            {Object.keys(
              planEditing ? planDraft.telefoni_emergenza : plan.telefoni_emergenza,
            ).length === 0 ? (
              <p className="text-xs text-muted-foreground italic">
                Nessun numero configurato (al momento della generazione verrà
                incluso almeno il Numero Unico Europeo 112).
              </p>
            ) : (
              <div className="space-y-2">
                {Object.entries(
                  planEditing
                    ? planDraft.telefoni_emergenza
                    : plan.telefoni_emergenza,
                ).map(([k, v]) =>
                  planEditing ? (
                    <div key={k} className="flex gap-2">
                      <Input
                        value={k}
                        onChange={(e) => {
                          // Renaming the key is a delete-then-add to keep
                          // React row identity sane while the user types.
                          const newKey = e.target.value;
                          setPlanDraft((prev) => {
                            const next = { ...prev.telefoni_emergenza };
                            delete next[k];
                            next[newKey] = v;
                            return { ...prev, telefoni_emergenza: next };
                          });
                        }}
                        placeholder="Ente / Ruolo"
                        className="flex-1"
                      />
                      <Input
                        value={v}
                        onChange={(e) => updateTelefono(k, e.target.value)}
                        placeholder="Numero"
                        className="flex-1"
                      />
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        onClick={() => removeTelefono(k)}
                        aria-label="Rimuovi"
                      >
                        <Trash2 className="h-3.5 w-3.5 text-destructive" />
                      </Button>
                    </div>
                  ) : (
                    <div
                      key={k}
                      className="flex items-center justify-between rounded-md border border-border bg-background px-3 py-1.5 text-sm"
                    >
                      <span className="text-muted-foreground">{k}</span>
                      <span className="font-mono">{v}</span>
                    </div>
                  ),
                )}
              </div>
            )}
          </div>
        </CardContent>
        {planEditing && (
          <CardFooter className="gap-2">
            <Button onClick={savePlan} disabled={planSaving}>
              {planSaving ? (
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="mr-1 h-3.5 w-3.5" />
              )}
              Salva configurazione
            </Button>
            <Button
              variant="ghost"
              onClick={cancelPlanEdit}
              disabled={planSaving}
            >
              <X className="mr-1 h-3.5 w-3.5" />
              Annulla
            </Button>
          </CardFooter>
        )}
      </Card>

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
