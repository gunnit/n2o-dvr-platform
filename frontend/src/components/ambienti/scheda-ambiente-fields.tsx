"use client";

/**
 * Scheda ambiente — the per-room facts the incendio allegato and the PEE
 * both print (segnalazioni 2026-08-25): description of the room, materials
 * present, maximum number of people, possible ignition sources.
 *
 * The fields live on the Ambiente row so the operator enters them once,
 * from either assessment. Three of them can be proposed from the photos
 * uploaded in step-ambienti ("Compila da foto"); the proposal is shown,
 * inserted into the inputs only when the operator asks, and saved only
 * when they press Salva. Persone max is never proposed.
 */

import { useEffect, useState } from "react";
import { Loader2, Save, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useApi } from "@/hooks/use-api";
import type { Ambiente } from "@/types";

interface SchedaProposal {
  descrizione_locale: string;
  materiali_presenti: string;
  sorgenti_innesco: string;
  motivazione: string;
  photos_used: number;
}

interface SchedaDraft {
  descrizione_locale: string;
  materiali_presenti: string;
  max_persone: string;
  sorgenti_innesco: string;
}

type TextKey = "descrizione_locale" | "materiali_presenti" | "sorgenti_innesco";

const PROPOSED_KEYS: readonly TextKey[] = [
  "descrizione_locale",
  "materiali_presenti",
  "sorgenti_innesco",
];

function draftFrom(ambiente: Ambiente): SchedaDraft {
  return {
    descrizione_locale: ambiente.descrizione_locale ?? "",
    materiali_presenti: ambiente.materiali_presenti ?? "",
    max_persone:
      ambiente.max_persone == null ? "" : String(ambiente.max_persone),
    sorgenti_innesco: ambiente.sorgenti_innesco ?? "",
  };
}

export interface SchedaAmbienteFieldsProps {
  ambiente: Ambiente;
  /** Fires with the server's copy after a successful save. */
  onSaved?: (ambiente: Ambiente) => void;
}

export function SchedaAmbienteFields({
  ambiente,
  onSaved,
}: SchedaAmbienteFieldsProps) {
  const { apiFetch } = useApi();
  const [draft, setDraft] = useState<SchedaDraft>(() => draftFrom(ambiente));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [proposal, setProposal] = useState<SchedaProposal | null>(null);
  // Fields currently holding AI text the operator has not edited yet —
  // badged so the provenance is visible until they touch or save them.
  const [aiFilled, setAiFilled] = useState<ReadonlySet<TextKey>>(new Set());

  const {
    id: ambienteId,
    descrizione_locale: savedDescrizione,
    materiali_presenti: savedMateriali,
    max_persone: savedMaxPersone,
    sorgenti_innesco: savedInnesco,
  } = ambiente;
  useEffect(() => {
    // Re-seed when the row changes underneath (another card saved it, or
    // the parent swapped the linked ambiente).
    setDraft({
      descrizione_locale: savedDescrizione ?? "",
      materiali_presenti: savedMateriali ?? "",
      max_persone: savedMaxPersone == null ? "" : String(savedMaxPersone),
      sorgenti_innesco: savedInnesco ?? "",
    });
    setDirty(false);
    setProposal(null);
    setAiFilled(new Set());
  }, [ambienteId, savedDescrizione, savedMateriali, savedMaxPersone, savedInnesco]);

  const setField = (key: keyof SchedaDraft, value: string) => {
    setDraft((d) => ({ ...d, [key]: value }));
    setDirty(true);
    setAiFilled((prev) => {
      if (!prev.has(key as TextKey)) return prev;
      const next = new Set(prev);
      next.delete(key as TextKey);
      return next;
    });
  };

  async function save() {
    const maxRaw = draft.max_persone.trim();
    const max = maxRaw === "" ? null : Number(maxRaw);
    if (max !== null && (!Number.isInteger(max) || max < 0)) {
      toast.error("Persone max deve essere un numero intero maggiore o uguale a 0.");
      return;
    }
    setSaving(true);
    try {
      const updated = await apiFetch<Ambiente>(
        `/api/v1/aziende/${ambiente.azienda_id}/ambienti/${ambiente.id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            descrizione_locale: draft.descrizione_locale.trim() || null,
            materiali_presenti: draft.materiali_presenti.trim() || null,
            max_persone: max,
            sorgenti_innesco: draft.sorgenti_innesco.trim() || null,
          }),
        },
      );
      setDirty(false);
      setAiFilled(new Set());
      toast.success(`Scheda "${ambiente.nome}" salvata.`);
      onSaved?.(updated);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Salvataggio della scheda non riuscito.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function extract() {
    setExtracting(true);
    try {
      const p = await apiFetch<SchedaProposal>(
        `/api/v1/aziende/${ambiente.azienda_id}/ambienti/${ambiente.id}/scheda/estrai-foto`,
        { method: "POST" },
      );
      setProposal(p);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Analisi delle foto non riuscita.",
      );
    } finally {
      setExtracting(false);
    }
  }

  function applyProposal() {
    if (!proposal) return;
    const filled = new Set<TextKey>();
    setDraft((d) => {
      const next = { ...d };
      for (const key of PROPOSED_KEYS) {
        const value = proposal[key].trim();
        if (value) {
          next[key] = value;
          filled.add(key);
        }
      }
      return next;
    });
    setAiFilled(filled);
    setDirty(true);
    setProposal(null);
    toast.info("Testi proposti inseriti nei campi: controllali, poi salva la scheda.");
  }

  const fieldId = (key: keyof SchedaDraft) => `scheda-${ambiente.id}-${key}`;

  return (
    <div className="space-y-3 rounded-md border bg-muted/10 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-sm font-medium">Scheda ambiente</h4>
            <Badge variant="outline" className="text-[10px]">
              Condivisa con Rischio Incendio e PEE
            </Badge>
          </div>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            Descrizione del locale, materiali presenti, affollamento massimo e
            sorgenti di innesco. Inserita una volta, stampata in entrambi gli
            allegati.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={extract}
          disabled={extracting || saving}
          title="Propone descrizione, materiali e sorgenti di innesco dalle foto caricate per questo ambiente (4 crediti AI). Persone max resta a cura dell'operatore."
        >
          {extracting ? (
            <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Sparkles className="mr-1 h-3.5 w-3.5" />
          )}
          Compila da foto
        </Button>
      </div>

      {proposal && (
        <div className="space-y-2 rounded-md border border-[rgba(0,61,116,0.25)] bg-[rgba(0,61,116,0.04)] p-3 text-xs">
          <div className="flex items-center gap-2">
            <Badge variant="ai" className="text-[9px]">
              Proposta AI
            </Badge>
            <span className="text-muted-foreground">
              da {proposal.photos_used} foto — non ancora salvata
            </span>
          </div>
          <div>
            <span className="font-medium">Descrizione: </span>
            {proposal.descrizione_locale || "—"}
          </div>
          <div>
            <span className="font-medium">Materiali: </span>
            {proposal.materiali_presenti || "—"}
          </div>
          <div>
            <span className="font-medium">Sorgenti di innesco: </span>
            {proposal.sorgenti_innesco || "—"}
          </div>
          {proposal.motivazione && (
            <p className="italic text-muted-foreground">{proposal.motivazione}</p>
          )}
          <div className="flex gap-2 pt-1">
            <Button type="button" size="sm" onClick={applyProposal}>
              Inserisci nei campi
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setProposal(null)}
            >
              Scarta
            </Button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Label htmlFor={fieldId("descrizione_locale")} className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Descrizione del locale
            {aiFilled.has("descrizione_locale") && (
              <Badge variant="ai" className="ml-2 text-[9px]">AI · da verificare</Badge>
            )}
          </Label>
          <Textarea
            id={fieldId("descrizione_locale")}
            rows={2}
            placeholder="Es. Capannone in muratura di 120 mq, soffitto in lamiera coibentata, due portoni carrai…"
            value={draft.descrizione_locale}
            onChange={(e) => setField("descrizione_locale", e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor={fieldId("materiali_presenti")} className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Materiali presenti
            {aiFilled.has("materiali_presenti") && (
              <Badge variant="ai" className="ml-2 text-[9px]">AI · da verificare</Badge>
            )}
          </Label>
          <Textarea
            id={fieldId("materiali_presenti")}
            rows={2}
            placeholder="Es. Scaffalature metalliche; imballaggi in cartone; bancali in legno"
            value={draft.materiali_presenti}
            onChange={(e) => setField("materiali_presenti", e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor={fieldId("sorgenti_innesco")} className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Possibili sorgenti di innesco
            {aiFilled.has("sorgenti_innesco") && (
              <Badge variant="ai" className="ml-2 text-[9px]">AI · da verificare</Badge>
            )}
          </Label>
          <Textarea
            id={fieldId("sorgenti_innesco")}
            rows={2}
            placeholder="Es. Quadro elettrico; forno; lavorazioni a caldo"
            value={draft.sorgenti_innesco}
            onChange={(e) => setField("sorgenti_innesco", e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor={fieldId("max_persone")} className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Persone max presenti
          </Label>
          <Input
            id={fieldId("max_persone")}
            type="number"
            min={0}
            step={1}
            inputMode="numeric"
            placeholder="Es. 12"
            value={draft.max_persone}
            onChange={(e) => setField("max_persone", e.target.value)}
          />
          <p className="mt-1 text-[11px] text-muted-foreground">
            Dato dell&apos;operatore: non viene proposto dalle foto.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-end gap-2">
        {dirty && (
          <span className="text-[11px] text-muted-foreground">Modifiche non salvate</span>
        )}
        <Button
          type="button"
          size="sm"
          onClick={save}
          disabled={!dirty || saving || extracting}
        >
          {saving ? (
            <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Save className="mr-1 h-3.5 w-3.5" />
          )}
          Salva scheda
        </Button>
      </div>
    </div>
  );
}
