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
  const [summary, setSummary] = useState<VdtSummary>(EMPTY_SUMMARY);
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeMessage, setFinalizeMessage] = useState<string | null>(null);

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
    async (valutazioneId: string, nominativo: string) => {
      if (
        !window.confirm(
          `Eliminare la valutazione VDT più recente di ${nominativo}? L'operazione è irreversibile.`,
        )
      ) {
        return;
      }
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const headers = await authHeaders();
        const res = await fetch(`${apiUrl}/api/v1/vdt/${valutazioneId}`, {
          method: "DELETE",
          headers,
        });
        if (!res.ok && res.status !== 204) {
          throw new Error(`Errore ${res.status}`);
        }
        await refetchValutazioni();
      } catch (err) {
        setLoadError(
          err instanceof Error ? err.message : "Eliminazione fallita",
        );
      }
    },
    [refetchValutazioni],
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

  // Most-recent valutazione per persona_id, for "Già valutati" surfacing.
  const valutatePerPersona = useMemo(() => {
    const map = new Map<string, VdtValutazioneRow>();
    for (const row of existingValutazioni) {
      if (!row.persona_id) continue;
      const prev = map.get(row.persona_id);
      if (!prev || new Date(row.created_at) > new Date(prev.created_at)) {
        map.set(row.persona_id, row);
      }
    }
    return map;
  }, [existingValutazioni]);

  const personeGiaValutate = useMemo(() => {
    return persone.filter((p) => valutatePerPersona.has(p.id));
  }, [persone, valutatePerPersona]);

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

      {personeGiaValutate.length > 0 && (
        <Card className="border-emerald-300/60 bg-emerald-50/60">
          <CardContent className="space-y-2 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-emerald-600 text-white hover:bg-emerald-600">
                Già valutati: {personeGiaValutate.length}
              </Badge>
              <span className="text-xs text-muted-foreground">
                Lavoratori con almeno una valutazione VDT in archivio.
              </span>
            </div>
            <ul className="flex flex-wrap gap-2 text-xs">
              {personeGiaValutate.map((p) => {
                const v = valutatePerPersona.get(p.id);
                return (
                  <li
                    key={p.id}
                    className="flex items-center gap-1 rounded-md border border-emerald-300/70 bg-white px-2 py-1 text-emerald-900"
                  >
                    <span aria-hidden className="text-emerald-600">
                      ✓
                    </span>
                    <span className="font-medium">{p.nominativo}</span>
                    {v ? (
                      <span className="text-emerald-700/80">
                        — Valutato il {formatDateIt(v.created_at)}
                      </span>
                    ) : null}
                    {v ? (
                      <button
                        type="button"
                        aria-label={`Elimina ultima valutazione di ${p.nominativo}`}
                        title="Elimina valutazione più recente"
                        onClick={() => deleteValutazione(v.id, p.nominativo)}
                        className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full text-emerald-600/70 hover:bg-rose-100 hover:text-rose-700"
                      >
                        ×
                      </button>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      )}

      <VdtForm
        aziendaId={aziendaId}
        persone={persone}
        onSummaryChange={setSummary}
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
