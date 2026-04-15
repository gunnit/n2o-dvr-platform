"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import type { FemaleWorker } from "./types";

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
        <select
          id="worker-select"
          disabled={loading || workers.length === 0}
          value={selectedId ?? ""}
          onChange={(e) => onSelect(e.target.value)}
          className="h-9 flex-1 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs disabled:cursor-not-allowed disabled:opacity-50"
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
        </select>
        <span className="text-xs text-muted-foreground md:whitespace-nowrap">
          {workers.length} lavoratric{workers.length === 1 ? "e" : "i"}
        </span>
      </CardContent>
    </Card>
  );
}
