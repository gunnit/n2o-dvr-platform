"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { RischiEditor } from "@/components/rischi/rischi-editor";
import type { Ambiente, Attrezzatura, Azienda } from "@/types";

/**
 * Standalone Valutazione Rischi page.
 *
 * Replaces the in-wizard step-rischi (extracted 2026-04-30 per admin
 * feedback #2 + #5: "rischio è una pagina a sé, non uno step", and the
 * wizard column is too narrow for a meaningful risk table). The page lives
 * inside the (dashboard) route group so it inherits the auth guard +
 * sidebar; we just bust the layout's max-w-screen-xl with a small CSS
 * trick so the editor stretches as wide as it needs.
 */
export default function RiskAssessmentPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;
  const router = useRouter();
  const { apiFetch, isAuthenticated } = useApi();

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [ambienti, setAmbienti] = useState<Ambiente[]>([]);
  const [attrezzature, setAttrezzature] = useState<Attrezzatura[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      apiFetch<Azienda>(`/api/v1/aziende/${aziendaId}`),
      apiFetch<Ambiente[]>(`/api/v1/aziende/${aziendaId}/ambienti`).catch(
        () => [] as Ambiente[],
      ),
      apiFetch<Attrezzatura[]>(
        `/api/v1/aziende/${aziendaId}/attrezzature`,
      ).catch(() => [] as Attrezzatura[]),
    ])
      .then(([az, amb, att]) => {
        if (cancelled) return;
        setAzienda(az);
        setAmbienti(amb);
        setAttrezzature(att);
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(
          err instanceof Error ? err.message : "Errore nel caricamento",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [apiFetch, aziendaId, isAuthenticated]);

  const ragioneSociale = useMemo(
    () => azienda?.ragione_sociale ?? `Azienda ${aziendaId}`,
    [azienda, aziendaId],
  );

  return (
    // The dashboard layout caps content at max-w-screen-xl. The editor's
    // table needs more horizontal real estate, so we knock the cap off
    // *for this page only* via negative-margin tricks scoped to the
    // outermost wrapper. min-w-0 keeps long category names from blowing
    // out the layout if the user shrinks the viewport.
    <div className="-mx-4 min-w-0 space-y-6 lg:-mx-12 xl:-mx-20 2xl:-mx-32">
      <div className="space-y-3 px-4 lg:px-12 xl:px-20 2xl:px-32">
        <Link
          href={`/aziende/${aziendaId}?tab=rischi`}
          className="-mb-1 inline-flex items-center gap-1.5 text-[13px] font-medium text-[#64748d] transition-colors hover:text-[#061b31]"
        >
          <ArrowLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          {ragioneSociale}
        </Link>

        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
              <Badge variant="secondary">
                <ShieldAlert className="mr-1 h-3 w-3" />
                Valutazione Rischi
              </Badge>
              <span>D.Lgs. 81/2008 · Formula I = 2D + P</span>
            </div>
            <h1 className="mt-2 type-h1">Valutazione Rischi</h1>
            <p className="text-sm text-muted-foreground">
              {loadError
                ? `Azienda ${aziendaId} (metadati non disponibili)`
                : ragioneSociale}
            </p>
          </div>
          <Button
            type="button"
            onClick={() => router.push(`/aziende/${aziendaId}?tab=rischi`)}
          >
            Salva e torna all&apos;azienda
          </Button>
        </div>
      </div>

      <div className="px-4 lg:px-12 xl:px-20 2xl:px-32">
        {loading ? (
          <p className="text-sm text-muted-foreground">Caricamento…</p>
        ) : loadError ? (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive">
            {loadError}
          </div>
        ) : (
          <RischiEditor
            aziendaId={aziendaId}
            ambienti={ambienti}
            attrezzature={attrezzature}
          />
        )}
      </div>
    </div>
  );
}
