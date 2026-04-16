"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  ChevronDown,
  ChevronUp,
  Loader2,
  Plus,
  RefreshCcw,
  Save,
  Trash2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useApi } from "@/hooks/use-api";
import { cn } from "@/lib/utils";

/**
 * HACCP config review (US-4.3).
 *
 * Top card: client config (activity-type selector, numero pasti/giorno,
 * responsabile HACCP, tipi alimenti). Selecting an activity pre-loads CCPs
 * via `POST /regenerate-ccps` the first time (AC1) and opens a merge/replace
 * dialog on subsequent swaps (AC3 "edit-then-merge").
 *
 * Middle card: CCP table — codice, nome, limite critico inline. Each row
 * expands into a detailed editor for pericolo / monitoraggio / azione
 * correttiva / frequenza. Customs can be added/deleted.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Ccp {
  codice: string;
  nome: string;
  fase: string;
  pericolo: string;
  limite_critico: string;
  monitoraggio: string;
  azione_correttiva: string;
  frequenza: string;
}

interface HaccpConfig {
  id: string;
  azienda_id: string;
  tipologia_attivita: string | null;
  numero_pasti_giorno: number | null;
  tipi_alimenti_trattati: string[];
  responsabile_haccp: string | null;
  note: string | null;
  ccps: Ccp[];
  created_at: string;
  updated_at: string;
}

interface ActivityTypeCatalogItem {
  slug: string;
  nome: string;
  descrizione: string;
  ccp_count: number;
}

const EMPTY_CCP: Ccp = {
  codice: "",
  nome: "",
  fase: "",
  pericolo: "",
  limite_critico: "",
  monitoraggio: "",
  azione_correttiva: "",
  frequenza: "",
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function HaccpAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;
  const { apiFetch, isAuthenticated } = useApi();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const [activityTypes, setActivityTypes] = useState<ActivityTypeCatalogItem[]>(
    [],
  );
  // Local form state — Save is explicit; we don't mirror the server row back
  // into a separate `config` state because all surface-visible fields live
  // in the controlled inputs below.
  const [tipologia, setTipologia] = useState<string>("");
  const [numeroPasti, setNumeroPasti] = useState<string>("");
  const [responsabile, setResponsabile] = useState<string>("");
  const [tipiAlimenti, setTipiAlimenti] = useState<string>(""); // comma-separated in UI
  const [ccps, setCcps] = useState<Ccp[]>([]);
  const [expandedCodice, setExpandedCodice] = useState<string | null>(null);

  const [dirty, setDirty] = useState(false);
  const [regenDialog, setRegenDialog] = useState<{
    open: boolean;
    // Pending activity slug the operator picked in the dropdown — held
    // until they confirm replace/merge so we don't clobber edits.
    pendingSlug: string | null;
  }>({ open: false, pendingSlug: null });

  // -------------------------------------------------------------------------
  // Load config + catalog
  // -------------------------------------------------------------------------

  const loadAll = useCallback(async () => {
    if (!aziendaId || !isAuthenticated) return;
    setLoading(true);
    setError(null);
    try {
      const catalog = await apiFetch<{ items: ActivityTypeCatalogItem[] }>(
        "/api/v1/haccp/_meta/activity-types",
      );
      setActivityTypes(catalog.items);

      try {
        const cfg = await apiFetch<HaccpConfig>(
          `/api/v1/aziende/${aziendaId}/haccp/config`,
        );
        setTipologia(cfg.tipologia_attivita ?? "");
        setNumeroPasti(
          cfg.numero_pasti_giorno != null
            ? String(cfg.numero_pasti_giorno)
            : "",
        );
        setResponsabile(cfg.responsabile_haccp ?? "");
        setTipiAlimenti((cfg.tipi_alimenti_trattati ?? []).join(", "));
        setCcps(cfg.ccps ?? []);
        setDirty(false);
      } catch {
        // 404 = config not yet created; start blank.
        setTipologia("");
        setNumeroPasti("");
        setResponsabile("");
        setTipiAlimenti("");
        setCcps([]);
        setDirty(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore caricamento");
    } finally {
      setLoading(false);
    }
  }, [apiFetch, aziendaId, isAuthenticated]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------

  const markDirty = () => setDirty(true);

  const handleActivityChange = (newSlug: string) => {
    // AC3: if the operator already has CCPs (whether seeded or edited) and
    // switches activity, show the merge-vs-replace dialog before touching
    // anything.
    if (ccps.length > 0 && tipologia && newSlug && newSlug !== tipologia) {
      setRegenDialog({ open: true, pendingSlug: newSlug });
      return;
    }
    setTipologia(newSlug);
    markDirty();
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setToast(null);
    try {
      const body = {
        tipologia_attivita: tipologia || null,
        numero_pasti_giorno: numeroPasti ? Number(numeroPasti) : null,
        responsabile_haccp: responsabile || null,
        tipi_alimenti_trattati: tipiAlimenti
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        note: null,
        ccps,
      };
      const saved = await apiFetch<HaccpConfig>(
        `/api/v1/aziende/${aziendaId}/haccp/config`,
        {
          method: "PUT",
          body: JSON.stringify(body),
        },
      );
      setCcps(saved.ccps ?? []);
      setTipologia(saved.tipologia_attivita ?? "");
      setDirty(false);
      setToast("Configurazione salvata");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Errore nel salvataggio",
      );
    } finally {
      setSaving(false);
    }
  };

  const runRegenerate = async (strategy: "merge" | "replace") => {
    // If the operator picked a new activity type in the dropdown but didn't
    // save yet, we need to PUT that first so the backend knows which slug
    // to regenerate for.
    const pending = regenDialog.pendingSlug;
    setRegenerating(true);
    setError(null);
    setToast(null);
    try {
      if (pending) {
        await apiFetch<HaccpConfig>(
          `/api/v1/aziende/${aziendaId}/haccp/config`,
          {
            method: "PUT",
            body: JSON.stringify({
              tipologia_attivita: pending,
              numero_pasti_giorno: numeroPasti ? Number(numeroPasti) : null,
              responsabile_haccp: responsabile || null,
              tipi_alimenti_trattati: tipiAlimenti
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
              note: null,
              // Keep the existing CCPs so the merge call can diff against
              // them — backend doesn't overwrite when we send non-empty.
              ccps,
            }),
          },
        );
      }

      const resp = await apiFetch<{
        ccps: Ccp[];
        preserved_codici: string[];
        strategy: string;
        tipologia_attivita: string | null;
      }>(`/api/v1/aziende/${aziendaId}/haccp/config/regenerate-ccps`, {
        method: "POST",
        body: JSON.stringify({ strategy }),
      });

      setCcps(resp.ccps);
      if (pending) setTipologia(pending);
      setDirty(false);
      setRegenDialog({ open: false, pendingSlug: null });

      if (strategy === "merge") {
        if (resp.preserved_codici.length > 0) {
          setToast(
            `${resp.preserved_codici.length} CCP personalizzati mantenuti (${resp.preserved_codici.join(", ")})`,
          );
        } else {
          setToast("CCP aggiornati dal catalogo di default");
        }
      } else {
        setToast(`${resp.ccps.length} CCP ricaricati dai default`);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Errore durante la rigenerazione",
      );
    } finally {
      setRegenerating(false);
    }
  };

  const updateCcp = (index: number, patch: Partial<Ccp>) => {
    setCcps((prev) =>
      prev.map((c, i) => (i === index ? { ...c, ...patch } : c)),
    );
    markDirty();
  };

  const deleteCcp = (index: number) => {
    setCcps((prev) => prev.filter((_, i) => i !== index));
    markDirty();
  };

  const addCustomCcp = () => {
    const used = new Set(ccps.map((c) => c.codice));
    let n = 1;
    while (used.has(`CUSTOM${n}`)) n += 1;
    setCcps((prev) => [
      ...prev,
      { ...EMPTY_CCP, codice: `CUSTOM${n}`, nome: "Nuovo CCP personalizzato" },
    ]);
    setExpandedCodice(`CUSTOM${n}`);
    markDirty();
  };

  // -------------------------------------------------------------------------
  // Derived
  // -------------------------------------------------------------------------

  const selectedActivity = useMemo(
    () => activityTypes.find((a) => a.slug === tipologia) ?? null,
    [activityTypes, tipologia],
  );

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          HACCP — Configurazione & CCP
        </h1>
        <p className="text-sm text-muted-foreground">
          Tipologia attivita, responsabile e punti critici di controllo per la
          generazione del manuale HACCP.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      )}
      {toast && (
        <div className="rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-300">
          {toast}
        </div>
      )}

      {/* Config card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configurazione attivita</CardTitle>
          <CardDescription>
            Selezionando la tipologia si caricano i CCP standard per quella
            tipologia di attivita alimentare.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="tipologia">Tipologia attivita</Label>
            <select
              id="tipologia"
              value={tipologia}
              onChange={(e) => handleActivityChange(e.target.value)}
              className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm"
            >
              <option value="">-- Seleziona --</option>
              {activityTypes.map((a) => (
                <option key={a.slug} value={a.slug}>
                  {a.nome} ({a.ccp_count} CCP)
                </option>
              ))}
            </select>
            {selectedActivity && (
              <p className="text-xs text-muted-foreground">
                {selectedActivity.descrizione}
              </p>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="pasti">Numero pasti / giorno</Label>
              <Input
                id="pasti"
                type="number"
                min={0}
                value={numeroPasti}
                onChange={(e) => {
                  setNumeroPasti(e.target.value);
                  markDirty();
                }}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="responsabile">Responsabile HACCP</Label>
              <Input
                id="responsabile"
                value={responsabile}
                onChange={(e) => {
                  setResponsabile(e.target.value);
                  markDirty();
                }}
                placeholder="Nome e cognome"
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="alimenti">
              Tipi di alimenti trattati (separati da virgola)
            </Label>
            <Input
              id="alimenti"
              value={tipiAlimenti}
              onChange={(e) => {
                setTipiAlimenti(e.target.value);
                markDirty();
              }}
              placeholder="Carne, pesce, verdure, latticini"
            />
          </div>

          <div className="flex items-center justify-end gap-2 border-t pt-3">
            <span
              className={cn(
                "text-xs",
                dirty
                  ? "text-amber-700 dark:text-amber-400"
                  : "text-muted-foreground",
              )}
            >
              {dirty ? "Modifiche non salvate" : "Tutto salvato"}
            </span>
            <Button
              onClick={handleSave}
              disabled={saving || !dirty}
              size="sm"
            >
              {saving ? (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-1 h-4 w-4" />
              )}
              Salva
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* CCPs card */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="text-base">
                Punti Critici di Controllo (CCP)
              </CardTitle>
              <CardDescription>
                {ccps.length > 0
                  ? `${ccps.length} CCP configurati. Modifica inline o aggiungi un CCP personalizzato.`
                  : "Nessun CCP configurato. Seleziona una tipologia di attivita per caricare i default."}
              </CardDescription>
            </div>
            <div className="flex flex-shrink-0 gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setRegenDialog({ open: true, pendingSlug: null })
                }
                disabled={!tipologia || regenerating}
              >
                <RefreshCcw className="mr-1 h-3.5 w-3.5" />
                Rigenera dai default
              </Button>
              <Button variant="outline" size="sm" onClick={addCustomCcp}>
                <Plus className="mr-1 h-3.5 w-3.5" />
                Aggiungi CCP
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {ccps.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nessun CCP ancora. Seleziona una tipologia qui sopra oppure
              aggiungi un CCP personalizzato.
            </p>
          ) : (
            <div className="space-y-2">
              {ccps.map((ccp, idx) => {
                const expanded = expandedCodice === ccp.codice;
                const isCustom = ccp.codice.startsWith("CUSTOM");
                return (
                  <div
                    key={`${ccp.codice}-${idx}`}
                    className="rounded-md border border-input"
                  >
                    <div className="flex items-center gap-3 p-3">
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedCodice(expanded ? null : ccp.codice)
                        }
                        className="flex-shrink-0 text-muted-foreground hover:text-foreground"
                        aria-label={
                          expanded ? "Chiudi dettaglio" : "Apri dettaglio"
                        }
                      >
                        {expanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </button>
                      <Badge
                        variant={isCustom ? "secondary" : "outline"}
                        className="flex-shrink-0"
                      >
                        {ccp.codice}
                      </Badge>
                      <Input
                        value={ccp.nome}
                        onChange={(e) =>
                          updateCcp(idx, { nome: e.target.value })
                        }
                        className="h-8 flex-1 text-sm"
                        placeholder="Nome CCP"
                      />
                      <Input
                        value={ccp.limite_critico}
                        onChange={(e) =>
                          updateCcp(idx, { limite_critico: e.target.value })
                        }
                        className="hidden h-8 flex-1 text-sm md:block"
                        placeholder="Limite critico"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteCcp(idx)}
                        aria-label={`Elimina ${ccp.codice}`}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                    {expanded && (
                      <div className="grid gap-3 border-t border-input bg-muted/20 p-3 md:grid-cols-2">
                        <div className="grid gap-1">
                          <Label className="text-xs">Codice</Label>
                          <Input
                            value={ccp.codice}
                            onChange={(e) =>
                              updateCcp(idx, { codice: e.target.value })
                            }
                            className="h-8 text-sm"
                          />
                        </div>
                        <div className="grid gap-1">
                          <Label className="text-xs">Fase</Label>
                          <Input
                            value={ccp.fase}
                            onChange={(e) =>
                              updateCcp(idx, { fase: e.target.value })
                            }
                            className="h-8 text-sm"
                          />
                        </div>
                        <div className="grid gap-1 md:col-span-2">
                          <Label className="text-xs">Pericolo</Label>
                          <Textarea
                            value={ccp.pericolo}
                            onChange={(e) =>
                              updateCcp(idx, { pericolo: e.target.value })
                            }
                            rows={2}
                            className="text-sm"
                          />
                        </div>
                        <div className="grid gap-1 md:col-span-2">
                          <Label className="text-xs">Limite critico</Label>
                          <Textarea
                            value={ccp.limite_critico}
                            onChange={(e) =>
                              updateCcp(idx, {
                                limite_critico: e.target.value,
                              })
                            }
                            rows={2}
                            className="text-sm"
                          />
                        </div>
                        <div className="grid gap-1">
                          <Label className="text-xs">Monitoraggio</Label>
                          <Textarea
                            value={ccp.monitoraggio}
                            onChange={(e) =>
                              updateCcp(idx, { monitoraggio: e.target.value })
                            }
                            rows={2}
                            className="text-sm"
                          />
                        </div>
                        <div className="grid gap-1">
                          <Label className="text-xs">Azione correttiva</Label>
                          <Textarea
                            value={ccp.azione_correttiva}
                            onChange={(e) =>
                              updateCcp(idx, {
                                azione_correttiva: e.target.value,
                              })
                            }
                            rows={2}
                            className="text-sm"
                          />
                        </div>
                        <div className="grid gap-1 md:col-span-2">
                          <Label className="text-xs">Frequenza</Label>
                          <Input
                            value={ccp.frequenza}
                            onChange={(e) =>
                              updateCcp(idx, { frequenza: e.target.value })
                            }
                            className="h-8 text-sm"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Regenerate dialog — AC3 "warn before destroy" */}
      <Dialog
        open={regenDialog.open}
        onOpenChange={(o) =>
          setRegenDialog((p) => ({ ...p, open: o, pendingSlug: o ? p.pendingSlug : null }))
        }
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {regenDialog.pendingSlug
                ? "Tipologia attivita cambiata"
                : "Rigenera CCP dai default"}
            </DialogTitle>
            <DialogDescription>
              {regenDialog.pendingSlug
                ? "Hai modificato la tipologia di attivita. Le personalizzazioni ai CCP possono andare perse. Scegli come procedere:"
                : "I CCP verranno rigenerati dal catalogo. Scegli se preservare le tue personalizzazioni:"}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-sm">
            <div className="rounded-md border border-emerald-300 bg-emerald-50 p-3 dark:border-emerald-800 dark:bg-emerald-900/20">
              <p className="font-medium text-emerald-900 dark:text-emerald-300">
                Unisci (consigliato)
              </p>
              <p className="mt-1 text-xs text-emerald-900/80 dark:text-emerald-300/80">
                Mantiene le righe che hai modificato + i CCP personalizzati, e
                aggiunge i nuovi CCP dal catalogo.
              </p>
            </div>
            <div className="rounded-md border border-amber-300 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-900/20">
              <p className="font-medium text-amber-900 dark:text-amber-300">
                Sostituisci
              </p>
              <p className="mt-1 text-xs text-amber-900/80 dark:text-amber-300/80">
                Cancella tutti i CCP esistenti e carica solo i default della
                nuova tipologia. Le personalizzazioni vanno perse.
              </p>
            </div>
          </div>

          <DialogFooter className="flex flex-col gap-2 sm:flex-row sm:justify-between">
            <Button
              variant="ghost"
              onClick={() => setRegenDialog({ open: false, pendingSlug: null })}
              disabled={regenerating}
            >
              Annulla
            </Button>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => runRegenerate("replace")}
                disabled={regenerating}
              >
                Sostituisci
              </Button>
              <Button
                onClick={() => runRegenerate("merge")}
                disabled={regenerating}
              >
                {regenerating ? (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                ) : null}
                Unisci
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
