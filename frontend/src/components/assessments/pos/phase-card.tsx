"use client";

/**
 * Draggable phase card (US-4.7 AC2).
 *
 * Wraps one PosPhase: drag handle, name input, dependency chip-picker,
 * expand/collapse, and the per-phase detail tabs.
 *
 * The card uses `useSortable` from @dnd-kit/sortable. The id passed in
 * MUST match the phase's `id` so the parent's reorder logic can locate
 * it; we never derive it from react-hook-form's internal _rhfId.
 */

import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ChevronDown, GripVertical, Trash2 } from "lucide-react";
import type { UseFormReturn } from "react-hook-form";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

import { PhaseDetailForm } from "./phase-detail-form";
import type { PhasesUpdateValues, PhaseValues } from "./phase-schema";

interface PhaseCardProps {
  /** The phase id — also the dnd-kit sortable key. */
  id: string;
  index: number;
  form: UseFormReturn<PhasesUpdateValues>;
  /** All phases (used to render the dependency chip-picker). */
  allPhases: PhaseValues[];
  onRemove: () => void;
}

export function PhaseCard({
  id,
  index,
  form,
  allPhases,
  onRemove,
}: PhaseCardProps) {
  const [open, setOpen] = useState(false);
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const base = `fasi.${index}` as const;
  const phase = form.watch(base);
  const dipendeDa = phase?.dipende_da ?? [];

  // Eligible predecessors: every other phase, named for the dropdown.
  const candidates = allPhases.filter((p) => p.id !== phase?.id);

  const togglePredecessor = (predId: string) => {
    const next = dipendeDa.includes(predId)
      ? dipendeDa.filter((d) => d !== predId)
      : [...dipendeDa, predId];
    form.setValue(`${base}.dipende_da` as const, next, { shouldDirty: true });
  };

  return (
    <Card
      ref={setNodeRef}
      style={style}
      className={cn("border-muted", isDragging && "ring-2 ring-primary/40")}
    >
      <CardHeader className="flex flex-row items-center gap-2 py-3">
        <button
          type="button"
          className="touch-none cursor-grab rounded-md p-1 text-muted-foreground hover:bg-muted active:cursor-grabbing"
          aria-label="Trascina per riordinare"
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <span className="text-xs tabular-nums text-muted-foreground">
          #{index + 1}
        </span>
        <Input
          {...form.register(`${base}.nome` as const)}
          placeholder="Nome fase (es. Scavo, Getto calcestruzzo…)"
          className="flex-1 border-0 bg-transparent shadow-none focus-visible:ring-0"
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label="Espandi dettaglio fase"
        >
          <ChevronDown
            className={cn("h-4 w-4 transition-transform", open && "rotate-180")}
          />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={onRemove}
          aria-label="Rimuovi fase"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-4">
          <div>
            <Label className="text-xs">Descrizione</Label>
            <Textarea
              {...form.register(`${base}.descrizione` as const)}
              rows={2}
              placeholder="Dettaglio della lavorazione svolta in questa fase…"
            />
          </div>

          {/* --- Dipende da (chip picker) ---------------------------- */}
          <div>
            <Label className="text-xs">
              Dipende da (predecessori) — clicca per aggiungere/rimuovere
            </Label>
            {candidates.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                Nessun'altra fase ancora definita.
              </p>
            ) : (
              <div className="flex flex-wrap gap-2 pt-2">
                {candidates.map((c) => {
                  const active = dipendeDa.includes(c.id);
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => togglePredecessor(c.id)}
                      aria-pressed={active}
                      className="focus:outline-none"
                    >
                      <Badge
                        variant={active ? "default" : "outline"}
                        className={cn(
                          "cursor-pointer text-xs",
                          active &&
                            "bg-primary/15 text-primary-foreground ring-1 ring-primary/40",
                        )}
                      >
                        {c.nome || `(senza nome) #${c.ordine + 1}`}
                      </Badge>
                    </button>
                  );
                })}
              </div>
            )}
            {dipendeDa.length > 0 && (
              <p className="pt-1 text-[10px] text-muted-foreground">
                {dipendeDa.length} predecessor
                {dipendeDa.length === 1 ? "e" : "i"} selezionat
                {dipendeDa.length === 1 ? "o" : "i"}.
              </p>
            )}
          </div>

          <PhaseDetailForm form={form} phaseIndex={index} />
        </CardContent>
      )}
    </Card>
  );
}
