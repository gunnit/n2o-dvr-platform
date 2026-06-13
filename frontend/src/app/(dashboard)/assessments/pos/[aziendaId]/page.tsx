"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2, Plus, RotateCcw, Save, Sparkles, X } from "lucide-react";
import { toast } from "sonner";

import { Input } from "@/components/ui/input";

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
import { useApi } from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import { PhaseBuilder } from "@/components/assessments/pos/phase-builder";
import {
  promoteLegacyPhase,
  type PhaseValues,
} from "@/components/assessments/pos/phase-schema";
import {
  PosAnagraficaSummary,
  PosInfoEditor,
  type PosInfoFields,
} from "@/components/assessments/pos/pos-info-cards";

/**
 * POS DPI matrix editor (US-4.8).
 *
 * Three-card layout: Ruoli picker, Fasi picker, then the role x phase
 * matrix with per-cell DPI override popovers. Single POS per azienda for
 * MVP — we auto-create one if none exists so the operator lands on a
 * usable editor regardless of whether they've visited the azienda before.
 */

// Feedback #61 (2026-05-26): sentinel value persisted inside a DPI
// matrix cell to indicate "this role does not perform this operation".
// We use a __underscore__ key that can never collide with a real DPI
// code (the catalog keys are lowercase alphanum). The docx generator
// recognises the same sentinel and renders "Non effettua" instead of
// the DPI list.
const NON_EFFETTUA = "__non_effettua__";

// Slugify a free-text label so it can live alongside catalog keys in
// dpi_matrix_roles / dpi_matrix_phases. We strip accents, lowercase,
// and underscore-join — same shape as backend catalog keys, so the
// label fallback (key.replaceAll('_',' ')) reads naturally.
function slugify(input: string): string {
  return input
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

// Orchestrator will move these to frontend/src/types/index.ts.
interface DpiCatalog {
  roles: string[];
  phases: string[];
  dpi_catalog: Record<string, string>;
}

interface DpiMatrix {
  [phase: string]: { [role: string]: string[] };
}

interface Pos extends PosInfoFields {
  id: string;
  azienda_id: string;
  cantiere_indirizzo: string;
  dpi_matrix: DpiMatrix;
  dpi_matrix_roles: string[];
  dpi_matrix_phases: string[];
  // US-4.7: structured phase entries — read straight off the row, sent
  // back via PUT /pos/{id}/fasi by <PhaseBuilder>. Optional so legacy
  // rows still parse.
  fasi_lavorative?: PhaseValues[];
}

/** Pull the editable subset out of the full POS row for the info editor. */
function infoFieldsOf(p: Pos): PosInfoFields {
  return {
    committente: p.committente ?? null,
    progettista_responsabile: p.progettista_responsabile ?? null,
    direttore_lavori: p.direttore_lavori ?? null,
    direttore_operativo_edilizia: p.direttore_operativo_edilizia ?? null,
    direttore_operativo_impianti: p.direttore_operativo_impianti ?? null,
    responsabile_lavori: p.responsabile_lavori ?? null,
    coordinatore_progettazione: p.coordinatore_progettazione ?? null,
    coordinatore_sicurezza: p.coordinatore_sicurezza ?? null,
    orario_lavoro_cantiere: p.orario_lavoro_cantiere ?? null,
    turni_descrizione: p.turni_descrizione ?? null,
    riunioni_coordinamento: p.riunioni_coordinamento ?? null,
    monoblocchi_installati: p.monoblocchi_installati ?? false,
    monoblocchi_dettagli: p.monoblocchi_dettagli ?? null,
    modalita_pasti: p.modalita_pasti ?? null,
  };
}

// --- Italian labels for the role/phase keys returned by the backend.
// The backend only ever returns keys; labels live frontend-side so the
// operator can tweak them per locale without a migration.
const ROLE_LABELS: Record<string, string> = {
  carpentiere: "Carpentiere",
  manovale: "Manovale",
  gruista: "Gruista",
  operatore_escavatore: "Operatore escavatore",
  ponteggiatore: "Ponteggiatore",
  saldatore: "Saldatore",
  elettricista: "Elettricista",
  muratore: "Muratore",
  capo_cantiere: "Capo cantiere",
  autista_mezzi: "Autista mezzi",
};

const PHASE_LABELS: Record<string, string> = {
  allestimento_cantiere: "Allestimento cantiere",
  scavi: "Scavi",
  fondazioni: "Fondazioni",
  getto_calcestruzzo: "Getto calcestruzzo",
  montaggio_ponteggi: "Montaggio ponteggi",
  opere_murarie: "Opere murarie",
  finiture: "Finiture",
  smobilizzo_cantiere: "Smobilizzo cantiere",
};

function labelRole(key: string): string {
  return ROLE_LABELS[key] ?? key.replaceAll("_", " ");
}

function labelPhase(key: string): string {
  return PHASE_LABELS[key] ?? key.replaceAll("_", " ");
}

export default function PosDpiMatrixPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;
  const { apiFetch, isAuthenticated } = useApi();

  const [catalog, setCatalog] = useState<DpiCatalog | null>(null);
  const [pos, setPos] = useState<Pos | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [regenOpen, setRegenOpen] = useState(false);
  const [regenRunning, setRegenRunning] = useState(false);
  const [aiRunning, setAiRunning] = useState(false);
  const [openCell, setOpenCell] = useState<{ phase: string; role: string } | null>(null);
  // Feedback #59/#60: free-text inputs for adding custom roles/phases
  // that are not in the backend catalog. Persisted into dpi_matrix_roles
  // / dpi_matrix_phases as slugified keys; labels render via the
  // existing labelRole / labelPhase fallback (key→spaces).
  const [customRoleInput, setCustomRoleInput] = useState("");
  const [customPhaseInput, setCustomPhaseInput] = useState("");

  // Debounce matrix saves so clicking multiple DPI chips in a row batches
  // into one POST instead of hammering the backend.
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Track mount so a debounced save that lands after unmount still completes
  // the network write (no data loss) but skips the setState (no React warning).
  const mountedRef = useRef(true);

  const persist = useCallback(
    async (next: Pos, matrixOverride: DpiMatrix | null) => {
      try {
        const updated = await apiFetch<Pos>(
          `/api/v1/aziende/${aziendaId}/pos/${next.id}/dpi-matrix`,
          {
            method: "POST",
            body: JSON.stringify({
              roles: next.dpi_matrix_roles,
              phases: next.dpi_matrix_phases,
              matrix: matrixOverride,
            }),
          }
        );
        if (mountedRef.current) setPos(updated);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Salvataggio non riuscito.";
        toast.error(msg);
      }
    },
    [aziendaId, apiFetch]
  );

  const scheduleSave = useCallback(
    (next: Pos) => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => {
        void persist(next, next.dpi_matrix);
      }, 500);
    },
    [persist]
  );

  // --- Initial load ------------------------------------------------------
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cat, list] = await Promise.all([
        apiFetch<DpiCatalog>(`/api/v1/aziende/${aziendaId}/pos/meta/dpi-catalog`),
        apiFetch<Pos[]>(`/api/v1/aziende/${aziendaId}/pos`),
      ]);
      setCatalog(cat);
      let current = list[0] ?? null;
      if (!current) {
        current = await apiFetch<Pos>(`/api/v1/aziende/${aziendaId}/pos`, {
          method: "POST",
          body: JSON.stringify({ cantiere_indirizzo: "Da definire" }),
        });
      }
      setPos(current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Caricamento non riuscito.");
    } finally {
      setLoading(false);
    }
  }, [aziendaId, apiFetch]);

  useEffect(() => {
    if (!isAuthenticated) return;
    void load();
  }, [isAuthenticated, load]);

  // On unmount, mark unmounted so a pending debounced save still writes to the
  // server but skips its setState. We deliberately do NOT clearTimeout here —
  // that would drop the last edit (the very data we're trying to persist).
  useEffect(
    () => () => {
      mountedRef.current = false;
    },
    [],
  );

  // --- Card 1 / 2: role + phase selection --------------------------------
  const toggleRole = (role: string) => {
    if (!pos) return;
    const exists = pos.dpi_matrix_roles.includes(role);
    const next: Pos = {
      ...pos,
      dpi_matrix_roles: exists
        ? pos.dpi_matrix_roles.filter((r) => r !== role)
        : [...pos.dpi_matrix_roles, role],
    };
    setPos(next);
    // Persist on toggle (debounced), not only on blur — selections were lost
    // if the operator saved/navigated before a chip lost focus.
    scheduleSave(next);
  };

  const togglePhase = (phase: string) => {
    if (!pos) return;
    const exists = pos.dpi_matrix_phases.includes(phase);
    const next: Pos = {
      ...pos,
      dpi_matrix_phases: exists
        ? pos.dpi_matrix_phases.filter((p) => p !== phase)
        : [...pos.dpi_matrix_phases, phase],
    };
    setPos(next);
    scheduleSave(next);
  };

  const persistSelection = () => {
    if (!pos) return;
    void persist(pos, pos.dpi_matrix);
  };

  // Feedback #59/#60: add a custom role/phase. We slugify so the key
  // looks like the catalog ones (lowercase_underscore) and the label
  // fallback in labelRole/labelPhase renders it nicely. Persisted
  // immediately — no need for the operator to blur a chip.
  const addCustomRole = () => {
    if (!pos) return;
    const slug = slugify(customRoleInput);
    if (!slug) return;
    if (pos.dpi_matrix_roles.includes(slug)) {
      toast.error("Questo ruolo è già presente.");
      return;
    }
    const next: Pos = {
      ...pos,
      dpi_matrix_roles: [...pos.dpi_matrix_roles, slug],
    };
    setPos(next);
    setCustomRoleInput("");
    void persist(next, next.dpi_matrix);
  };

  const addCustomPhase = () => {
    if (!pos) return;
    const slug = slugify(customPhaseInput);
    if (!slug) return;
    if (pos.dpi_matrix_phases.includes(slug)) {
      toast.error("Questa fase è già presente.");
      return;
    }
    const next: Pos = {
      ...pos,
      dpi_matrix_phases: [...pos.dpi_matrix_phases, slug],
    };
    setPos(next);
    setCustomPhaseInput("");
    void persist(next, next.dpi_matrix);
  };

  // Remove a custom role/phase. Only meaningful for non-catalog keys
  // (catalog keys are toggled via the standard chip click). Cleans up
  // the related matrix cells so we don't leave orphan data.
  const removeCustomRole = (role: string) => {
    if (!pos) return;
    const nextMatrix: DpiMatrix = {};
    for (const [phase, row] of Object.entries(pos.dpi_matrix ?? {})) {
      const { [role]: _drop, ...rest } = row;
      nextMatrix[phase] = rest;
    }
    const next: Pos = {
      ...pos,
      dpi_matrix_roles: pos.dpi_matrix_roles.filter((r) => r !== role),
      dpi_matrix: nextMatrix,
    };
    setPos(next);
    void persist(next, next.dpi_matrix);
  };

  const removeCustomPhase = (phase: string) => {
    if (!pos) return;
    const { [phase]: _drop, ...nextMatrix } = pos.dpi_matrix ?? {};
    const next: Pos = {
      ...pos,
      dpi_matrix_phases: pos.dpi_matrix_phases.filter((p) => p !== phase),
      dpi_matrix: nextMatrix,
    };
    setPos(next);
    void persist(next, next.dpi_matrix);
  };

  // Custom roles/phases = those in the POS state but not in the catalog.
  const customRoles = useMemo(
    () => pos?.dpi_matrix_roles.filter((r) => !catalog?.roles.includes(r)) ?? [],
    [pos, catalog],
  );
  const customPhases = useMemo(
    () => pos?.dpi_matrix_phases.filter((p) => !catalog?.phases.includes(p)) ?? [],
    [pos, catalog],
  );

  // --- Card 3: matrix cell edits -----------------------------------------
  const cellDpi = (phase: string, role: string): string[] => {
    if (!pos) return [];
    return pos.dpi_matrix?.[phase]?.[role] ?? [];
  };

  const toggleCellDpi = (phase: string, role: string, code: string) => {
    if (!pos) return;
    const current = cellDpi(phase, role);
    // Feedback #61: toggling any real DPI code clears the "non effettua"
    // sentinel — the operator is implicitly saying the role does perform
    // the operation after all.
    const cleaned = current.filter((c) => c !== NON_EFFETTUA);
    const nextCodes = cleaned.includes(code)
      ? cleaned.filter((c) => c !== code)
      : [...cleaned, code];
    const nextMatrix: DpiMatrix = {
      ...pos.dpi_matrix,
      [phase]: { ...(pos.dpi_matrix?.[phase] ?? {}), [role]: nextCodes },
    };
    const next: Pos = { ...pos, dpi_matrix: nextMatrix };
    setPos(next);
    scheduleSave(next);
  };

  // Feedback #61: flip the "non effettua questa operazione" flag for a
  // single cell. When enabled the cell holds only the sentinel and all
  // DPI codes are cleared. Disabling restores an empty array (operator
  // re-picks DPI codes).
  const toggleCellNonEffettua = (phase: string, role: string) => {
    if (!pos) return;
    const current = cellDpi(phase, role);
    const isNonEffettua = current.includes(NON_EFFETTUA);
    const nextCodes = isNonEffettua ? [] : [NON_EFFETTUA];
    const nextMatrix: DpiMatrix = {
      ...pos.dpi_matrix,
      [phase]: { ...(pos.dpi_matrix?.[phase] ?? {}), [role]: nextCodes },
    };
    const next: Pos = { ...pos, dpi_matrix: nextMatrix };
    setPos(next);
    scheduleSave(next);
  };

  const regenerate = async () => {
    if (!pos) return;
    setRegenRunning(true);
    try {
      await persist(pos, null);
      toast.success("Matrice rigenerata dai default.");
    } finally {
      setRegenRunning(false);
      setRegenOpen(false);
    }
  };

  // Feedback #64/#50: AI auto-fill for the DPI matrix. The endpoint returns
  // a {phase: {role: [codes]}} suggestion; we merge it into EMPTY cells only
  // — never overwriting a cell the operator already set, including the
  // "__non_effettua__" sentinel. After merging we persist() so it saves.
  const suggestWithAI = async () => {
    if (!pos) return;
    setAiRunning(true);
    try {
      const { matrix: suggestion } = await apiFetch<{ matrix: DpiMatrix }>(
        `/api/v1/aziende/${aziendaId}/pos/meta/suggest-dpi-matrix`,
        {
          method: "POST",
          body: JSON.stringify({
            roles: pos.dpi_matrix_roles,
            phases: pos.dpi_matrix_phases,
          }),
        }
      );

      const nextMatrix: DpiMatrix = {};
      let filled = 0;
      for (const phase of pos.dpi_matrix_phases) {
        nextMatrix[phase] = { ...(pos.dpi_matrix?.[phase] ?? {}) };
        for (const role of pos.dpi_matrix_roles) {
          const existing = pos.dpi_matrix?.[phase]?.[role] ?? [];
          // An empty array is the only "untouched" state. A populated cell
          // — DPI codes OR the non-effettua sentinel — is an operator
          // choice and must be preserved.
          if (existing.length > 0) continue;
          const proposed = suggestion?.[phase]?.[role];
          if (proposed && proposed.length > 0) {
            nextMatrix[phase][role] = proposed;
            filled += 1;
          }
        }
      }

      if (filled === 0) {
        toast.info("Nessuna cella vuota da compilare.");
        return;
      }

      const next: Pos = { ...pos, dpi_matrix: nextMatrix };
      setPos(next);
      await persist(next, nextMatrix);
      toast.success(
        `${filled} cell${filled === 1 ? "a" : "e"} compilat${
          filled === 1 ? "a" : "e"
        } con AI.`
      );
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Compilazione AI non riuscita.";
      toast.error(msg);
    } finally {
      setAiRunning(false);
    }
  };

  // --- Render ------------------------------------------------------------
  const dpiKeys = useMemo(() => (catalog ? Object.keys(catalog.dpi_catalog) : []), [catalog]);
  const hasMatrix = !!pos && pos.dpi_matrix_roles.length > 0 && pos.dpi_matrix_phases.length > 0;

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !catalog || !pos) {
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
        {error ?? "Dati non disponibili."}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="type-h1">POS — Cantiere</h1>
        <p className="text-sm text-muted-foreground">
          Inserisci soggetti di riferimento, modalità organizzative e
          logistica del cantiere, costruisci le fasi lavorative (US-4.7) e
          personalizza la matrice DPI per ruolo / fase (US-4.8). I campi
          testuali sono auto-salvati; il phase builder richiede il pulsante
          &quot;Salva fasi&quot;.
        </p>
      </header>

      {/* Anagrafica + dipendenti — read-only summary linking back to
          azienda/persone pages (Luca's 2026-05-25 POS template Groups A & B). */}
      <PosAnagraficaSummary aziendaId={aziendaId} />

      {/* Editable info cards: soggetti di riferimento, modalità
          organizzative, organizzazione logistica (Groups D, E, F). */}
      <PosInfoEditor
        aziendaId={aziendaId}
        posId={pos.id}
        initial={infoFieldsOf(pos)}
      />

      {/* US-4.7 — Phase builder (rischi, NIOSH, rumore, vibrazioni, drag-drop, dipende_da) */}
      <PhaseBuilder
        aziendaId={aziendaId}
        posId={pos.id}
        // B-06: Legacy seeds store fasi_lavorative as `{fase, dpi[], mezzi[],
        // rischi[], descrizione}` without id/ordine/dipende_da. Promote them
        // here (mirrors the backend's PosPhase in-place promotion) so the
        // builder never reads through `undefined.map()`.
        initialPhases={(pos.fasi_lavorative ?? []).map((raw, i) =>
          promoteLegacyPhase(raw as Record<string, unknown>, i),
        )}
        onSaved={() => void load()}
      />

      {/* Card 1 — Ruoli (US-4.8 DPI matrix) */}
      <Card>
        <CardHeader>
          <CardTitle>Ruoli in cantiere</CardTitle>
          <CardDescription>
            Seleziona i ruoli coinvolti nei lavori. Puoi aggiungere mansioni
            personalizzate non presenti nel catalogo (feedback #60).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2" onBlur={persistSelection}>
            {catalog.roles.map((role) => {
              const selected = pos.dpi_matrix_roles.includes(role);
              return (
                <button
                  key={role}
                  type="button"
                  onClick={() => toggleRole(role)}
                  onBlur={persistSelection}
                  className={cn(
                    "rounded-full border px-3 py-1 text-sm transition",
                    selected
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-input bg-background hover:bg-muted"
                  )}
                >
                  {labelRole(role)}
                </button>
              );
            })}
            {/* Feedback #60: chip per ogni ruolo personalizzato, con × per
                rimuoverlo. Sempre "selezionato" (è presente perché
                l'operatore l'ha aggiunto manualmente). */}
            {customRoles.map((role) => (
              <span
                key={role}
                className="inline-flex items-center gap-1 rounded-full border border-primary bg-primary px-3 py-1 text-sm text-primary-foreground"
              >
                {labelRole(role)}
                <button
                  type="button"
                  aria-label={`Rimuovi ruolo ${labelRole(role)}`}
                  onClick={() => removeCustomRole(role)}
                  className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full hover:bg-primary-foreground/20"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
          {/* Feedback #60: input + Aggiungi per ruoli non in catalogo. */}
          <div className="flex flex-wrap items-center gap-2 border-t pt-3">
            <Input
              value={customRoleInput}
              onChange={(e) => setCustomRoleInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addCustomRole();
                }
              }}
              placeholder="Es. Lattoniere, Posatore di pavimenti…"
              className="h-9 w-72"
            />
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={addCustomRole}
              disabled={!customRoleInput.trim()}
            >
              <Plus className="mr-1 h-3 w-3" />
              Aggiungi mansione
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Card 2 — Fasi (DPI matrix) */}
      <Card>
        <CardHeader>
          <CardTitle>Fasi per la matrice DPI</CardTitle>
          <CardDescription>
            Seleziona le fasi standard o aggiungi lavorazioni personalizzate
            (feedback #59). Le fasi qui scelte diventano le colonne della
            matrice DPI sottostante.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2" onBlur={persistSelection}>
            {catalog.phases.map((phase) => {
              const selected = pos.dpi_matrix_phases.includes(phase);
              return (
                <button
                  key={phase}
                  type="button"
                  onClick={() => togglePhase(phase)}
                  onBlur={persistSelection}
                  className={cn(
                    "rounded-full border px-3 py-1 text-sm transition",
                    selected
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-input bg-background hover:bg-muted"
                  )}
                >
                  {labelPhase(phase)}
                </button>
              );
            })}
            {/* Feedback #59: chip per fasi personalizzate. */}
            {customPhases.map((phase) => (
              <span
                key={phase}
                className="inline-flex items-center gap-1 rounded-full border border-primary bg-primary px-3 py-1 text-sm text-primary-foreground"
              >
                {labelPhase(phase)}
                <button
                  type="button"
                  aria-label={`Rimuovi fase ${labelPhase(phase)}`}
                  onClick={() => removeCustomPhase(phase)}
                  className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full hover:bg-primary-foreground/20"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2 border-t pt-3">
            <Input
              value={customPhaseInput}
              onChange={(e) => setCustomPhaseInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addCustomPhase();
                }
              }}
              placeholder="Es. Tinteggiatura interni, Cappotto termico…"
              className="h-9 w-72"
            />
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={addCustomPhase}
              disabled={!customPhaseInput.trim()}
            >
              <Plus className="mr-1 h-3 w-3" />
              Aggiungi lavorazione
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Card 3 — Matrice */}
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Matrice DPI</CardTitle>
            <CardDescription>
              Clicca una cella per modificare i DPI richiesti a quel ruolo durante
              la fase selezionata.
            </CardDescription>
          </div>
          <div className="flex shrink-0 gap-2">
            <Button
              size="sm"
              onClick={suggestWithAI}
              disabled={!hasMatrix || aiRunning || regenRunning}
              title="Compila i DPI delle celle vuote con AI (gpt-5.4-mini) in base a ruolo e lavorazione. Non sovrascrive le celle gia' impostate."
            >
              {aiRunning ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Compilazione...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Compila con AI
                </>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRegenOpen(true)}
              disabled={!hasMatrix || regenRunning || aiRunning}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              Rigenera dai default
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!hasMatrix ? (
            <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
              Seleziona almeno un ruolo e una fase per generare la matrice.
            </div>
          ) : (
            <div className="overflow-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="sticky left-0 z-10 min-w-[10rem] border p-2 text-left bg-muted/50">
                      Ruolo
                    </th>
                    {pos.dpi_matrix_phases.map((phase) => (
                      <th
                        key={phase}
                        className="min-w-[12rem] border p-2 text-left font-medium"
                      >
                        {labelPhase(phase)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pos.dpi_matrix_roles.map((role) => (
                    <tr key={role} className="align-top">
                      <td className="sticky left-0 z-10 border bg-background p-2 font-medium">
                        {labelRole(role)}
                      </td>
                      {pos.dpi_matrix_phases.map((phase) => {
                        const codes = cellDpi(phase, role);
                        const isOpen =
                          openCell?.phase === phase && openCell?.role === role;
                        return (
                          <td
                            key={phase}
                            className="border p-2 align-top"
                            onClick={() =>
                              setOpenCell(isOpen ? null : { phase, role })
                            }
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                setOpenCell(isOpen ? null : { phase, role });
                              }
                            }}
                          >
                            {(() => {
                              const isNonEffettua = codes.includes(NON_EFFETTUA);
                              const realCodes = codes.filter(
                                (c) => c !== NON_EFFETTUA,
                              );
                              return (
                                <div className="flex flex-wrap gap-1">
                                  {/* Feedback #61: visualizza "Non effettua"
                                      come stato distinto da "Nessun DPI". */}
                                  {isNonEffettua ? (
                                    <span className="text-xs italic text-muted-foreground">
                                      Non effettua questa operazione
                                    </span>
                                  ) : realCodes.length === 0 ? (
                                    <span className="text-xs italic text-muted-foreground">
                                      Nessun DPI
                                    </span>
                                  ) : (
                                    realCodes.map((c) => (
                                      <Badge
                                        key={c}
                                        variant="secondary"
                                        className="text-[11px]"
                                      >
                                        {catalog.dpi_catalog[c] ?? c}
                                      </Badge>
                                    ))
                                  )}
                                </div>
                              );
                            })()}
                            {isOpen && (() => {
                              const isNonEffettua = codes.includes(NON_EFFETTUA);
                              return (
                              <div
                                className="mt-2 rounded-md border bg-popover p-2 text-popover-foreground shadow-md"
                                onClick={(e) => e.stopPropagation()}
                              >
                                {/* Feedback #61: opzione "Non effettua questa
                                    operazione". Quando attiva, la cella
                                    contiene solo il sentinel e le checkbox
                                    DPI sono disabilitate. */}
                                <label className="mb-2 flex items-center gap-2 text-xs font-medium">
                                  <input
                                    type="checkbox"
                                    checked={isNonEffettua}
                                    onChange={() =>
                                      toggleCellNonEffettua(phase, role)
                                    }
                                  />
                                  <span>Non effettua questa operazione</span>
                                </label>
                                <div className="mb-1 border-t pt-2 text-xs font-medium text-muted-foreground">
                                  DPI richiesti
                                </div>
                                <div className="flex flex-col gap-1">
                                  {dpiKeys.map((code) => {
                                    const checked = codes.includes(code);
                                    return (
                                      <label
                                        key={code}
                                        className={cn(
                                          "flex items-center gap-2 text-xs",
                                          isNonEffettua &&
                                            "opacity-50",
                                        )}
                                      >
                                        <input
                                          type="checkbox"
                                          checked={checked}
                                          disabled={isNonEffettua}
                                          onChange={() =>
                                            toggleCellDpi(phase, role, code)
                                          }
                                        />
                                        <span>{catalog.dpi_catalog[code]}</span>
                                      </label>
                                    );
                                  })}
                                </div>
                                <div className="mt-2 flex justify-end">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setOpenCell(null)}
                                  >
                                    <Save className="mr-1 h-3 w-3" />
                                    Chiudi
                                  </Button>
                                </div>
                              </div>
                              );
                            })()}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={regenOpen} onOpenChange={setRegenOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rigenera dai default?</DialogTitle>
            <DialogDescription>
              Sovrascriverà le personalizzazioni. Continuare?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRegenOpen(false)}
              disabled={regenRunning}
            >
              Annulla
            </Button>
            <Button onClick={regenerate} disabled={regenRunning}>
              {regenRunning && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Rigenera
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
