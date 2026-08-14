"use client";

/**
 * POS cantiere cards — client request 2026-08-13 ("CAMPI DA INSERIRE
 * ALL'INTERNO DEL POS"):
 *
 * 1. Dati cantiere — indirizzo (manual), data inizio/fine lavori (manual).
 * 2. Subappalti — sì/no flag + manual list when sì.
 * 3. Dipendenti impegnati in cantiere — multi-select from the organigramma.
 * 4. Figure di sicurezza sul cantiere — per-role dropdown (persona from the
 *    organigramma or free text), prefilled from the Persona ruolo_* flags.
 * 5. Sostanze pericolose — sì/no flag + manual list when sì.
 *
 * Save strategy mirrors PosInfoEditor: optimistic setState + debounced PUT
 * to /api/v1/aziende/{id}/pos/{pos_id}, sending only the fields these cards
 * own so parallel surfaces (info cards, DPI matrix, phase builder) are never
 * clobbered.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { useApi } from "@/hooks/use-api";
import type { Persona } from "@/types";

export interface PosSubappaltatore {
  ragione_sociale: string;
  lavori: string | null;
}

export interface PosFiguraSicurezza {
  ruolo: string;
  persona_id: string | null;
  nominativo: string | null;
}

export interface PosSostanzaPericolosa {
  nome: string;
  uso: string | null;
}

/** Subset of `Pos` carrying the fields these cards own. */
export interface PosCantiereFields {
  cantiere_indirizzo: string;
  data_inizio: string | null;
  data_fine: string | null;
  subappalti_presenti: boolean;
  subappaltatori: PosSubappaltatore[];
  dipendenti_cantiere: string[];
  figure_sicurezza: PosFiguraSicurezza[];
  sostanze_pericolose_presenti: boolean;
  sostanze_pericolose: PosSostanzaPericolosa[];
}

// Canonical dropdown roles — keys mirror FIGURE_SICUREZZA_RUOLI in
// backend/app/schemas/pos.py (same key/label split as the DPI matrix).
// `prefill` picks the organigramma candidates for the role.
const FIGURE_RUOLI: Array<{
  key: string;
  label: string;
  prefill?: (p: Persona) => boolean;
}> = [
  {
    key: "datore_lavoro",
    label: "Datore di Lavoro",
    prefill: (p) => p.ruolo_datore_lavoro,
  },
  { key: "direttore_tecnico_cantiere", label: "Direttore Tecnico di Cantiere" },
  {
    key: "capocantiere_preposto",
    label: "Capocantiere / Preposto",
    prefill: (p) => p.ruolo_preposto,
  },
  { key: "rspp", label: "RSPP", prefill: (p) => p.ruolo_rspp },
  { key: "rls", label: "RLS", prefill: (p) => p.ruolo_rls },
  {
    key: "medico_competente",
    label: "Medico Competente",
    prefill: (p) => p.ruolo_medico_competente,
  },
  {
    key: "addetto_primo_soccorso",
    label: "Addetto Primo Soccorso",
    prefill: (p) => p.ruolo_primo_soccorso,
  },
  {
    key: "addetto_antincendio",
    label: "Addetto Antincendio",
    prefill: (p) => p.ruolo_antincendio,
  },
];

// Sentinel <select> value for "free text" assignment (a Persona id can
// never collide with it).
const FREE_TEXT = "__testo_libero__";

interface PosCantiereEditorProps {
  aziendaId: string;
  posId: string;
  initial: PosCantiereFields;
}

export function PosCantiereEditor({
  aziendaId,
  posId,
  initial,
}: PosCantiereEditorProps) {
  const { apiFetch, isAuthenticated } = useApi();
  const [values, setValues] = useState<PosCantiereFields>(initial);
  const [persone, setPersone] = useState<Persona[]>([]);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prefilledRef = useRef(false);

  // Re-sync when the parent reloads (e.g. after PhaseBuilder save).
  useEffect(() => {
    setValues(initial);
  }, [initial]);

  const persist = useCallback(
    async (next: PosCantiereFields) => {
      // cantiere_indirizzo is non-nullable server-side (min_length 1):
      // omit it from the payload while the operator has the field cleared.
      const { cantiere_indirizzo, ...rest } = next;
      const payload: Record<string, unknown> = {
        ...rest,
        // Rows still being typed (empty name) stay local-only until they
        // are valid — the backend rejects empty ragione_sociale/nome.
        subappaltatori: next.subappaltatori.filter((s) =>
          s.ragione_sociale.trim(),
        ),
        sostanze_pericolose: next.sostanze_pericolose.filter((s) =>
          s.nome.trim(),
        ),
      };
      if (cantiere_indirizzo.trim()) {
        payload.cantiere_indirizzo = cantiere_indirizzo.trim();
      }
      try {
        await apiFetch(`/api/v1/aziende/${aziendaId}/pos/${posId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Salvataggio non riuscito.";
        toast.error(msg);
      }
    },
    [apiFetch, aziendaId, posId],
  );

  const schedule = useCallback(
    (next: PosCantiereFields) => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => void persist(next), 600);
    },
    [persist],
  );

  const update = useCallback(
    (patch: Partial<PosCantiereFields>) => {
      setValues((prev) => {
        const next = { ...prev, ...patch };
        schedule(next);
        return next;
      });
    },
    [schedule],
  );

  // --- Organigramma load + figure prefill --------------------------------
  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const p = await apiFetch<Persona[]>(
          `/api/v1/aziende/${aziendaId}/persone`,
        );
        if (!cancelled) setPersone(p);
      } catch {
        // Non-blocking: the free-text path still works without the roster.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [aziendaId, apiFetch, isAuthenticated]);

  // Prefill the figure from the organigramma once, only while the operator
  // hasn't assigned anyone yet (platform principle: prefill what the
  // operator can correct). Persisted immediately so the generated POS sees
  // the same values the editor shows.
  useEffect(() => {
    if (prefilledRef.current) return;
    if (!persone.length) return;
    if (values.figure_sicurezza.length > 0) {
      prefilledRef.current = true;
      return;
    }
    const prefill: PosFiguraSicurezza[] = [];
    for (const ruolo of FIGURE_RUOLI) {
      if (!ruolo.prefill) continue;
      const match = persone.find((p) => ruolo.prefill?.(p));
      if (match) {
        prefill.push({
          ruolo: ruolo.key,
          persona_id: match.id,
          nominativo: match.nominativo,
        });
      }
    }
    prefilledRef.current = true;
    if (prefill.length > 0) {
      update({ figure_sicurezza: prefill });
    }
  }, [persone, values.figure_sicurezza, update]);

  // --- Figure helpers ------------------------------------------------------
  const figuraFor = (ruolo: string): PosFiguraSicurezza | undefined =>
    values.figure_sicurezza.find((f) => f.ruolo === ruolo);

  const setFigura = (ruolo: string, entry: PosFiguraSicurezza | null) => {
    const rest = values.figure_sicurezza.filter((f) => f.ruolo !== ruolo);
    update({ figure_sicurezza: entry ? [...rest, entry] : rest });
  };

  const toggleDipendente = (personaId: string) => {
    const selected = values.dipendenti_cantiere.includes(personaId);
    update({
      dipendenti_cantiere: selected
        ? values.dipendenti_cantiere.filter((id) => id !== personaId)
        : [...values.dipendenti_cantiere, personaId],
    });
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Card: Dati cantiere */}
      <Card>
        <CardHeader>
          <CardTitle>Dati cantiere</CardTitle>
          <CardDescription>
            Indirizzo del cantiere e periodo dei lavori. Questi dati vengono
            stampati nell&apos;intestazione del POS.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1 sm:col-span-2">
              <Label htmlFor="pos-cantiere-indirizzo">
                Indirizzo cantiere
              </Label>
              <Input
                id="pos-cantiere-indirizzo"
                value={values.cantiere_indirizzo}
                maxLength={500}
                placeholder="Es. Via Roma 12, 20100 Milano (MI)"
                onChange={(e) =>
                  update({ cantiere_indirizzo: e.target.value })
                }
              />
              {!values.cantiere_indirizzo.trim() && (
                <p className="text-xs text-destructive">
                  L&apos;indirizzo del cantiere è obbligatorio.
                </p>
              )}
            </div>
            <div className="space-y-1">
              <Label htmlFor="pos-data-inizio">Data inizio lavori</Label>
              <Input
                id="pos-data-inizio"
                type="date"
                value={values.data_inizio ?? ""}
                onChange={(e) =>
                  update({ data_inizio: e.target.value || null })
                }
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="pos-data-fine">Data fine lavori</Label>
              <Input
                id="pos-data-fine"
                type="date"
                value={values.data_fine ?? ""}
                onChange={(e) => update({ data_fine: e.target.value || null })}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Card: Figure di sicurezza */}
      <Card>
        <CardHeader>
          <CardTitle>Figure di sicurezza sul cantiere</CardTitle>
          <CardDescription>
            Assegna le figure dalla tendina (persone dell&apos;organigramma) o
            inserisci un nominativo libero. Le figure sono precompilate dai
            ruoli registrati in anagrafica — verifica e correggi.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            {FIGURE_RUOLI.map((ruolo) => {
              const current = figuraFor(ruolo.key);
              const selectValue = current
                ? (current.persona_id ?? FREE_TEXT)
                : "";
              return (
                <div key={ruolo.key} className="space-y-1">
                  <Label htmlFor={`pos-figura-${ruolo.key}`}>
                    {ruolo.label}
                  </Label>
                  <Select
                    id={`pos-figura-${ruolo.key}`}
                    value={selectValue}
                    onChange={(e) => {
                      const v = e.target.value;
                      if (!v) {
                        setFigura(ruolo.key, null);
                      } else if (v === FREE_TEXT) {
                        setFigura(ruolo.key, {
                          ruolo: ruolo.key,
                          persona_id: null,
                          nominativo: current?.nominativo ?? "",
                        });
                      } else {
                        const persona = persone.find((p) => p.id === v);
                        setFigura(ruolo.key, {
                          ruolo: ruolo.key,
                          persona_id: v,
                          nominativo: persona?.nominativo ?? null,
                        });
                      }
                    }}
                  >
                    <option value="">— Non nominato —</option>
                    {persone.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.nominativo}
                        {p.mansione ? ` — ${p.mansione}` : ""}
                      </option>
                    ))}
                    <option value={FREE_TEXT}>Altro (testo libero)…</option>
                  </Select>
                  {current && current.persona_id === null && (
                    <Input
                      aria-label={`Nominativo ${ruolo.label}`}
                      placeholder="Nome e cognome"
                      maxLength={255}
                      value={current.nominativo ?? ""}
                      onChange={(e) =>
                        setFigura(ruolo.key, {
                          ruolo: ruolo.key,
                          persona_id: null,
                          nominativo: e.target.value || null,
                        })
                      }
                    />
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Card: Dipendenti in cantiere */}
      <Card>
        <CardHeader>
          <CardTitle>Dipendenti che lavorano in cantiere</CardTitle>
          <CardDescription>
            Seleziona dall&apos;organigramma i dipendenti impegnati in questo
            cantiere. Se non selezioni nessuno, nel POS verranno stampati
            tutti i dipendenti registrati.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {persone.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nessun dipendente registrato in anagrafica.
            </p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {persone.map((p) => (
                <label
                  key={p.id}
                  className="flex items-center gap-2 rounded-md border p-2 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={values.dipendenti_cantiere.includes(p.id)}
                    onChange={() => toggleDipendente(p.id)}
                  />
                  <span className="font-medium">{p.nominativo}</span>
                  {p.mansione && (
                    <span className="text-muted-foreground">
                      — {p.mansione}
                    </span>
                  )}
                </label>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Card: Subappalti */}
      <Card>
        <CardHeader>
          <CardTitle>Subappalti</CardTitle>
          <CardDescription>
            Indica se sono previsti lavori in subappalto e, in caso
            affermativo, elenca le imprese subappaltatrici.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={values.subappalti_presenti}
              onChange={(e) =>
                update({ subappalti_presenti: e.target.checked })
              }
            />
            <span>Sono previsti lavori in subappalto</span>
          </label>
          {!values.subappalti_presenti ? (
            <p className="text-xs text-muted-foreground">
              Nel POS sarà stampato: &quot;Non è previsto l&apos;affidamento
              di lavorazioni in subappalto per il presente cantiere.&quot;
            </p>
          ) : (
            <div className="space-y-2">
              {values.subappaltatori.map((s, i) => (
                <div
                  key={i}
                  className="flex flex-col gap-2 sm:flex-row sm:items-center"
                >
                  <Input
                    aria-label={`Ragione sociale subappaltatore ${i + 1}`}
                    placeholder="Ragione sociale"
                    maxLength={255}
                    value={s.ragione_sociale}
                    onChange={(e) => {
                      const next = [...values.subappaltatori];
                      next[i] = { ...next[i], ragione_sociale: e.target.value };
                      update({ subappaltatori: next });
                    }}
                  />
                  <Input
                    aria-label={`Lavori affidati subappaltatore ${i + 1}`}
                    placeholder="Lavori affidati (es. opere di scavo)"
                    value={s.lavori ?? ""}
                    onChange={(e) => {
                      const next = [...values.subappaltatori];
                      next[i] = { ...next[i], lavori: e.target.value || null };
                      update({ subappaltatori: next });
                    }}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-label={`Rimuovi subappaltatore ${i + 1}`}
                    onClick={() =>
                      update({
                        subappaltatori: values.subappaltatori.filter(
                          (_, j) => j !== i,
                        ),
                      })
                    }
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() =>
                  update({
                    subappaltatori: [
                      ...values.subappaltatori,
                      { ragione_sociale: "", lavori: null },
                    ],
                  })
                }
              >
                <Plus className="mr-1 h-3 w-3" />
                Aggiungi subappaltatore
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Card: Sostanze pericolose */}
      <Card>
        <CardHeader>
          <CardTitle>Sostanze pericolose</CardTitle>
          <CardDescription>
            Indica se in cantiere saranno utilizzate sostanze o preparati
            pericolosi (All. XV punto 3.2.1 lettera e).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={values.sostanze_pericolose_presenti}
              onChange={(e) =>
                update({ sostanze_pericolose_presenti: e.target.checked })
              }
            />
            <span>In cantiere saranno utilizzate sostanze pericolose</span>
          </label>
          {!values.sostanze_pericolose_presenti ? (
            <p className="text-xs text-muted-foreground">
              Nel POS sarà stampato: &quot;L&apos;impresa non utilizzerà
              sostanze chimiche nelle lavorazioni che effettuerà presso il
              cantiere.&quot;
            </p>
          ) : (
            <div className="space-y-2">
              {values.sostanze_pericolose.map((s, i) => (
                <div
                  key={i}
                  className="flex flex-col gap-2 sm:flex-row sm:items-center"
                >
                  <Input
                    aria-label={`Nome sostanza ${i + 1}`}
                    placeholder="Sostanza (es. malta cementizia)"
                    maxLength={255}
                    value={s.nome}
                    onChange={(e) => {
                      const next = [...values.sostanze_pericolose];
                      next[i] = { ...next[i], nome: e.target.value };
                      update({ sostanze_pericolose: next });
                    }}
                  />
                  <Input
                    aria-label={`Uso sostanza ${i + 1}`}
                    placeholder="Uso (es. allettamento murature)"
                    value={s.uso ?? ""}
                    onChange={(e) => {
                      const next = [...values.sostanze_pericolose];
                      next[i] = { ...next[i], uso: e.target.value || null };
                      update({ sostanze_pericolose: next });
                    }}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-label={`Rimuovi sostanza ${i + 1}`}
                    onClick={() =>
                      update({
                        sostanze_pericolose:
                          values.sostanze_pericolose.filter(
                            (_, j) => j !== i,
                          ),
                      })
                    }
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() =>
                  update({
                    sostanze_pericolose: [
                      ...values.sostanze_pericolose,
                      { nome: "", uso: null },
                    ],
                  })
                }
              >
                <Plus className="mr-1 h-3 w-3" />
                Aggiungi sostanza
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
