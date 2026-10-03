"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import type { FemaleWorker } from "./types";
import { Select } from "@/components/ui/select";

interface Props {
  workers: FemaleWorker[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
}

/**
 * Dropdown listing the azienda's female workers (Sesso "F", or a female
 * codice fiscale when Sesso is empty), followed by persone whose sex was
 * never recorded. Selecting one triggers the cross-reference call on the
 * parent page.
 */
export function WorkerSelector({ workers, selectedId, onSelect, loading }: Props) {
  const women = workers.filter((w) => !w.sessoNonIndicato);
  const unknown = workers.filter((w) => w.sessoNonIndicato);
  const label = (w: FemaleWorker) =>
    `${w.nominativo}${w.mansione ? ` — ${w.mansione}` : ""}`;
  return (
    <Card>
      <CardContent className="flex flex-col gap-2 py-4 md:flex-row md:items-center md:gap-4">
        <Label htmlFor="worker-select" className="text-sm md:whitespace-nowrap">
          Lavoratrice da valutare
        </Label>
        <Select
          id="worker-select"
          disabled={loading || workers.length === 0}
          value={selectedId ?? ""}
          onChange={(e) => onSelect(e.target.value)} size="sm" className="flex-1"
        >
          <option value="" disabled>
            {loading
              ? "Caricamento lavoratrici…"
              : workers.length === 0
                ? "Nessuna lavoratrice censita per questa azienda"
                : "— seleziona —"}
          </option>
          {women.map((w) => (
            <option key={w.id} value={w.id}>
              {label(w)}
            </option>
          ))}
          {unknown.length > 0 && (
            <optgroup label="Sesso non indicato nel censimento">
              {unknown.map((w) => (
                <option key={w.id} value={w.id}>
                  {label(w)}
                </option>
              ))}
            </optgroup>
          )}
        </Select>
        <span className="text-xs text-muted-foreground md:whitespace-nowrap">
          {women.length} lavoratric{women.length === 1 ? "e" : "i"}
          {unknown.length > 0 && ` · ${unknown.length} senza sesso`}
        </span>
      </CardContent>
    </Card>
  );
}
