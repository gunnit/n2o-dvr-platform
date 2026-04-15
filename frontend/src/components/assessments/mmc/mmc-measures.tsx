"use client";

import { useEffect, useRef, useState } from "react";
import { type UseFormReturn } from "react-hook-form";
import { AlertTriangle, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { MmcFormValues } from "./mmc-form";

const DEFAULT_MEASURES: string[] = [
  "Introdurre ausili meccanici per la movimentazione (carrelli, transpallet, sollevatori).",
  "Riorganizzare la postazione di lavoro riducendo la distanza orizzontale e l'angolo di asimmetria.",
  "Frazionare i carichi in unita piu leggere (<15 kg per donne, <25 kg per uomini adulti).",
  "Alternare il personale per ridurre la frequenza di sollevamento per singolo lavoratore.",
  "Prevedere formazione specifica sulla movimentazione manuale dei carichi ai sensi dell'art. 169 D.Lgs. 81/2008.",
];

export function MmcMeasures({
  form,
  visible,
}: {
  form: UseFormReturn<MmcFormValues>;
  visible: boolean;
}) {
  // Snapshot any pre-existing measures from the form ONCE on mount.
  const initialRef = useRef<string[] | null>(null);
  if (initialRef.current === null) {
    const stored = form.getValues("measures") ?? [];
    initialRef.current = stored.length > 0 ? stored : DEFAULT_MEASURES;
  }
  const [items, setItems] = useState<string[]>(initialRef.current);

  // Sync back to the form when the user edits the list.
  useEffect(() => {
    form.setValue("measures", items, {
      shouldDirty: true,
      shouldValidate: false,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items]);

  if (!visible) return null;

  const update = (i: number, v: string) => {
    setItems((prev) => {
      const next = [...prev];
      next[i] = v;
      return next;
    });
  };

  const remove = (i: number) => {
    setItems((prev) => prev.filter((_, j) => j !== i));
  };

  const add = () => setItems((prev) => [...prev, ""]);

  return (
    <Card className="border-rose-400/40 bg-rose-50/40 dark:bg-rose-950/20">
      <CardHeader className="flex flex-row items-center gap-2 border-b">
        <AlertTriangle className="h-5 w-5 text-rose-600" />
        <CardTitle className="text-sm">
          Misure obbligatorie — zona ROSSA (IR &gt; 1.00)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pt-4">
        <p className="text-xs text-muted-foreground">
          Misure di prevenzione primaria richieste ai sensi dell&apos;art. 168
          D.Lgs. 81/2008 quando l&apos;indice di sollevamento supera 1.00.
          Rivedere ciascuna misura e adattarla alla realta aziendale.
        </p>
        {items.map((m, i) => (
          <div key={i} className="flex gap-2">
            <textarea
              value={m}
              onChange={(e) => update(i, e.target.value)}
              rows={2}
              className="flex-1 min-h-16 rounded-md border bg-background px-3 py-2 text-sm"
              placeholder={`Misura ${i + 1}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => remove(i)}
              aria-label={`Rimuovi misura ${i + 1}`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
        <Button type="button" variant="outline" onClick={add}>
          <Plus className="mr-2 h-4 w-4" /> Aggiungi misura
        </Button>
      </CardContent>
    </Card>
  );
}
