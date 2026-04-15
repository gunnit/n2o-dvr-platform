"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

import type { FireLivello } from "./incendio-form";

// ---------------------------------------------------------------------------
// Measures checklist. Fetches the canonical list for the band from the
// `/api/v1/calculate/fire-measures` endpoint (backed by
// `app/data/fire_measures.py`). Selection state lives locally — the page is
// responsible for harvesting it at submit time.
// ---------------------------------------------------------------------------

export interface IncendioMeasuresProps {
  /**
   * Current risk band for this area. The component re-fetches whenever the
   * band changes so the operator sees band-appropriate measures only.
   */
  livello: FireLivello;
  /**
   * Stable area identifier (index or array-field id) — used to scope the
   * local storage key so each area keeps its own selection.
   */
  areaIndex: number;
}

const apiUrl =
  (typeof process !== "undefined" &&
    (process.env.NEXT_PUBLIC_API_URL as string | undefined)) ||
  "http://localhost:8000";

export function IncendioMeasures({ livello, areaIndex }: IncendioMeasuresProps) {
  const [measures, setMeasures] = useState<string[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [custom, setCustom] = useState("");
  const [customMeasures, setCustomMeasures] = useState<string[]>([]);
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
          // Pre-select everything by default — operators can uncheck items
          // that do not apply. Mirrors the existing AZIONE_PER_LIVELLO copy.
          setSelected(new Set(data.misure));
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

  const toggle = (m: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(m)) next.delete(m);
      else next.add(m);
      return next;
    });
  };

  const addCustom = () => {
    const trimmed = custom.trim();
    if (!trimmed) return;
    setCustomMeasures((prev) => [...prev, trimmed]);
    setSelected((prev) => new Set(prev).add(trimmed));
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
