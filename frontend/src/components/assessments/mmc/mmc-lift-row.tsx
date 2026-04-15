"use client";

import { type Control, type UseFormRegister, type FieldErrors, useWatch } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MmcFormValues, LiftResult } from "./mmc-form";

interface Props {
  index: number;
  control: Control<MmcFormValues>;
  register: UseFormRegister<MmcFormValues>;
  errors: FieldErrors<MmcFormValues>;
  result?: LiftResult;
  onRemove: () => void;
  canRemove: boolean;
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="text-[11px] text-rose-600 dark:text-rose-400">{message}</p>;
}

export function MmcLiftRow({
  index,
  control,
  register,
  errors,
  result,
  onRemove,
  canRemove,
}: Props) {
  const name = useWatch({ control, name: `lifts.${index}.name` });
  const liftErrors = errors?.lifts?.[index];

  const bandClass =
    result?.zona === "VERDE"
      ? "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30 dark:text-emerald-400"
      : result?.zona === "GIALLA"
      ? "bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-300"
      : result?.zona === "ROSSA"
      ? "bg-rose-500/15 text-rose-700 ring-rose-500/30 dark:text-rose-400"
      : "bg-muted text-muted-foreground";

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3 border-b">
        <div>
          <CardTitle className="text-sm">
            Sollevamento {index + 1}
            {name ? ` — ${name}` : ""}
          </CardTitle>
        </div>
        {canRemove && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onRemove}
            aria-label={`Rimuovi sollevamento ${index + 1}`}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-4 pt-4 md:grid-cols-2">
        <div className="grid gap-1.5 md:col-span-2">
          <Label htmlFor={`lift-${index}-name`} className="text-xs">
            Etichetta (opzionale)
          </Label>
          <Input
            id={`lift-${index}-name`}
            placeholder="es. Sollevamento cassetta su bancale"
            {...register(`lifts.${index}.name` as const)}
          />
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor={`lift-${index}-peso_reale`} className="text-xs">
            Peso sollevato (kg)
          </Label>
          <Input
            id={`lift-${index}-peso_reale`}
            type="number"
            inputMode="decimal"
            step="0.1"
            min={0}
            className={cn(liftErrors?.peso_reale && "border-rose-500")}
            {...register(`lifts.${index}.peso_reale` as const, { valueAsNumber: true })}
          />
          <FieldError message={liftErrors?.peso_reale?.message} />
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor={`lift-${index}-altezza`} className="text-xs">
            Altezza inizio presa (cm)
          </Label>
          <Input
            id={`lift-${index}-altezza`}
            type="number"
            inputMode="decimal"
            step="1"
            min={0}
            max={175}
            className={cn(liftErrors?.altezza && "border-rose-500")}
            {...register(`lifts.${index}.altezza` as const, { valueAsNumber: true })}
          />
          <FieldError message={liftErrors?.altezza?.message} />
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor={`lift-${index}-dislocazione`} className="text-xs">
            Dislocazione verticale (cm)
          </Label>
          <Input
            id={`lift-${index}-dislocazione`}
            type="number"
            inputMode="decimal"
            step="1"
            min={0}
            max={175}
            className={cn(liftErrors?.dislocazione && "border-rose-500")}
            {...register(`lifts.${index}.dislocazione` as const, { valueAsNumber: true })}
          />
          <FieldError message={liftErrors?.dislocazione?.message} />
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor={`lift-${index}-distanza`} className="text-xs">
            Distanza orizzontale caviglie-carico (cm)
          </Label>
          <Input
            id={`lift-${index}-distanza`}
            type="number"
            inputMode="decimal"
            step="1"
            min={25}
            max={63}
            className={cn(liftErrors?.distanza && "border-rose-500")}
            {...register(`lifts.${index}.distanza` as const, { valueAsNumber: true })}
          />
          <FieldError message={liftErrors?.distanza?.message} />
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor={`lift-${index}-angolo`} className="text-xs">
            Angolo di asimmetria (°)
          </Label>
          <Input
            id={`lift-${index}-angolo`}
            type="number"
            inputMode="decimal"
            step="5"
            min={0}
            max={135}
            className={cn(liftErrors?.angolo && "border-rose-500")}
            {...register(`lifts.${index}.angolo` as const, { valueAsNumber: true })}
          />
          <FieldError message={liftErrors?.angolo?.message} />
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor={`lift-${index}-presa`} className="text-xs">
            Qualità della presa
          </Label>
          <select
            id={`lift-${index}-presa`}
            className={cn(
              "h-9 rounded-md border bg-background px-2 text-sm",
              liftErrors?.presa && "border-rose-500",
            )}
            {...register(`lifts.${index}.presa` as const)}
          >
            <option value="buona">Buona</option>
            <option value="discreta">Discreta</option>
            <option value="scarsa">Scarsa</option>
          </select>
          <FieldError message={liftErrors?.presa?.message} />
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor={`lift-${index}-frequenza`} className="text-xs">
            Frequenza (atti/min)
          </Label>
          <Input
            id={`lift-${index}-frequenza`}
            type="number"
            inputMode="decimal"
            step="0.1"
            min={0.2}
            max={15}
            className={cn(liftErrors?.frequenza && "border-rose-500")}
            {...register(`lifts.${index}.frequenza` as const, { valueAsNumber: true })}
          />
          <FieldError message={liftErrors?.frequenza?.message} />
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor={`lift-${index}-durata`} className="text-xs">
            Durata del compito
          </Label>
          <select
            id={`lift-${index}-durata`}
            className={cn(
              "h-9 rounded-md border bg-background px-2 text-sm",
              liftErrors?.durata && "border-rose-500",
            )}
            {...register(`lifts.${index}.durata` as const)}
          >
            <option value="breve">Breve (&lt;1h)</option>
            <option value="media">Media (1-2h)</option>
            <option value="lunga">Lunga (&gt;2h)</option>
          </select>
          <FieldError message={liftErrors?.durata?.message} />
        </div>

        {result && (
          <div className="col-span-full mt-2 flex flex-wrap items-center gap-3 rounded-md border bg-muted/30 p-3">
            <span className="text-sm font-medium tabular-nums">
              PLR: {result.plr.toFixed(2)} kg
            </span>
            <span className="text-sm tabular-nums">
              IR: {isFinite(result.ir) ? result.ir.toFixed(2) : "∞"}
            </span>
            <Badge
              className={cn(
                "ring-1",
                bandClass,
              )}
            >
              {result.zona}
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
