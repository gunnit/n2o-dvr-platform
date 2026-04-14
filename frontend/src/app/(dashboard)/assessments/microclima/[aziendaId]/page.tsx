"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  MicroclimaPhsForm,
  MicroclimaPmvForm,
} from "@/components/assessments/microclima-form";
import type { Azienda } from "@/types";

// ---------------------------------------------------------------------------

export default function MicroclimaAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Load azienda metadata (best-effort).
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        let token: string | null = null;
        try {
          const s = await fetch("/api/auth/session");
          const session = await s.json();
          token = session?.accessToken ?? null;
        } catch {
          /* noop */
        }
        const res = await fetch(`${apiUrl}/api/v1/aziende/${aziendaId}`, {
          headers: token
            ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
            : { "Content-Type": "application/json" },
        });
        if (!res.ok) throw new Error(`Errore ${res.status}`);
        const data = (await res.json()) as Azienda;
        if (!cancelled) setAzienda(data);
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error ? err.message : "Impossibile caricare l'azienda",
          );
        }
      }
    }
    if (aziendaId) load();
    return () => {
      cancelled = true;
    };
  }, [aziendaId]);

  const pageSubtitle = useMemo(() => {
    if (loadError) return `Azienda ${aziendaId} (metadati non disponibili)`;
    if (azienda) return azienda.ragione_sociale ?? `Azienda ${aziendaId}`;
    return "Caricamento…";
  }, [azienda, aziendaId, loadError]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
            <Badge variant="secondary">Allegato Microclima</Badge>
            <span>D.Lgs. 81/2008 · ISO 7730 / ISO 7933</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">
            Valutazione Microclima
          </h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
      </div>

      <Tabs defaultValue="pmv">
        <TabsList>
          <TabsTrigger value="pmv">Comfort (PMV/PPD)</TabsTrigger>
          <TabsTrigger value="phs">Stress termico (PHS)</TabsTrigger>
        </TabsList>

        <TabsContent value="pmv" className="mt-4">
          <MicroclimaPmvForm aziendaId={aziendaId} />
        </TabsContent>

        <TabsContent value="phs" className="mt-4">
          <MicroclimaPhsForm aziendaId={aziendaId} />
        </TabsContent>
      </Tabs>

      <p className="text-[11px] text-muted-foreground">
        Bozze salvate in locale (chiavi: <code>microclima-pmv-draft-{aziendaId}</code>,{" "}
        <code>microclima-phs-draft-{aziendaId}</code>)
      </p>
    </div>
  );
}
