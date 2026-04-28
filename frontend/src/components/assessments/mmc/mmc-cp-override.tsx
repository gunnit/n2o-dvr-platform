"use client";

import { useEffect, useState } from "react";
import { type UseFormReturn } from "react-hook-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { MmcFormValues } from "./mmc-form";

export function MmcCpOverride({
  form,
  onAutoCpChange,
}: {
  form: UseFormReturn<MmcFormValues>;
  onAutoCpChange?: (cp: number | null) => void;
}) {
  const sesso = form.watch("worker_sesso");
  const eta = form.watch("worker_eta");
  const override = form.watch("cp_override");
  const motivazione = form.watch("cp_motivazione");

  const [autoCp, setAutoCp] = useState<number | null>(null);
  const [fascia, setFascia] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);

  useEffect(() => {
    if (!sesso || !eta || Number.isNaN(eta) || eta < 15) {
      // Defer so we don't trigger cascading renders inside the effect body.
      const t = setTimeout(() => {
        setAutoCp(null);
        setFascia(null);
        onAutoCpChange?.(null);
      }, 0);
      return () => clearTimeout(t);
    }

    // Optimistic local lookup so the display is correct *immediately* for the
    // current (sesso, eta) pair — eliminates the "stale 20 kg until next
    // interaction" flash that QA flagged as H-04 (US-3.2) when rapidly editing
    // worker attributes. The server-side fetch below overwrites with the
    // canonical NIOSH reference value once it resolves.
    const localLookup = () => {
      const cp =
        sesso === "M"
          ? eta <= 17
            ? 20
            : eta <= 45
              ? 25
              : 20
          : eta <= 17
            ? 15
            : eta <= 45
              ? 20
              : 15;
      const fasciaLbl =
        eta <= 17 ? "giovane" : eta <= 45 ? "adulto" : "anziano";
      return { cp, fascia: fasciaLbl };
    };
    const local = localLookup();
    setAutoCp(local.cp);
    setFascia(local.fascia);
    onAutoCpChange?.(local.cp);

    const ctrl = new AbortController();
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(
      `${apiUrl}/api/v1/calculate/niosh-cp?sesso=${sesso}&eta=${eta}`,
      { signal: ctrl.signal },
    )
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d: { cp: number; fascia: string }) => {
        setAutoCp(d.cp);
        setFascia(d.fascia);
        setLookupError(null);
        onAutoCpChange?.(d.cp);
      })
      .catch((err) => {
        if (err?.name === "AbortError") return;
        // Fallback: optimistic local value is already applied above; just
        // surface the offline hint.
        setLookupError("Lookup offline — valore calcolato localmente");
      });
    return () => ctrl.abort();
  }, [sesso, eta, onAutoCpChange]);

  const effectiveCp = override ?? autoCp;
  const motivazioneError = form.formState.errors.cp_motivazione?.message;

  return (
    <Card>
      <CardHeader className="border-b">
        <CardTitle className="text-sm">Lavoratore e Costante di Peso (CP)</CardTitle>
        <CardDescription className="text-xs">
          CP deriva da sesso e fascia d&apos;eta secondo NIOSH ISO 11228-1.
          Puoi modificare il valore fornendo una motivazione.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="grid gap-1.5">
            <Label htmlFor="worker-sesso" className="text-xs">
              Sesso lavoratore
            </Label>
            <select
              id="worker-sesso"
              className="h-9 rounded-md border bg-background px-2 text-sm"
              {...form.register("worker_sesso")}
            >
              <option value="M">Maschio</option>
              <option value="F">Femmina</option>
            </select>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="worker-eta" className="text-xs">
              Eta (anni)
            </Label>
            <Input
              id="worker-eta"
              type="number"
              min={15}
              max={70}
              {...form.register("worker_eta", { valueAsNumber: true })}
            />
            {form.formState.errors.worker_eta?.message && (
              <p className="text-[11px] text-rose-600">
                {form.formState.errors.worker_eta.message}
              </p>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 rounded-md border bg-muted/30 p-3">
          <span className="text-sm">CP effettivo:</span>
          <span className="text-lg font-semibold tabular-nums">
            {effectiveCp ?? "—"} kg
          </span>
          {override === undefined ? (
            <Badge variant="secondary">Auto</Badge>
          ) : (
            <Badge className="bg-amber-500/20 text-amber-800 ring-1 ring-amber-500/30">
              Modificato
            </Badge>
          )}
          {fascia && override === undefined && (
            <span className="text-xs text-muted-foreground">
              fascia: {fascia}
            </span>
          )}
          {!editing && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setEditing(true)}
            >
              Modifica CP
            </Button>
          )}
        </div>

        {lookupError && (
          <p className="text-[11px] text-amber-700 dark:text-amber-400">
            {lookupError}
          </p>
        )}

        {editing && (
          <div className="grid gap-3 rounded-md border border-amber-300 bg-amber-100 p-3 dark:border-amber-700 dark:bg-amber-950/40">
            <div className="grid gap-1.5">
              <Label htmlFor="cp-override" className="text-xs">
                Nuovo valore CP (kg)
              </Label>
              <Input
                id="cp-override"
                type="number"
                step="0.5"
                min={1}
                {...form.register("cp_override", {
                  setValueAs: (v) =>
                    v === "" || v === null || v === undefined
                      ? undefined
                      : Number(v),
                })}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="cp-motivazione" className="text-xs">
                Motivazione (obbligatoria, min. 5 caratteri)
              </Label>
              <textarea
                id="cp-motivazione"
                rows={2}
                className={cn(
                  "min-h-16 rounded-md border bg-background px-3 py-2 text-sm",
                  motivazioneError && "border-rose-500",
                )}
                {...form.register("cp_motivazione")}
              />
              {motivazioneError && (
                <p className="text-[11px] text-rose-600">{motivazioneError}</p>
              )}
              <p className="text-[11px] text-muted-foreground">
                Caratteri: {motivazione?.length ?? 0}
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  form.setValue("cp_override", undefined);
                  form.setValue("cp_motivazione", "");
                  setEditing(false);
                }}
              >
                Annulla
              </Button>
              <Button type="button" onClick={() => setEditing(false)}>
                Applica
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
