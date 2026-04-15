"use client";

/**
 * POS phase-builder (US-4.7).
 *
 * Top-level composition for the per-cantiere phase list:
 *  - DnD Kit Sortable for drag-drop reorder (AC2)
 *  - Per-card detail tabs (AC1: rischi/DPI/mezzi/NIOSH/rumore/vibrazioni)
 *  - Per-card chip picker for `dipende_da` (AC3: dependency links)
 *  - Quadro Sinottico summary card mirroring the docx output for a quick
 *    visual of the dependency graph
 *  - PUT /aziende/{id}/pos/{pos_id}/fasi on save; backend renumbers
 *    `ordine` to 0..n-1 and rejects cycles / self-deps / unknown deps
 *    with an Italian operator-facing message.
 */

import { useCallback, useMemo, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { Plus, Save } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";

import { PhaseCard } from "./phase-card";
import {
  makeBlankPhase,
  phasesUpdateSchema,
  type PhasesUpdateValues,
  type PhaseValues,
} from "./phase-schema";

interface PhaseBuilderProps {
  aziendaId: string;
  posId: string;
  initialPhases: PhaseValues[];
  onSaved?: () => void;
}

export function PhaseBuilder({
  aziendaId,
  posId,
  initialPhases,
  onSaved,
}: PhaseBuilderProps) {
  const { apiFetch } = useApi();
  const [saving, setSaving] = useState(false);

  const form = useForm<PhasesUpdateValues>({
    resolver: zodResolver(phasesUpdateSchema),
    defaultValues: {
      fasi: initialPhases
        .slice()
        .sort((a, b) => a.ordine - b.ordine)
        .map((p, i) => ({ ...p, ordine: i })),
    },
    mode: "onBlur",
  });

  const phasesArray = useFieldArray({
    control: form.control,
    name: "fasi",
    keyName: "_rhfId",
  });

  const phases = form.watch("fasi");

  // dnd-kit sensors. Distance:5 keeps clicks on the input from triggering drag.
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const handleDragEnd = useCallback(
    (ev: DragEndEvent) => {
      const { active, over } = ev;
      if (!over || active.id === over.id) return;
      const oldIdx = phases.findIndex((p) => p.id === active.id);
      const newIdx = phases.findIndex((p) => p.id === over.id);
      if (oldIdx < 0 || newIdx < 0) return;
      // arrayMove + react-hook-form's `replace` so the form state stays
      // perfectly aligned with the visible order. (`move()` from
      // useFieldArray works too but `replace()` lets us renumber `ordine`
      // in the same pass which keeps the docx and UI ordering identical.)
      const reordered = arrayMove(phases, oldIdx, newIdx).map((p, i) => ({
        ...p,
        ordine: i,
      }));
      form.setValue("fasi", reordered, { shouldDirty: true });
    },
    [form, phases],
  );

  const sortableIds = useMemo(() => phases.map((p) => p.id), [phases]);

  const addPhase = () => {
    phasesArray.append(makeBlankPhase(phases.length));
  };

  const handleRemovePhase = useCallback(
    (idx: number) => {
      const removedId = phases[idx]?.id;
      // First strip dependency edges that pointed at the removed phase…
      if (removedId) {
        const cleaned = phases.map((p, pi) =>
          pi === idx
            ? p
            : { ...p, dipende_da: p.dipende_da.filter((d) => d !== removedId) },
        );
        form.setValue("fasi", cleaned, { shouldDirty: true });
      }
      // …then drop the phase row and renumber.
      phasesArray.remove(idx);
      // Field array doesn't renumber `ordine` on its own. Read the new
      // value back via `getValues` so we don't depend on the watch tick.
      const after = form.getValues("fasi");
      form.setValue(
        "fasi",
        after.map((p, i) => ({ ...p, ordine: i })),
        { shouldDirty: true },
      );
    },
    [form, phases, phasesArray],
  );

  // Render the Quadro Sinottico (mirrors the docx generator output).
  const synoptic = useMemo(() => {
    const nameById = new Map(phases.map((p) => [p.id, p.nome] as const));
    return phases.map((p) => ({
      ordine: p.ordine,
      nome: p.nome || "(senza nome)",
      dipende_da: p.dipende_da
        .map((d) => nameById.get(d) ?? d)
        .join(", "),
    }));
  }, [phases]);

  const onSave = form.handleSubmit(async (v) => {
    setSaving(true);
    try {
      // The backend re-validates and returns the persisted POS row with
      // canonical `fasi_lavorative`. We swap our form state to that
      // result so the operator sees the server-renumbered ordine.
      const saved = await apiFetch<{ fasi_lavorative: PhaseValues[] }>(
        `/api/v1/aziende/${aziendaId}/pos/${posId}/fasi`,
        {
          method: "PUT",
          body: JSON.stringify({ fasi: v.fasi }),
        },
      );
      const fresh = (saved.fasi_lavorative ?? [])
        .slice()
        .sort((a, b) => (a.ordine ?? 0) - (b.ordine ?? 0));
      form.reset({ fasi: fresh });
      toast.success("Fasi salvate");
      onSaved?.();
    } catch (err) {
      toast.error((err as Error).message || "Salvataggio fasi fallito");
    } finally {
      setSaving(false);
    }
  });

  const isDirty = form.formState.isDirty;

  return (
    <form onSubmit={onSave} className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base">Fasi lavorative</CardTitle>
            <CardDescription className="text-xs">
              Trascina per riordinare. Espandi una fase per assegnare
              rischi/DPI, snapshot NIOSH/rumore/vibrazioni e predecessori.
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" onClick={addPhase}>
              <Plus className="mr-1 h-3 w-3" /> Aggiungi fase
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={saving || !isDirty}
              aria-label="Salva fasi"
            >
              <Save className="mr-1 h-3 w-3" />
              {saving ? "Salvataggio…" : "Salva fasi"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          {phasesArray.fields.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Nessuna fase. Aggiungi la prima lavorazione del cantiere
              (es. Allestimento cantiere, Scavo, Getto calcestruzzo).
            </p>
          )}
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={sortableIds}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {phasesArray.fields.map((f, i) => (
                  <PhaseCard
                    key={f._rhfId}
                    id={phases[i]?.id ?? f._rhfId}
                    index={i}
                    form={form}
                    allPhases={phases}
                    onRemove={() => handleRemovePhase(i)}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </CardContent>
      </Card>

      {/* --- Quadro sinottico (Gantt logico) ------------------------- */}
      {phases.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Quadro sinottico (Gantt logico)
            </CardTitle>
            <CardDescription className="text-xs">
              Anteprima di come le fasi compariranno nel POS .docx. La colonna
              "Dipende da" rispecchia i predecessori scelti per ogni fase.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">#</TableHead>
                  <TableHead>Fase</TableHead>
                  <TableHead>Dipende da</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {synoptic.map((row) => (
                  <TableRow key={`${row.ordine}-${row.nome}`}>
                    <TableCell className="tabular-nums">
                      {row.ordine + 1}
                    </TableCell>
                    <TableCell>{row.nome}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {row.dipende_da || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </form>
  );
}

