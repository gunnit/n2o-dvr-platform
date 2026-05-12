"use client";

/**
 * Per-categoria expandable panel that shows the N pericoli rows from the
 * Schede Specifiche catalog (filtered by ambiente.tipo + declared
 * attrezzature) and lets the operator review/score each row independently.
 *
 * Wire-up:
 *
 *   <PericoliPanel
 *     aziendaId
 *     ambienteId
 *     valutazione   // the parent ValutazioneRischio for this categoria
 *     categoriaLong // long-form name from CATEGORIA_SHORT_TO_LONG
 *   />
 *
 * Data flow:
 *   1. On first expand, GET /pericoli-suggeriti?categoria=X.
 *   2. GET existing children at /rischi/{id}/pericoli.
 *   3. If no children exist: auto-seed children for *suggested-and-applies*
 *      catalog rows (matches_ambiente true OR triggered by attrezzatura).
 *   4. Operator can toggle apply, edit P/D, edit text via inline expand,
 *      delete, and add custom rows. Every change debounce-saves via
 *      POST /rischi/{id}/pericoli/batch.
 */
import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { toast } from "sonner";
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
  Wrench,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import { MeasuresPanel } from "@/components/ai/measures-panel";
import type {
  LivelloRischio,
  PericoloLibreria,
  PericoloSuggestionItem,
  PericoloSuggestionResponse,
  PericoloValutazione,
  ValutazioneRischio,
} from "@/types";

/**
 * Aggregate snapshot of this panel's children, published upward so the
 * parent ValutazioneRischio row can show the children-derived I/Livello
 * instead of its own (now stale) P/D. See BUG-3 in the audit:
 * without this, a parent could read "ACCETTABILE" while 12 GRAVE
 * pericoli sat underneath.
 */
export interface PericoliSummary {
  /** Number of pericoli in the panel (any source / any applicable state). */
  totalCount: number;
  /** Number of pericoli with applicabile = true. */
  applicableCount: number;
  /** Max indice across applicable children, null when none are applicable. */
  maxIndice: number | null;
  /** Livello matching maxIndice, null when none are applicable. */
  maxLivello: LivelloRischio | null;
}

interface PericoliPanelProps {
  aziendaId: string;
  ambienteId: string;
  /** The parent ValutazioneRischio whose children we are managing. */
  valutazione: ValutazioneRischio;
  /** Canonical long-form categoria name (e.g. "Impianti Elettrici"). */
  categoriaLong: string;
  /**
   * Optional — fires whenever the children list changes (load, edit,
   * delete, add). Lets the parent re-derive its row badge so the table
   * agrees with what's actually inside.
   */
  onSummaryChange?: (rischioId: string, summary: PericoliSummary) => void;
  /**
   * Persists the rischio-level `misure_prevenzione` text. Called by the
   * AI MeasuresPanel after the operator accepts/edits suggestions. The
   * parent should route this through its own batch-save pipeline so we
   * don't bypass scheduleAmbienteSave.
   */
  onSaveMisure?: (rischioId: string, combinedText: string) => Promise<void>;
}

function calcIndice(p: number, d: number): number {
  return 2 * d + p;
}

function getLivello(indice: number): LivelloRischio {
  if (indice <= 4) return "ACCETTABILE";
  if (indice <= 6) return "MODESTO";
  if (indice <= 8) return "GRAVE";
  return "GRAVISSIMO";
}

const LIVELLO_STYLE: Record<LivelloRischio, string> = {
  ACCETTABILE:
    "bg-green-100 text-green-800 border-green-200",
  MODESTO:
    "bg-yellow-100 text-yellow-800 border-yellow-200",
  GRAVE:
    "bg-orange-100 text-orange-800 border-orange-200",
  GRAVISSIMO:
    "bg-red-100 text-red-800 border-red-200",
};

export function PericoliPanel({
  aziendaId,
  ambienteId,
  valutazione,
  categoriaLong,
  onSummaryChange,
  onSaveMisure,
}: PericoliPanelProps) {
  const { apiFetch } = useApi();
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<PericoloSuggestionItem[]>([]);
  const [pericoli, setPericoli] = useState<PericoloValutazione[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  // True once we have either loaded pericoli from the backend or the user
  // has edited them locally. Until then, the empty `pericoli` array does NOT
  // represent reality — publishing an applicableCount=0 summary upward would
  // overwrite whatever the parent had cached from a previous mount and
  // reset the macro row's indice to the raw P/D defaults. Feedback
  // #a460cb42 (2026-05-09): "le macrosezioni si resettano come se fossero
  // di default quando cambio ambiente".
  const [loadedOnce, setLoadedOnce] = useState(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const rischioId = valutazione.id;

  // Lazy-load on first expand (avoids fetching for every applicable
  // categoria up front when the operator only reviews a few).
  const loadInitial = useCallback(async () => {
    setLoading(true);
    try {
      const [sugg, existing] = await Promise.all([
        apiFetch<PericoloSuggestionResponse>(
          `/api/v1/aziende/${aziendaId}/ambienti/${ambienteId}/pericoli-suggeriti?categoria=${encodeURIComponent(categoriaLong)}`,
        ),
        apiFetch<PericoloValutazione[]>(
          `/api/v1/aziende/${aziendaId}/ambienti/${ambienteId}/rischi/${rischioId}/pericoli`,
        ),
      ]);
      setSuggestions(sugg.items);

      if (existing.length > 0) {
        setPericoli(existing);
        return;
      }

      // No children yet — auto-seed from suggestions. Only rows whose
      // ambiente actually matches OR whose equipment-keyword fired are
      // auto-applied; the rest become available via "Aggiungi suggeriti
      // disponibili" if the operator wants to opt in later.
      const seedItems = sugg.items.map((s, idx) => ({
        pericolo_libreria_id: s.pericolo.id,
        source: "catalog" as const,
        pericolo: s.pericolo.pericolo,
        condizioni_esposizione: s.pericolo.condizioni_esposizione,
        rischio: s.pericolo.rischio,
        misure_prevenzione: s.pericolo.misure_prevenzione,
        probabilita_p: s.pericolo.p_default,
        danno_d: s.pericolo.d_default,
        valutazione_riferimento: s.pericolo.valutazione_riferimento,
        applicabile: true,
        ordine: idx,
      }));
      if (seedItems.length === 0) return;
      const saved = await apiFetch<PericoloValutazione[]>(
        `/api/v1/aziende/${aziendaId}/ambienti/${ambienteId}/rischi/${rischioId}/pericoli/batch`,
        { method: "POST", body: JSON.stringify({ items: seedItems }) },
      );
      setPericoli(saved);
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Errore caricamento pericoli",
      );
    } finally {
      setLoading(false);
      setLoadedOnce(true);
    }
  }, [apiFetch, aziendaId, ambienteId, rischioId, categoriaLong]);

  useEffect(() => {
    if (expanded && pericoli.length === 0 && !loading) {
      void loadInitial();
    }
    // We intentionally only run when expanded flips.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expanded]);

  // Debounced save of the current pericoli list to /pericoli/batch. Replaces
  // the whole categoria's children — the API handles deletes for ids we omit.
  const scheduleSave = useCallback(
    (next: PericoloValutazione[]) => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveTimerRef.current = setTimeout(async () => {
        saveTimerRef.current = null;
        try {
          const body = {
            items: next.map((p) => ({
              id: p.id,
              pericolo_libreria_id: p.pericolo_libreria_id,
              source: p.source,
              pericolo: p.pericolo,
              condizioni_esposizione: p.condizioni_esposizione,
              rischio: p.rischio,
              misure_prevenzione: p.misure_prevenzione,
              probabilita_p: p.probabilita_p,
              danno_d: p.danno_d,
              valutazione_riferimento: p.valutazione_riferimento,
              applicabile: p.applicabile,
              ordine: p.ordine,
            })),
          };
          const saved = await apiFetch<PericoloValutazione[]>(
            `/api/v1/aziende/${aziendaId}/ambienti/${ambienteId}/rischi/${rischioId}/pericoli/batch`,
            { method: "POST", body: JSON.stringify(body) },
          );
          // Reconcile server ids back so subsequent saves use them.
          setPericoli(saved);
        } catch (err) {
          toast.error(
            err instanceof Error
              ? err.message
              : "Errore salvataggio pericoli",
          );
        }
      }, 600);
    },
    [apiFetch, aziendaId, ambienteId, rischioId],
  );

  const updatePericolo = useCallback(
    (id: string, patch: Partial<PericoloValutazione>) => {
      setPericoli((prev) => {
        const next = prev.map((p) => {
          if (p.id !== id) return p;
          const merged = { ...p, ...patch };
          if (
            ("probabilita_p" in patch || "danno_d" in patch) &&
            merged.probabilita_p != null &&
            merged.danno_d != null
          ) {
            const indice = calcIndice(merged.probabilita_p, merged.danno_d);
            merged.indice_i = indice;
            merged.livello_rischio = getLivello(indice);
          }
          return merged;
        });
        scheduleSave(next);
        return next;
      });
    },
    [scheduleSave],
  );

  const deletePericolo = useCallback(
    (id: string) => {
      setPericoli((prev) => {
        const next = prev.filter((p) => p.id !== id);
        scheduleSave(next);
        return next;
      });
    },
    [scheduleSave],
  );

  const addCustom = useCallback(() => {
    const tempId = crypto.randomUUID();
    const ordine = pericoli.length;
    const newRow: PericoloValutazione = {
      id: tempId,
      valutazione_rischio_id: rischioId,
      pericolo_libreria_id: null,
      source: "custom",
      pericolo: "Nuovo pericolo (modifica)",
      condizioni_esposizione: "Durante le ordinarie attività lavorative.",
      rischio: null,
      misure_prevenzione: null,
      probabilita_p: 1,
      danno_d: 1,
      valutazione_riferimento: null,
      applicabile: true,
      ordine,
      indice_i: 3,
      livello_rischio: "ACCETTABILE",
    };
    const next = [...pericoli, newRow];
    setPericoli(next);
    setEditingId(tempId);
    scheduleSave(next);
  }, [pericoli, rischioId, scheduleSave]);

  const addSuggestion = useCallback(
    (suggestion: PericoloSuggestionItem) => {
      // Avoid duplicate inserts of the same catalog row.
      if (
        pericoli.some(
          (p) => p.pericolo_libreria_id === suggestion.pericolo.id,
        )
      ) {
        return;
      }
      const tempId = crypto.randomUUID();
      const ordine = pericoli.length;
      const lib = suggestion.pericolo;
      const p = lib.p_default ?? 1;
      const d = lib.d_default ?? 1;
      const indice = calcIndice(p, d);
      const newRow: PericoloValutazione = {
        id: tempId,
        valutazione_rischio_id: rischioId,
        pericolo_libreria_id: lib.id,
        source: "catalog",
        pericolo: lib.pericolo,
        condizioni_esposizione: lib.condizioni_esposizione,
        rischio: lib.rischio,
        misure_prevenzione: lib.misure_prevenzione,
        probabilita_p: lib.p_default,
        danno_d: lib.d_default,
        valutazione_riferimento: lib.valutazione_riferimento,
        applicabile: true,
        ordine,
        indice_i: lib.p_default != null && lib.d_default != null ? indice : null,
        livello_rischio:
          lib.p_default != null && lib.d_default != null
            ? getLivello(indice)
            : null,
      };
      const next = [...pericoli, newRow];
      setPericoli(next);
      scheduleSave(next);
    },
    [pericoli, rischioId, scheduleSave],
  );

  const summary = useMemo(() => {
    const applied = pericoli.filter((p) => p.applicabile);
    return {
      applied: applied.length,
      total: pericoli.length,
    };
  }, [pericoli]);

  // BUG-3 — publish a child-aggregated summary upward whenever pericoli
  // change. The parent table row uses this to render its I/Livello so it
  // can't disagree with its children. We compute max indice over the
  // *applicable* rows only — disabled pericoli shouldn't drive the
  // parent badge any more than they drive the DVR.
  const externalSummary = useMemo<PericoliSummary>(() => {
    let maxIndice: number | null = null;
    let applicableCount = 0;
    for (const p of pericoli) {
      if (!p.applicabile) continue;
      applicableCount += 1;
      const pVal = p.probabilita_p ?? 1;
      const dVal = p.danno_d ?? 1;
      const indice = calcIndice(pVal, dVal);
      if (maxIndice == null || indice > maxIndice) maxIndice = indice;
    }
    return {
      totalCount: pericoli.length,
      applicableCount,
      maxIndice,
      maxLivello: maxIndice != null ? getLivello(maxIndice) : null,
    };
  }, [pericoli]);

  useEffect(() => {
    // See `loadedOnce` declaration: don't publish until we know what the
    // real pericoli state is, otherwise re-mounting on ambient switch
    // resets the parent's cached macro indice to defaults.
    if (!loadedOnce) return;
    onSummaryChange?.(rischioId, externalSummary);
  }, [externalSummary, onSummaryChange, rischioId, loadedOnce]);

  const availableSuggestions = useMemo(
    () =>
      suggestions.filter(
        (s) =>
          !pericoli.some((p) => p.pericolo_libreria_id === s.pericolo.id),
      ),
    [suggestions, pericoli],
  );

  return (
    <div className="border-t bg-muted/30">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-2 text-left text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/50"
      >
        <span className="inline-flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" />
          )}
          Dettaglio pericoli — {categoriaLong}
          {summary.total > 0 && (
            <Badge variant="outline" className="ml-1 text-[10px]">
              {summary.applied}/{summary.total} righe
            </Badge>
          )}
        </span>
        {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
      </button>

      {expanded && (
        <div className="space-y-3 px-4 pb-4">
          {/* US-2.6 — AI improvement measures for the rischio (above the
              pericoli list). Mounted only when we have a parent save
              handler; otherwise the panel can't persist what it gathers. */}
          {onSaveMisure && (
            <MeasuresPanel
              aziendaId={aziendaId}
              rischioId={valutazione.id}
              categoriaRischio={valutazione.categoria_rischio}
              initialText={valutazione.misure_prevenzione ?? undefined}
              onSave={(combinedText) =>
                onSaveMisure(valutazione.id, combinedText)
              }
            />
          )}

          {pericoli.length === 0 && !loading && (
            <p className="text-xs italic text-muted-foreground">
              Nessun pericolo applicabile dal catalogo per questa
              combinazione (tipo ambiente + attrezzature). Aggiungi un
              pericolo personalizzato sotto.
            </p>
          )}

          {pericoli.length > 0 && (
            <div className="overflow-hidden rounded-md border bg-background">
              <table className="w-full text-xs">
                <thead className="bg-muted/50 text-[10px] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="w-[28px] p-2"></th>
                    <th className="p-2 text-left">Pericolo</th>
                    <th className="w-[80px] p-2 text-center">P</th>
                    <th className="w-[80px] p-2 text-center">D</th>
                    <th className="w-[60px] p-2 text-center">I</th>
                    <th className="w-[120px] p-2 text-center">Livello</th>
                    <th className="w-[36px] p-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {pericoli.map((p) => {
                    const isEditing = editingId === p.id;
                    const isDelegated = p.valutazione_riferimento != null;
                    const pVal = p.probabilita_p;
                    const dVal = p.danno_d;
                    const indice =
                      pVal != null && dVal != null
                        ? calcIndice(pVal, dVal)
                        : null;
                    const livello = indice != null ? getLivello(indice) : null;
                    return (
                      <Fragment key={p.id}>
                        <tr
                          className={cn(
                            "group cursor-pointer border-t transition-colors hover:bg-muted/30",
                            !p.applicabile && "opacity-50",
                            isEditing && "bg-muted/40",
                          )}
                          onClick={() =>
                            setEditingId(isEditing ? null : p.id)
                          }
                        >
                          <td
                            className="p-2 text-center"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <input
                              type="checkbox"
                              checked={p.applicabile}
                              onChange={(e) =>
                                updatePericolo(p.id, {
                                  applicabile: e.target.checked,
                                })
                              }
                              className="h-3.5 w-3.5 accent-primary"
                            />
                          </td>
                          <td className="p-2">
                            <div className="flex flex-col gap-0.5">
                              <button
                                type="button"
                                onClick={(e) => {
                                  // The whole row is clickable; stop here so
                                  // we don't toggle twice when the label is
                                  // the actual click target.
                                  e.stopPropagation();
                                  setEditingId(isEditing ? null : p.id);
                                }}
                                className="flex items-center gap-1.5 text-left text-xs font-medium hover:text-primary"
                                title="Clicca per espandere/modificare"
                              >
                                {isEditing ? (
                                  <ChevronDown className="h-3.5 w-3.5 text-muted-foreground transition-transform group-hover:text-foreground" />
                                ) : (
                                  <ChevronRight className="h-3.5 w-3.5 text-muted-foreground transition-transform group-hover:text-foreground" />
                                )}
                                <span>{p.pericolo}</span>
                              </button>
                              <div className="flex flex-wrap items-center gap-1">
                                {p.source === "custom" && (
                                  <Badge
                                    variant="outline"
                                    className="border-blue-200 bg-blue-50 text-[9px] text-blue-700"
                                  >
                                    Personalizzato
                                  </Badge>
                                )}
                                {isDelegated && (
                                  <Badge
                                    variant="outline"
                                    className="border-purple-200 bg-purple-50 text-[9px] text-purple-700"
                                  >
                                    {p.valutazione_riferimento}
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </td>
                          <td
                            className="p-2 text-center"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {p.applicabile && !isDelegated && (
                              <select
                                value={pVal ?? 1}
                                onChange={(e) =>
                                  updatePericolo(p.id, {
                                    probabilita_p: Number(e.target.value),
                                  })
                                }
                                className="h-6 w-14 rounded border bg-background text-center text-xs"
                              >
                                <option value={1}>1</option>
                                <option value={2}>2</option>
                                <option value={3}>3</option>
                                <option value={4}>4</option>
                              </select>
                            )}
                          </td>
                          <td
                            className="p-2 text-center"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {p.applicabile && !isDelegated && (
                              <select
                                value={dVal ?? 1}
                                onChange={(e) =>
                                  updatePericolo(p.id, {
                                    danno_d: Number(e.target.value),
                                  })
                                }
                                className="h-6 w-14 rounded border bg-background text-center text-xs"
                              >
                                <option value={1}>1</option>
                                <option value={2}>2</option>
                                <option value={3}>3</option>
                                <option value={4}>4</option>
                              </select>
                            )}
                          </td>
                          <td className="p-2 text-center font-bold">
                            {p.applicabile && indice != null ? indice : "—"}
                          </td>
                          <td className="p-2 text-center">
                            {p.applicabile && livello && (
                              <Badge
                                variant="outline"
                                className={cn(
                                  "text-[10px] font-semibold",
                                  LIVELLO_STYLE[livello],
                                )}
                              >
                                {livello}
                              </Badge>
                            )}
                          </td>
                          <td
                            className="p-2 text-center"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <button
                              type="button"
                              onClick={() => deletePericolo(p.id)}
                              className="text-muted-foreground hover:text-red-600"
                              title="Rimuovi pericolo"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </td>
                        </tr>
                        {isEditing && (
                          <tr className="border-t bg-muted/20">
                            <td colSpan={7} className="space-y-2 p-3">
                              <PericoloEditor
                                pericolo={p}
                                onChange={(patch) =>
                                  updatePericolo(p.id, patch)
                                }
                                onClose={() => setEditingId(null)}
                              />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={addCustom}
              className="h-7 text-xs"
            >
              <Plus className="mr-1 h-3 w-3" />
              Aggiungi pericolo personalizzato
            </Button>
            {availableSuggestions.length > 0 && (
              <details className="text-xs">
                <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                  + {availableSuggestions.length} dal catalogo non ancora
                  applicati
                </summary>
                <ul className="mt-2 space-y-1">
                  {availableSuggestions.map((s) => (
                    <li
                      key={s.pericolo.id}
                      className="flex items-start justify-between gap-2 rounded border bg-background px-2 py-1.5"
                    >
                      <div className="flex-1">
                        <div className="text-xs font-medium">
                          {s.pericolo.pericolo}
                        </div>
                        <div className="mt-0.5 flex flex-wrap items-center gap-1">
                          {s.matches_ambiente && (
                            <Badge
                              variant="outline"
                              className="border-emerald-200 bg-emerald-50 text-[9px] text-emerald-700"
                            >
                              <Sparkles className="mr-0.5 h-2.5 w-2.5" />
                              Adatto all&apos;ambiente
                            </Badge>
                          )}
                          {s.triggered_by_attrezzature.length > 0 && (
                            <Badge
                              variant="outline"
                              className="border-amber-200 bg-amber-50 text-[9px] text-amber-800"
                            >
                              <Wrench className="mr-0.5 h-2.5 w-2.5" />
                              {s.triggered_by_attrezzature.join(", ")}
                            </Badge>
                          )}
                        </div>
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="h-6 px-2 text-xs"
                        onClick={() => addSuggestion(s)}
                      >
                        Aggiungi
                      </Button>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

interface PericoloEditorProps {
  pericolo: PericoloValutazione;
  onChange: (patch: Partial<PericoloValutazione>) => void;
  onClose: () => void;
}

function PericoloEditor({ pericolo, onChange, onClose }: PericoloEditorProps) {
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
        <label className="text-xs">
          <span className="mb-1 block font-medium text-muted-foreground">
            Pericolo
          </span>
          <textarea
            value={pericolo.pericolo}
            onChange={(e) => onChange({ pericolo: e.target.value })}
            rows={2}
            className="w-full rounded border bg-background p-1.5 text-xs"
          />
        </label>
        <label className="text-xs">
          <span className="mb-1 block font-medium text-muted-foreground">
            Condizioni di impiego o esposizione
          </span>
          <textarea
            value={pericolo.condizioni_esposizione ?? ""}
            onChange={(e) =>
              onChange({ condizioni_esposizione: e.target.value || null })
            }
            rows={2}
            className="w-full rounded border bg-background p-1.5 text-xs"
          />
        </label>
        <label className="text-xs">
          <span className="mb-1 block font-medium text-muted-foreground">
            Rischio
          </span>
          <textarea
            value={pericolo.rischio ?? ""}
            onChange={(e) => onChange({ rischio: e.target.value || null })}
            rows={2}
            className="w-full rounded border bg-background p-1.5 text-xs"
          />
        </label>
        <label className="text-xs">
          <span className="mb-1 block font-medium text-muted-foreground">
            Misure di prevenzione e DPI
          </span>
          <textarea
            value={pericolo.misure_prevenzione ?? ""}
            onChange={(e) =>
              onChange({ misure_prevenzione: e.target.value || null })
            }
            rows={3}
            className="w-full rounded border bg-background p-1.5 text-xs"
          />
        </label>
      </div>
      <div className="flex justify-end">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onClose}
          className="h-7 text-xs"
        >
          Chiudi
        </Button>
      </div>
    </div>
  );
}
