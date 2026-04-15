"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2, RotateCcw, Save } from "lucide-react";
import { toast } from "sonner";

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
import type { PhaseValues } from "@/components/assessments/pos/phase-schema";

/**
 * POS DPI matrix editor (US-4.8).
 *
 * Three-card layout: Ruoli picker, Fasi picker, then the role x phase
 * matrix with per-cell DPI override popovers. Single POS per azienda for
 * MVP — we auto-create one if none exists so the operator lands on a
 * usable editor regardless of whether they've visited the azienda before.
 */

// Orchestrator will move these to frontend/src/types/index.ts.
interface DpiCatalog {
  roles: string[];
  phases: string[];
  dpi_catalog: Record<string, string>;
}

interface DpiMatrix {
  [phase: string]: { [role: string]: string[] };
}

interface Pos {
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
  const [openCell, setOpenCell] = useState<{ phase: string; role: string } | null>(null);

  // Debounce matrix saves so clicking multiple DPI chips in a row batches
  // into one POST instead of hammering the backend.
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

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
        setPos(updated);
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
  };

  const persistSelection = () => {
    if (!pos) return;
    void persist(pos, pos.dpi_matrix);
  };

  // --- Card 3: matrix cell edits -----------------------------------------
  const cellDpi = (phase: string, role: string): string[] => {
    if (!pos) return [];
    return pos.dpi_matrix?.[phase]?.[role] ?? [];
  };

  const toggleCellDpi = (phase: string, role: string, code: string) => {
    if (!pos) return;
    const current = cellDpi(phase, role);
    const nextCodes = current.includes(code)
      ? current.filter((c) => c !== code)
      : [...current, code];
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
        <h1 className="text-2xl font-semibold tracking-tight">POS — Cantiere</h1>
        <p className="text-sm text-muted-foreground">
          Costruisci le fasi lavorative del cantiere (US-4.7) e personalizza
          la matrice DPI per ruolo / fase (US-4.8). Le modifiche al phase
          builder vanno salvate manualmente; la matrice DPI è auto-salvata.
        </p>
      </header>

      {/* US-4.7 — Phase builder (rischi, NIOSH, rumore, vibrazioni, drag-drop, dipende_da) */}
      <PhaseBuilder
        aziendaId={aziendaId}
        posId={pos.id}
        initialPhases={(pos.fasi_lavorative ?? []) as PhaseValues[]}
        onSaved={() => void load()}
      />

      {/* Card 1 — Ruoli (US-4.8 DPI matrix) */}
      <Card>
        <CardHeader>
          <CardTitle>Ruoli in cantiere</CardTitle>
          <CardDescription>
            Seleziona i ruoli coinvolti nei lavori. Le modifiche sono salvate quando
            esci dal campo.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2" onBlur={persistSelection}>
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
        </CardContent>
      </Card>

      {/* Card 2 — Fasi (DPI matrix) */}
      <Card>
        <CardHeader>
          <CardTitle>Fasi per la matrice DPI</CardTitle>
          <CardDescription>
            Seleziona le fasi standard usate come colonne della matrice DPI
            (sotto). Le fasi reali del cantiere si gestiscono nel
            phase-builder in alto.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2" onBlur={persistSelection}>
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
          <Button
            variant="outline"
            size="sm"
            onClick={() => setRegenOpen(true)}
            disabled={!hasMatrix || regenRunning}
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            Rigenera dai default
          </Button>
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
                            <div className="flex flex-wrap gap-1">
                              {codes.length === 0 ? (
                                <span className="text-xs italic text-muted-foreground">
                                  Nessun DPI
                                </span>
                              ) : (
                                codes.map((c) => (
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
                            {isOpen && (
                              <div
                                className="mt-2 rounded-md border bg-popover p-2 text-popover-foreground shadow-md"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <div className="mb-1 text-xs font-medium text-muted-foreground">
                                  DPI richiesti
                                </div>
                                <div className="flex flex-col gap-1">
                                  {dpiKeys.map((code) => {
                                    const checked = codes.includes(code);
                                    return (
                                      <label
                                        key={code}
                                        className="flex items-center gap-2 text-xs"
                                      >
                                        <input
                                          type="checkbox"
                                          checked={checked}
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
                            )}
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
