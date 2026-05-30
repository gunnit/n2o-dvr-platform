"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Pencil, Trash2, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { parseApiError } from "@/lib/api-errors";
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
  peso_kg: number;
  sesso: string;
  fascia_eta: string;
  altezza_cm: number | null;
  dislocazione_cm: number | null;
  distanza_cm: number | null;
  angolo_gradi: number | null;
  giudizio_presa: string | null;
  frequenza_atti_min: number | null;
  durata_min: number | null;
  cp: number | null;
  indice_ir: number | null;
  livello_rischio: string | null;
  area_classificazione: string | null;
  note: string | null;
  misure_proposte: string | null;
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

const LABEL_TO_GRIP: Record<string, "buona" | "discreta" | "scarsa"> = {
  Buono: "buona",
  Discreto: "discreta",
  Scarso: "scarsa",
};

const MIN_TO_DURATION: Record<number, "breve" | "media" | "lunga"> = {
  30: "breve",
  90: "media",
  240: "lunga",
};

/** Convert saved API rows for one persona back into MmcFormValues for editing. */
function rowsToFormValues(
  rows: MmcValutazioneRow[],
): Partial<MmcFormValues> {
  const first = rows[0];
  if (!first) return {};

  const lifts: LiftValues[] = rows.map((r, i) => ({
    name: r.compito || `Sollevamento ${i + 1}`,
    altezza: r.altezza_cm ?? 75,
    dislocazione: r.dislocazione_cm ?? 25,
    distanza: r.distanza_cm ?? 25,
    angolo: r.angolo_gradi ?? 0,
    presa: LABEL_TO_GRIP[r.giudizio_presa ?? ""] ?? "buona",
    frequenza: r.frequenza_atti_min ?? 1,
    durata: MIN_TO_DURATION[r.durata_min ?? 30] ?? "breve",
    peso_reale: r.peso_kg ?? 10,
  }));

  return {
    worker_sesso: first.sesso === "F" ? "F" : "M",
    worker_eta: 30, // will be overridden by CF-derived if available
    cp_override: first.cp ?? undefined,
    cp_motivazione: first.note ?? "",
    lifts,
    measures: first.misure_proposte
      ? first.misure_proposte.split("\n").filter(Boolean)
      : [],
  };
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

  // Edit-mode state: when non-null, the form is pre-filled with existing
  // assessment data and saves via PATCH instead of POST.
  const [editingIds, setEditingIds] = useState<string[] | null>(null);
  const [editFormKey, setEditFormKey] = useState(0);

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

  const deleteValutazione = useCallback(
    async (personaId: string, nominativo: string) => {
      // Find all assessment rows for this persona.
      const rows = existingValutazioni.filter(
        (r) => r.persona_id === personaId,
      );
      if (!rows.length) return;

      const countLabel =
        rows.length === 1
          ? "la valutazione MMC"
          : `tutte le ${rows.length} valutazioni MMC`;
      if (
        !window.confirm(
          `Sei sicuro di voler eliminare ${countLabel} di ${nominativo}? L'operazione è irreversibile.`,
        )
      ) {
        return;
      }
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const headers = await authHeaders();
        for (const row of rows) {
          const res = await fetch(
            `${apiUrl}/api/v1/aziende/${aziendaId}/mmc/${row.id}`,
            { method: "DELETE", headers },
          );
          if (!res.ok && res.status !== 204) {
            throw new Error(`Errore ${res.status}`);
          }
        }
        // If we were editing this persona, exit edit mode.
        if (editingIds && selectedPersonaId === personaId) {
          setEditingIds(null);
          setEditFormKey((k) => k + 1);
        }
        await refetchValutazioni();
      } catch (err) {
        setLoadError(
          err instanceof Error ? err.message : "Eliminazione fallita",
        );
      }
    },
    [aziendaId, existingValutazioni, editingIds, selectedPersonaId, refetchValutazioni],
  );

  /** Jump to a persona's existing assessment — selecting them is enough,
   * the auto-sync effect below pulls their saved data into the form. */
  const startEditing = useCallback(
    (personaId: string) => {
      setSelectedPersonaId(personaId);
      setFinalizeMessage(null);
    },
    [],
  );

  /** Discard any unsaved changes by remounting the form. editingIds stays
   * set so the next save still PATCHes the same rows. */
  const cancelEditing = useCallback(() => {
    setEditFormKey((k) => k + 1);
    setFinalizeMessage(null);
  }, []);

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

  // Auto-sync edit mode with the selected persona's existing assessments.
  // When a persona with saved data is picked (from the dropdown OR auto-
  // selected on first load), pre-fill the form with what's already in the
  // DVR. Before this, the form opened blank for already-evaluated workers,
  // making operators think their data hadn't been saved (Luca, 2026-05-28).
  useEffect(() => {
    const rowsForPersona = selectedPersonaId
      ? existingValutazioni
          .filter((r) => r.persona_id === selectedPersonaId)
          .sort(
            (a, b) =>
              new Date(a.created_at).getTime() -
              new Date(b.created_at).getTime(),
          )
      : [];

    if (rowsForPersona.length > 0) {
      const newIds = rowsForPersona.map((r) => r.id);
      const sameAsCurrent =
        editingIds !== null &&
        editingIds.length === newIds.length &&
        editingIds.every((id, i) => id === newIds[i]);
      if (!sameAsCurrent) {
        setEditingIds(newIds);
        setEditFormKey((k) => k + 1);
      }
    } else if (editingIds !== null) {
      setEditingIds(null);
      setEditFormKey((k) => k + 1);
    }
    // editingIds intentionally excluded — it's read as a guard but only
    // re-assigned when (selectedPersonaId, existingValutazioni) imply a
    // different value, so listing it would create a feedback loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPersonaId, existingValutazioni]);

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

  // When editing, compute form values from the saved rows.
  const editFormValues = useMemo<Partial<MmcFormValues> | undefined>(() => {
    if (!editingIds) return undefined;
    const rows = existingValutazioni.filter((r) => editingIds.includes(r.id));
    if (!rows.length) return undefined;
    return rowsToFormValues(rows);
  }, [editingIds, existingValutazioni]);

  // Pass to MmcForm via initialValues. We also key the form by personaId so
  // changing the dropdown remounts with the right defaults — this avoids
  // mutating an in-progress form state for a different worker.
  // In edit mode, merge CF-derived age/sex on top of the saved data.
  const formInitialValues = useMemo<Partial<MmcFormValues> | undefined>(() => {
    const cfPart = cfDerived
      ? {
          worker_eta: Math.max(15, Math.min(70, cfDerived.age)),
          worker_sesso: cfDerived.sex as "M" | "F",
        }
      : {};
    if (editFormValues) {
      return { ...editFormValues, ...cfPart };
    }
    if (Object.keys(cfPart).length) return cfPart;
    return undefined;
  }, [cfDerived, editFormValues]);

  const handleFinalize = async (
    values: MmcFormValues,
    result: MmcResult,
  ): Promise<boolean> => {
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

      // Build the payload for each lift.
      const buildBody = (lift: LiftValues, i: number) => ({
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
      });

      const saved = [];

      if (editingIds && editingIds.length > 0) {
        // ---- EDIT MODE: PATCH existing rows, POST extras, DELETE surplus ----
        for (let i = 0; i < values.lifts.length; i++) {
          const body = buildBody(values.lifts[i], i);
          if (i < editingIds.length) {
            // PATCH the existing row.
            const res = await fetch(
              `${apiUrl}/api/v1/aziende/${aziendaId}/mmc/${editingIds[i]}`,
              { method: "PATCH", headers, body: JSON.stringify(body) },
            );
            if (!res.ok) {
              const parsed = await parseApiError(res);
              throw new Error(parsed.message);
            }
            saved.push(await res.json());
          } else {
            // More lifts than before — POST the extras.
            const res = await fetch(
              `${apiUrl}/api/v1/aziende/${aziendaId}/mmc`,
              { method: "POST", headers, body: JSON.stringify(body) },
            );
            if (!res.ok) {
              const parsed = await parseApiError(res);
              throw new Error(parsed.message);
            }
            saved.push(await res.json());
          }
        }
        // If fewer lifts than before, delete the surplus rows.
        for (let i = values.lifts.length; i < editingIds.length; i++) {
          await fetch(
            `${apiUrl}/api/v1/aziende/${aziendaId}/mmc/${editingIds[i]}`,
            { method: "DELETE", headers },
          );
        }
        // editingIds gets re-synced by the auto-sync effect after refetch.
      } else {
        // ---- CREATE MODE: POST each lift as a new row ----
        for (let i = 0; i < values.lifts.length; i++) {
          const body = buildBody(values.lifts[i], i);
          const res = await fetch(
            `${apiUrl}/api/v1/aziende/${aziendaId}/mmc`,
            { method: "POST", headers, body: JSON.stringify(body) },
          );
          if (!res.ok) {
            const parsed = await parseApiError(res);
            throw new Error(parsed.message);
          }
          saved.push(await res.json());
        }
      }

      const worstIr = result.worst?.ir ?? 0;
      setFinalizeMessage(
        `Valutazione MMC archiviata: ${saved.length} sollevamento/i salvati nel DVR. ` +
          `IR peggiore ${worstIr.toFixed(2)} - ` +
          `zona ${result.worst?.zona ?? "—"}.`,
      );
      // Re-fetch so the "Già valutati" badge reflects the new/updated rows.
      await refetchValutazioni();
      // Tell MmcForm to clear its dirty state — without this the
      // "Modifiche non salvate" badge stays on after a successful save
      // and operators report "non si salva" (feedback #55).
      return true;
    } catch (err) {
      setFinalizeMessage(
        err instanceof Error
          ? `Errore salvataggio: ${err.message}`
          : "Errore salvataggio sconosciuto",
      );
      return false;
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
                const isBeingEdited =
                  editingIds !== null && selectedPersonaId === p.id;
                return (
                  <li
                    key={p.id}
                    className={cn(
                      "flex items-center gap-1 rounded-md border bg-white px-2 py-1",
                      isBeingEdited
                        ? "border-blue-400 bg-blue-50 text-blue-900"
                        : "border-emerald-300/70 text-emerald-900",
                    )}
                  >
                    <span
                      aria-hidden
                      className={
                        isBeingEdited ? "text-blue-500" : "text-emerald-600"
                      }
                    >
                      {isBeingEdited ? "..." : "✓"}
                    </span>
                    <span className="font-medium">{p.nominativo}</span>
                    {v && !isBeingEdited ? (
                      <span className="text-emerald-700/80">
                        — Valutato il {formatDateIt(v.created_at)}
                      </span>
                    ) : null}
                    {isBeingEdited ? (
                      <span className="text-blue-600/80">— In modifica</span>
                    ) : null}
                    {v && !isBeingEdited ? (
                      <button
                        type="button"
                        aria-label={`Modifica valutazione di ${p.nominativo}`}
                        title="Modifica valutazione"
                        onClick={() => startEditing(p.id)}
                        className="ml-1 inline-flex h-5 w-5 items-center justify-center rounded text-emerald-600/70 hover:bg-blue-100 hover:text-blue-700"
                      >
                        <Pencil className="h-3 w-3" />
                      </button>
                    ) : null}
                    {v ? (
                      <button
                        type="button"
                        aria-label={`Elimina valutazione di ${p.nominativo}`}
                        title="Elimina valutazione"
                        onClick={() => deleteValutazione(p.id, p.nominativo)}
                        className="ml-0.5 inline-flex h-5 w-5 items-center justify-center rounded text-emerald-600/70 hover:bg-rose-100 hover:text-rose-700"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
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
            onChange={(e) => {
              setSelectedPersonaId(e.target.value);
              setFinalizeMessage(null);
            }}
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

      {editingIds !== null && (
        <div className="flex items-center justify-between rounded-md border border-blue-300 bg-blue-50 px-4 py-3 text-sm text-blue-900">
          <span>
            Valutazione esistente caricata: il form mostra i dati già salvati
            nel DVR. Le modifiche sovrascriveranno i dati precedenti.
          </span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={cancelEditing}
            className="text-blue-700 hover:text-blue-900"
          >
            <X className="mr-1 h-4 w-4" />
            Annulla modifiche
          </Button>
        </div>
      )}

      <MmcForm
        // Remount when persona changes or when entering/exiting edit mode.
        key={`${selectedPersonaId || "no-persona"}-${editFormKey}`}
        aziendaId={aziendaId}
        finalizing={finalizing}
        initialValues={formInitialValues}
        onFinalize={handleFinalize}
      />
    </div>
  );
}
