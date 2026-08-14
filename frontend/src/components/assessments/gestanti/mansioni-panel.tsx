"use client";

/**
 * Preventive per-mansione assessment (art. 11 D.Lgs. 151/2001).
 *
 * Client request: the operator must be able to run an objective valutazione
 * of each mansione's gravidanza/allattamento risks WITHOUT any pregnant
 * worker registered. The list is prefilled from the azienda's organigramma
 * (distinct mansioni) with the D.Lgs. 151/2001 catalog matches already
 * ticked — the operator reviews, never re-enters. Missing mansioni can be
 * added by hand.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { throwApiError } from "@/lib/api-errors";

import { AllegatoBadge } from "./allegato-badge";
import type {
  CatalogRisk,
  EsitoMansione,
  MansioneOverviewItem,
  MansioniOverview,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ESITO_LABELS: Record<EsitoMansione, string> = {
  compatibile: "Compatibile",
  compatibile_con_limitazioni: "Compatibile con limitazioni",
  non_compatibile: "Non compatibile",
};

async function authHeaders(): Promise<HeadersInit> {
  try {
    const s = await fetch("/api/auth/session");
    const session = await s.json();
    const token = (session?.accessToken as string | undefined) ?? null;
    return token
      ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
      : { "Content-Type": "application/json" };
  } catch {
    return { "Content-Type": "application/json" };
  }
}

interface EditState {
  esito: EsitoMansione;
  /** risk_key -> selected. Prefilled: every suggested risk checked. */
  selected: Record<string, boolean>;
  misure: string;
  note: string;
}

function initialEditState(item: MansioneOverviewItem): EditState {
  const saved = item.valutazione;
  const selected: Record<string, boolean> = {};
  if (saved) {
    for (const r of item.suggested_risks) selected[r.risk_key] = false;
    for (const r of saved.rischi ?? []) selected[r.risk_key] = true;
  } else {
    // Prefill: catalog matches pre-checked, esito suggested from them.
    for (const r of item.suggested_risks) selected[r.risk_key] = true;
  }
  return {
    esito:
      saved?.esito ??
      (item.suggested_risks.length > 0
        ? "compatibile_con_limitazioni"
        : "compatibile"),
    selected,
    misure: saved?.misure ?? "",
    note: saved?.note ?? "",
  };
}

/** Union of suggested catalog risks and already-persisted ones, by risk_key. */
function riskUniverse(item: MansioneOverviewItem): CatalogRisk[] {
  const seen = new Map<string, CatalogRisk>();
  for (const r of item.suggested_risks) seen.set(r.risk_key, r);
  for (const r of item.valutazione?.rischi ?? []) {
    if (!seen.has(r.risk_key)) seen.set(r.risk_key, r);
  }
  return [...seen.values()];
}

export function MansioniPanel({ aziendaId }: { aziendaId: string }) {
  const [items, setItems] = useState<MansioneOverviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // One mansione (lowercased key) open for editing at a time keeps the
  // panel compact even with many mansioni.
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [edit, setEdit] = useState<EditState | null>(null);
  const [busy, setBusy] = useState(false);
  const [rowMessage, setRowMessage] = useState<string | null>(null);

  const [newMansione, setNewMansione] = useState("");
  const [adding, setAdding] = useState(false);

  const refetch = useCallback(async () => {
    try {
      const headers = await authHeaders();
      const res = await fetch(
        `${API_URL}/api/v1/aziende/${aziendaId}/gestanti/mansioni`,
        { headers },
      );
      if (!res.ok) await throwApiError(res);
      const data = (await res.json()) as MansioniOverview;
      setItems(data.items);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Impossibile caricare le mansioni",
      );
    } finally {
      setLoading(false);
    }
  }, [aziendaId]);

  useEffect(() => {
    if (aziendaId) refetch();
  }, [aziendaId, refetch]);

  const openEditor = useCallback((item: MansioneOverviewItem) => {
    setOpenKey(item.mansione.toLowerCase());
    setEdit(initialEditState(item));
    setRowMessage(null);
  }, []);

  const closeEditor = useCallback(() => {
    setOpenKey(null);
    setEdit(null);
    setRowMessage(null);
  }, []);

  const misureMissing =
    edit !== null &&
    edit.esito !== "compatibile" &&
    edit.misure.trim().length < 10;

  const save = useCallback(
    async (item: MansioneOverviewItem) => {
      if (!edit) return;
      setBusy(true);
      setRowMessage(null);
      try {
        const universe = riskUniverse(item);
        const rischi = universe
          .filter((r) => edit.selected[r.risk_key])
          .map((r) => ({
            risk_key: r.risk_key,
            allegato: r.allegato,
            descrizione: r.descrizione,
          }));
        const headers = await authHeaders();
        const res = await fetch(
          `${API_URL}/api/v1/aziende/${aziendaId}/gestanti/mansioni`,
          {
            method: "PUT",
            headers,
            body: JSON.stringify({
              mansione: item.mansione,
              esito: edit.esito,
              rischi,
              misure: edit.misure.trim() || null,
              note: edit.note.trim() || null,
            }),
          },
        );
        if (!res.ok) await throwApiError(res);
        await refetch();
        closeEditor();
      } catch (err) {
        setRowMessage(
          err instanceof Error ? `Errore: ${err.message}` : "Errore sconosciuto",
        );
      } finally {
        setBusy(false);
      }
    },
    [aziendaId, closeEditor, edit, refetch],
  );

  const removeValutazione = useCallback(
    async (item: MansioneOverviewItem) => {
      if (!item.valutazione) return;
      setBusy(true);
      try {
        const headers = await authHeaders();
        const res = await fetch(
          `${API_URL}/api/v1/aziende/${aziendaId}/gestanti/mansioni/${item.valutazione.id}`,
          { method: "DELETE", headers },
        );
        if (!res.ok && res.status !== 204) await throwApiError(res);
        await refetch();
        closeEditor();
      } catch (err) {
        setRowMessage(
          err instanceof Error ? `Errore: ${err.message}` : "Errore sconosciuto",
        );
      } finally {
        setBusy(false);
      }
    },
    [aziendaId, closeEditor, refetch],
  );

  const addMansione = useCallback(async () => {
    const mansione = newMansione.trim().replace(/\s+/g, " ");
    if (mansione.length < 2) return;
    setAdding(true);
    try {
      const headers = await authHeaders();
      // rischi: null → the server prefills the D.Lgs. 151/2001 catalog
      // matches for the mansione; the operator then reviews them below.
      const res = await fetch(
        `${API_URL}/api/v1/aziende/${aziendaId}/gestanti/mansioni`,
        {
          method: "PUT",
          headers,
          body: JSON.stringify({
            mansione,
            esito: "compatibile",
            rischi: null,
            misure: null,
            note: null,
          }),
        },
      );
      if (!res.ok) await throwApiError(res);
      setNewMansione("");
      await refetch();
      setOpenKey(mansione.toLowerCase());
      // Editor state is rebuilt from the refetched item below via effect-less
      // lazy init: find it in the fresh list on next render.
      setEdit(null);
    } catch (err) {
      setError(
        err instanceof Error ? `Errore: ${err.message}` : "Errore sconosciuto",
      );
    } finally {
      setAdding(false);
    }
  }, [aziendaId, newMansione, refetch]);

  // After addMansione refetch, openKey points at an item without edit state:
  // hydrate it lazily so the freshly added mansione opens in the editor with
  // the server-prefilled risks visible.
  const openItem = useMemo(
    () =>
      openKey
        ? items.find((it) => it.mansione.toLowerCase() === openKey) ?? null
        : null,
    [items, openKey],
  );
  useEffect(() => {
    if (openItem && edit === null) setEdit(initialEditState(openItem));
  }, [openItem, edit]);

  const assessed = items.filter((it) => it.valutazione !== null).length;

  return (
    <Card>
      <CardHeader className="border-b">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle className="text-sm">
              Valutazione oggettiva per mansione
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              Art. 11 D.Lgs. 151/2001 — la valutazione preventiva dei rischi
              per gravidanza/allattamento è richiesta per ogni mansione, anche
              senza lavoratrici in gestazione.
            </p>
          </div>
          <Badge variant="outline">
            {assessed}/{items.length} valutate
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        {loading && (
          <p className="text-sm text-muted-foreground">Caricamento mansioni…</p>
        )}
        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
        {!loading && items.length === 0 && !error && (
          <p className="text-sm text-muted-foreground">
            Nessuna mansione trovata nell&apos;organigramma. Aggiungine una qui
            sotto per avviare la valutazione preventiva.
          </p>
        )}

        <ul className="divide-y rounded-md ring-1 ring-border">
          {items.map((item) => {
            const key = item.mansione.toLowerCase();
            const isOpen = openKey === key;
            const universe = riskUniverse(item);
            return (
              <li key={key} className="p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium">{item.mansione}</span>
                    <Badge variant="secondary">
                      {item.num_persone} person{item.num_persone === 1 ? "a" : "e"}
                    </Badge>
                    {item.valutazione ? (
                      <Badge
                        variant="outline"
                        className={cn(
                          item.valutazione.esito === "compatibile"
                            ? "border-[rgba(16,140,61,0.4)] text-[#0c6b2f]"
                            : item.valutazione.esito === "non_compatibile"
                              ? "border-[rgba(199,42,58,0.4)] text-[#b01e2e]"
                              : "border-[rgba(245,158,11,0.4)] text-[#8a5c23]",
                        )}
                      >
                        {ESITO_LABELS[item.valutazione.esito]}
                      </Badge>
                    ) : (
                      <Badge
                        variant="outline"
                        className="border-[rgba(245,158,11,0.4)] text-[#8a5c23]"
                      >
                        Da valutare
                      </Badge>
                    )}
                    {item.suggested_risks.length > 0 && !item.valutazione && (
                      <span className="inline-flex items-center gap-1 text-xs text-[#8a5c23]">
                        <AlertTriangle className="size-3.5" aria-hidden />
                        {item.suggested_risks.length} rischi suggeriti
                      </span>
                    )}
                    {item.suggested_risks.length === 0 && !item.valutazione && (
                      <span className="inline-flex items-center gap-1 text-xs text-[#0c6b2f]">
                        <CheckCircle2 className="size-3.5" aria-hidden />
                        nessun rischio dal catalogo
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {item.valutazione && item.num_persone === 0 && (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy}
                        onClick={() => removeValutazione(item)}
                        title="Rimuovi la valutazione (mansione non più presente in organigramma)"
                      >
                        <Trash2 className="size-4" aria-hidden />
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant={isOpen ? "default" : "outline"}
                      onClick={() => (isOpen ? closeEditor() : openEditor(item))}
                    >
                      {isOpen
                        ? "Chiudi"
                        : item.valutazione
                          ? "Modifica"
                          : "Valuta"}
                    </Button>
                  </div>
                </div>

                {isOpen && edit && (
                  <div className="mt-3 space-y-3 rounded-md bg-muted/40 p-3">
                    <div className="grid gap-2 md:max-w-xs">
                      <Label htmlFor={`esito-${key}`}>Esito valutazione</Label>
                      <Select
                        id={`esito-${key}`}
                        size="sm"
                        value={edit.esito}
                        onChange={(e) =>
                          setEdit({
                            ...edit,
                            esito: e.target.value as EsitoMansione,
                          })
                        }
                      >
                        <option value="compatibile">Compatibile</option>
                        <option value="compatibile_con_limitazioni">
                          Compatibile con limitazioni
                        </option>
                        <option value="non_compatibile">Non compatibile</option>
                      </Select>
                    </div>

                    <div className="grid gap-2">
                      <Label>Rischi D.Lgs. 151/2001 (prefilati dal catalogo)</Label>
                      {universe.length === 0 ? (
                        <p className="text-xs text-muted-foreground">
                          Nessun rischio suggerito dal catalogo per questa
                          mansione.
                        </p>
                      ) : (
                        <ul className="space-y-1">
                          {universe.map((r) => (
                            <li key={r.risk_key}>
                              <label className="flex items-start gap-2 text-sm">
                                <input
                                  type="checkbox"
                                  className="mt-1"
                                  checked={!!edit.selected[r.risk_key]}
                                  onChange={(e) =>
                                    setEdit({
                                      ...edit,
                                      selected: {
                                        ...edit.selected,
                                        [r.risk_key]: e.target.checked,
                                      },
                                    })
                                  }
                                />
                                <span className="flex flex-wrap items-center gap-2">
                                  <AllegatoBadge allegato={r.allegato} />
                                  <span>{r.descrizione}</span>
                                </span>
                              </label>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div className="grid gap-2">
                      <Label htmlFor={`misure-${key}`}>
                        Misure di prevenzione / limitazioni
                        {edit.esito !== "compatibile" && (
                          <span className="text-destructive"> *</span>
                        )}
                      </Label>
                      <Textarea
                        id={`misure-${key}`}
                        rows={3}
                        value={edit.misure}
                        placeholder="Es. esonero dalla movimentazione carichi; adibizione a postazione seduta…"
                        onChange={(e) =>
                          setEdit({ ...edit, misure: e.target.value })
                        }
                      />
                      {misureMissing && (
                        <p className="text-xs text-destructive">
                          Obbligatorie (min 10 caratteri) quando l&apos;esito non
                          è &quot;Compatibile&quot;.
                        </p>
                      )}
                    </div>

                    <div className="grid gap-2">
                      <Label htmlFor={`note-${key}`}>Note (facoltative)</Label>
                      <Input
                        id={`note-${key}`}
                        value={edit.note}
                        onChange={(e) =>
                          setEdit({ ...edit, note: e.target.value })
                        }
                      />
                    </div>

                    {rowMessage && (
                      <p className="text-xs text-destructive" role="alert">
                        {rowMessage}
                      </p>
                    )}
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        disabled={busy || misureMissing}
                        onClick={() => save(item)}
                      >
                        {busy ? "Salvataggio…" : "Salva valutazione mansione"}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={busy}
                        onClick={closeEditor}
                      >
                        Annulla
                      </Button>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>

        <div className="flex flex-col gap-2 md:flex-row md:items-center">
          <Label htmlFor="nuova-mansione" className="md:whitespace-nowrap">
            Aggiungi mansione mancante
          </Label>
          <Input
            id="nuova-mansione"
            value={newMansione}
            placeholder="Es. Addetta banco gastronomia"
            className="md:max-w-sm"
            onChange={(e) => setNewMansione(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") addMansione();
            }}
          />
          <Button
            size="sm"
            variant="outline"
            disabled={adding || newMansione.trim().length < 2}
            onClick={addMansione}
          >
            <Plus className="mr-1 size-4" aria-hidden />
            {adding ? "Aggiunta…" : "Aggiungi"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
