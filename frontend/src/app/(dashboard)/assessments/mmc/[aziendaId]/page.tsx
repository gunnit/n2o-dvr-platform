"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  MmcForm,
  type LiftValues,
  type MmcFormValues,
  type MmcResult,
} from "@/components/assessments/mmc/mmc-form";
import {
  extractAge,
  extractSex,
  fasciaEtaFromAge,
} from "@/lib/codice-fiscale";
import type { Azienda } from "@/types";

interface PersonaOption {
  id: string;
  nominativo: string;
  mansione: string | null;
  codice_fiscale: string | null;
  sesso: string | null;
}

interface MmcValutazioneRow {
  id: string;
  persona_id: string | null;
  compito: string;
  indice_ir: number | null;
  livello_rischio: string | null;
  area_classificazione: string | null;
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

const DURATION_TO_MIN: Record<"breve" | "media" | "lunga", number> = {
  breve: 30,
  media: 90,
  lunga: 240,
};

const GRIP_TO_LABEL: Record<"buona" | "discreta" | "scarsa", "Buono" | "Discreto" | "Scarso"> = {
  buona: "Buono",
  discreta: "Discreto",
  scarsa: "Scarso",
};

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

export default function MmcAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [persone, setPersone] = useState<PersonaOption[]>([]);
  const [existingValutazioni, setExistingValutazioni] = useState<MmcValutazioneRow[]>([]);
  const [selectedPersonaId, setSelectedPersonaId] = useState<string>("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeMessage, setFinalizeMessage] = useState<string | null>(null);

  const refetchValutazioni = useCallback(async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const headers = await authHeaders();
      const res = await fetch(
        `${apiUrl}/api/v1/aziende/${aziendaId}/mmc`,
        { headers },
      );
      if (res.ok) {
        const rows = (await res.json()) as MmcValutazioneRow[];
        setExistingValutazioni(Array.isArray(rows) ? rows : []);
      }
    } catch {
      /* noop */
    }
  }, [aziendaId]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const headers = await authHeaders();
        const [azRes, persRes, mmcRes] = await Promise.all([
          fetch(`${apiUrl}/api/v1/aziende/${aziendaId}`, { headers }),
          fetch(`${apiUrl}/api/v1/aziende/${aziendaId}/persone`, { headers }),
          fetch(`${apiUrl}/api/v1/aziende/${aziendaId}/mmc`, { headers }),
        ]);
        if (!azRes.ok) throw new Error(`Errore ${azRes.status}`);
        const azData = (await azRes.json()) as Azienda;
        if (!cancelled) setAzienda(azData);
        if (persRes.ok) {
          const persData = (await persRes.json()) as PersonaOption[];
          if (!cancelled) {
            setPersone(persData);
            if (persData.length && !selectedPersonaId) {
              setSelectedPersonaId(persData[0].id);
            }
          }
        }
        if (mmcRes.ok) {
          const mmcData = (await mmcRes.json()) as MmcValutazioneRow[];
          if (!cancelled) {
            setExistingValutazioni(Array.isArray(mmcData) ? mmcData : []);
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
    // selectedPersonaId intentionally excluded — we only seed it on first load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aziendaId]);

  // Most-recent valutazione per persona_id, for "Già valutati" surfacing.
  const valutatePerPersona = useMemo(() => {
    const map = new Map<string, MmcValutazioneRow>();
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

  const pageSubtitle = useMemo(() => {
    if (loadError) return `Azienda ${aziendaId} (metadati non disponibili)`;
    if (azienda) return azienda.ragione_sociale ?? `Azienda ${aziendaId}`;
    return "Caricamento in corso...";
  }, [azienda, aziendaId, loadError]);

  // CF-derived worker metadata for the currently selected persona. Used to
  // pre-fill MmcForm.initialValues so the operator doesn't manually pick the
  // age band when the CF already encodes it (admin feedback 2026-05-04 #1).
  const selectedPersona = useMemo(
    () => persone.find((p) => p.id === selectedPersonaId) ?? null,
    [persone, selectedPersonaId],
  );

  const cfDerived = useMemo(() => {
    if (!selectedPersona?.codice_fiscale) return null;
    const age = extractAge(selectedPersona.codice_fiscale);
    if (age === null) return null;
    const sex = extractSex(selectedPersona.codice_fiscale);
    return {
      age,
      sex: sex ?? (selectedPersona.sesso === "F" ? "F" : "M"),
    } as const;
  }, [selectedPersona]);

  // Pass to MmcForm via initialValues. We also key the form by personaId so
  // changing the dropdown remounts with the right defaults — this avoids
  // mutating an in-progress form state for a different worker.
  const formInitialValues = useMemo<Partial<MmcFormValues> | undefined>(() => {
    if (!cfDerived) return undefined;
    return {
      worker_eta: Math.max(15, Math.min(70, cfDerived.age)),
      worker_sesso: cfDerived.sex,
    };
  }, [cfDerived]);

  const handleFinalize = async (values: MmcFormValues, result: MmcResult) => {
    setFinalizing(true);
    setFinalizeMessage(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const headers = await authHeaders();

      if (!values.lifts.length) {
        throw new Error("Aggiungi almeno un sollevamento prima di salvare.");
      }

      const personaId = selectedPersonaId || null;
      // Prefer CF-derived age band when available; falls back to the
      // form's worker_eta value (manual entry).
      const ageForBand = cfDerived?.age ?? values.worker_eta;
      const fasciaEta = fasciaEtaFromAge(ageForBand);
      const measuresText = (values.measures ?? []).filter(Boolean).join("\n");

      // Persist one MmcValutazione per lift. Server runs NIOSH math from
      // inputs (single source of truth in app.data.niosh_factors) and
      // returns the persisted row with derived multipliers + IR + zone.
      const created = [];
      for (let i = 0; i < values.lifts.length; i++) {
        const lift: LiftValues = values.lifts[i];
        const body = {
          persona_id: personaId,
          compito: lift.name?.trim() || `Sollevamento ${i + 1}`,
          peso_kg: lift.peso_reale,
          sesso: values.worker_sesso,
          fascia_eta: fasciaEta,
          altezza_cm: Math.round(lift.altezza),
          dislocazione_cm: Math.round(lift.dislocazione),
          distanza_cm: Math.round(lift.distanza),
          angolo_gradi: Math.round(lift.angolo),
          giudizio_presa: GRIP_TO_LABEL[lift.presa],
          frequenza_atti_min: lift.frequenza,
          durata_min: DURATION_TO_MIN[lift.durata],
          cp: values.cp_override,
          note: values.cp_motivazione || null,
          misure_proposte: measuresText || null,
        };
        const res = await fetch(
          `${apiUrl}/api/v1/aziende/${aziendaId}/mmc`,
          { method: "POST", headers, body: JSON.stringify(body) },
        );
        if (!res.ok) {
          const detail = await res.text().catch(() => "");
          throw new Error(`API error ${res.status}: ${detail.slice(0, 200)}`);
        }
        const data = await res.json();
        created.push(data);
      }

      const worstIr = result.worst?.ir ?? 0;
      setFinalizeMessage(
        `Valutazione MMC archiviata: ${created.length} sollevamento/i salvati nel DVR. ` +
          `IR peggiore ${worstIr.toFixed(2)} - ` +
          `zona ${result.worst?.zona ?? "—"}.`,
      );
      // Re-fetch so the "Già valutati" badge reflects the new rows.
      await refetchValutazioni();
    } catch (err) {
      setFinalizeMessage(
        err instanceof Error
          ? `Errore salvataggio: ${err.message}`
          : "Errore salvataggio sconosciuto",
      );
    } finally {
      setFinalizing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
            <Badge variant="secondary">Allegato Rischio MMC</Badge>
            <span>D.Lgs. 81/2008 · NIOSH ISO 11228-1</span>
          </div>
          <h1 className="mt-2 type-h1">
            Valutazione Movimentazione Manuale dei Carichi
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
                Lavoratori con almeno un sollevamento MMC in archivio.
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
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      )}

      {persone.length > 0 && (
        <div className="rounded-md border bg-card px-4 py-3">
          <label
            htmlFor="mmc-persona"
            className="block text-xs font-medium uppercase tracking-wide text-muted-foreground"
          >
            Lavoratore valutato
          </label>
          <select
            id="mmc-persona"
            value={selectedPersonaId}
            onChange={(e) => setSelectedPersonaId(e.target.value)}
            className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
          >
            <option value="">— Nessun lavoratore (valutazione generica) —</option>
            {persone.map((p) => {
              const v = valutatePerPersona.get(p.id);
              return (
                <option key={p.id} value={p.id}>
                  {p.nominativo}
                  {p.mansione ? ` — ${p.mansione}` : ""}
                  {v ? ` ✓ valutato il ${formatDateIt(v.created_at)}` : ""}
                </option>
              );
            })}
          </select>
          {cfDerived && (
            <p className="mt-2 text-xs text-muted-foreground">
              (età {cfDerived.age}
              {cfDerived.sex ? `, sesso ${cfDerived.sex}` : ""}, dedotta da CF)
            </p>
          )}
        </div>
      )}

      {finalizeMessage && (
        <div
          className={cn(
            "rounded-md border px-4 py-3 text-sm",
            finalizeMessage.startsWith("Errore")
              ? "border-rose-300 bg-rose-100 text-rose-900"
              : "border-emerald-300 bg-emerald-100 text-emerald-900",
          )}
        >
          {finalizeMessage}
        </div>
      )}

      <MmcForm
        // Remount when persona changes so CF-derived defaults take effect.
        // The form state is per-worker anyway, so resetting on switch is the
        // expected UX (and avoids stale lifts carrying over).
        key={selectedPersonaId || "no-persona"}
        aziendaId={aziendaId}
        finalizing={finalizing}
        initialValues={formInitialValues}
        onFinalize={handleFinalize}
      />
    </div>
  );
}
