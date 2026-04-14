"use client";

import { useCallback } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Plus, Trash2 } from "lucide-react";
import type { Ambiente } from "@/types";

interface StepAmbientiProps {
  aziendaId: string;
  ambienti: Ambiente[];
  onChange: (ambienti: Ambiente[]) => void;
}

const TIPI_AMBIENTE = [
  "Ufficio",
  "Magazzino",
  "Cucina",
  "Laboratorio",
  "Officina",
  "Sala Corsi",
  "Esterno",
  "Bagno/Spogliatoio",
];

function createEmptyAmbiente(aziendaId: string): Ambiente {
  return {
    id: crypto.randomUUID(),
    azienda_id: aziendaId,
    nome: "",
    tipo: "",
    superficie_mq: null,
    preposto_id: null,
    descrizione_attivita: null,
  };
}

export function StepAmbienti({
  aziendaId,
  ambienti,
  onChange,
}: StepAmbientiProps) {
  const addAmbiente = useCallback(() => {
    onChange([...ambienti, createEmptyAmbiente(aziendaId)]);
  }, [ambienti, onChange, aziendaId]);

  const removeAmbiente = useCallback(
    (index: number) => {
      onChange(ambienti.filter((_, i) => i !== index));
    },
    [ambienti, onChange]
  );

  const updateAmbiente = useCallback(
    (index: number, fields: Partial<Ambiente>) => {
      const updated = ambienti.map((a, i) =>
        i === index ? { ...a, ...fields } : a
      );
      onChange(updated);
    },
    [ambienti, onChange]
  );

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Ambienti di Lavoro</CardTitle>
          <CardDescription>
            Definisci gli ambienti di lavoro dell&apos;azienda
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {ambienti.length === 0 && (
            <p className="py-8 text-center text-muted-foreground">
              Nessun ambiente aggiunto. Clicca &quot;Aggiungi Ambiente&quot; per
              iniziare.
            </p>
          )}

          {ambienti.map((ambiente, index) => (
            <div key={ambiente.id}>
              {index > 0 && <Separator className="mb-6" />}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium">
                    Ambiente {index + 1}
                    {ambiente.nome ? ` - ${ambiente.nome}` : ""}
                  </h3>
                  <Button
                    variant="destructive"
                    size="icon-sm"
                    onClick={() => removeAmbiente(index)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  {/* Nome */}
                  <div className="space-y-2">
                    <Label htmlFor={`amb-nome-${index}`}>
                      Nome Ambiente *
                    </Label>
                    <Input
                      id={`amb-nome-${index}`}
                      value={ambiente.nome}
                      onChange={(e) =>
                        updateAmbiente(index, {
                          nome: e.target.value,
                        })
                      }
                      placeholder="Es. Ufficio Piano Terra"
                    />
                  </div>

                  {/* Tipo */}
                  <div className="space-y-2">
                    <Label htmlFor={`amb-tipo-${index}`}>
                      Tipo
                    </Label>
                    <select
                      id={`amb-tipo-${index}`}
                      value={ambiente.tipo}
                      onChange={(e) =>
                        updateAmbiente(index, {
                          tipo: e.target.value,
                        })
                      }
                      className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                    >
                      <option value="">Seleziona tipo</option>
                      {TIPI_AMBIENTE.map((tipo) => (
                        <option key={tipo} value={tipo}>
                          {tipo}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Superficie */}
                  <div className="space-y-2">
                    <Label htmlFor={`amb-superficie-${index}`}>
                      Superficie (mq)
                    </Label>
                    <Input
                      id={`amb-superficie-${index}`}
                      type="number"
                      value={ambiente.superficie_mq ?? ""}
                      onChange={(e) =>
                        updateAmbiente(index, {
                          superficie_mq: e.target.value
                            ? Number(e.target.value)
                            : null,
                        })
                      }
                      placeholder="Es. 50"
                    />
                  </div>
                </div>

                {/* Descrizione Attivita */}
                <div className="space-y-2">
                  <Label htmlFor={`amb-desc-${index}`}>
                    Descrizione Attivita
                  </Label>
                  <textarea
                    id={`amb-desc-${index}`}
                    value={ambiente.descrizione_attivita ?? ""}
                    onChange={(e) =>
                      updateAmbiente(index, {
                        descrizione_attivita:
                          e.target.value || null,
                      })
                    }
                    rows={2}
                    placeholder="Descrivi le attivita svolte in questo ambiente..."
                    className="w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  />
                </div>
              </div>
            </div>
          ))}

          <Button
            variant="outline"
            onClick={addAmbiente}
            className="w-full"
          >
            <Plus className="mr-2 h-4 w-4" />
            Aggiungi Ambiente
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
