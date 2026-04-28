"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, CalendarClock } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useApi } from "@/hooks/use-api";

/**
 * Dashboard widgets for mandatory VDT health-surveillance alerts (US-3.5).
 *
 * Two side-by-side cards:
 *   - "Visite in scadenza" — next exam due within 60 days (amber).
 *   - "Visite scadute"     — next exam already overdue (rose).
 *
 * Both feed from a single API call (`GET /api/v1/sorveglianza/alerts`) to
 * keep the widget a cheap render on dashboard mount. Each row links to
 * the client's azienda page so the operator can schedule the visit in
 * context. Kept as a separate component so it can be reused on any
 * future "Sorveglianza sanitaria" landing page without copy-paste.
 */

export interface SurveillanceWorkerRow {
  valutazione_id: string;
  azienda_id: string;
  azienda_ragione_sociale: string;
  persona_id: string | null;
  nominativo: string | null;
  postazione: string;
  data_ultima_visita: string | null;
  data_prossima_visita: string;
  periodicita_sorveglianza: "biennale" | "quinquennale" | null;
  eta_50_plus: boolean;
  days_until_due: number;
}

interface SurveillanceAlertsResponse {
  in_scadenza: SurveillanceWorkerRow[];
  scadute: SurveillanceWorkerRow[];
  as_of: string;
  window_days: number;
}

function formatItalianDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function describeDelta(days: number): string {
  if (days === 0) return "oggi";
  if (days < 0) return `scaduta da ${Math.abs(days)} ${Math.abs(days) === 1 ? "giorno" : "giorni"}`;
  if (days === 1) return "domani";
  return `tra ${days} giorni`;
}

function WorkerRow({ row, tone }: { row: SurveillanceWorkerRow; tone: "amber" | "rose" }) {
  const toneClasses =
    tone === "rose"
      ? "border-[rgba(186,26,26,0.3)] bg-[rgba(186,26,26,0.06)]"
      : "border-[rgba(155,104,41,0.3)] bg-[rgba(245,158,11,0.08)]";
  const deltaClasses =
    tone === "rose" ? "text-[#ba1a1a]" : "text-[#9b6829]";
  const display = row.nominativo ?? row.postazione;
  return (
    <li
      className={`rounded-md border px-3 py-2 text-sm transition-colors ${toneClasses}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-medium text-[#061b31]">{display}</p>
          <Link
            href={`/aziende/${row.azienda_id}`}
            className="truncate text-xs text-[#64748d] hover:underline"
          >
            {row.azienda_ragione_sociale}
          </Link>
          <p className="mt-0.5 text-[11px] text-[#64748d]">
            Postazione: {row.postazione}
            {row.eta_50_plus ? " · over 50 (biennale)" : ""}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs font-medium tabular-nums text-[#061b31]">
            {formatItalianDate(row.data_prossima_visita)}
          </p>
          <p className={`text-[11px] font-medium ${deltaClasses}`}>{describeDelta(row.days_until_due)}</p>
        </div>
      </div>
    </li>
  );
}

export function SurveillanceAlerts() {
  const { apiFetch, isAuthenticated } = useApi();
  const [data, setData] = useState<SurveillanceAlertsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    setLoading(true);
    apiFetch<SurveillanceAlertsResponse>("/api/v1/sorveglianza/alerts")
      .then((res) => {
        if (cancelled) return;
        setData(res);
        setError(null);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message || "Errore caricamento sorveglianza");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [apiFetch, isAuthenticated]);

  // Don't take up dashboard space while loading — a silent absence
  // beats a flash of empty-state cards.
  if (loading) return null;

  // Hide entirely when there's nothing to flag. Clean dashboards are
  // better than dashboards cluttered with empty panels.
  const inScadenza = data?.in_scadenza ?? [];
  const scadute = data?.scadute ?? [];
  if (!error && inScadenza.length === 0 && scadute.length === 0) return null;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {/* Scadute — red, most urgent, always first */}
      <Card className="border-[rgba(186,26,26,0.25)]">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-[#ba1a1a]" aria-hidden />
            <CardTitle className="text-sm font-medium">
              Visite sorveglianza scadute
            </CardTitle>
            <Badge variant="destructive" className="ml-auto">
              {scadute.length}
            </Badge>
          </div>
          <CardDescription className="text-xs">
            Lavoratori VDT con visita oculistica obbligatoria gi&agrave;
            scaduta. Contattare il medico competente.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {scadute.length === 0 ? (
            <p className="py-2 text-xs text-[#64748d]">
              Nessuna visita scaduta.
            </p>
          ) : (
            <ul className="space-y-2">
              {scadute.slice(0, 5).map((row) => (
                <WorkerRow key={row.valutazione_id} row={row} tone="rose" />
              ))}
              {scadute.length > 5 && (
                <li className="pt-1 text-xs text-[#64748d]">
                  + altri {scadute.length - 5} lavoratori
                </li>
              )}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* In scadenza — amber, upcoming */}
      <Card className="border-[rgba(155,104,41,0.3)]">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <CalendarClock className="h-4 w-4 text-[#9b6829]" aria-hidden />
            <CardTitle className="text-sm font-medium">
              Visite in scadenza
            </CardTitle>
            <Badge className="ml-auto bg-[rgba(245,158,11,0.14)] text-[#9b6829] border-[rgba(155,104,41,0.3)]">
              {inScadenza.length}
            </Badge>
          </div>
          <CardDescription className="text-xs">
            Visita oculistica obbligatoria nei prossimi{" "}
            {data?.window_days ?? 60} giorni.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {inScadenza.length === 0 ? (
            <p className="py-2 text-xs text-[#64748d]">
              Nessuna visita in scadenza nel periodo.
            </p>
          ) : (
            <ul className="space-y-2">
              {inScadenza.slice(0, 5).map((row) => (
                <WorkerRow key={row.valutazione_id} row={row} tone="amber" />
              ))}
              {inScadenza.length > 5 && (
                <li className="pt-1 text-xs text-[#64748d]">
                  + altri {inScadenza.length - 5} lavoratori
                </li>
              )}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
