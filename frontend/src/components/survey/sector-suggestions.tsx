"use client";

// Phase 8.4 — sector pre-population banner.
//
// Sits above the wizard step content. On mount fetches /sector-summary;
// renders nothing when no peer data exists (sector_size === 0) so an
// empty org never sees a useless banner. When peers exist the banner
// shows a one-line "we found N similar DVRs" hook with a button that
// opens a dialog listing typical attrezzature / rischi / sostanze.
//
// The dialog is read-only on purpose — the operator sees what's typical
// in their sector and decides what to add. Auto-application would have
// to thread through every wizard step's setter; out of scope for v1.

import { useEffect, useMemo, useState } from "react";
import { useApi } from "@/hooks/use-api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Lightbulb, History } from "lucide-react";

interface SectorAttrezzatura {
  descrizione: string;
  count: number;
}

interface SectorRischio {
  categoria_rischio: string;
  applicabile_count: number;
  total: number;
  avg_p: number | null;
  avg_d: number | null;
}

interface SectorSostanza {
  nome_prodotto: string;
  count: number;
}

interface SectorSummary {
  sector_size: number;
  ateco_prefix: string | null;
  attrezzature_by_tipo: Record<string, SectorAttrezzatura[]>;
  rischi_by_tipo: Record<string, SectorRischio[]>;
  top_sostanze: SectorSostanza[];
}

export function SectorSuggestions({ aziendaId }: { aziendaId: string }) {
  const { apiFetch } = useApi();
  const [summary, setSummary] = useState<SectorSummary | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await apiFetch<SectorSummary>(
          `/api/v1/aziende/${aziendaId}/sector-summary`,
        );
        if (!cancelled) setSummary(data);
      } catch {
        // Silent fail — banner is non-essential.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiFetch, aziendaId]);

  const tipos = useMemo(() => {
    if (!summary) return [];
    const set = new Set<string>([
      ...Object.keys(summary.attrezzature_by_tipo),
      ...Object.keys(summary.rischi_by_tipo),
    ]);
    return Array.from(set).sort();
  }, [summary]);

  if (!summary || summary.sector_size === 0) return null;

  return (
    <>
      <div className="flex flex-col gap-2 rounded-lg border border-emerald-300 bg-emerald-100 px-4 py-3 text-sm dark:border-emerald-700 dark:bg-emerald-950/40 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-2 text-emerald-950 dark:text-emerald-100">
          <Lightbulb className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-semibold">
              Trovati {summary.sector_size} DVR simili nel tuo settore
              {summary.ateco_prefix
                ? ` (ATECO ${summary.ateco_prefix}xx)`
                : ""}
            </p>
            <p className="text-xs text-emerald-900 dark:text-emerald-200">
              Vedi attrezzature, rischi e sostanze ricorrenti — usali come
              punto di partenza.
            </p>
          </div>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setOpen(true)}
          className="border-emerald-300 text-emerald-800 hover:bg-emerald-100 dark:border-emerald-700 dark:text-emerald-200 dark:hover:bg-emerald-900/30"
        >
          <History className="mr-1.5 h-3.5 w-3.5" />
          Vedi consigli del settore
        </Button>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[80vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-emerald-600" />
              Consigli dal settore
            </DialogTitle>
            <DialogDescription>
              Aggregati da {summary.sector_size} DVR completati di altre
              aziende nel tuo settore. I valori sono solo indicativi —
              decidi tu cosa applicare al tuo cliente.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 pt-2">
            {tipos.map((tipo) => {
              const att = summary.attrezzature_by_tipo[tipo] ?? [];
              const ris = summary.rischi_by_tipo[tipo] ?? [];
              if (att.length === 0 && ris.length === 0) return null;
              return (
                <section key={tipo} className="space-y-3">
                  <h4 className="font-semibold capitalize">
                    Ambienti tipo &quot;{tipo}&quot;
                  </h4>

                  {att.length > 0 && (
                    <div>
                      <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                        Attrezzature ricorrenti
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {att.map((a) => (
                          <Badge
                            key={a.descrizione}
                            variant="outline"
                            className="font-normal"
                          >
                            {a.descrizione}
                            <span className="ml-1.5 text-muted-foreground">
                              ×{a.count}
                            </span>
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {ris.length > 0 && (
                    <div>
                      <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                        Rischi tipici (% applicabile, P medio, D medio)
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {ris.map((r) => {
                          const pct = r.total
                            ? Math.round(
                                (r.applicabile_count / r.total) * 100,
                              )
                            : 0;
                          return (
                            <Badge
                              key={r.categoria_rischio}
                              variant="outline"
                              className="font-normal"
                            >
                              {r.categoria_rischio}
                              <span className="ml-1.5 text-muted-foreground">
                                {pct}% · P{r.avg_p ?? "—"} D{r.avg_d ?? "—"}
                              </span>
                            </Badge>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </section>
              );
            })}

            {summary.top_sostanze.length > 0 && (
              <section className="space-y-2">
                <h4 className="font-semibold">Sostanze chimiche ricorrenti</h4>
                <div className="flex flex-wrap gap-1.5">
                  {summary.top_sostanze.map((s) => (
                    <Badge
                      key={s.nome_prodotto}
                      variant="outline"
                      className="font-normal"
                    >
                      {s.nome_prodotto}
                      <span className="ml-1.5 text-muted-foreground">
                        ×{s.count}
                      </span>
                    </Badge>
                  ))}
                </div>
              </section>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
