"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  BAND_CLASS,
  IncendioForm,
  useIncendioForm,
  type IncendioResult,
  type FireLivello,
} from "@/components/assessments/incendio/incendio-form";
import { IncendioVvfBanner } from "@/components/assessments/incendio/incendio-vvf-banner";
import type { Ambiente, Azienda } from "@/types";

// Italian action text per livello (kept for the "Azione consigliata" summary
// card — the per-area checklist lives inside `IncendioMeasures`).
const AZIONE_PER_LIVELLO: Record<FireLivello, string> = {
  Basso:
    "Rischio incendio basso: mantenere in efficienza le misure di prevenzione e protezione esistenti, verificare periodicamente estintori, vie di esodo e segnaletica, e aggiornare la formazione antincendio del personale.",
  Medio:
    "Rischio incendio medio: adottare misure aggiuntive di prevenzione e protezione (rilevazione automatica, compartimentazione, controllo sorgenti di innesco), designare e formare gli addetti alla gestione dell'emergenza e aggiornare il piano di emergenza ed evacuazione.",
  Alto:
    "Rischio incendio alto: attivare immediatamente misure straordinarie di prevenzione e protezione, coinvolgere il professionista antincendio, presentare SCIA ai VV.F. ove dovuta, adottare impianti di rilevazione e spegnimento automatici e garantire formazione di livello 3 agli addetti all'emergenza.",
};

// Server livello (BASSO/MEDIO/ALTO) <-> UI livello (Basso/Medio/Alto).
type ServerLivello = "BASSO" | "MEDIO" | "ALTO";
function toUi(l: ServerLivello | null): FireLivello | null {
  if (!l) return null;
  return { BASSO: "Basso", MEDIO: "Medio", ALTO: "Alto" }[l] as FireLivello;
}

interface ServerRow {
  id: string;
  azienda_id: string;
  ambiente_id: string | null;
  nome_area: string | null;
  inf: number;
  si: number;
  pi: number;
  punteggio_totale: number | null;
  livello_rischio: ServerLivello | null;
  created_at: string;
  updated_at: string;
}

async function authHeaders(): Promise<HeadersInit> {
  try {
    const s = await fetch("/api/auth/session");
    const session = await s.json();
    if (session?.accessToken) {
      return {
        Authorization: `Bearer ${session.accessToken}`,
        "Content-Type": "application/json",
      };
    }
  } catch {
    /* noop */
  }
  return { "Content-Type": "application/json" };
}

// ---------------------------------------------------------------------------

export default function IncendioAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [ambienti, setAmbienti] = useState<Ambiente[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [existing, setExisting] = useState<ServerRow[]>([]);
  const form = useIncendioForm();
  const [result, setResult] = useState<IncendioResult>({
    areas: [],
    maxLivello: null,
    allComplete: false,
  });
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    const subscription = form.watch(() => setDirty(form.formState.isDirty));
    return () => subscription.unsubscribe();
  }, [form]);

  const refetchExisting = useCallback(async () => {
    const headers = await authHeaders();
    const res = await fetch(
      `${apiUrl}/api/v1/aziende/${aziendaId}/incendio-valutazioni`,
      { headers },
    );
    if (!res.ok) throw new Error(`Errore ${res.status}`);
    const rows = (await res.json()) as ServerRow[];
    setExisting(rows);
    return rows;
  }, [apiUrl, aziendaId]);

  // Initial load: azienda + existing valutazioni. Hydrate form from existing
  // rows so the user sees their last save instead of an empty form.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const headers = await authHeaders();
        const [azRes, rowsRes, ambRes] = await Promise.all([
          fetch(`${apiUrl}/api/v1/aziende/${aziendaId}`, { headers }),
          fetch(
            `${apiUrl}/api/v1/aziende/${aziendaId}/incendio-valutazioni`,
            { headers },
          ),
          fetch(`${apiUrl}/api/v1/aziende/${aziendaId}/ambienti`, {
            headers,
          }),
        ]);
        if (!azRes.ok) throw new Error(`Errore azienda ${azRes.status}`);
        const azData = (await azRes.json()) as Azienda;
        if (cancelled) return;
        setAzienda(azData);
        if (ambRes.ok) {
          const ambData = (await ambRes.json()) as Ambiente[];
          if (!cancelled) setAmbienti(ambData);
        }

        if (rowsRes.ok) {
          const rows = (await rowsRes.json()) as ServerRow[];
          if (cancelled) return;
          setExisting(rows);
          if (rows.length > 0) {
            form.reset({
              areas: rows.map((r) => ({
                nome: r.nome_area ?? "",
                inf: r.inf as 1 | 2 | 3,
                si: r.si as 1 | 2 | 3,
                pi: r.pi as 1 | 2 | 3,
              })),
            });
          }
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error
              ? err.message
              : "Impossibile caricare l'azienda",
          );
        }
      }
    }
    if (aziendaId) load();
    return () => {
      cancelled = true;
    };
    // form is stable; we don't want to re-run on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aziendaId, apiUrl]);

  // Save: delete existing rows for this azienda, then POST one row per area.
  // Simpler than diffing — for a small list (typically 1-5 areas) the cost is
  // negligible and the resulting state is always consistent with the form.
  const save = useCallback(async () => {
    if (!result.allComplete || result.areas.length === 0) return;
    setSaving(true);
    setSaveMessage(null);
    try {
      const headers = await authHeaders();

      // 1. Delete any previously-saved rows.
      for (const old of existing) {
        await fetch(
          `${apiUrl}/api/v1/aziende/${aziendaId}/incendio-valutazioni/${old.id}`,
          { method: "DELETE", headers },
        );
      }

      // 2. POST one row per area from the form.
      for (const area of result.areas) {
        if (
          area.inf === undefined ||
          area.si === undefined ||
          area.pi === undefined
        )
          continue;
        const body = JSON.stringify({
          nome_area: area.nome || null,
          inf: area.inf,
          si: area.si,
          pi: area.pi,
        });
        const res = await fetch(
          `${apiUrl}/api/v1/aziende/${aziendaId}/incendio-valutazioni`,
          { method: "POST", headers, body },
        );
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(`Salvataggio area "${area.nome}" fallito: ${txt}`);
        }
      }

      const fresh = await refetchExisting();
      setSaveMessage(
        `Valutazione salvata: ${fresh.length} area/e archiviata/e.`,
      );
      form.reset(form.getValues()); // marks RHF as pristine
      setDirty(false);
    } catch (err) {
      setSaveMessage(
        err instanceof Error
          ? `Errore salvataggio: ${err.message}`
          : "Errore salvataggio sconosciuto",
      );
    } finally {
      setSaving(false);
    }
  }, [result, existing, apiUrl, aziendaId, form, refetchExisting]);

  const pageSubtitle = useMemo(() => {
    if (loadError) return `Azienda ${aziendaId} (metadati non disponibili)`;
    if (azienda) return azienda.ragione_sociale ?? `Azienda ${aziendaId}`;
    return "Caricamento…";
  }, [azienda, aziendaId, loadError]);

  const vvfVisible = result.maxLivello === "Alto";

  return (
    <div className="space-y-6">
      <IncendioVvfBanner visible={vvfVisible} />

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
            <Badge variant="secondary">Allegato Rischio Incendio</Badge>
            <span>D.Lgs. 81/2008 · D.M. 03/09/2021</span>
          </div>
          <h1 className="mt-2 type-h1">Valutazione Rischio Incendio</h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
        {dirty && (
          <Badge
            variant="outline"
            className="border-amber-400/60 bg-amber-50 text-amber-800"
          >
            Modifiche non salvate
          </Badge>
        )}
      </div>

      {existing.length > 0 && (
        <Card className="border-emerald-200/60 bg-emerald-50/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">
              Valutazioni archiviate ({existing.length})
            </CardTitle>
            <CardDescription className="text-xs">
              Modifica i valori qui sotto e premi "Salva valutazione" per
              aggiornare il fascicolo.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
              {existing.map((r) => {
                const livello = toUi(r.livello_rischio);
                return (
                  <li
                    key={r.id}
                    className="flex items-center justify-between rounded-md bg-background px-3 py-2 ring-1 ring-border"
                  >
                    <span className="truncate">{r.nome_area || "—"}</span>
                    {livello ? (
                      <span
                        className={cn(
                          "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium ring-1",
                          BAND_CLASS[livello],
                        )}
                      >
                        {livello} · {r.punteggio_totale}/9
                      </span>
                    ) : (
                      <Badge variant="secondary">—</Badge>
                    )}
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      )}

      <IncendioForm form={form} onResultChange={setResult} ambienti={ambienti} />

      {/* Azione consigliata riepilogo (livello massimo) */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-sm">
                Azione consigliata — livello massimo
              </CardTitle>
              <CardDescription className="text-xs">
                {result.maxLivello
                  ? AZIONE_PER_LIVELLO[result.maxLivello]
                  : "Completa i tre parametri di almeno un'area per ottenere l'azione consigliata."}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide text-muted-foreground">
                livello max
              </span>
              {result.maxLivello ? (
                <span
                  className={cn(
                    "inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium ring-1",
                    BAND_CLASS[result.maxLivello],
                  )}
                >
                  {result.maxLivello}
                </span>
              ) : (
                <Badge variant="secondary">—</Badge>
              )}
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Save */}
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div>
            <p className="text-sm font-medium">Salva valutazione</p>
            <p className="text-xs text-muted-foreground">
              {result.allComplete
                ? `Tutte le aree (${result.areas.length}) sono compilate. La valutazione sarà archiviata nel fascicolo cliente.`
                : "Completa INF, SI e PI per ciascuna area per salvare la valutazione."}
            </p>
            {saveMessage && (
              <p
                className={cn(
                  "mt-1 text-xs",
                  saveMessage.startsWith("Errore") ||
                    saveMessage.startsWith("Discrepanza")
                    ? "text-destructive"
                    : "text-emerald-700",
                )}
              >
                {saveMessage}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button disabled={!result.allComplete || saving} onClick={save}>
              {saving ? "Salvataggio in corso…" : "Salva valutazione"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
