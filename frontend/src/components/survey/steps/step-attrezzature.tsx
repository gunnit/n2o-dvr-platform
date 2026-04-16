"use client";

import { useCallback, useState, useMemo } from "react";
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
import { Plus, Trash2, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Ambiente, Attrezzatura } from "@/types";

interface StepAttrezzatureProps {
  aziendaId: string;
  ambienti: Ambiente[];
  attrezzature: Attrezzatura[];
  onChange: (attrezzature: Attrezzatura[]) => void;
}

const EQUIPMENT_BY_TYPE: Record<string, string[]> = {
  Ufficio: [
    "Scrivania",
    "Sedia ergonomica",
    "Monitor/Schermo",
    "Tastiera",
    "Mouse",
    "Stampante",
    "Scaffalatura ufficio",
    "Climatizzatore",
  ],
  Magazzino: [
    "Scaffalatura industriale",
    "Transpallet manuale",
    "Transpallet elettrico",
    "Muletto/Carrello elevatore",
    "Scala portatile",
    "Nastro trasportatore",
  ],
  Produzione: [
    "Tornio",
    "Fresa",
    "Pressa",
    "Saldatrice",
    "Compressore",
    "Trapano a colonna",
    "Nastro trasportatore",
    "Carroponte",
  ],
  Cucina: [
    "Forno industriale",
    "Piano cottura",
    "Frigorifero industriale",
    "Abbattitore",
    "Affettatrice",
    "Lavastoviglie industriale",
    "Cappa aspirante",
  ],
  Laboratorio: [
    "Cappa chimica",
    "Centrifuga",
    "Microscopio",
    "Autoclave",
    "Bilancia di precisione",
    "Agitatore magnetico",
  ],
  Esterno: [
    "Escavatore",
    "Gru",
    "Betoniera",
    "Ponteggio",
    "Trabattello",
    "Martello demolitore",
  ],
  Negozio: [
    "Registratore di cassa",
    "Scaffalatura espositiva",
    "Scala portatile",
    "Frigorifero espositore",
  ],
};

function createEmptyAttrezzatura(aziendaId: string): Attrezzatura {
  return {
    id: crypto.randomUUID(),
    azienda_id: aziendaId,
    descrizione: "",
    marcatura_ce: false,
    verifiche_periodiche: false,
  };
}

export function StepAttrezzature({
  aziendaId,
  ambienti,
  attrezzature,
  onChange,
}: StepAttrezzatureProps) {
  const [selectedAmbienteIndex, setSelectedAmbienteIndex] = useState(0);

  const selectedAmbiente = ambienti[selectedAmbienteIndex];

  // Get suggested equipment list for the currently selected environment type
  const suggestedEquipment = useMemo(() => {
    if (!selectedAmbiente) return [];
    return EQUIPMENT_BY_TYPE[selectedAmbiente.tipo] ?? [];
  }, [selectedAmbiente]);

  // Set of currently selected equipment descriptions (for quick lookup)
  const selectedDescriptions = useMemo(
    () => new Set(attrezzature.map((a) => a.descrizione)),
    [attrezzature]
  );

  // Toggle a suggested equipment item on/off
  const toggleSuggested = useCallback(
    (descrizione: string) => {
      if (selectedDescriptions.has(descrizione)) {
        // Remove it
        onChange(attrezzature.filter((a) => a.descrizione !== descrizione));
      } else {
        // Add it with defaults
        onChange([
          ...attrezzature,
          {
            id: crypto.randomUUID(),
            azienda_id: aziendaId,
            descrizione,
            marcatura_ce: false,
            verifiche_periodiche: false,
          },
        ]);
      }
    },
    [attrezzature, onChange, aziendaId, selectedDescriptions]
  );

  // Custom equipment = items whose descrizione is NOT in ANY suggested list
  const allSuggestedNames = useMemo(() => {
    const names = new Set<string>();
    for (const items of Object.values(EQUIPMENT_BY_TYPE)) {
      for (const item of items) {
        names.add(item);
      }
    }
    return names;
  }, []);

  const customAttrezzature = useMemo(
    () => attrezzature.filter((a) => !allSuggestedNames.has(a.descrizione)),
    [attrezzature, allSuggestedNames]
  );

  const addCustomAttrezzatura = useCallback(() => {
    onChange([...attrezzature, createEmptyAttrezzatura(aziendaId)]);
  }, [attrezzature, onChange, aziendaId]);

  const removeAttrezzatura = useCallback(
    (id: string) => {
      onChange(attrezzature.filter((a) => a.id !== id));
    },
    [attrezzature, onChange]
  );

  const updateAttrezzatura = useCallback(
    (id: string, fields: Partial<Attrezzatura>) => {
      const updated = attrezzature.map((a) =>
        a.id === id ? { ...a, ...fields } : a
      );
      onChange(updated);
    },
    [attrezzature, onChange]
  );

  if (ambienti.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-on-surface-variant">
          Aggiungi almeno un ambiente di lavoro nel passo 3 prima di
          procedere con le attrezzature.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="mb-6">
          <h3 className="font-heading text-xl font-bold text-on-surface">
            Attrezzature
          </h3>
          <p className="mt-1 text-sm text-on-surface-variant">
            Seleziona un ambiente per visualizzare le attrezzature suggerite in
            base alla tipologia. Le attrezzature selezionate sono condivise tra
            tutti gli ambienti.
          </p>
        </div>
        <div>
          <div className="space-y-3">
            <Label>Seleziona Ambiente</Label>
            <div className="flex flex-wrap gap-2">
              {ambienti.map((amb, idx) => (
                <button
                  key={amb.id}
                  type="button"
                  onClick={() => setSelectedAmbienteIndex(idx)}
                  className={cn(
                    "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
                    idx === selectedAmbienteIndex
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-input bg-background text-foreground hover:bg-muted"
                  )}
                >
                  {amb.nome || `Ambiente ${idx + 1}`}
                  {amb.tipo ? ` (${amb.tipo})` : ""}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Suggested equipment */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Attrezzature suggerite
            {selectedAmbiente?.tipo
              ? ` - ${selectedAmbiente.tipo}`
              : ""}
          </CardTitle>
          <CardDescription>
            {suggestedEquipment.length > 0
              ? "Clicca per aggiungere o rimuovere un'attrezzatura dall'elenco"
              : "Nessun suggerimento disponibile per questo tipo di ambiente. Usa la sezione sottostante per aggiungere attrezzature manualmente."}
          </CardDescription>
        </CardHeader>
        {suggestedEquipment.length > 0 && (
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {suggestedEquipment.map((item) => {
                const isSelected = selectedDescriptions.has(item);
                return (
                  <button
                    key={item}
                    type="button"
                    onClick={() => toggleSuggested(item)}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                      isSelected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input bg-background text-foreground hover:bg-muted"
                    )}
                  >
                    {isSelected && <Check className="h-3.5 w-3.5" />}
                    {item}
                  </button>
                );
              })}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Selected equipment details */}
      {attrezzature.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Attrezzature selezionate ({attrezzature.length})
            </CardTitle>
            <CardDescription>
              Imposta marcatura CE e verifiche periodiche per ogni attrezzatura
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {attrezzature.map((att) => (
              <div
                key={att.id}
                className="flex flex-wrap items-center gap-3 rounded-lg border border-input p-3"
              >
                <span className="min-w-[160px] flex-1 text-sm font-medium">
                  {att.descrizione || "Senza nome"}
                </span>

                <label className="flex items-center gap-2 rounded-lg border border-input px-3 py-1.5 text-sm transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                  <input
                    type="checkbox"
                    checked={att.marcatura_ce}
                    onChange={(e) =>
                      updateAttrezzatura(att.id, {
                        marcatura_ce: e.target.checked,
                      })
                    }
                    className="accent-primary"
                  />
                  Marcatura CE
                </label>

                <label className="flex items-center gap-2 rounded-lg border border-input px-3 py-1.5 text-sm transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                  <input
                    type="checkbox"
                    checked={att.verifiche_periodiche}
                    onChange={(e) =>
                      updateAttrezzatura(att.id, {
                        verifiche_periodiche: e.target.checked,
                      })
                    }
                    className="accent-primary"
                  />
                  Verifiche Periodiche
                </label>

                <Button
                  variant="destructive"
                  size="icon-sm"
                  onClick={() => removeAttrezzatura(att.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Custom equipment */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Attrezzature personalizzate
          </CardTitle>
          <CardDescription>
            Aggiungi attrezzature non presenti nei suggerimenti
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {customAttrezzature.length > 0 && (
            <>
              {customAttrezzature.map((att, index) => (
                <div key={att.id}>
                  {index > 0 && <Separator className="mb-4" />}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium">
                        Personalizzata
                        {att.descrizione ? ` - ${att.descrizione}` : ""}
                      </h3>
                      <Button
                        variant="destructive"
                        size="icon-sm"
                        onClick={() => removeAttrezzatura(att.id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor={`att-desc-${att.id}`}>
                        Descrizione *
                      </Label>
                      <Input
                        id={`att-desc-${att.id}`}
                        value={att.descrizione}
                        onChange={(e) =>
                          updateAttrezzatura(att.id, {
                            descrizione: e.target.value,
                          })
                        }
                        placeholder="Es. Carrello elevatore, Trapano a colonna"
                      />
                    </div>

                    <div className="flex flex-wrap gap-4">
                      <label className="flex items-center gap-2 rounded-lg border border-input px-4 py-2 text-sm transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                        <input
                          type="checkbox"
                          checked={att.marcatura_ce}
                          onChange={(e) =>
                            updateAttrezzatura(att.id, {
                              marcatura_ce: e.target.checked,
                            })
                          }
                          className="accent-primary"
                        />
                        Marcatura CE
                      </label>

                      <label className="flex items-center gap-2 rounded-lg border border-input px-4 py-2 text-sm transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                        <input
                          type="checkbox"
                          checked={att.verifiche_periodiche}
                          onChange={(e) =>
                            updateAttrezzatura(att.id, {
                              verifiche_periodiche: e.target.checked,
                            })
                          }
                          className="accent-primary"
                        />
                        Verifiche Periodiche
                      </label>
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}

          <Button
            variant="outline"
            onClick={addCustomAttrezzatura}
            className="w-full"
          >
            <Plus className="mr-2 h-4 w-4" />
            Aggiungi Attrezzatura
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
