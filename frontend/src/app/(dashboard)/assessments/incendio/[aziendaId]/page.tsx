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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useUnsavedChangesGuard } from "@/hooks/use-unsaved-changes-guard";
import {
  BAND_CLASS,
  IncendioForm,
  useIncendioForm,
  type IncendioResult,
  type FireLivello,
} from "@/components/assessments/incendio/incendio-form";
import { IncendioVvfBanner } from "@/components/assessments/incendio/incendio-vvf-banner";
import {
  incendioAreaFromServer,
  incendioAreaToRequest,
  incendioSaveAllowed,
} from "@/components/assessments/incendio/incendio-roundtrip";
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
  note: string | null;
  misure_prevenzione: string | null;
  estintori_presenti: number;
  idranti_presenti: number;
  uscite_emergenza: number;
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

// Saved rows arrive in creation order (the API sorts ascending) and are
// sorted again here so the form, the "Valutazioni archiviate" card and the
// allegato agree even against an older API. Newest-first reversed the areas
// on every reload (UI/UX audit 2026-09-07, F2).
function sortByCreation(rows: ServerRow[]): ServerRow[] {
  return [...rows].sort(
    (a, b) =>
      a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id),
  );
}

// Render cold starts answer the first requests with a 5xx. Retry those and
// network failures a few times before giving up; a 4xx is returned as-is
// because retrying cannot change it.
async function fetchWithRetry(
  url: string,
  headers: HeadersInit,
  attempts = 3,
): Promise<Response> {
  let last: Response | undefined;
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch(url, { headers });
      if (res.status < 500) return res;
      last = res;
    } catch {
      last = undefined;
    }
    if (i < attempts - 1) {
      await new Promise((resolve) => setTimeout(resolve, 400 * 2 ** i));
    }
  }
  if (last) return last;
  throw new Error("Connessione al server non riuscita.");
}

type LoadState = "loading" | "ready" | "error";

// ---------------------------------------------------------------------------

export default function IncendioAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [ambienti, setAmbienti] = useState<Ambiente[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  // Bumped by "Riprova" to run the initial load again.
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [existing, setExisting] = useState<ServerRow[]>([]);
  const form = useIncendioForm();
  const [result, setResult] = useState<IncendioResult>({
    areas: [],
    maxLivello: null,
    allComplete: false,
  });
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  // Read during render, not inside a `watch` callback: react-hook-form only
  // computes `isDirty` once something has subscribed to it, so the callback
  // version missed the first edit — a single changed note showed no badge and
  // left the page without a prompt (UI/UX audit 2026-09-07, F4).
  const dirty = form.formState.isDirty;
  // Never save against rows the page could not read: with `existing` empty
  // the save would create every area again next to the invisible ones.
  const saveAllowed =
    loadState === "ready" &&
    incendioSaveAllowed({
      allScoresComplete: result.allComplete,
      formIsValid: form.formState.isValid,
    });
  const { pendingHref, confirmLeave, cancelLeave } =
    useUnsavedChangesGuard(dirty);

  const refetchExisting = useCallback(async () => {
    const headers = await authHeaders();
    const res = await fetch(
      `${apiUrl}/api/v1/aziende/${aziendaId}/incendio-valutazioni`,
      { headers },
    );
    if (!res.ok) throw new Error(`Errore ${res.status}`);
    const rows = sortByCreation((await res.json()) as ServerRow[]);
    setExisting(rows);
    return rows;
  }, [apiUrl, aziendaId]);

  // Initial load: azienda, saved valutazioni and ambienti. All three have to
  // succeed before the form is shown. A failed read of the saved rows used
  // to render an empty form with no error, and a save from that state
  // re-created every area next to the rows it could not see (June audit
  // F10, UI/UX audit 2026-09-07 F3). The form hydrates from the saved rows
  // so the operator sees their last save instead of an empty form.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoadState("loading");
      setLoadError(null);
      try {
        const headers = await authHeaders();
        const [azRes, rowsRes, ambRes] = await Promise.all([
          fetchWithRetry(`${apiUrl}/api/v1/aziende/${aziendaId}`, headers),
          fetchWithRetry(
            `${apiUrl}/api/v1/aziende/${aziendaId}/incendio-valutazioni`,
            headers,
          ),
          fetchWithRetry(
            `${apiUrl}/api/v1/aziende/${aziendaId}/ambienti`,
            headers,
          ),
        ]);
        if (!azRes.ok) {
          throw new Error(
            `Non è stato possibile leggere i dati dell'azienda (errore ${azRes.status}).`,
          );
        }
        if (!rowsRes.ok) {
          throw new Error(
            `Non è stato possibile leggere le valutazioni archiviate (errore ${rowsRes.status}).`,
          );
        }
        if (!ambRes.ok) {
          throw new Error(
            `Non è stato possibile leggere gli ambienti (errore ${ambRes.status}).`,
          );
        }
        const azData = (await azRes.json()) as Azienda;
        const rows = sortByCreation((await rowsRes.json()) as ServerRow[]);
        const ambData = (await ambRes.json()) as Ambiente[];
        if (cancelled) return;
        setAzienda(azData);
        setAmbienti(ambData);
        setExisting(rows);
        if (rows.length > 0) {
          form.reset({
            areas: rows.map((row) =>
              incendioAreaFromServer(
                row,
                ambData.find((ambiente) => ambiente.id === row.ambiente_id)
                  ?.nome,
              ),
            ),
          });
        }
        setLoadState("ready");
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error
              ? err.message
              : "Non è stato possibile caricare la valutazione.",
          );
          setLoadState("error");
        }
      }
    }
    if (aziendaId) load();
    return () => {
      cancelled = true;
    };
    // form is stable; we don't want to re-run on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aziendaId, apiUrl, loadAttempt]);

  // Save: POST one row per area FIRST, then delete the previously-saved rows.
  // The old order (delete-then-recreate) lost data if a POST failed mid-save —
  // e.g. a cold-start/deploy 5xx after the deletes ran left zero rows. By
  // creating all new rows before deleting any old one, a failed POST aborts
  // before anything is destroyed. Worst case on a failed DELETE is a duplicate
  // (recoverable), which we surface rather than silently swallow.
  const save = useCallback(async () => {
    if (!saveAllowed || result.areas.length === 0) return;
    setSaving(true);
    setSaveMessage(null);
    try {
      const headers = await authHeaders();

      // 1. POST one row per area from the form. If any fails we throw before
      //    touching the existing rows — no data loss.
      for (const area of form.getValues().areas) {
        const body = JSON.stringify(incendioAreaToRequest(area));
        const res = await fetch(
          `${apiUrl}/api/v1/aziende/${aziendaId}/incendio-valutazioni`,
          { method: "POST", headers, body },
        );
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(`Salvataggio area "${area.nome}" fallito: ${txt}`);
        }
      }

      // 2. New rows are safely persisted — now delete the old ones. A delete
      //    failure can't lose data (the new rows exist); it can only leave a
      //    stale duplicate, so we count failures and warn instead of throwing.
      let staleLeft = 0;
      for (const old of existing) {
        const del = await fetch(
          `${apiUrl}/api/v1/aziende/${aziendaId}/incendio-valutazioni/${old.id}`,
          { method: "DELETE", headers },
        );
        if (!del.ok && del.status !== 204 && del.status !== 404) staleLeft += 1;
      }

      const fresh = await refetchExisting();
      setSaveMessage(
        staleLeft > 0
          ? `Valutazione salvata (${fresh.length} aree), ma ${staleLeft} riga/he precedente/i non è stata rimossa — ricarica e verifica eventuali duplicati.`
          : `Valutazione salvata: ${fresh.length} area/e archiviata/e.`,
      );
      form.reset(form.getValues()); // marks RHF as pristine
    } catch (err) {
      setSaveMessage(
        err instanceof Error
          ? `Errore salvataggio: ${err.message}`
          : "Errore salvataggio sconosciuto",
      );
    } finally {
      setSaving(false);
    }
  }, [saveAllowed, result, existing, apiUrl, aziendaId, form, refetchExisting]);

  const pageSubtitle = useMemo(() => {
    if (azienda) return azienda.ragione_sociale ?? `Azienda ${aziendaId}`;
    if (loadState === "error") return `Azienda ${aziendaId}`;
    return "Caricamento…";
  }, [azienda, aziendaId, loadState]);

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
            className="border-[rgba(155,104,41,0.34)] bg-[rgba(155,104,41,0.12)] text-[#8a5c23]"
          >
            Modifiche non salvate
          </Badge>
        )}
      </div>

      {loadState === "loading" && (
        <p className="text-sm text-muted-foreground" aria-live="polite">
          Lettura della valutazione archiviata…
        </p>
      )}

      {loadState === "error" && (
        <Card
          role="alert"
          className="border-[rgba(199,42,58,0.28)] bg-[rgba(199,42,58,0.05)]"
        >
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
            <div>
              <p className="text-sm font-medium text-[#c72a3a]">
                Impossibile caricare la valutazione
              </p>
              <p className="text-xs text-muted-foreground">
                {loadError} Il modulo resta chiuso finché le aree archiviate
                non sono leggibili, per non creare duplicati.
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              onClick={() => setLoadAttempt((n) => n + 1)}
            >
              Riprova
            </Button>
          </CardContent>
        </Card>
      )}

      {loadState === "ready" && (
        <>
          {existing.length > 0 && (
            <Card className="border-[rgba(16,140,61,0.26)] bg-[rgba(16,140,61,0.05)]">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">
                  Valutazioni archiviate ({existing.length})
                </CardTitle>
                <CardDescription className="text-xs">
                  Modifica i valori qui sotto e premi &quot;Salva valutazione&quot;
                  per aggiornare il fascicolo.
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
                  {saveAllowed
                    ? `Tutte le aree (${result.areas.length}) sono compilate. La valutazione sarà archiviata nel fascicolo cliente.`
                    : result.allComplete
                      ? "Correggi i campi non validi prima di salvare la valutazione."
                      : "Completa INF, SI e PI per ciascuna area per salvare la valutazione."}
                </p>
                {saveMessage && (
                  <p
                    className={cn(
                      "mt-1 text-xs",
                      saveMessage.startsWith("Errore") ||
                        saveMessage.startsWith("Discrepanza")
                        ? "text-destructive"
                        : "text-[#0c6b2f]",
                    )}
                  >
                    {saveMessage}
                  </p>
                )}
              </div>
              <div className="flex gap-2">
                <Button disabled={!saveAllowed || saving} onClick={save}>
                  {saving ? "Salvataggio in corso…" : "Salva valutazione"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Unsaved-changes guard: a same-origin link click while dirty is held
          by the hook until the operator decides here. */}
      <Dialog
        open={pendingHref !== null}
        onOpenChange={(open) => {
          if (!open) cancelLeave();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Modifiche non salvate</DialogTitle>
            <DialogDescription>
              La valutazione contiene modifiche non ancora archiviate. Se esci
              ora andranno perse.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={cancelLeave}>
              Continua a modificare
            </Button>
            <Button type="button" variant="destructive" onClick={confirmLeave}>
              Esci senza salvare
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
