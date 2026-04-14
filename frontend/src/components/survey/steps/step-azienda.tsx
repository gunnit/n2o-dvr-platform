"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Azienda } from "@/types";

interface StepAziendaProps {
  aziendaId: string;
  data: Partial<Azienda>;
  onChange: (fields: Partial<Azienda>) => void;
}

interface ValidationErrors {
  ragione_sociale?: string;
  partita_iva?: string;
  codice_ateco?: string;
}

const ZONE_SISMICHE = [
  { value: 1, label: "Zona 1 - Alta pericolosita" },
  { value: 2, label: "Zona 2 - Media pericolosita" },
  { value: 3, label: "Zona 3 - Bassa pericolosita" },
  { value: 4, label: "Zona 4 - Molto bassa pericolosita" },
];

const PARTITA_IVA_REGEX = /^\d{11}$/;
const CODICE_ATECO_REGEX = /^\d{2}\.\d{2}\.\d{2}$/;

export function StepAzienda({ data, onChange }: StepAziendaProps) {
  const [errors, setErrors] = useState<ValidationErrors>({});

  function validateRagioneSociale(value: string | undefined) {
    if (!value || value.trim() === "") {
      setErrors((prev) => ({ ...prev, ragione_sociale: "Campo obbligatorio" }));
    } else {
      setErrors((prev) => {
        const { ragione_sociale: _, ...rest } = prev;
        return rest;
      });
    }
  }

  function validatePartitaIva(value: string | undefined | null) {
    if (value && value.trim() !== "" && !PARTITA_IVA_REGEX.test(value.trim())) {
      setErrors((prev) => ({
        ...prev,
        partita_iva: "La partita IVA deve essere di 11 cifre",
      }));
    } else {
      setErrors((prev) => {
        const { partita_iva: _, ...rest } = prev;
        return rest;
      });
    }
  }

  function validateCodiceAteco(value: string | undefined | null) {
    if (value && value.trim() !== "" && !CODICE_ATECO_REGEX.test(value.trim())) {
      setErrors((prev) => ({
        ...prev,
        codice_ateco: "Formato non valido (es. 56.10.11)",
      }));
    } else {
      setErrors((prev) => {
        const { codice_ateco: _, ...rest } = prev;
        return rest;
      });
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Dati Azienda</CardTitle>
          <CardDescription>
            Inserisci i dati identificativi dell&apos;azienda
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Ragione Sociale */}
          <div className="space-y-2">
            <Label htmlFor="ragione_sociale">Ragione Sociale *</Label>
            <Input
              id="ragione_sociale"
              value={data.ragione_sociale ?? ""}
              onChange={(e) =>
                onChange({ ragione_sociale: e.target.value })
              }
              onBlur={(e) => validateRagioneSociale(e.target.value)}
              placeholder="Es. Mario Rossi S.r.l."
              className={errors.ragione_sociale ? "border-destructive" : ""}
            />
            {errors.ragione_sociale && (
              <p className="text-xs text-destructive">{errors.ragione_sociale}</p>
            )}
          </div>

          {/* Partita IVA */}
          <div className="space-y-2">
            <Label htmlFor="partita_iva">Partita IVA</Label>
            <Input
              id="partita_iva"
              value={data.partita_iva ?? ""}
              onChange={(e) =>
                onChange({ partita_iva: e.target.value || null })
              }
              onBlur={(e) => validatePartitaIva(e.target.value)}
              placeholder="Es. 12345678901"
              className={errors.partita_iva ? "border-destructive" : ""}
            />
            {errors.partita_iva && (
              <p className="text-xs text-destructive">{errors.partita_iva}</p>
            )}
          </div>

          {/* Attivita */}
          <div className="space-y-2">
            <Label htmlFor="attivita">Attivita</Label>
            <Input
              id="attivita"
              value={data.attivita ?? ""}
              onChange={(e) => onChange({ attivita: e.target.value })}
              placeholder="Es. Produzione alimentare"
            />
          </div>

          {/* Codice ATECO */}
          <div className="space-y-2">
            <Label htmlFor="codice_ateco">Codice ATECO</Label>
            <Input
              id="codice_ateco"
              value={data.codice_ateco ?? ""}
              onChange={(e) =>
                onChange({ codice_ateco: e.target.value })
              }
              onBlur={(e) => validateCodiceAteco(e.target.value)}
              placeholder="Es. 56.10.11"
              className={errors.codice_ateco ? "border-destructive" : ""}
            />
            {errors.codice_ateco && (
              <p className="text-xs text-destructive">{errors.codice_ateco}</p>
            )}
          </div>

          {/* Sede Legale */}
          <div>
            <h3 className="mb-3 text-sm font-medium text-foreground">
              Sede Legale
            </h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="sede_legale_via">Via / Indirizzo</Label>
                <Input
                  id="sede_legale_via"
                  value={data.sede_legale_via ?? ""}
                  onChange={(e) =>
                    onChange({ sede_legale_via: e.target.value })
                  }
                  placeholder="Es. Via Roma, 1"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sede_legale_citta">Citta</Label>
                <Input
                  id="sede_legale_citta"
                  value={data.sede_legale_citta ?? ""}
                  onChange={(e) =>
                    onChange({ sede_legale_citta: e.target.value })
                  }
                  placeholder="Es. Roma"
                />
              </div>
            </div>
          </div>

          {/* Sede Operativa */}
          <div>
            <h3 className="mb-3 text-sm font-medium text-foreground">
              Sede Operativa
            </h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="sede_operativa_via">Via / Indirizzo</Label>
                <Input
                  id="sede_operativa_via"
                  value={data.sede_operativa_via ?? ""}
                  onChange={(e) =>
                    onChange({ sede_operativa_via: e.target.value })
                  }
                  placeholder="Es. Via Milano, 5"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sede_operativa_citta">Citta</Label>
                <Input
                  id="sede_operativa_citta"
                  value={data.sede_operativa_citta ?? ""}
                  onChange={(e) =>
                    onChange({ sede_operativa_citta: e.target.value })
                  }
                  placeholder="Es. Milano"
                />
              </div>
            </div>
          </div>

          {/* Orario Lavoro, Metratura, Zona Sismica */}
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="orario_lavoro">Orario di Lavoro</Label>
              <Input
                id="orario_lavoro"
                value={data.orario_lavoro ?? ""}
                onChange={(e) =>
                  onChange({ orario_lavoro: e.target.value })
                }
                placeholder="Es. 08:00 - 17:00"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="metratura_totale">Metratura Totale (mq)</Label>
              <Input
                id="metratura_totale"
                type="number"
                value={data.metratura_totale ?? ""}
                onChange={(e) =>
                  onChange({
                    metratura_totale: e.target.value
                      ? Number(e.target.value)
                      : null,
                  })
                }
                placeholder="Es. 500"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="zona_sismica">Zona Sismica</Label>
              <select
                id="zona_sismica"
                value={data.zona_sismica ?? ""}
                onChange={(e) =>
                  onChange({
                    zona_sismica: e.target.value
                      ? Number(e.target.value)
                      : null,
                  })
                }
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <option value="">Seleziona zona</option>
                {ZONE_SISMICHE.map((z) => (
                  <option key={z.value} value={z.value}>
                    {z.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
