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
import { Plus, Trash2, X } from "lucide-react";
import type { SostanzaChimica } from "@/types";

interface StepSostanzeProps {
  aziendaId: string;
  sostanze: SostanzaChimica[];
  onChange: (sostanze: SostanzaChimica[]) => void;
}

const PITTOGRAMMI_GHS = [
  { code: "GHS01", label: "Esplosivo" },
  { code: "GHS02", label: "Infiammabile" },
  { code: "GHS03", label: "Comburente" },
  { code: "GHS04", label: "Gas compresso" },
  { code: "GHS05", label: "Corrosivo" },
  { code: "GHS06", label: "Tossicita acuta" },
  { code: "GHS07", label: "Irritante" },
  { code: "GHS08", label: "Pericolo per la salute" },
  { code: "GHS09", label: "Pericolo per l'ambiente" },
];

const STATI_MISCELA = [
  "Solido",
  "Liquido",
  "Gassoso",
  "Polvere",
  "Aerosol",
  "Pasta",
];

function createEmptySostanza(aziendaId: string): SostanzaChimica {
  return {
    id: crypto.randomUUID(),
    azienda_id: aziendaId,
    nome_prodotto: "",
    produttore: null,
    pittogrammi: [],
    stato_miscela: null,
    frasi_h: [],
    frasi_p: [],
  };
}

function TagInput({
  label,
  value,
  onChange,
  placeholder,
  id,
}: {
  label: string;
  value: string[];
  onChange: (val: string[]) => void;
  placeholder: string;
  id: string;
}) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const input = e.currentTarget;
      const val = input.value.trim().toUpperCase();
      if (val && !value.includes(val)) {
        onChange([...value, val]);
        input.value = "";
      }
    }
  };

  const removeTag = (tag: string) => {
    onChange(value.filter((v) => v !== tag));
  };

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex flex-wrap gap-1.5 rounded-lg border border-input p-2">
        {value.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs font-medium"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          id={id}
          type="text"
          onKeyDown={handleKeyDown}
          placeholder={value.length === 0 ? placeholder : ""}
          className="min-w-[120px] flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />
      </div>
      <p className="text-xs text-muted-foreground">
        Premi Invio o virgola per aggiungere
      </p>
    </div>
  );
}

export function StepSostanze({
  aziendaId,
  sostanze,
  onChange,
}: StepSostanzeProps) {
  const addSostanza = useCallback(() => {
    onChange([...sostanze, createEmptySostanza(aziendaId)]);
  }, [sostanze, onChange, aziendaId]);

  const removeSostanza = useCallback(
    (index: number) => {
      onChange(sostanze.filter((_, i) => i !== index));
    },
    [sostanze, onChange]
  );

  const updateSostanza = useCallback(
    (index: number, fields: Partial<SostanzaChimica>) => {
      const updated = sostanze.map((s, i) =>
        i === index ? { ...s, ...fields } : s
      );
      onChange(updated);
    },
    [sostanze, onChange]
  );

  const togglePittogramma = useCallback(
    (index: number, code: string) => {
      const sostanza = sostanze[index];
      const pitt = sostanza.pittogrammi.includes(code)
        ? sostanza.pittogrammi.filter((p) => p !== code)
        : [...sostanza.pittogrammi, code];
      updateSostanza(index, { pittogrammi: pitt });
    },
    [sostanze, updateSostanza]
  );

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Sostanze Chimiche</CardTitle>
          <CardDescription>
            Elenco delle sostanze chimiche pericolose utilizzate in azienda
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {sostanze.length === 0 && (
            <p className="py-8 text-center text-muted-foreground">
              Nessuna sostanza chimica aggiunta. Clicca &quot;Aggiungi
              Sostanza&quot; per iniziare.
            </p>
          )}

          {sostanze.map((sost, index) => (
            <div key={sost.id}>
              {index > 0 && <Separator className="mb-6" />}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium">
                    Sostanza {index + 1}
                    {sost.nome_prodotto
                      ? ` - ${sost.nome_prodotto}`
                      : ""}
                  </h3>
                  <Button
                    variant="destructive"
                    size="icon-sm"
                    onClick={() => removeSostanza(index)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  {/* Nome Prodotto */}
                  <div className="space-y-2">
                    <Label htmlFor={`sost-nome-${index}`}>
                      Nome Prodotto *
                    </Label>
                    <Input
                      id={`sost-nome-${index}`}
                      value={sost.nome_prodotto}
                      onChange={(e) =>
                        updateSostanza(index, {
                          nome_prodotto: e.target.value,
                        })
                      }
                      placeholder="Es. Detergente industriale"
                    />
                  </div>

                  {/* Produttore */}
                  <div className="space-y-2">
                    <Label htmlFor={`sost-prod-${index}`}>
                      Produttore
                    </Label>
                    <Input
                      id={`sost-prod-${index}`}
                      value={sost.produttore ?? ""}
                      onChange={(e) =>
                        updateSostanza(index, {
                          produttore: e.target.value || null,
                        })
                      }
                      placeholder="Es. ChemCo S.r.l."
                    />
                  </div>

                  {/* Stato Miscela */}
                  <div className="space-y-2">
                    <Label htmlFor={`sost-stato-${index}`}>
                      Stato / Miscela
                    </Label>
                    <select
                      id={`sost-stato-${index}`}
                      value={sost.stato_miscela ?? ""}
                      onChange={(e) =>
                        updateSostanza(index, {
                          stato_miscela:
                            e.target.value || null,
                        })
                      }
                      className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                    >
                      <option value="">Seleziona stato</option>
                      {STATI_MISCELA.map((stato) => (
                        <option key={stato} value={stato}>
                          {stato}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Pittogrammi */}
                <div className="space-y-2">
                  <Label>Pittogrammi GHS</Label>
                  <div className="flex flex-wrap gap-2">
                    {PITTOGRAMMI_GHS.map((p) => (
                      <button
                        key={p.code}
                        type="button"
                        onClick={() =>
                          togglePittogramma(index, p.code)
                        }
                        className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                          sost.pittogrammi.includes(p.code)
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-input text-muted-foreground hover:bg-muted"
                        }`}
                      >
                        {p.code} - {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Frasi H */}
                <TagInput
                  id={`sost-h-${index}`}
                  label="Frasi H (Pericolo)"
                  value={sost.frasi_h}
                  onChange={(frasi_h) =>
                    updateSostanza(index, { frasi_h })
                  }
                  placeholder="Es. H302, H315"
                />

                {/* Frasi P */}
                <TagInput
                  id={`sost-p-${index}`}
                  label="Frasi P (Precauzione)"
                  value={sost.frasi_p}
                  onChange={(frasi_p) =>
                    updateSostanza(index, { frasi_p })
                  }
                  placeholder="Es. P264, P280"
                />
              </div>
            </div>
          ))}

          <Button
            variant="outline"
            onClick={addSostanza}
            className="w-full"
          >
            <Plus className="mr-2 h-4 w-4" />
            Aggiungi Sostanza
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
