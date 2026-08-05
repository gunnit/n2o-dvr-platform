"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

import type { FireLivello } from "./incendio-form";

// ---------------------------------------------------------------------------
// Measures checklist. Fetches the canonical list for the band from the
// `/api/v1/calculate/fire-measures` endpoint (backed by
// `app/data/fire_measures.py`). The displayed default remains local until the
// operator edits it; edits are mirrored into the owning form so persisted
// choices survive load/edit/save.
// ---------------------------------------------------------------------------

export interface IncendioMeasuresProps {
  /**
   * Current risk band for this area. The component re-fetches whenever the
   * band changes so the operator sees band-appropriate measures only.
   */
  livello: FireLivello;
  /**
   * Stable area identifier (index or array-field id) — keeps each async
   * recommendation fetch scoped to the area that requested it.
   */
  areaIndex: number;
  /** Newline-delimited persisted selection for this area. */
  value: string | null;
  /** Writes the newline-delimited selection back to the owning form. */
  onChange: (value: string) => void;
}

const apiUrl =
  (typeof process !== "undefined" &&
    (process.env.NEXT_PUBLIC_API_URL as string | undefined)) ||
  "http://localhost:8000";

function measureLines(value: string | null): string[] {
  return (value ?? "")
    .split("\n")
    .map((measure) => measure.trim())
    .filter(Boolean);
}

export function IncendioMeasures({
  livello,
  areaIndex,
  value,
  onChange,
}: IncendioMeasuresProps) {
  const [measures, setMeasures] = useState<string[]>([]);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [custom, setCustom] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `${apiUrl}/api/v1/calculate/fire-measures?livello=${encodeURIComponent(livello)}`,
        );
        if (!res.ok) throw new Error(`Errore ${res.status}`);
        const data = (await res.json()) as { misure: string[] };
        if (!cancelled) {
          setMeasures(data.misure);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Impossibile caricare le misure consigliate",
          );
          setMeasures([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
    // Reset custom list when the band changes; re-add happens per-area.
  }, [livello, areaIndex]);

  const persistedSelection = useMemo(() => measureLines(value), [value]);
  const selected = useMemo(
    () =>
      new Set(
        value === null && !hasInteracted ? measures : persistedSelection,
      ),
    [hasInteracted, measures, persistedSelection, value],
  );

  const customMeasures = useMemo(
    () => persistedSelection.filter((measure) => !measures.includes(measure)),
    [measures, persistedSelection],
  );

  const toggle = (m: string) => {
    const next = new Set(selected);
    if (next.has(m)) next.delete(m);
    else next.add(m);
    setHasInteracted(true);
    onChange(Array.from(next).join("\n"));
  };

  const addCustom = () => {
    const trimmed = custom.trim();
    if (!trimmed) return;
    const next = new Set(selected).add(trimmed);
    setHasInteracted(true);
    onChange(Array.from(next).join("\n"));
    setCustom("");
  };

  const allItems = [...measures, ...customMeasures];

  return (
    <div className="rounded-md border bg-background p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs font-medium">
          Misure consigliate — livello {livello}
        </div>
        <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
          {selected.size} / {allItems.length} selezionate
        </div>
      </div>

      {loading && (
        <p className="mt-2 text-[11px] text-muted-foreground">
          Caricamento misure…
        </p>
      )}
      {error && (
        <p className="mt-2 text-[11px] text-destructive" role="alert">
          {error}
        </p>
      )}

      <ul className="mt-2 space-y-1.5">
        {allItems.map((m) => {
          const isSelected = selected.has(m);
          return (
            <li key={m} className="flex items-start gap-2 text-[12px]">
              <button
                type="button"
                onClick={() => toggle(m)}
                aria-pressed={isSelected}
                className={cn(
                  "mt-0.5 inline-flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-sm border transition-colors",
                  isSelected
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-input bg-background hover:bg-muted",
                )}
              >
                {isSelected && (
                  <svg
                    viewBox="0 0 16 16"
                    className="h-3 w-3"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    aria-hidden="true"
                  >
                    <path d="M3 8l3 3 7-7" />
                  </svg>
                )}
              </button>
              <span
                className={cn(
                  "leading-relaxed",
                  !isSelected && "text-muted-foreground line-through",
                )}
              >
                {m}
              </span>
            </li>
          );
        })}
      </ul>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Input
          value={custom}
          onChange={(e) => setCustom(e.target.value)}
          placeholder="Aggiungi misura personalizzata…"
          className="max-w-md flex-1"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addCustom();
            }
          }}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addCustom}
          disabled={!custom.trim()}
        >
          <Plus className="mr-1 h-4 w-4" />
          Aggiungi
        </Button>
      </div>
    </div>
  );
}
