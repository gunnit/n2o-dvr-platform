"use client";

/**
 * Valutazione Gestanti / Puerpere / Allattamento (D.Lgs. 151/2001).
 *
 * Closes US-3.9 (auto cross-reference mansione <-> Allegati A/B/C) and
 * US-3.10 (relocation accept / reject flow with justification or misura
 * alternativa). See docs/superpowers/specs/2026-04-15-wave1-assessment-
 * frontends-design.md section 4.3.
 *
 * The page is a client component because the cross-reference call is
 * triggered by user interaction (worker selection) and drives local state
 * (match list, dialog open/close, decision mutations). We use
 * `useParams()` from next/navigation to read the dynamic [aziendaId]
 * segment — Next 16 turned the server-component `params` prop into a
 * Promise, so the old synchronous stub would no longer compile.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

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

import { MatchesPanel } from "@/components/assessments/gestanti/matches-panel";
import { RelocationDialog } from "@/components/assessments/gestanti/relocation-dialog";
import { WorkerSelector } from "@/components/assessments/gestanti/worker-selector";
import { parseApiError } from "@/lib/api-errors";
import type {
  CrossReferenceResponse,
  FemaleWorker,
  RiskMatch,
} from "@/components/assessments/gestanti/types";
import type { Azienda, Persona } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getToken(): Promise<string | null> {
  try {
    const s = await fetch("/api/auth/session");
    const session = await s.json();
    return (session?.accessToken as string | undefined) ?? null;
  } catch {
    return null;
  }
}

async function authHeaders(): Promise<HeadersInit> {
  const token = await getToken();
  return token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}

// ---------------------------------------------------------------------------

export default function GestantiAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [workers, setWorkers] = useState<FemaleWorker[]>([]);
  const [workersLoading, setWorkersLoading] = useState(true);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [matchData, setMatchData] = useState<CrossReferenceResponse | null>(null);
  const [matchLoading, setMatchLoading] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);

  // Relocation dialog state.
  const [dialogMatch, setDialogMatch] = useState<RiskMatch | null>(null);
  const [dialogAction, setDialogAction] = useState<"accept" | "reject" | null>(
    null,
  );
  const [dialogBusy, setDialogBusy] = useState(false);

  // Signature block (carried over from the previous stub).
  const [stato, setStato] = useState<"gestante" | "puerpera" | "allattamento">(
    "gestante",
  );
  const [dataNotifica, setDataNotifica] = useState("");
  const [dataPresuntoParto, setDataPresuntoParto] = useState("");
  const [firmaLavoratrice, setFirmaLavoratrice] = useState("");
  const [firmaDdl, setFirmaDdl] = useState("");
  const [firmaRspp, setFirmaRspp] = useState("");
  const [firmaMedico, setFirmaMedico] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // --- Azienda metadata (best effort; page still works without it) ------
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const headers = await authHeaders();
        const res = await fetch(`${API_URL}/api/v1/aziende/${aziendaId}`, {
          headers,
        });
        if (!res.ok) throw new Error(`Errore ${res.status}`);
        const data = (await res.json()) as Azienda;
        if (!cancelled) setAzienda(data);
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

  // --- Saved valutazioni (lets the operator see who already has a record).
  const [savedRows, setSavedRows] = useState<
    Array<{
      id: string;
      persona_id: string;
      stato: string;
      data_notifica: string | null;
    }>
  >([]);

  const refetchSaved = useCallback(async () => {
    try {
      const headers = await authHeaders();
      const res = await fetch(
        `${API_URL}/api/v1/aziende/${aziendaId}/gestanti`,
        { headers },
      );
      if (!res.ok) return;
      const rows = (await res.json()) as Array<{
        id: string;
        persona_id: string;
        stato: string;
        data_notifica: string | null;
      }>;
      setSavedRows(rows);
    } catch {
      /* best-effort */
    }
  }, [aziendaId]);

  useEffect(() => {
    if (aziendaId) refetchSaved();
  }, [aziendaId, refetchSaved]);

  // --- Female workers list --------------------------------------------
  useEffect(() => {
    let cancelled = false;
    async function loadWorkers() {
      setWorkersLoading(true);
      try {
        const headers = await authHeaders();
        const res = await fetch(
          `${API_URL}/api/v1/aziende/${aziendaId}/persone`,
          { headers },
        );
        if (!res.ok) throw new Error(`Errore ${res.status}`);
        const data = (await res.json()) as Persona[];
        if (cancelled) return;
        const females = data
          .filter((p) => p.sesso === "F")
          .map((p) => ({
            id: p.id,
            nominativo: p.nominativo,
            mansione: p.mansione,
          }));
        setWorkers(females);
      } catch (err) {
        if (!cancelled) {
          setMatchError(
            err instanceof Error
              ? err.message
              : "Impossibile caricare le lavoratrici",
          );
        }
      } finally {
        if (!cancelled) setWorkersLoading(false);
      }
    }
    if (aziendaId) loadWorkers();
    return () => {
      cancelled = true;
    };
  }, [aziendaId]);

  // --- Cross-reference: fire whenever the selected worker changes ------
  const runCrossReference = useCallback(
    async (workerId: string) => {
      setMatchLoading(true);
      setMatchError(null);
      try {
        const headers = await authHeaders();
        const res = await fetch(
          `${API_URL}/api/v1/aziende/${aziendaId}/gestanti/cross-reference`,
          {
            method: "POST",
            headers,
            body: JSON.stringify({ worker_id: workerId }),
          },
        );
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Errore ${res.status}`);
        }
        const data = (await res.json()) as CrossReferenceResponse;
        setMatchData(data);
      } catch (err) {
        setMatchError(
          err instanceof Error ? err.message : "Errore cross-riferimento",
        );
      } finally {
        setMatchLoading(false);
      }
    },
    [aziendaId],
  );

  useEffect(() => {
    if (selectedId) {
      runCrossReference(selectedId);
    } else {
      setMatchData(null);
    }
  }, [selectedId, runCrossReference]);

  // --- Decision flow ---------------------------------------------------
  const openDialog = useCallback((match: RiskMatch, action: "accept" | "reject") => {
    setDialogMatch(match);
    setDialogAction(action);
  }, []);

  const closeDialog = useCallback(() => {
    if (dialogBusy) return;
    setDialogMatch(null);
    setDialogAction(null);
  }, [dialogBusy]);

  const confirmDecision = useCallback(
    async (payload: {
      justification?: string;
      misura_alternativa?: string;
    }) => {
      if (!dialogMatch || !dialogAction || !matchData?.valutazione_id) {
        throw new Error(
          "Nessuna valutazione Gestanti esistente per questa lavoratrice. " +
            "Creare prima il record tramite il wizard (in arrivo).",
        );
      }
      setDialogBusy(true);
      try {
        const headers = await authHeaders();
        const res = await fetch(
          `${API_URL}/api/v1/aziende/${aziendaId}/gestanti/${matchData.valutazione_id}/decision`,
          {
            method: "POST",
            headers,
            body: JSON.stringify({
              risk_key: dialogMatch.risk_key,
              action: dialogAction,
              justification: payload.justification,
              misura_alternativa: payload.misura_alternativa,
            }),
          },
        );
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Errore ${res.status}`);
        }
        // Success: re-run the cross-reference so the decision badge is reflected.
        await runCrossReference(matchData.worker_id);
        setDialogMatch(null);
        setDialogAction(null);
      } finally {
        setDialogBusy(false);
      }
    },
    [aziendaId, dialogAction, dialogMatch, matchData, runCrossReference],
  );

  const markDirty = useCallback(() => setDirty(true), []);

  // Hydrate the signature/state block from the existing GestantiValutazione
  // whenever a worker is selected and the cross-reference returned a real
  // valutazione_id. Without this the operator sees stale firmwide state from
  // the previously selected worker.
  useEffect(() => {
    if (!matchData?.valutazione_id) return;
    let cancelled = false;
    async function loadDetails() {
      try {
        const headers = await authHeaders();
        const res = await fetch(
          `${API_URL}/api/v1/aziende/${aziendaId}/gestanti/${matchData?.valutazione_id}`,
          { headers },
        );
        if (!res.ok) return;
        const data = (await res.json()) as {
          stato: "gestante" | "puerpera" | "allattamento";
          data_notifica: string | null;
          data_presunto_parto: string | null;
          firma_lavoratrice: string | null;
          firma_datore_lavoro: string | null;
          firma_rspp: string | null;
          firma_medico_competente: string | null;
        };
        if (cancelled) return;
        setStato(data.stato || "gestante");
        setDataNotifica(data.data_notifica || "");
        setDataPresuntoParto(data.data_presunto_parto || "");
        setFirmaLavoratrice(data.firma_lavoratrice || "");
        setFirmaDdl(data.firma_datore_lavoro || "");
        setFirmaRspp(data.firma_rspp || "");
        setFirmaMedico(data.firma_medico_competente || "");
        setDirty(false);
      } catch {
        /* ignore — best-effort hydration */
      }
    }
    loadDetails();
    return () => {
      cancelled = true;
    };
  }, [aziendaId, matchData?.valutazione_id]);

  const handleSave = useCallback(async () => {
    if (!selectedId) {
      setSaveMessage("Seleziona prima una lavoratrice.");
      return;
    }
    setSaving(true);
    setSaveMessage(null);
    try {
      const headers = await authHeaders();
      const valId = matchData?.valutazione_id;
      const body = JSON.stringify({
        stato,
        data_notifica: dataNotifica || null,
        data_presunto_parto: dataPresuntoParto || null,
        firma_lavoratrice: firmaLavoratrice || null,
        firma_datore_lavoro: firmaDdl || null,
        firma_rspp: firmaRspp || null,
        firma_medico_competente: firmaMedico || null,
      });
      const res = valId
        ? await fetch(
            `${API_URL}/api/v1/aziende/${aziendaId}/gestanti/${valId}`,
            { method: "PATCH", headers, body },
          )
        : await fetch(`${API_URL}/api/v1/aziende/${aziendaId}/gestanti`, {
            method: "POST",
            headers,
            body: JSON.stringify({
              persona_id: selectedId,
              stato,
              data_notifica: dataNotifica || null,
              data_presunto_parto: dataPresuntoParto || null,
              firma_lavoratrice: firmaLavoratrice || null,
              firma_datore_lavoro: firmaDdl || null,
              firma_rspp: firmaRspp || null,
              firma_medico_competente: firmaMedico || null,
            }),
          });
      if (!res.ok) {
        const parsed = await parseApiError(res);
        throw new Error(parsed.message);
      }
      setDirty(false);
      setSaveMessage("Valutazione salvata.");
      // Refresh cross-reference to surface the new valutazione_id if created,
      // and refresh the list of saved records.
      if (selectedId) await runCrossReference(selectedId);
      await refetchSaved();
    } catch (err) {
      setSaveMessage(
        err instanceof Error ? `Errore: ${err.message}` : "Errore sconosciuto",
      );
    } finally {
      setSaving(false);
    }
  }, [
    aziendaId,
    selectedId,
    matchData,
    stato,
    dataNotifica,
    dataPresuntoParto,
    firmaLavoratrice,
    firmaDdl,
    firmaRspp,
    firmaMedico,
    runCrossReference,
    refetchSaved,
  ]);

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
            <Badge variant="secondary">Allegato Gestanti</Badge>
            <span>D.Lgs. 151/2001 · Allegati A / B / C</span>
            {dirty && (
              <Badge variant="outline" className="border-amber-500/50 text-amber-700">
                Modifiche non salvate
              </Badge>
            )}
          </div>
          <h1 className="mt-2 type-h1">
            Valutazione Gestanti / Puerpere / Allattamento
          </h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
      </div>

      {savedRows.length > 0 && (
        <Card className="border-emerald-200/60 bg-emerald-50/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">
              Valutazioni archiviate ({savedRows.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-2 md:grid-cols-3">
              {savedRows.map((r) => {
                const w = workers.find((x) => x.id === r.persona_id);
                return (
                  <li
                    key={r.id}
                    className="flex items-center justify-between rounded-md bg-background px-3 py-2 ring-1 ring-border"
                  >
                    <button
                      type="button"
                      className="truncate text-left hover:underline"
                      onClick={() => setSelectedId(r.persona_id)}
                    >
                      {w?.nominativo || "Lavoratrice"}
                    </button>
                    <Badge variant="outline" className="capitalize">
                      {r.stato}
                    </Badge>
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      )}

      <WorkerSelector
        workers={workers}
        selectedId={selectedId}
        onSelect={setSelectedId}
        loading={workersLoading}
      />

      {matchLoading && (
        <p className="text-sm text-muted-foreground">Cross-riferimento in corso…</p>
      )}
      {matchError && (
        <p className="text-sm text-destructive" role="alert">
          {matchError}
        </p>
      )}

      <MatchesPanel data={matchData} onDecide={openDialog} />

      {/* Dati lavoratrice & firme */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">
            Dati lavoratrice & firme
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="stato">Stato</Label>
            <select
              id="stato"
              value={stato}
              onChange={(e) => {
                setStato(
                  e.target.value as "gestante" | "puerpera" | "allattamento",
                );
                markDirty();
              }}
              className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm"
            >
              <option value="gestante">Gestante</option>
              <option value="puerpera">Puerpera (fino a 7 mesi)</option>
              <option value="allattamento">Allattamento</option>
            </select>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="notifica">Data notifica</Label>
              <Input
                id="notifica"
                type="date"
                value={dataNotifica}
                onChange={(e) => {
                  setDataNotifica(e.target.value);
                  markDirty();
                }}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="parto">Data presunto parto</Label>
              <Input
                id="parto"
                type="date"
                value={dataPresuntoParto}
                onChange={(e) => {
                  setDataPresuntoParto(e.target.value);
                  markDirty();
                }}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="grid gap-1">
              <Label htmlFor="firma-lav">Firma lavoratrice</Label>
              <Input
                id="firma-lav"
                value={firmaLavoratrice}
                onChange={(e) => {
                  setFirmaLavoratrice(e.target.value);
                  markDirty();
                }}
              />
            </div>
            <div className="grid gap-1">
              <Label htmlFor="firma-ddl">Firma Datore di Lavoro</Label>
              <Input
                id="firma-ddl"
                value={firmaDdl}
                onChange={(e) => {
                  setFirmaDdl(e.target.value);
                  markDirty();
                }}
              />
            </div>
            <div className="grid gap-1">
              <Label htmlFor="firma-rspp">Firma RSPP</Label>
              <Input
                id="firma-rspp"
                value={firmaRspp}
                onChange={(e) => {
                  setFirmaRspp(e.target.value);
                  markDirty();
                }}
              />
            </div>
            <div className="grid gap-1">
              <Label htmlFor="firma-mc">Firma Medico Competente</Label>
              <Input
                id="firma-mc"
                value={firmaMedico}
                onChange={(e) => {
                  setFirmaMedico(e.target.value);
                  markDirty();
                }}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Riferimento normativo */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Riferimento normativo</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Il D.Lgs. 26 marzo 2001 n. 151 tutela la salute delle lavoratrici in
            stato di gravidanza, puerperio e durante l&apos;allattamento. Gli
            Allegati A, B e C individuano rispettivamente i lavori vietati,
            quelli vietati salvo deroga e gli agenti nocivi cui la lavoratrice
            non puo&apos; essere esposta senza valutazione specifica.
          </p>
        </CardContent>
      </Card>

      {/* Salva */}
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div>
            <p className="text-sm font-medium">Salva valutazione</p>
            <p className="text-xs text-muted-foreground">
              Le decisioni di riallocazione vengono salvate in tempo reale.
              Firme e stato vengono persistiti al click di &quot;Salva&quot;.
            </p>
            {saveMessage && (
              <p
                className={
                  saveMessage.startsWith("Errore")
                    ? "mt-1 text-xs text-destructive"
                    : "mt-1 text-xs text-emerald-700"
                }
              >
                {saveMessage}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" disabled={saving} onClick={() => setDirty(false)}>
              Annulla modifiche
            </Button>
            <Button disabled={saving} onClick={handleSave}>
              {saving ? "Salvataggio…" : "Salva valutazione"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <RelocationDialog
        match={dialogMatch}
        action={dialogAction}
        onClose={closeDialog}
        onConfirm={confirmDecision}
        busy={dialogBusy}
      />
    </div>
  );
}

