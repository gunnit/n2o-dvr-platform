"use client";

/**
 * Per-phase detail form (US-4.7 AC1) — risks/DPI/mezzi/NIOSH/rumore/vibrazioni.
 *
 * Lives inside an expanded <PhaseCard>. Risks/DPI/mezzi are simple
 * comma-separated string editors (the backend dedupes/strips on save so
 * there's no need for per-row schema). NIOSH/rumore/vibrazioni are
 * opt-in: each tab shows an "Aggiungi" button until the operator decides
 * to attach a snapshot.
 */

import { useMemo } from "react";
import {
  Controller,
  type UseFormReturn,
} from "react-hook-form";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

import {
  DEFAULT_NIOSH,
  DEFAULT_RUMORE,
  DEFAULT_VIBRAZIONI,
  FASCIA_RUMORE_VALUES,
  ZONA_NIOSH_VALUES,
  type PhasesUpdateValues,
} from "./phase-schema";

interface Props {
  form: UseFormReturn<PhasesUpdateValues>;
  phaseIndex: number;
}

function CsvField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
      <Input
        value={value.join(", ")}
        placeholder={placeholder}
        onChange={(e) =>
          onChange(
            e.target.value
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
          )
        }
      />
      <p className="text-[10px] text-muted-foreground">Separa con virgole.</p>
    </div>
  );
}

export function PhaseDetailForm({ form, phaseIndex }: Props) {
  const base = `fasi.${phaseIndex}` as const;
  const { control, watch, setValue, register } = form;

  // Watching the sub-objects rather than the whole phase so the tab
  // labels can show a quick "✓" indicator when a snapshot is attached.
  const niosh = watch(`${base}.niosh`);
  const rumore = watch(`${base}.rumore`);
  const vibr = watch(`${base}.vibrazioni`);
  const rischi = watch(`${base}.rischi`) ?? [];
  const dpi = watch(`${base}.dpi`) ?? [];
  const mezzi = watch(`${base}.mezzi`) ?? [];

  // Memo so we don't re-derive the array on every render.
  const summary = useMemo(
    () => ({
      rischi: rischi.length,
      dpi: dpi.length,
      mezzi: mezzi.length,
    }),
    [rischi, dpi, mezzi],
  );

  return (
    <div className="space-y-4">
      {/* Feedback #58 (2026-05-26): Rischi + DPI sempre visibili sopra
          le schede. Prima erano nascosti dentro due tab separati e
          l'operatore doveva alternare per inserirli. Ora affiancati
          (rischi + DPI sulla stessa riga, mezzi sotto). */}
      <div className="rounded-md border bg-muted/30 p-3">
        <div className="grid gap-3 md:grid-cols-2">
          <Controller
            control={control}
            name={`${base}.rischi` as const}
            render={({ field }) => (
              <CsvField
                label={`Rischi della fase (${summary.rischi})`}
                value={field.value ?? []}
                onChange={field.onChange}
                placeholder="Caduta dall'alto, Schiacciamento, Rumore"
              />
            )}
          />
          <Controller
            control={control}
            name={`${base}.dpi` as const}
            render={({ field }) => (
              <CsvField
                label={`DPI obbligatori (${summary.dpi})`}
                value={field.value ?? []}
                onChange={field.onChange}
                placeholder="Casco, Scarpe, Imbragatura"
              />
            )}
          />
        </div>
        <div className="mt-3">
          <Controller
            control={control}
            name={`${base}.mezzi` as const}
            render={({ field }) => (
              <CsvField
                label={`Mezzi e attrezzature (${summary.mezzi})`}
                value={field.value ?? []}
                onChange={field.onChange}
                placeholder="Escavatore, Autobetoniera"
              />
            )}
          />
        </div>
      </div>

    <Tabs defaultValue="niosh" className="w-full">
      <TabsList>
        <TabsTrigger value="niosh">NIOSH {niosh ? "✓" : ""}</TabsTrigger>
        <TabsTrigger value="rumore">Rumore {rumore ? "✓" : ""}</TabsTrigger>
        <TabsTrigger value="vibrazioni">
          Vibrazioni {vibr ? "✓" : ""}
        </TabsTrigger>
      </TabsList>

      {/* --- NIOSH --------------------------------------------------- */}
      <TabsContent value="niosh" className="space-y-3 pt-3">
        {niosh ? (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <Label className="text-xs">Peso sollevato (kg)</Label>
                <Input
                  type="number"
                  step="0.1"
                  {...register(`${base}.niosh.peso_sollevato` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
              <div>
                <Label className="text-xs">CP</Label>
                <Input
                  type="number"
                  step="0.1"
                  {...register(`${base}.niosh.cp` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
              <div>
                <Label className="text-xs">Fattore A</Label>
                <Input
                  type="number"
                  step="0.01"
                  {...register(`${base}.niosh.fattore_a` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
              <div>
                <Label className="text-xs">Fattore B</Label>
                <Input
                  type="number"
                  step="0.01"
                  {...register(`${base}.niosh.fattore_b` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
              <div>
                <Label className="text-xs">Fattore C</Label>
                <Input
                  type="number"
                  step="0.01"
                  {...register(`${base}.niosh.fattore_c` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
              <div>
                <Label className="text-xs">Fattore D</Label>
                <Input
                  type="number"
                  step="0.01"
                  {...register(`${base}.niosh.fattore_d` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
              <div>
                <Label className="text-xs">Fattore E</Label>
                <Input
                  type="number"
                  step="0.01"
                  {...register(`${base}.niosh.fattore_e` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
              <div>
                <Label className="text-xs">Fattore F</Label>
                <Input
                  type="number"
                  step="0.01"
                  {...register(`${base}.niosh.fattore_f` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">PLR (kg)</Label>
                <Input
                  type="number"
                  step="0.01"
                  {...register(`${base}.niosh.plr` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
              <div>
                <Label className="text-xs">IR</Label>
                <Input
                  type="number"
                  step="0.01"
                  {...register(`${base}.niosh.ir` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
              <div>
                <Label className="text-xs">Zona</Label>
                <Controller
                  control={control}
                  name={`${base}.niosh.livello` as const}
                  render={({ field }) => (
                    <select
                      value={field.value ?? ""}
                      onChange={(e) =>
                        field.onChange(e.target.value || null)
                      }
                      className="flex h-10 w-full rounded-md border bg-background px-3 text-sm"
                    >
                      <option value="">—</option>
                      {ZONA_NIOSH_VALUES.map((z) => (
                        <option key={z} value={z}>
                          {z}
                        </option>
                      ))}
                    </select>
                  )}
                />
              </div>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setValue(`${base}.niosh` as const, null, { shouldDirty: true })}
            >
              <Trash2 className="mr-1 h-3 w-3" /> Rimuovi NIOSH
            </Button>
          </>
        ) : (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              setValue(`${base}.niosh` as const, { ...DEFAULT_NIOSH }, { shouldDirty: true })
            }
          >
            <Plus className="mr-1 h-3 w-3" /> Aggiungi snapshot NIOSH
          </Button>
        )}
      </TabsContent>

      {/* --- Rumore -------------------------------------------------- */}
      <TabsContent value="rumore" className="space-y-3 pt-3">
        {rumore ? (
          <>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">LEX,8h (dB(A))</Label>
                <Input
                  type="number"
                  step="0.1"
                  {...register(`${base}.rumore.lex_8h_dba` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
              <div>
                <Label className="text-xs">Fascia</Label>
                <Controller
                  control={control}
                  name={`${base}.rumore.fascia` as const}
                  render={({ field }) => (
                    <select
                      value={field.value ?? ""}
                      onChange={(e) =>
                        field.onChange(e.target.value || null)
                      }
                      className="flex h-10 w-full rounded-md border bg-background px-3 text-sm"
                    >
                      <option value="">—</option>
                      {FASCIA_RUMORE_VALUES.map((f) => (
                        <option key={f} value={f}>
                          {f}
                        </option>
                      ))}
                    </select>
                  )}
                />
              </div>
              <div className="flex items-end gap-2">
                <input
                  type="checkbox"
                  className="h-4 w-4"
                  {...register(`${base}.rumore.dpi_obbligatori` as const)}
                />
                <Label className="text-xs">DPI uditivi obbligatori</Label>
              </div>
            </div>
            <div>
              <Label className="text-xs">Note</Label>
              <Textarea
                rows={2}
                {...register(`${base}.rumore.note` as const)}
              />
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setValue(`${base}.rumore` as const, null, { shouldDirty: true })}
            >
              <Trash2 className="mr-1 h-3 w-3" /> Rimuovi Rumore
            </Button>
          </>
        ) : (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              setValue(`${base}.rumore` as const, { ...DEFAULT_RUMORE }, { shouldDirty: true })
            }
          >
            <Plus className="mr-1 h-3 w-3" /> Aggiungi esposizione al rumore
          </Button>
        )}
      </TabsContent>

      {/* --- Vibrazioni ---------------------------------------------- */}
      <TabsContent value="vibrazioni" className="space-y-3 pt-3">
        {vibr ? (
          <>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">A(8) mano-braccio (m/s²)</Label>
                <Input
                  type="number"
                  step="0.01"
                  {...register(`${base}.vibrazioni.a8_mano_braccio` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
              <div>
                <Label className="text-xs">A(8) corpo intero (m/s²)</Label>
                <Input
                  type="number"
                  step="0.01"
                  {...register(`${base}.vibrazioni.a8_corpo_intero` as const, {
                    valueAsNumber: true,
                  })}
                />
              </div>
              <div className="flex items-end gap-2">
                <input
                  type="checkbox"
                  className="h-4 w-4"
                  {...register(`${base}.vibrazioni.entro_limiti` as const)}
                />
                <Label className="text-xs">Entro i limiti di legge</Label>
              </div>
            </div>
            <div>
              <Label className="text-xs">Note</Label>
              <Textarea
                rows={2}
                {...register(`${base}.vibrazioni.note` as const)}
              />
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setValue(`${base}.vibrazioni` as const, null, { shouldDirty: true })}
            >
              <Trash2 className="mr-1 h-3 w-3" /> Rimuovi Vibrazioni
            </Button>
          </>
        ) : (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              setValue(`${base}.vibrazioni` as const, { ...DEFAULT_VIBRAZIONI }, { shouldDirty: true })
            }
          >
            <Plus className="mr-1 h-3 w-3" /> Aggiungi esposizione a vibrazioni
          </Button>
        )}
      </TabsContent>
    </Tabs>
    </div>
  );
}
