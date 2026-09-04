"use client";

/**
 * "Schede degli ambienti" card for the PEE page (segnalazione 2026-08-25):
 * one SchedaAmbienteFields block per ambiente of the azienda. Loads the
 * ambienti itself so the host page only has to place the card.
 */

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useApi } from "@/hooks/use-api";
import type { Ambiente } from "@/types";

import { SchedaAmbienteFields } from "./scheda-ambiente-fields";

export function SchedeAmbientiSection({ aziendaId }: { aziendaId: string }) {
  const { apiFetch } = useApi();
  const [ambienti, setAmbienti] = useState<Ambiente[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch<Ambiente[]>(`/api/v1/aziende/${aziendaId}/ambienti`)
      .then((rows) => {
        if (!cancelled) {
          setAmbienti(rows);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Caricamento degli ambienti non riuscito.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [aziendaId, apiFetch]);

  const handleSaved = (updated: Ambiente) => {
    setAmbienti((prev) =>
      prev ? prev.map((a) => (a.id === updated.id ? updated : a)) : prev,
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Schede degli ambienti</CardTitle>
        <CardDescription>
          Descrizione del locale, materiali presenti, affollamento massimo e
          sorgenti di innesco per ogni ambiente. Gli stessi dati vengono
          stampati nell&apos;allegato Rischio Incendio: si inseriscono una
          volta sola.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {ambienti === null && !error && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Caricamento ambienti...
          </div>
        )}
        {error && (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}
        {ambienti && ambienti.length === 0 && (
          <p className="text-sm italic text-muted-foreground">
            Nessun ambiente censito per questa azienda. Aggiungi gli ambienti
            dal sopralluogo per compilare le schede.
          </p>
        )}
        {ambienti?.map((amb) => (
          <div key={amb.id} className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">{amb.nome}</span>
              {amb.tipo && (
                <Badge variant="secondary" className="text-[10px]">
                  {amb.tipo}
                </Badge>
              )}
              {amb.superficie_mq != null && (
                <span className="text-[11px] text-muted-foreground">
                  {amb.superficie_mq} mq
                </span>
              )}
            </div>
            <SchedaAmbienteFields ambiente={amb} onSaved={handleSaved} />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
