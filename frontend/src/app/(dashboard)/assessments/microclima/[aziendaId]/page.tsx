"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
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

interface ServerRow {
  id: string;
  nome_area: string | null;
  tipo_ambiente: string;
  pmv: number | null;
  ppd: number | null;
  livello_rischio: string | null;
  dlim_loss50: number | null;
  created_at: string;
}

// ---------------------------------------------------------------------------

export default function MicroclimaAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [savedRows, setSavedRows] = useState<ServerRow[]>([]);

  const refetchSaved = useCallback(async () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    let token: string | null = null;
    try {
      const s = await fetch("/api/auth/session");
      const session = await s.json();
      token = session?.accessToken ?? null;
    } catch {
      /* noop */
    }
    const res = await fetch(
      `${apiUrl}/api/v1/aziende/${aziendaId}/microclima-valutazioni`,
      {
        headers: token
          ? {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            }
          : { "Content-Type": "application/json" },
      },
    );
    if (res.ok) {
      const rows = (await res.json()) as ServerRow[];
      setSavedRows(rows);
    }
  }, [aziendaId]);

  // Load azienda metadata + saved valutazioni.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const apiUrl =
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        let token: string | null = null;
        try {
          const s = await fetch("/api/auth/session");
          const session = await s.json();
          token = session?.accessToken ?? null;
        } catch {
          /* noop */
        }
        const headers: Record<string, string> = token
          ? {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            }
          : { "Content-Type": "application/json" };
        const [azRes, rowsRes] = await Promise.all([
          fetch(`${apiUrl}/api/v1/aziende/${aziendaId}`, { headers }),
          fetch(
            `${apiUrl}/api/v1/aziende/${aziendaId}/microclima-valutazioni`,
            { headers },
          ),
        ]);
        if (!azRes.ok) throw new Error(`Errore ${azRes.status}`);
        const data = (await azRes.json()) as Azienda;
        if (!cancelled) setAzienda(data);
        if (rowsRes.ok) {
          const rows = (await rowsRes.json()) as ServerRow[];
          if (!cancelled) setSavedRows(rows);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error
              ? err.message
              : "Impossibile caricare l'azienda",
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
          <h1 className="mt-2 type-h1">Valutazione Microclima</h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
      </div>

      {savedRows.length > 0 && (
        <Card className="border-emerald-200/60 bg-emerald-50/40">
          <CardContent className="py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-emerald-800">
              Valutazioni archiviate ({savedRows.length})
            </p>
            <ul className="mt-2 grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
              {savedRows.map((r) => (
                <li
                  key={r.id}
                  className="flex items-center justify-between rounded-md bg-background px-3 py-2 ring-1 ring-border"
                >
                  <span className="truncate">
                    {r.nome_area || "(senza nome)"} ·{" "}
                    <span className="text-muted-foreground">
                      {r.tipo_ambiente}
                    </span>
                  </span>
                  <span className="text-muted-foreground">
                    {r.tipo_ambiente === "moderato"
                      ? r.pmv !== null
                        ? `PMV ${r.pmv.toFixed(2)} · PPD ${r.ppd?.toFixed(1)}%`
                        : "—"
                      : r.dlim_loss50 !== null
                        ? `d_lim ${Math.round(r.dlim_loss50)}'`
                        : "—"}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="pmv">
        <TabsList>
          <TabsTrigger value="pmv">Comfort (PMV/PPD)</TabsTrigger>
          <TabsTrigger value="phs">Stress termico (PHS)</TabsTrigger>
        </TabsList>

        <TabsContent value="pmv" className="mt-4">
          <MicroclimaPmvForm aziendaId={aziendaId} onSaved={refetchSaved} />
        </TabsContent>

        <TabsContent value="phs" className="mt-4">
          <MicroclimaPhsForm aziendaId={aziendaId} onSaved={refetchSaved} />
        </TabsContent>
      </Tabs>

      <p className="text-[11px] text-muted-foreground">
        Le bozze sono salvate in locale; premi "Salva nel fascicolo" per
        archiviare la valutazione di un'area sul server.
      </p>
    </div>
  );
}
