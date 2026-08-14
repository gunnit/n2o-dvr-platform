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
import { RISK_CHIP, livelloFor } from "@/lib/ui/risk";
import { cn } from "@/lib/utils";
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
}

// Bulk-flag label for "come da valutazione allegata" — see
// bulkSetReferenceAttached below (feedback #a6f06283).
const DELEGATED_REFERENCE_LABEL = "Come da valutazione allegata";

// ---------------------------------------------------------------------------
// Special worker-category rows (client feedback 2026-08-13).
//
// The catalog rows for lavoratrici gestanti (OR-03), lavoratori minori
// (OR-04) and lavoratori stranieri (OR-05) used to ship a "Vedi normativa
// ..." marker in valutazione_riferimento, which blocked the P/D pickers and
// printed the marker verbatim in the DVR. New rules:
//   - gestanti:  defer to the dedicated allegato ("come da documento
//     allegato") when the azienda has a Valutazione Rischio Gestanti,
//     otherwise the operator scores the indice (P/D, I = 2D + P) like any
//     other row — with a toggle to switch between the two modes;
//   - minori:    same rule as gestanti, but no dedicated minori assessment
//     module exists yet, so the indice picker is the only mode;
//   - stranieri: indice picker only.
// Legacy markers found on load are migrated in place (and saved) so
// existing aziende stop printing "Vedi normativa" in the DVR.
// ---------------------------------------------------------------------------
type SpecialKind = "gestanti" | "minori" | "stranieri";

const SPECIAL_KIND_BY_CODE: Record<string, SpecialKind> = {
  "OR-03": "gestanti",
  "OR-04": "minori",
  "OR-05": "stranieri",
};

const LEGACY_MARKER_KIND: Record<string, SpecialKind> = {
  "Vedi normativa specifica (D.Lgs. 151/2001)": "gestanti",
  "Vedi normativa specifica (D.Lgs. 345/99)": "minori",
  "Verifica linguistica/formativa a cura del preposto": "stranieri",
};

// Must match GESTANTI_ALLEGATO_RIFERIMENTO in
// backend/app/services/document_generator/dvr_master.py so rows saved here
// and legacy rows the generator normalizes read identically in the DVR.
const GESTANTI_ALLEGATO_RIFERIMENTO =
  "Come da documento allegato: Valutazione Rischio Gestanti";

// Only the gestanti rows of this categoria can defer to an allegato, so the
// gestanti-presence lookup is skipped for every other categoria.
const CATEGORIA_ORGANIZZAZIONE = "Organizzazione del Lavoro";

// Prefill for the indice mode — same starter score the other Organizzazione
// del Lavoro catalog rows carry; the operator corrects it.
const SPECIAL_DEFAULT_P = 2;
const SPECIAL_DEFAULT_D = 2;

function specialKindOf(
  p: PericoloValutazione,
  codeById: ReadonlyMap<string, string>,
): SpecialKind | null {
  if (p.pericolo_libreria_id) {
    const code = codeById.get(p.pericolo_libreria_id);
    if (code && SPECIAL_KIND_BY_CODE[code]) return SPECIAL_KIND_BY_CODE[code];
  }
  const rif = p.valutazione_riferimento?.trim();
  if (rif && LEGACY_MARKER_KIND[rif]) return LEGACY_MARKER_KIND[rif];
  return null;
}

function calcIndice(p: number, d: number): number {
  return 2 * d + p;
}

/**
 * Bring special worker-category rows to their canonical state:
 * gestanti + allegato presente → delegated to the allegato; every other
 * case → scored P/D (prefilled, operator corrects). Rows whose state the
 * operator already owns (custom riferimento, or an explicit P/D score with
 * no legacy marker) are left untouched.
 */
function normalizeSpecialRows(
  rows: PericoloValutazione[],
  codeById: ReadonlyMap<string, string>,
  hasGestantiAllegato: boolean,
): { rows: PericoloValutazione[]; changed: boolean } {
  let changed = false;
  const next = rows.map((row) => {
    const kind = specialKindOf(row, codeById);
    if (!kind) return row;
    const rif = row.valutazione_riferimento?.trim() ?? null;
    const managed =
      (rif != null && rif in LEGACY_MARKER_KIND) ||
      rif === GESTANTI_ALLEGATO_RIFERIMENTO ||
      (rif == null && row.probabilita_p == null && row.danno_d == null);
    if (!managed) return row;

    if (kind === "gestanti" && hasGestantiAllegato) {
      if (
        rif === GESTANTI_ALLEGATO_RIFERIMENTO &&
        row.probabilita_p == null &&
        row.danno_d == null
      ) {
        return row;
      }
      changed = true;
      return {
        ...row,
        valutazione_riferimento: GESTANTI_ALLEGATO_RIFERIMENTO,
        probabilita_p: null,
        danno_d: null,
        indice_i: null,
        livello_rischio: null,
      };
    }

    if (rif == null && row.probabilita_p != null && row.danno_d != null) {
      return row;
    }
    changed = true;
    const p = row.probabilita_p ?? SPECIAL_DEFAULT_P;
    const d = row.danno_d ?? SPECIAL_DEFAULT_D;
    const indice = calcIndice(p, d);
    return {
      ...row,
      valutazione_riferimento: null,
      probabilita_p: p,
      danno_d: d,
      indice_i: indice,
      livello_rischio: getLivello(indice),
    };
  });
  return { rows: changed ? next : rows, changed };
}

const getLivello = livelloFor;
const LIVELLO_STYLE = RISK_CHIP;

export function PericoliPanel({
  aziendaId,
  ambienteId,
  valutazione,
  categoriaLong,
  onSummaryChange,
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
  // Separate from "loaded successfully with zero pericoli" — when the GET
  // throws transiently (Render cold start, network blip), the empty list
  // would otherwise render the "Nessun pericolo applicabile" copy and the
  // operator collapses/re-expands to retry. Feedback #e202bee9 (2026-05-12).
  const [loadError, setLoadError] = useState<string | null>(null);
  // True when the azienda has at least one Valutazione Rischio Gestanti —
  // the gestanti special row (OR-03) can then defer to the allegato instead
  // of carrying its own P/D score. Fetched together with the pericoli, and
  // only for the Organizzazione del Lavoro categoria.
  const [hasGestantiAllegato, setHasGestantiAllegato] = useState(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const rischioId = valutazione.id;

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

  // Lazy-load on first expand (avoids fetching for every applicable
  // categoria up front when the operator only reviews a few).
  const loadInitial = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    // Retry the reads a few times before surfacing an error. The API runs on
    // a basic-256mb Render instance that cold-starts after idle, so the first
    // GET when the operator opens a risk detail intermittently fails and a
    // manual collapse/re-expand "magically fixes it". Auto-retry with backoff
    // removes that manual workaround. Feedback #68 (2026-06-08).
    const fetchWithRetry = async <T,>(url: string, attempts = 3): Promise<T> => {
      let lastErr: unknown;
      for (let i = 0; i < attempts; i++) {
        try {
          return await apiFetch<T>(url);
        } catch (err) {
          lastErr = err;
          if (i < attempts - 1) {
            await new Promise((r) => setTimeout(r, 400 * 2 ** i));
          }
        }
      }
      throw lastErr;
    };
    try {
      const [sugg, existing, gestantiRows] = await Promise.all([
        fetchWithRetry<PericoloSuggestionResponse>(
          `/api/v1/aziende/${aziendaId}/ambienti/${ambienteId}/pericoli-suggeriti?categoria=${encodeURIComponent(categoriaLong)}`,
        ),
        fetchWithRetry<PericoloValutazione[]>(
          `/api/v1/aziende/${aziendaId}/ambienti/${ambienteId}/rischi/${rischioId}/pericoli`,
        ),
        // Gestanti-allegato presence drives the OR-03 row mode; a lookup
        // failure just means "no allegato", never a blocked panel.
        categoriaLong === CATEGORIA_ORGANIZZAZIONE
          ? apiFetch<unknown[]>(`/api/v1/aziende/${aziendaId}/gestanti`).catch(
              () => [] as unknown[],
            )
          : Promise.resolve([] as unknown[]),
      ]);
      setSuggestions(sugg.items);
      const gestantiAllegato = gestantiRows.length > 0;
      setHasGestantiAllegato(gestantiAllegato);
      const codeById = new Map(
        sugg.items.map((s) => [s.pericolo.id, s.pericolo.code]),
      );

      if (existing.length > 0) {
        // Migrate legacy "Vedi normativa ..." markers in place (and persist
        // the migration) — see normalizeSpecialRows.
        const normalized = normalizeSpecialRows(
          existing,
          codeById,
          gestantiAllegato,
        );
        setPericoli(normalized.rows);
        if (normalized.changed) scheduleSave(normalized.rows);
        return;
      }

      // No children yet — auto-seed from suggestions. Only rows whose
      // ambiente actually matches OR whose equipment-keyword fired are
      // auto-applied; the rest become available via "Aggiungi suggeriti
      // disponibili" if the operator wants to opt in later.
      // The gestanti row (OR-03) seeds in "come da documento allegato"
      // mode when the azienda already has a Valutazione Rischio Gestanti;
      // the toggle in the row lets the operator switch to an indice score.
      const seedItems = sugg.items.map((s, idx) => {
        const gestantiDelegata =
          gestantiAllegato &&
          SPECIAL_KIND_BY_CODE[s.pericolo.code] === "gestanti";
        return {
          pericolo_libreria_id: s.pericolo.id,
          source: "catalog" as const,
          pericolo: s.pericolo.pericolo,
          condizioni_esposizione: s.pericolo.condizioni_esposizione,
          rischio: s.pericolo.rischio,
          misure_prevenzione: s.pericolo.misure_prevenzione,
          probabilita_p: gestantiDelegata ? null : s.pericolo.p_default,
          danno_d: gestantiDelegata ? null : s.pericolo.d_default,
          valutazione_riferimento: gestantiDelegata
            ? GESTANTI_ALLEGATO_RIFERIMENTO
            : s.pericolo.valutazione_riferimento,
          applicabile: true,
          ordine: idx,
        };
      });
      if (seedItems.length === 0) return;
      const saved = await apiFetch<PericoloValutazione[]>(
        `/api/v1/aziende/${aziendaId}/ambienti/${ambienteId}/rischi/${rischioId}/pericoli/batch`,
        { method: "POST", body: JSON.stringify({ items: seedItems }) },
      );
      // Fresh seeds still need the special-row pass: the gestanti row flips
      // to "come da documento allegato" when the azienda already has one.
      const normalizedSeed = normalizeSpecialRows(
        saved,
        codeById,
        gestantiAllegato,
      );
      setPericoli(normalizedSeed.rows);
      if (normalizedSeed.changed) scheduleSave(normalizedSeed.rows);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Errore caricamento pericoli";
      setLoadError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
      setLoadedOnce(true);
    }
  }, [apiFetch, aziendaId, ambienteId, rischioId, categoriaLong, scheduleSave]);

  useEffect(() => {
    if (expanded && pericoli.length === 0 && !loading) {
      void loadInitial();
    }
    // We intentionally only run when expanded flips.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expanded]);

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

  // Special worker-category support — resolve the catalog code for each row
  // so the render pass can spot the gestanti row and offer the mode toggle.
  const codeById = useMemo(
    () => new Map(suggestions.map((s) => [s.pericolo.id, s.pericolo.code])),
    [suggestions],
  );

  // Gestanti row: switch between "come da documento allegato" and a direct
  // indice score (I = 2D + P). Only offered when the azienda has the
  // Valutazione Rischio Gestanti.
  const toggleGestantiMode = useCallback(
    (row: PericoloValutazione) => {
      if (row.valutazione_riferimento === GESTANTI_ALLEGATO_RIFERIMENTO) {
        updatePericolo(row.id, {
          valutazione_riferimento: null,
          probabilita_p: SPECIAL_DEFAULT_P,
          danno_d: SPECIAL_DEFAULT_D,
        });
      } else {
        updatePericolo(row.id, {
          valutazione_riferimento: GESTANTI_ALLEGATO_RIFERIMENTO,
          probabilita_p: null,
          danno_d: null,
          indice_i: null,
          livello_rischio: null,
        });
      }
    },
    [updatePericolo],
  );

  // Bulk-set valutazione_riferimento on all pericoli to defer detail to an
  // external attached assessment (feedback #a6f06283 — fire risk pattern,
  // generalised here because the same pattern helps other categorie too).
  const bulkSetReferenceAttached = useCallback(
    (set: boolean) => {
      setPericoli((prev) => {
        const next = prev.map((p) => ({
          ...p,
          valutazione_riferimento: set ? DELEGATED_REFERENCE_LABEL : null,
        }));
        scheduleSave(next);
        return next;
      });
      toast.success(
        set
          ? "Tutti i pericoli rinviati alla valutazione allegata."
          : "Rinvio alla valutazione allegata rimosso.",
      );
    },
    [scheduleSave],
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
          {loadError && !loading && (
            <div className="flex items-center justify-between gap-3 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              <span>Caricamento pericoli non riuscito: {loadError}</span>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => void loadInitial()}
              >
                Riprova
              </Button>
            </div>
          )}

          {!loadError && pericoli.length === 0 && !loading && (
            <p className="text-xs italic text-muted-foreground">
              Nessun pericolo applicabile dal catalogo per questa
              combinazione (tipo ambiente + attrezzature). Aggiungi un
              pericolo personalizzato sotto.
            </p>
          )}

          {pericoli.length > 0 && (
            <div className="flex flex-wrap items-center justify-end gap-2">
              {/* Feedback #a6f06283 (2026-05-09): bulk-flag all pericoli as
                  "Come da valutazione allegata" so the operator can defer
                  detail to an external attached assessment in one click. */}
              {(() => {
                const flagged = pericoli.filter(
                  (p) =>
                    p.valutazione_riferimento === DELEGATED_REFERENCE_LABEL,
                ).length;
                const allFlagged =
                  flagged === pericoli.length && pericoli.length > 0;
                return (
                  <Button
                    type="button"
                    variant="outline"
                    size="xs"
                    onClick={() => bulkSetReferenceAttached(!allFlagged)}
                    title={
                      allFlagged
                        ? "Rimuovi il rinvio alla valutazione allegata da tutti i pericoli"
                        : "Imposta 'Come da valutazione allegata' su tutti i pericoli"
                    }
                  >
                    {allFlagged
                      ? "Annulla rinvio a valutazione allegata"
                      : "Come da valutazione allegata"}
                  </Button>
                );
              })()}
            </div>
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
                    const showGestantiToggle =
                      specialKindOf(p, codeById) === "gestanti" &&
                      hasGestantiAllegato;
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
                                    variant="info"
                                    className="text-[9px]"
                                  >
                                    Personalizzato
                                  </Badge>
                                )}
                                {isDelegated && (
                                  <Badge
                                    variant="ai"
                                    className="text-[9px]"
                                  >
                                    {p.valutazione_riferimento}
                                  </Badge>
                                )}
                                {showGestantiToggle && (
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="xs"
                                    className="h-5 px-1.5 text-[9px]"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      toggleGestantiMode(p);
                                    }}
                                  >
                                    {isDelegated
                                      ? "Scegli indice di rischio"
                                      : "Usa documento allegato"}
                                  </Button>
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
                              className="text-muted-foreground hover:text-[#b01e2e]"
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
                              variant="success"
                              className="text-[9px]"
                            >
                              <Sparkles className="mr-0.5 h-2.5 w-2.5" />
                              Adatto all&apos;ambiente
                            </Badge>
                          )}
                          {s.triggered_by_attrezzature.length > 0 && (
                            <Badge
                              variant="warning"
                              className="text-[9px]"
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
