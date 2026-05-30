"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  VdtForm,
  summarize,
  type PersonaOption,
  type VdtSummary,
} from "@/components/assessments/vdt-form";
import type { Azienda } from "@/types";

const EMPTY_SUMMARY: VdtSummary = summarize([]);

interface VdtValutazioneRow {
  id: string;
  persona_id: string | null;
  postazione: string;
  ore_settimanali: number;
  esposto: boolean;
  created_at: string;
}

function formatDateIt(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    const dd = String(d.getDate()).padStart(2, "0");
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    return `${dd}/${mm}/${d.getFullYear()}`;
  } catch {
    return iso;
  }
}

async function authHeaders(): Promise<HeadersInit> {
  let token: string | null = null;
  try {
    const s = await fetch("/api/auth/session");
    const session = await s.json();
    token = session?.accessToken ?? null;
  } catch {
    /* noop */
  }
  return token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}

export default function VdtAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [persone, setPersone] = useState<PersonaOption[]>([]);
  const [existingValutazioni, setExistingValutazioni] = useState<VdtValutazioneRow[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [summary, setSummary] = useState<VdtSummary>(EMPTY_SUMMARY);
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeMessage, setFinalizeMessage] = useState<string | null>(null);
  // Bumped after every successful finalize so VdtForm clears its draft +
  // workers. Feedback #56 — operators kept reporting "non si salva"
  // because the old form rows sat there after a successful save.
  const [clearSignal, setClearSignal] = useState(0);

  const refetchValutazioni = useCallback(async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const headers = await authHeaders();
      const res = await fetch(
        `${apiUrl}/api/v1/aziende/${aziendaId}/vdt`,
        { headers },
      );
      if (res.ok) {
        const rows = (await res.json()) as VdtValutazioneRow[];
        setExistingValutazioni(Array.isArray(rows) ? rows : []);
      }
    } catch {
      /* noop */
    }
  }, [aziendaId]);

  const deleteValutazione = useCallback(
    async (valutazioneId: string, label: string) => {
      if (
        !window.confirm(
          `Eliminare la valutazione VDT di ${label}? L'operazione è irreversibile.`,
        )
      ) {
        return;
      }
      setActionError(null);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const headers = await authHeaders();
        // The VDT router is mounted under the azienda (mirrors MMC):
        // DELETE /api/v1/aziende/{aziendaId}/vdt/{id}. The old URL
        // (/api/v1/vdt/{id}) matched no route and 404'd, so every delete
        // failed silently.
        const res = await fetch(
          `${apiUrl}/api/v1/aziende/${aziendaId}/vdt/${valutazioneId}`,
          { method: "DELETE", headers },
        );
        if (!res.ok && res.status !== 204) {
          throw new Error(`Errore ${res.status}`);
        }
        await refetchValutazioni();
      } catch (err) {
        setActionError(
          err instanceof Error ? err.message : "Eliminazione fallita",
        );
      }
    },
    [aziendaId, refetchValutazioni],
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const headers = await authHeaders();
        const [azRes, persRes, vdtRes] = await Promise.all([
          fetch(`${apiUrl}/api/v1/aziende/${aziendaId}`, { headers }),
          fetch(`${apiUrl}/api/v1/aziende/${aziendaId}/persone`, { headers }),
          fetch(`${apiUrl}/api/v1/aziende/${aziendaId}/vdt`, { headers }),
        ]);
        if (!azRes.ok) throw new Error(`Errore ${azRes.status}`);
        const azData = (await azRes.json()) as Azienda;
        if (!cancelled) setAzienda(azData);
        if (persRes.ok) {
          const persData = (await persRes.json()) as PersonaOption[];
          if (!cancelled) setPersone(persData);
        }
        if (vdtRes.ok) {
          const vdtData = (await vdtRes.json()) as VdtValutazioneRow[];
          if (!cancelled) {
            setExistingValutazioni(Array.isArray(vdtData) ? vdtData : []);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error ? err.message : "Impossibile caricare l'azienda",
          );
        }
      }
    }
    if (aziendaId) load();
    return () => {
      cancelled = true;
    };
  }, [aziendaId]);

  // Name to show next to a saved row. Generic workstations (persona_id =
  // null) are valid VDT rows too — they must still be listed and deletable,
  // which the old per-persona "Già valutati" card silently skipped.
  const personaLabel = useCallback(
    (personaId: string | null): string => {
      if (!personaId) return "Generica";
      return (
        persone.find((p) => p.id === personaId)?.nominativo ??
        "(lavoratore rimosso)"
      );
    },
    [persone],
  );

  const savedEsposti = useMemo(
    () => existingValutazioni.filter((v) => v.esposto).length,
    [existingValutazioni],
  );

  const allClassified = summary.total > 0 && summary.incompleti === 0;

  const finalize = useCallback(async () => {
    setFinalizing(true);
    setFinalizeMessage(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const headers = await authHeaders();

      const validRows = summary.workers.filter(
        (w) => w.ore_settimanali != null && w.postazione.trim() !== "",
      );
      if (!validRows.length) {
        throw new Error("Nessuna riga valida da salvare.");
      }

      let saved = 0;
      const failures: string[] = [];
      for (const w of validRows) {
        const body: Record<string, unknown> = {
          persona_id: w.persona_id,
          postazione: w.postazione.trim(),
          ore_settimanali: w.ore_settimanali ?? 0,
          schermo_conforme: w.schermo_conforme,
          tastiera_separata: w.tastiera_separata,
          sedile_regolabile: w.sedile_regolabile,
          poggiapiedi_disponibile: w.poggiapiedi_disponibile,
          illuminazione_adeguata: w.illuminazione_adeguata,
          riflessi_assenti: w.riflessi_assenti,
          spazio_adeguato: w.spazio_adeguato,
          pause_previste: w.pause_previste,
          eta_50_plus: w.eta_50_plus,
          idoneita_visiva: w.idoneita_visiva || null,
          data_ultima_visita: w.data_ultima_visita || null,
          note: w.note || null,
        };
        const res = await fetch(
          `${apiUrl}/api/v1/aziende/${aziendaId}/vdt`,
          { method: "POST", headers, body: JSON.stringify(body) },
        );
        if (!res.ok) {
          const detail = await res.text().catch(() => "");
          failures.push(`${w.postazione}: ${res.status} ${detail.slice(0, 120)}`);
        } else {
          saved += 1;
        }
      }

      if (failures.length) {
        throw new Error(
          `Salvati ${saved}/${validRows.length}. Errori:\n${failures.join("\n")}`,
        );
      }
      setFinalizeMessage(
        `Valutazione archiviata: ${saved} postazioni salvate · ${summary.esposti} esposti.`,
      );
      // Re-fetch so the "Già valutati" badge reflects the new rows.
      await refetchValutazioni();
      // Clear the in-progress form + localStorage draft so the operator
      // sees an empty form (ready for the next worker) instead of the
      // just-saved rows still sitting there looking dirty. Feedback #56.
      setClearSignal((s) => s + 1);
    } catch (err) {
      setFinalizeMessage(
        err instanceof Error
          ? `Errore conferma: ${err.message}`
          : "Errore conferma sconosciuto",
      );
    } finally {
      setFinalizing(false);
    }
  }, [aziendaId, summary, refetchValutazioni]);

  const pageSubtitle = useMemo(() => {
    if (loadError) return `Azienda ${aziendaId} (metadati non disponibili)`;
    if (azienda) return azienda.ragione_sociale ?? `Azienda ${aziendaId}`;
    return "Caricamento…";
  }, [azienda, aziendaId, loadError]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
            <Badge variant="secondary">Allegato Rischio VDT</Badge>
            <span>D.Lgs. 81/2008 Titolo VII · ISO 9241</span>
          </div>
          <h1 className="mt-2 type-h1">
            Valutazione Esposizione Videoterminali
          </h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
      </div>

      {actionError && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {actionError}
        </div>
      )}

      {/* Persistent view of everything archived for this azienda — generic
          workstations included. Operators reported the page "didn't save /
          didn't show / couldn't delete" because the only saved-data surface
          was a per-persona badge that skipped generic rows, and its delete
          button hit a 404 (wrong URL, now fixed). */}
      <Card>
        <CardContent className="space-y-3 py-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Badge variant="secondary">
                Valutazioni salvate: {existingValutazioni.length}
              </Badge>
              {savedEsposti > 0 && (
                <span className="text-xs font-medium text-rose-700">
                  {savedEsposti} esposti
                </span>
              )}
            </div>
            <span className="text-xs text-muted-foreground">
              Archiviate nel fascicolo cliente.
            </span>
          </div>

          {existingValutazioni.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nessuna valutazione VDT salvata. Compila il form e premi
              «Conferma valutazione».
            </p>
          ) : (
            <ul className="divide-y rounded-md border">
              {existingValutazioni.map((v) => {
                const nominativo = personaLabel(v.persona_id);
                return (
                  <li
                    key={v.id}
                    className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm"
                  >
                    <div className="min-w-0 flex-1">
                      <span className="font-medium">{v.postazione}</span>
                      <span className="text-muted-foreground">
                        {" "}
                        · {nominativo}
                      </span>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="text-xs tabular-nums text-muted-foreground">
                        {v.ore_settimanali} h/sett
                      </span>
                      {v.esposto ? (
                        <span className="inline-flex items-center rounded-md bg-rose-500/15 px-2 py-0.5 text-xs font-medium text-rose-700 ring-1 ring-rose-500/30">
                          ESPOSTO
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-md bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-500/30">
                          NON ESPOSTO
                        </span>
                      )}
                      <span className="text-xs text-muted-foreground">
                        {formatDateIt(v.created_at)}
                      </span>
                      <button
                        type="button"
                        aria-label={`Elimina valutazione ${v.postazione}`}
                        title="Elimina questa valutazione"
                        onClick={() =>
                          deleteValutazione(v.id, `${v.postazione} — ${nominativo}`)
                        }
                        className="inline-flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-rose-100 hover:text-rose-700"
                      >
                        ×
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      <VdtForm
        aziendaId={aziendaId}
        persone={persone}
        onSummaryChange={setSummary}
        clearSignal={clearSignal}
      />

      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div>
            <p className="text-sm font-medium">Conferma valutazione</p>
            <p className="text-xs text-muted-foreground">
              {summary.total === 0
                ? "Aggiungi almeno una postazione per confermare."
                : allClassified
                ? `Pronto per archiviare ${summary.total} postazioni nel fascicolo cliente.`
                : `Completa postazione e ore per ${summary.incompleti} righe.`}
            </p>
            {finalizeMessage && (
              <p
                className={cn(
                  "mt-1 whitespace-pre-line text-xs",
                  finalizeMessage.startsWith("Errore")
                    ? "text-destructive"
                    : "text-emerald-700",
                )}
              >
                {finalizeMessage}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button disabled={!allClassified || finalizing} onClick={finalize}>
              {finalizing ? "Conferma in corso…" : "Conferma valutazione"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <p className="text-[11px] text-muted-foreground">
        Bozza salvata in locale (chiave: <code>vdt-draft-{aziendaId}</code>).
        Al salvataggio le righe vengono archiviate sul server.
      </p>
    </div>
  );
}
