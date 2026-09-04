"use client";

import { useFormContext } from "react-hook-form";
import { Copy, Trash2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { Ambiente } from "@/types";

import {
  BAND_CLASS,
  type AreaResult,
  type FireScore,
  type IncendioFormValues,
} from "./incendio-form";
import { IncendioMeasures } from "./incendio-measures";
import { incendioAreaNameIsReadOnly } from "./incendio-roundtrip";
import { Select } from "@/components/ui/select";
import { SchedaAmbienteFields } from "@/components/ambienti/scheda-ambiente-fields";

// ---------------------------------------------------------------------------
// Parameter copy — Italian labels from REFERENCE_DATA.md section 4.1.
// ---------------------------------------------------------------------------

interface ParamOption {
  value: FireScore;
  label: string;
  hint: string;
}

interface ParamDef {
  key: "inf" | "si" | "pi";
  code: string;
  title: string;
  description: string;
  options: [ParamOption, ParamOption, ParamOption];
}

const PARAMS: ParamDef[] = [
  {
    key: "inf",
    code: "INF",
    title: "Infiammabilità delle sostanze",
    description:
      "Caratteristiche di infiammabilità delle sostanze presenti nell'area.",
    options: [
      { value: 1, label: "A basso tasso", hint: "Sostanze a basso tasso di infiammabilità o assenti." },
      { value: 2, label: "Infiammabili", hint: "Presenza di sostanze infiammabili in quantità limitate." },
      { value: 3, label: "Altamente infiammabili", hint: "Sostanze altamente infiammabili, esplosive o fiamme libere." },
    ],
  },
  {
    key: "si",
    code: "SI",
    title: "Sorgenti di innesco",
    description: "Possibilità di sviluppo di un incendio per presenza di sorgenti di innesco.",
    options: [
      { value: 1, label: "Bassa", hint: "Sorgenti di innesco assenti o ben controllate." },
      { value: 2, label: "Limitata", hint: "Sorgenti presenti ma limitate a specifiche lavorazioni." },
      { value: 3, label: "Notevole", hint: "Sorgenti di innesco diffuse: fiamme libere, lavorazioni a caldo, impianti elettrici critici." },
    ],
  },
  {
    key: "pi",
    code: "PI",
    title: "Propagazione dell'incendio",
    description: "Probabilità che un incendio possa propagarsi all'interno dell'area.",
    options: [
      { value: 1, label: "Basso", hint: "Compartimentazione efficace, scarsa presenza di materiali combustibili." },
      { value: 2, label: "Medio", hint: "Presenza di materiali combustibili con compartimentazioni o misure di contenimento." },
      { value: 3, label: "Elevato", hint: "Notevole quantità di materiali combustibili, assenza di compartimentazione." },
    ],
  },
];

// ---------------------------------------------------------------------------
// ScoreButton — replaces the shadcn slider (not installed) with a 3-button
// segmented control that still validates as 1/2/3.
// ---------------------------------------------------------------------------

function ScoreButton({
  label,
  value,
  active,
  onClick,
}: {
  label: string;
  value: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex-1 rounded-md px-3 py-2 text-sm font-medium ring-1 transition-colors",
        active
          ? "bg-primary/10 text-primary ring-primary/40"
          : "bg-background text-muted-foreground ring-border hover:bg-muted",
      )}
    >
      <span className="mr-1 text-[11px] uppercase tracking-wide opacity-70">
        {value}
      </span>
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------

export interface IncendioAreaCardProps {
  index: number;
  totalAreas: number;
  result: AreaResult | undefined;
  ambienti?: Ambiente[];
  onDuplicate: () => void;
  onRemove: () => void;
}

export function IncendioAreaCard({
  index,
  totalAreas,
  result,
  ambienti = [],
  onDuplicate,
  onRemove,
}: IncendioAreaCardProps) {
  const {
    register,
    setValue,
    watch,
    formState: { errors },
  } = useFormContext<IncendioFormValues>();

  const current = watch(`areas.${index}`);
  const areaErrors = errors.areas?.[index];
  const linkedNameIsReadOnly = incendioAreaNameIsReadOnly(
    current?.ambiente_id ?? null,
    ambienti.map((ambiente) => ambiente.id),
  );

  return (
    <Card>
      <CardHeader className="border-b">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary" className="text-[10px]">
                Area {index + 1}
              </Badge>
              <CardTitle className="text-sm">Dettagli area</CardTitle>
              {result?.livello && (
                <span
                  className={cn(
                    "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium ring-1",
                    BAND_CLASS[result.livello],
                  )}
                >
                  {result.livello} · {result.totale}/9
                </span>
              )}
            </div>
            <div className="mt-2 max-w-md space-y-2">
              {ambienti.length > 0 && (
                <div>
                  <label
                    htmlFor={`areas.${index}.ambiente_select`}
                    className="text-[11px] uppercase tracking-wide text-muted-foreground"
                  >
                    Locale / Ambiente
                  </label>
                  <Select
                    id={`areas.${index}.ambiente_select`}
                    value={current?.ambiente_id ?? "__altro__"}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val === "__altro__") {
                        setValue(`areas.${index}.ambiente_id`, null, {
                          shouldValidate: true,
                          shouldDirty: true,
                        });
                        return;
                      }
                      const ambiente = ambienti.find((amb) => amb.id === val);
                      if (ambiente) {
                        setValue(`areas.${index}.ambiente_id`, ambiente.id, {
                          shouldValidate: true,
                          shouldDirty: true,
                        });
                        setValue(`areas.${index}.nome`, ambiente.nome, {
                          shouldValidate: true,
                          shouldDirty: true,
                        });
                      }
                    }}
                  >
                    {ambienti.map((amb) => (
                      <option key={amb.id} value={amb.id}>
                        {amb.nome}
                        {amb.tipo ? ` (${amb.tipo})` : ""}
                      </option>
                    ))}
                    <option value="__altro__">Altro (inserisci manualmente)</option>
                  </Select>
                </div>
              )}
              <div>
                <label
                  htmlFor={`areas.${index}.nome`}
                  className="text-[11px] uppercase tracking-wide text-muted-foreground"
                >
                  Nome / identificativo area
                </label>
                <Input
                  id={`areas.${index}.nome`}
                  placeholder="Es. Magazzino materie prime"
                  maxLength={255}
                  readOnly={linkedNameIsReadOnly}
                  title={
                    linkedNameIsReadOnly
                      ? "Per usare un nome manuale, seleziona Altro come ambiente."
                      : undefined
                  }
                  aria-invalid={areaErrors?.nome ? true : undefined}
                  {...register(`areas.${index}.nome`, {
                    onChange: () => {
                      // If the linked Ambiente is no longer available, a
                      // manual rename turns this into an unlinked area rather
                      // than persisting contradictory identifiers and names.
                      if (current?.ambiente_id) {
                        setValue(`areas.${index}.ambiente_id`, null, {
                          shouldValidate: true,
                          shouldDirty: true,
                        });
                      }
                    },
                  })}
                />
                {areaErrors?.nome && (
                  <p className="mt-1 text-[11px] text-destructive">
                    {areaErrors.nome.message}
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onDuplicate}
              title="Duplica area (copia i valori INF/SI/PI in una nuova area)"
            >
              <Copy className="mr-1 h-4 w-4" />
              Duplica area
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onRemove}
              disabled={totalAreas <= 1}
              title={
                totalAreas <= 1
                  ? "Deve esserci almeno un'area"
                  : "Rimuovi questa area"
              }
            >
              <Trash2 className="mr-1 h-4 w-4" />
              Rimuovi
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        {PARAMS.map((p) => {
          const val = current?.[p.key] as FireScore | undefined;
          const selectedOption = p.options.find((o) => o.value === val);
          const err = areaErrors?.[p.key];
          return (
            <div
              key={p.key}
              className="space-y-2 rounded-md border bg-muted/10 p-3"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px]">
                      {p.code}
                    </Badge>
                    <h4 className="text-sm font-medium">{p.title}</h4>
                  </div>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    {p.description}
                  </p>
                </div>
                {selectedOption && (
                  <Badge variant="secondary" className="text-[11px]">
                    {selectedOption.label}
                  </Badge>
                )}
              </div>

              <div
                className="flex flex-wrap gap-2"
                role="radiogroup"
                aria-label={p.title}
              >
                {p.options.map((opt) => (
                  <ScoreButton
                    key={opt.value}
                    label={opt.label}
                    value={opt.value}
                    active={val === opt.value}
                    onClick={() =>
                      setValue(`areas.${index}.${p.key}`, opt.value, {
                        shouldValidate: true,
                        shouldDirty: true,
                      })
                    }
                  />
                ))}
              </div>

              {selectedOption && (
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  {selectedOption.hint}
                </p>
              )}

              {err && (
                <p className="text-[11px] text-destructive" role="alert">
                  {err.message as string}
                </p>
              )}
            </div>
          );
        })}

        <div className="space-y-3 rounded-md border bg-muted/10 p-3">
          <div>
            <h4 className="text-sm font-medium">Dotazioni antincendio presenti</h4>
            <p className="mt-0.5 text-[11px] text-muted-foreground">
              Indica le quantità presenti nell&apos;area valutata.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {(
              [
                ["estintori_presenti", "Estintori"],
                ["idranti_presenti", "Idranti"],
                ["uscite_emergenza", "Uscite di emergenza"],
              ] as const
            ).map(([field, label]) => (
              <div key={field}>
                <label
                  htmlFor={`areas.${index}.${field}`}
                  className="text-[11px] uppercase tracking-wide text-muted-foreground"
                >
                  {label}
                </label>
                <Input
                  id={`areas.${index}.${field}`}
                  type="number"
                  min={0}
                  step={1}
                  aria-invalid={areaErrors?.[field] ? true : undefined}
                  {...register(`areas.${index}.${field}`, {
                    valueAsNumber: true,
                  })}
                />
                {areaErrors?.[field] && (
                  <p className="mt-1 text-[11px] text-destructive">
                    {areaErrors[field]?.message}
                  </p>
                )}
              </div>
            ))}
          </div>
          <div>
            <label
              htmlFor={`areas.${index}.note`}
              className="text-[11px] uppercase tracking-wide text-muted-foreground"
            >
              Note
            </label>
            <Textarea
              id={`areas.${index}.note`}
              placeholder="Annotazioni specifiche sull'area, verifiche o criticità…"
              {...register(`areas.${index}.note`)}
            />
          </div>
        </div>

        {/* Segnalazione 2026-08-25: the scheda ambiente (descrizione,
            materiali, persone max, sorgenti di innesco) lives on the
            linked Ambiente so the PEE reads the same facts. Only offered
            when the area is linked — a manual "Altro" area has no row to
            hold them. */}
        {(() => {
          const linked = current?.ambiente_id
            ? ambienti.find((amb) => amb.id === current.ambiente_id)
            : undefined;
          return linked ? <SchedaAmbienteFields ambiente={linked} /> : null;
        })()}

        {result?.complete && result.livello && (
          <IncendioMeasures
            areaIndex={index}
            livello={result.livello}
            value={current?.misure_prevenzione ?? null}
            onChange={(value) =>
              setValue(`areas.${index}.misure_prevenzione`, value, {
                shouldValidate: true,
                shouldDirty: true,
              })
            }
          />
        )}
      </CardContent>
    </Card>
  );
}
