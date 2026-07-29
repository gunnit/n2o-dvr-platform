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
 * Dropdown listing every female worker (Persona.sesso == 'F') for the
 * current azienda. Selecting one triggers the cross-reference call on
 * the parent page.
 */
export function WorkerSelector({ workers, selectedId, onSelect, loading }: Props) {
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
          {workers.map((w) => (
            <option key={w.id} value={w.id}>
              {w.nominativo}
              {w.mansione ? ` — ${w.mansione}` : ""}
            </option>
          ))}
        </Select>
        <span className="text-xs text-muted-foreground md:whitespace-nowrap">
          {workers.length} lavoratric{workers.length === 1 ? "e" : "i"}
        </span>
      </CardContent>
    </Card>
  );
}
