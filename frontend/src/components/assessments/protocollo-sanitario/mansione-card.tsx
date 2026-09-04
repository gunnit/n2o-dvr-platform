"use client";

/**
 * One mansione of the protocollo sanitario aziendale.
 *
 * Read-only on top: the rischi specifici and DPI aggregated from every
 * persona holding the role (the union the DVR §4.3 prints). Editable
 * below: accertamenti with cadence, overall periodicità, the correlated
 * occupational diseases (reference rows to tick plus free entries) and
 * notes. "Compila con AI" asks for a proposal the operator applies or
 * discards — nothing is saved until "Salva".
 *
 * Per mansione, never per person: the card never sees a name.
 */

import { useCallback, useState } from "react";
import { Loader2, Plus, Sparkles, Trash2, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
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
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

import {
  FONTE_LABELS,
  type Accertamento,
  type Fonte,
  type MalattiaCorrelata,
  type MansioneItem,
  type ProtocolloProposta,
  type ProtocolloUpsert,
} from "./types";

const DEFAULT_ACCERTAMENTI: Accertamento[] = [
  { esame: "Visita medica preventiva e periodica", periodicita: "annuale" },
];

interface EditState {
  accertamenti: Accertamento[];
  periodicita: string;
  /** reference codice -> ticked */
  selected: Record<string, boolean>;
  /** operator-added diseases not in the reference list */
  extra: MalattiaCorrelata[];
  note: string;
  fonte: Fonte;
}

function initialState(item: MansioneItem): EditState {
  const saved = item.protocollo;
  const selected: Record<string, boolean> = {};
  const refCodes = new Set(item.malattie_riferimento.map((m) => m.codice));
  if (saved) {
    const savedCodes = new Set(
      saved.malattie_correlate.map((m) => m.codice).filter(Boolean),
    );
    for (const m of item.malattie_riferimento)
      selected[m.codice] = savedCodes.has(m.codice);
    return {
      accertamenti: saved.accertamenti.length
        ? saved.accertamenti.map((a) => ({ ...a }))
        : [],
      periodicita: saved.periodicita ?? "",
      selected,
      extra: saved.malattie_correlate
        .filter((m) => !m.codice || !refCodes.has(m.codice))
        .map((m) => ({ ...m })),
      note: saved.note ?? "",
      fonte: saved.fonte,
    };
  }
  // Prefill: the reference matches pre-ticked, the visita medica row in
  // place. The operator reviews, never re-enters.
  for (const m of item.malattie_riferimento) selected[m.codice] = true;
  return {
    accertamenti: DEFAULT_ACCERTAMENTI.map((a) => ({ ...a })),
    periodicita: "",
    selected,
    extra: [],
    note: "",
    fonte: "manuale",
  };
}

/** An edit after an applied AI proposal turns "ai" into "ai_modificato". */
function touched(fonte: Fonte): Fonte {
  return fonte === "ai" ? "ai_modificato" : fonte;
}

export function MansioneCard({
  item,
  periodicitaOptions,
  onSave,
  onSuggest,
  onDelete,
}: {
  item: MansioneItem;
  periodicitaOptions: string[];
  onSave: (body: ProtocolloUpsert) => Promise<void>;
  onSuggest: (mansione: string) => Promise<ProtocolloProposta>;
  onDelete: (protocolloId: string) => Promise<void>;
}) {
  const [state, setState] = useState<EditState>(() => initialState(item));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [proposta, setProposta] = useState<ProtocolloProposta | null>(null);

  const edit = useCallback((patch: (s: EditState) => EditState) => {
    setState((s) => {
      const next = patch(s);
      return { ...next, fonte: touched(next.fonte) };
    });
    setDirty(true);
  }, []);

  const saved = item.protocollo;
  const hasRischi = item.rischi_specifici.length > 0;

  // --- AI ------------------------------------------------------------------
  const handleSuggest = async () => {
    setSuggesting(true);
    try {
      const p = await onSuggest(item.mansione);
      setProposta(p);
    } finally {
      setSuggesting(false);
    }
  };

  const applyProposta = () => {
    if (!proposta) return;
    const selected: Record<string, boolean> = {};
    const chosen = new Set(
      proposta.malattie_correlate.map((m) => m.codice).filter(Boolean),
    );
    for (const m of item.malattie_riferimento)
      selected[m.codice] = chosen.has(m.codice);
    setState((s) => ({
      ...s,
      accertamenti: proposta.accertamenti.map((a) => ({
        esame: a.esame,
        periodicita: a.periodicita,
      })),
      periodicita: proposta.periodicita,
      selected,
      note: s.note
        ? s.note
        : `Motivazione AI: ${proposta.motivazione}`,
      fonte: "ai",
    }));
    setDirty(true);
    setProposta(null);
  };

  // --- save / delete -------------------------------------------------------
  const buildBody = (): ProtocolloUpsert => {
    const fromRef: MalattiaCorrelata[] = item.malattie_riferimento
      .filter((m) => state.selected[m.codice])
      .map((m) => ({
        codice: m.codice,
        malattia: m.malattia,
        riferimento: m.tabella,
      }));
    const extra = state.extra
      .map((m) => ({
        codice: m.codice || null,
        malattia: m.malattia.trim(),
        riferimento: m.riferimento?.trim() || null,
      }))
      .filter((m) => m.malattia.length >= 2);
    return {
      mansione: item.mansione,
      rischi_specifici: item.rischi_specifici,
      accertamenti: state.accertamenti
        .map((a) => ({
          esame: a.esame.trim(),
          periodicita: a.periodicita.trim(),
        }))
        .filter((a) => a.esame.length >= 2),
      periodicita: state.periodicita || null,
      malattie_correlate: [...fromRef, ...extra],
      note: state.note.trim() || null,
      fonte: state.fonte,
    };
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(buildBody());
      setDirty(false);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!saved) return;
    if (
      !window.confirm(
        `Eliminare il protocollo salvato per "${item.mansione}"? I flag delle persone non vengono toccati.`,
      )
    )
      return;
    setDeleting(true);
    try {
      await onDelete(saved.id);
    } finally {
      setDeleting(false);
    }
  };

  // --- render --------------------------------------------------------------
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <CardTitle className="flex flex-wrap items-center gap-2">
              <span>{item.mansione}</span>
              <Badge variant="secondary">
                {item.num_persone === 1
                  ? "1 persona"
                  : `${item.num_persone} persone`}
              </Badge>
              {saved && (
                <Badge variant={saved.fonte === "manuale" ? "neutral" : "ai"}>
                  {FONTE_LABELS[saved.fonte]}
                </Badge>
              )}
              {dirty && <Badge variant="warning">Modifiche non salvate</Badge>}
            </CardTitle>
            <CardDescription>
              {saved
                ? `Protocollo salvato il ${new Date(saved.updated_at).toLocaleDateString("it-IT")}.`
                : "Nessun protocollo salvato: il DVR mostra “[DA COMPILARE — MC]” per questa mansione."}
            </CardDescription>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleSuggest}
            disabled={suggesting}
          >
            {suggesting ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Sparkles />
            )}
            Compila con AI
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* Read-only aggregation */}
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-[#94a3b8]">
              Rischi specifici della mansione
            </p>
            {hasRischi ? (
              <div className="flex flex-wrap gap-1.5">
                {item.rischi_specifici.map((r) => (
                  <Badge key={r.code} variant="outline">
                    {r.etichetta}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-[13px] text-[#64748d]">
                Nessun rischio specifico flaggato sulle persone con questa
                mansione: compila i flag nel censimento persone per un
                protocollo mirato.
              </p>
            )}
          </div>
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-[#94a3b8]">
              DPI assegnati
            </p>
            {item.dpi.length ? (
              <div className="flex flex-wrap gap-1.5">
                {item.dpi.map((d) => (
                  <Badge key={d.code} variant="outline">
                    {d.etichetta}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-[13px] text-[#64748d]">Nessun DPI assegnato.</p>
            )}
          </div>
        </div>

        {/* AI proposal */}
        {proposta && (
          <Callout
            tone="info"
            icon={<Sparkles className="h-3.5 w-3.5" strokeWidth={1.9} />}
            title="Proposta AI"
            action={
              <div className="flex gap-2">
                <Button type="button" size="sm" onClick={applyProposta}>
                  Applica
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => setProposta(null)}
                >
                  <X />
                  Scarta
                </Button>
              </div>
            }
          >
            <div className="space-y-2">
              <p>{proposta.motivazione}</p>
              <p>
                <span className="font-medium">Periodicità visita:</span>{" "}
                {proposta.periodicita}
              </p>
              <ul className="list-disc space-y-0.5 pl-4">
                {proposta.accertamenti.map((a, i) => (
                  <li key={i}>
                    <span className="font-medium">{a.esame}</span> —{" "}
                    {a.periodicita}
                    <span className="text-[#64748d]"> · {a.motivazione}</span>
                  </li>
                ))}
              </ul>
              {proposta.malattie_correlate.length > 0 && (
                <p>
                  <span className="font-medium">Malattie correlate:</span>{" "}
                  {proposta.malattie_correlate.map((m) => m.malattia).join("; ")}
                </p>
              )}
            </div>
          </Callout>
        )}

        {/* Accertamenti */}
        <div className="space-y-2">
          <Label>Accertamenti sanitari</Label>
          {state.accertamenti.length === 0 && (
            <p className="text-[13px] text-[#64748d]">
              Nessun accertamento: aggiungi almeno la visita medica.
            </p>
          )}
          {state.accertamenti.map((a, idx) => (
            <div key={idx} className="flex flex-col gap-2 sm:flex-row">
              <Input
                aria-label="Esame"
                placeholder="Esame (es. Audiometria)"
                value={a.esame}
                onChange={(e) =>
                  edit((s) => ({
                    ...s,
                    accertamenti: s.accertamenti.map((row, i) =>
                      i === idx ? { ...row, esame: e.target.value } : row,
                    ),
                  }))
                }
                className="sm:flex-[2]"
              />
              <Input
                aria-label="Periodicità accertamento"
                placeholder="Periodicità (es. annuale)"
                value={a.periodicita}
                onChange={(e) =>
                  edit((s) => ({
                    ...s,
                    accertamenti: s.accertamenti.map((row, i) =>
                      i === idx ? { ...row, periodicita: e.target.value } : row,
                    ),
                  }))
                }
                className="sm:flex-1"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label="Rimuovi accertamento"
                onClick={() =>
                  edit((s) => ({
                    ...s,
                    accertamenti: s.accertamenti.filter((_, i) => i !== idx),
                  }))
                }
              >
                <Trash2 />
              </Button>
            </div>
          ))}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() =>
              edit((s) => ({
                ...s,
                accertamenti: [...s.accertamenti, { esame: "", periodicita: "" }],
              }))
            }
          >
            <Plus />
            Aggiungi accertamento
          </Button>
        </div>

        {/* Periodicità */}
        <div className="grid gap-1.5 sm:max-w-xs">
          <Label htmlFor={`periodicita-${item.mansione}`}>
            Periodicità della visita periodica
          </Label>
          <Select
            id={`periodicita-${item.mansione}`}
            value={state.periodicita}
            onChange={(e) =>
              edit((s) => ({ ...s, periodicita: e.target.value }))
            }
          >
            <option value="">— da definire dal MC —</option>
            {periodicitaOptions.map((o) => (
              <option key={o} value={o}>
                {o.charAt(0).toUpperCase() + o.slice(1)}
              </option>
            ))}
          </Select>
        </div>

        {/* Malattie correlate */}
        <div className="space-y-2">
          <Label>Malattie professionali correlate</Label>
          {item.malattie_riferimento.length === 0 ? (
            <p className="text-[13px] text-[#64748d]">
              Nessuna voce della tabella (D.M. 9/4/2008) corrisponde ai rischi
              specifici flaggati. Puoi aggiungere una malattia a mano.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {item.malattie_riferimento.map((m) => {
                const checked = !!state.selected[m.codice];
                return (
                  <li key={m.codice}>
                    <label
                      className={cn(
                        "flex cursor-pointer items-start gap-2.5 rounded-md border px-3 py-2 transition-colors",
                        checked
                          ? "border-[rgba(0,61,116,0.25)] bg-[rgba(0,61,116,0.04)]"
                          : "border-[#e5edf5] bg-white hover:bg-[#f6f9fc]",
                      )}
                    >
                      <input
                        type="checkbox"
                        className="mt-0.5 h-4 w-4 accent-primary"
                        checked={checked}
                        onChange={(e) =>
                          edit((s) => ({
                            ...s,
                            selected: {
                              ...s.selected,
                              [m.codice]: e.target.checked,
                            },
                          }))
                        }
                      />
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-1.5 text-[13px] font-medium text-[#061b31]">
                          {m.malattia}
                          {!m.tabellata && (
                            <Badge variant="neutral">non tabellata</Badge>
                          )}
                        </span>
                        <span className="block text-[12px] text-[#64748d]">
                          {m.agente_o_rischio} · {m.tabella}
                        </span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}

          {state.extra.map((m, idx) => (
            <div key={idx} className="flex flex-col gap-2 sm:flex-row">
              <Input
                aria-label="Malattia"
                placeholder="Malattia"
                value={m.malattia}
                onChange={(e) =>
                  edit((s) => ({
                    ...s,
                    extra: s.extra.map((row, i) =>
                      i === idx ? { ...row, malattia: e.target.value } : row,
                    ),
                  }))
                }
                className="sm:flex-[2]"
              />
              <Input
                aria-label="Riferimento tabellare"
                placeholder="Riferimento (es. Tab. Industria voce …)"
                value={m.riferimento ?? ""}
                onChange={(e) =>
                  edit((s) => ({
                    ...s,
                    extra: s.extra.map((row, i) =>
                      i === idx ? { ...row, riferimento: e.target.value } : row,
                    ),
                  }))
                }
                className="sm:flex-[2]"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label="Rimuovi malattia"
                onClick={() =>
                  edit((s) => ({
                    ...s,
                    extra: s.extra.filter((_, i) => i !== idx),
                  }))
                }
              >
                <Trash2 />
              </Button>
            </div>
          ))}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() =>
              edit((s) => ({
                ...s,
                extra: [
                  ...s.extra,
                  { codice: null, malattia: "", riferimento: "" },
                ],
              }))
            }
          >
            <Plus />
            Aggiungi malattia
          </Button>
        </div>

        {/* Note */}
        <div className="grid gap-1.5">
          <Label htmlFor={`note-${item.mansione}`}>Note per il Medico Competente</Label>
          <Textarea
            id={`note-${item.mansione}`}
            value={state.note}
            onChange={(e) => edit((s) => ({ ...s, note: e.target.value }))}
            placeholder="Es. esposizione stagionale, turni notturni, prescrizioni in essere…"
          />
        </div>

        {/* Footer */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#eef2f7] pt-4">
          <p className="text-[12px] text-[#64748d]">
            Il protocollo è per mansione e viene riportato nel DVR §4.3; la
            validazione finale spetta al Medico Competente (art. 41 D.Lgs.
            81/2008).
          </p>
          <div className="flex gap-2">
            {saved && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? <Loader2 className="animate-spin" /> : <Trash2 />}
                Elimina
              </Button>
            )}
            <Button
              type="button"
              size="sm"
              onClick={handleSave}
              disabled={saving || (!dirty && !!saved)}
            >
              {saving && <Loader2 className="animate-spin" />}
              Salva
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
