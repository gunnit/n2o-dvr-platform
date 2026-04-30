"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  MmcForm,
  type LiftValues,
  type MmcFormValues,
  type MmcResult,
} from "@/components/assessments/mmc/mmc-form";
import type { Azienda } from "@/types";

interface PersonaOption {
  id: string;
  nominativo: string;
  mansione: string | null;
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
  const [selectedPersonaId, setSelectedPersonaId] = useState<string>("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeMessage, setFinalizeMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const headers = await authHeaders();
        const [azRes, persRes] = await Promise.all([
          fetch(`${apiUrl}/api/v1/aziende/${aziendaId}`, { headers }),
          fetch(`${apiUrl}/api/v1/aziende/${aziendaId}/persone`, { headers }),
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

  const pageSubtitle = useMemo(() => {
    if (loadError) return `Azienda ${aziendaId} (metadati non disponibili)`;
    if (azienda) return azienda.ragione_sociale ?? `Azienda ${aziendaId}`;
    return "Caricamento in corso...";
  }, [azienda, aziendaId, loadError]);

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
      const fasciaEta = values.worker_eta >= 18 ? ">18" : "15-18";
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
            {persone.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nominativo}
                {p.mansione ? ` — ${p.mansione}` : ""}
              </option>
            ))}
          </select>
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
        aziendaId={aziendaId}
        finalizing={finalizing}
        onFinalize={handleFinalize}
      />
    </div>
  );
}
