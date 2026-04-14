"use client";

import { useCallback, useState } from "react";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Trash2 } from "lucide-react";
import type { Persona } from "@/types";

interface StepPersoneProps {
  aziendaId: string;
  persone: Persona[];
  onChange: (persone: Persona[]) => void;
}

const TIPOLOGIE_CONTRATTUALI = [
  "Indeterminato",
  "Determinato",
  "Apprendistato",
  "Somministrazione",
  "Collaborazione",
  "Stagionale",
  "Tirocinio",
];

const RUOLI = [
  { key: "ruolo_datore_lavoro" as const, label: "Datore di Lavoro (DdL)" },
  { key: "ruolo_rspp" as const, label: "RSPP" },
  { key: "ruolo_rls" as const, label: "RLS" },
  { key: "ruolo_primo_soccorso" as const, label: "Primo Soccorso" },
  { key: "ruolo_antincendio" as const, label: "Antincendio" },
  { key: "ruolo_preposto" as const, label: "Preposto" },
];

function createEmptyPersona(aziendaId: string): Persona {
  return {
    id: crypto.randomUUID(),
    azienda_id: aziendaId,
    nominativo: "",
    codice_fiscale: null,
    mansione: null,
    tipologia_contrattuale: null,
    sesso: null,
    fascia_eta: null,
    ruolo_rspp: false,
    ruolo_rls: false,
    ruolo_primo_soccorso: false,
    ruolo_antincendio: false,
    ruolo_preposto: false,
    ruolo_datore_lavoro: false,
  };
}

const CF_REGEX = /^[A-Z0-9]{16}$/;

export function StepPersone({ aziendaId, persone, onChange }: StepPersoneProps) {
  const [cfErrors, setCfErrors] = useState<Record<number, string>>({});
  const [deleteDialogIndex, setDeleteDialogIndex] = useState<number | null>(null);

  const validateCodiceFiscale = useCallback((value: string, index: number) => {
    if (value && !CF_REGEX.test(value)) {
      setCfErrors((prev) => ({
        ...prev,
        [index]: "Codice fiscale non valido (16 caratteri alfanumerici)",
      }));
    } else {
      setCfErrors((prev) => {
        const next = { ...prev };
        delete next[index];
        return next;
      });
    }
  }, []);

  const addPersona = useCallback(() => {
    onChange([...persone, createEmptyPersona(aziendaId)]);
  }, [persone, onChange, aziendaId]);

  const removePersona = useCallback(
    (index: number) => {
      onChange(persone.filter((_, i) => i !== index));
    },
    [persone, onChange]
  );

  const updatePersona = useCallback(
    (index: number, fields: Partial<Persona>) => {
      const updated = persone.map((p, i) =>
        i === index ? { ...p, ...fields } : p
      );
      onChange(updated);
    },
    [persone, onChange]
  );

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Persone</CardTitle>
          <CardDescription>
            Gestisci l&apos;elenco dei dipendenti e i relativi ruoli di
            sicurezza
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {persone.length === 0 && (
            <p className="py-8 text-center text-muted-foreground">
              Nessun dipendente aggiunto. Clicca &quot;Aggiungi Persona&quot; per
              iniziare.
            </p>
          )}

          {persone.map((persona, index) => (
            <div key={persona.id}>
              {index > 0 && <Separator className="mb-6" />}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium">
                    Persona {index + 1}
                    {persona.nominativo
                      ? ` - ${persona.nominativo}`
                      : ""}
                  </h3>
                  <Button
                    variant="destructive"
                    size="icon-sm"
                    onClick={() => setDeleteDialogIndex(index)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  {/* Nominativo */}
                  <div className="space-y-2">
                    <Label htmlFor={`nome-${index}`}>
                      Nominativo *
                    </Label>
                    <Input
                      id={`nome-${index}`}
                      value={persona.nominativo}
                      onChange={(e) =>
                        updatePersona(index, {
                          nominativo: e.target.value,
                        })
                      }
                      placeholder="Nome e Cognome"
                    />
                  </div>

                  {/* Codice Fiscale */}
                  <div className="space-y-2">
                    <Label htmlFor={`cf-${index}`}>
                      Codice Fiscale
                    </Label>
                    <Input
                      id={`cf-${index}`}
                      value={persona.codice_fiscale ?? ""}
                      onChange={(e) => {
                        const upper = e.target.value.toUpperCase();
                        updatePersona(index, {
                          codice_fiscale: upper || null,
                        });
                        if (cfErrors[index]) {
                          setCfErrors((prev) => {
                            const next = { ...prev };
                            delete next[index];
                            return next;
                          });
                        }
                      }}
                      onBlur={(e) =>
                        validateCodiceFiscale(e.target.value, index)
                      }
                      placeholder="Es. RSSMRA80A01H501U"
                      className={cfErrors[index] ? "border-destructive" : ""}
                    />
                    {cfErrors[index] && (
                      <p className="text-xs text-destructive">
                        {cfErrors[index]}
                      </p>
                    )}
                  </div>

                  {/* Mansione */}
                  <div className="space-y-2">
                    <Label htmlFor={`mansione-${index}`}>
                      Mansione
                    </Label>
                    <Input
                      id={`mansione-${index}`}
                      value={persona.mansione ?? ""}
                      onChange={(e) =>
                        updatePersona(index, {
                          mansione: e.target.value || null,
                        })
                      }
                      placeholder="Es. Operaio, Impiegato"
                    />
                  </div>

                  {/* Tipologia Contrattuale */}
                  <div className="space-y-2">
                    <Label htmlFor={`contratto-${index}`}>
                      Tipologia Contrattuale
                    </Label>
                    <select
                      id={`contratto-${index}`}
                      value={persona.tipologia_contrattuale ?? ""}
                      onChange={(e) =>
                        updatePersona(index, {
                          tipologia_contrattuale:
                            e.target.value || null,
                        })
                      }
                      className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                    >
                      <option value="">Seleziona tipo</option>
                      {TIPOLOGIE_CONTRATTUALI.map((tipo) => (
                        <option key={tipo} value={tipo}>
                          {tipo}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Sesso */}
                  <div className="space-y-2">
                    <Label htmlFor={`sesso-${index}`}>Sesso</Label>
                    <select
                      id={`sesso-${index}`}
                      value={persona.sesso ?? ""}
                      onChange={(e) =>
                        updatePersona(index, {
                          sesso:
                            (e.target.value as "M" | "F") || null,
                        })
                      }
                      className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                    >
                      <option value="">Seleziona</option>
                      <option value="M">Maschio</option>
                      <option value="F">Femmina</option>
                    </select>
                  </div>

                  {/* Fascia Eta */}
                  <div className="space-y-2">
                    <Label htmlFor={`eta-${index}`}>
                      Fascia Eta
                    </Label>
                    <select
                      id={`eta-${index}`}
                      value={persona.fascia_eta ?? ""}
                      onChange={(e) =>
                        updatePersona(index, {
                          fascia_eta:
                            (e.target.value as ">18" | "15-18") ||
                            null,
                        })
                      }
                      className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                    >
                      <option value="">Seleziona</option>
                      <option value=">18">Maggiorenne (&gt;18)</option>
                      <option value="15-18">Minorenne (15-18)</option>
                    </select>
                  </div>
                </div>

                {/* Ruoli di sicurezza */}
                <div className="space-y-2">
                  <Label>Ruoli di Sicurezza</Label>
                  <div className="flex flex-wrap gap-3">
                    {RUOLI.map((ruolo) => (
                      <label
                        key={ruolo.key}
                        className="flex items-center gap-2 rounded-lg border border-input px-3 py-1.5 text-sm transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                      >
                        <input
                          type="checkbox"
                          checked={persona[ruolo.key]}
                          onChange={(e) =>
                            updatePersona(index, {
                              [ruolo.key]: e.target.checked,
                            })
                          }
                          className="accent-primary"
                        />
                        {ruolo.label}
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}

          <Button variant="outline" onClick={addPersona} className="w-full">
            <Plus className="mr-2 h-4 w-4" />
            Aggiungi Persona
          </Button>
        </CardContent>
      </Card>

      {/* Delete confirmation dialog */}
      <Dialog
        open={deleteDialogIndex !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteDialogIndex(null);
        }}
      >
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>Elimina persona</DialogTitle>
            <DialogDescription>
              Sei sicuro di voler eliminare{" "}
              {deleteDialogIndex !== null && persone[deleteDialogIndex]?.nominativo
                ? persone[deleteDialogIndex].nominativo
                : "questa persona"}
              ? Questa azione non può essere annullata.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogIndex(null)}
            >
              Annulla
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (deleteDialogIndex !== null) {
                  removePersona(deleteDialogIndex);
                  setDeleteDialogIndex(null);
                }
              }}
            >
              Elimina
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
