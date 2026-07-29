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
import { Select } from "@/components/ui/select";

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
  return <p className="text-[11px] text-[#b01e2e]">{message}</p>;
}

interface PesoFieldProps {
  index: number;
  control: Control<MmcFormValues>;
  register: UseFormRegister<MmcFormValues>;
  hasError: boolean;
  errorMessage?: string;
}

// Lifted out so we can subscribe to the live peso value (useWatch) and show a
// "did you really mean this?" warning. The cap is 200kg to catch typos like
// 1010 while still allowing legitimate heavy lifts (drums, motors). The legal
// reference points (15kg women / 25kg adult men under D.Lgs. 81/2008) inform
// the warning thresholds — these are *advisory*, the IR badge does the real
// risk classification.
function PesoField({ index, control, register, hasError, errorMessage }: PesoFieldProps) {
  const peso = useWatch({ control, name: `lifts.${index}.peso_reale` });
  const numericPeso = typeof peso === "number" && isFinite(peso) ? peso : 0;
  const warning =
    numericPeso > 100
      ? "Peso molto elevato: verifica di non aver digitato uno zero in più."
      : numericPeso > 50
      ? "Peso elevato: doppio controllo del valore inserito."
      : numericPeso > 25
      ? "Sopra il limite di legge per uomini adulti (25 kg)."
      : null;

  return (
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
        max={200}
        className={cn(hasError && "border-[#c72a3a]")}
        {...register(`lifts.${index}.peso_reale` as const, { valueAsNumber: true })}
      />
      <FieldError message={errorMessage} />
      {!errorMessage && warning && (
        <p className="text-[11px] text-[#8a5c23]" role="alert">
          ⚠ {warning}
        </p>
      )}
    </div>
  );
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
      ? "bg-[rgba(21,190,83,0.16)] text-[#0c6b2f] ring-[rgba(21,190,83,0.34)]"
      : result?.zona === "GIALLA"
      ? "bg-[rgba(245,158,11,0.18)] text-[#8a5c23] ring-[rgba(245,158,11,0.36)]"
      : result?.zona === "ROSSA"
      ? "bg-[rgba(239,68,68,0.16)] text-[#b01e2e] ring-[rgba(239,68,68,0.34)]"
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

        <PesoField
          index={index}
          control={control}
          register={register}
          hasError={!!liftErrors?.peso_reale}
          errorMessage={liftErrors?.peso_reale?.message}
        />


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
            className={cn(liftErrors?.altezza && "border-[#c72a3a]")}
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
            className={cn(liftErrors?.dislocazione && "border-[#c72a3a]")}
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
            className={cn(liftErrors?.distanza && "border-[#c72a3a]")}
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
            className={cn(liftErrors?.angolo && "border-[#c72a3a]")}
            {...register(`lifts.${index}.angolo` as const, { valueAsNumber: true })}
          />
          <FieldError message={liftErrors?.angolo?.message} />
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor={`lift-${index}-presa`} className="text-xs">
            Qualità della presa
          </Label>
          <Select
            id={`lift-${index}-presa`}
            size="sm"
            className={cn(liftErrors?.presa && "border-[#c72a3a]")}
            {...register(`lifts.${index}.presa` as const)}
          >
            <option value="buona">Buona</option>
            <option value="discreta">Discreta</option>
            <option value="scarsa">Scarsa</option>
          </Select>
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
            className={cn(liftErrors?.frequenza && "border-[#c72a3a]")}
            {...register(`lifts.${index}.frequenza` as const, { valueAsNumber: true })}
          />
          <FieldError message={liftErrors?.frequenza?.message} />
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor={`lift-${index}-durata`} className="text-xs">
            Durata del compito
          </Label>
          <Select
            id={`lift-${index}-durata`}
            size="sm"
            className={cn(liftErrors?.durata && "border-[#c72a3a]")}
            {...register(`lifts.${index}.durata` as const)}
          >
            <option value="breve">Breve (&lt;1h)</option>
            <option value="media">Media (1-2h)</option>
            <option value="lunga">Lunga (&gt;2h)</option>
          </Select>
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
