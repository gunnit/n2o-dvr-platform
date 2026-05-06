"use client";

import { useMemo } from "react";
import Link from "next/link";
import { ArrowRight, Layers, ShieldAlert } from "lucide-react";
import {
  EmptyState,
  Panel,
  PanelHeader,
  StatTile,
} from "@/components/aziende/tabs/_shared";
import type { Ambiente, LivelloRischio, ValutazioneRischio } from "@/types";

interface RischiTabProps {
  aziendaId: string;
  rischi: ValutazioneRischio[];
  ambienti: Ambiente[];
  /**
   * Kept in the prop signature for back-compat with the parent fetchData
   * callback, even though the summary view doesn't trigger measure saves
   * — those moved with the editor onto /assessments/risk/[aziendaId].
   */
  onMeasuresSaved?: () => void;
}

const LIVELLO_ORDER: LivelloRischio[] = [
  "ACCETTABILE",
  "MODESTO",
  "GRAVE",
  "GRAVISSIMO",
];

const LIVELLO_LABEL: Record<LivelloRischio, string> = {
  ACCETTABILE: "Accettabile",
  MODESTO: "Modesto",
  GRAVE: "Grave",
  GRAVISSIMO: "Gravissimo",
};

const LIVELLO_BAR: Record<LivelloRischio, string> = {
  ACCETTABILE: "bg-[#15be53]",
  MODESTO: "bg-[#9b6829]",
  GRAVE: "bg-[#003d74]",
  GRAVISSIMO: "bg-[#b51648]",
};

const LIVELLO_DOT: Record<LivelloRischio, string> = LIVELLO_BAR;

/**
 * Read-only summary of the valutazione rischi for the azienda detail page.
 *
 * Replaces the previous inline editor (extracted to /assessments/risk/[id]
 * 2026-04-30 per admin feedback #2). The tab now serves three purposes:
 *  - quick at-a-glance stats (total, levels, P/D distribution)
 *  - per-ambiente headline counts so the user knows where the heat is
 *  - prominent CTA to open the standalone editor
 */
export default function RischiTab({
  aziendaId,
  rischi,
  ambienti,
}: RischiTabProps) {
  const applicable = useMemo(
    () => rischi.filter((r) => r.applicabile),
    [rischi],
  );

  const ambienteById = useMemo(() => {
    const map = new Map<string, Ambiente>();
    for (const a of ambienti) map.set(a.id, a);
    return map;
  }, [ambienti]);

  const counts = useMemo(() => {
    const c: Record<LivelloRischio, number> = {
      ACCETTABILE: 0,
      MODESTO: 0,
      GRAVE: 0,
      GRAVISSIMO: 0,
    };
    for (const r of applicable) {
      if (r.livello_rischio) c[r.livello_rischio] += 1;
    }
    return c;
  }, [applicable]);

  const total = applicable.length;
  const critici = counts.GRAVE + counts.GRAVISSIMO;

  // P/D histogram (1-4). P spans applicable rows; D ditto. Buckets that
  // never appeared in the applicable set still render so the operator can
  // tell at a glance whether the assessment is uniformly low/high.
  const pdDistribution = useMemo(() => {
    const buckets = [1, 2, 3, 4];
    const p: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0 };
    const d: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0 };
    for (const r of applicable) {
      if (r.probabilita_p && p[r.probabilita_p] !== undefined) {
        p[r.probabilita_p] += 1;
      }
      if (r.danno_d && d[r.danno_d] !== undefined) {
        d[r.danno_d] += 1;
      }
    }
    return { buckets, p, d };
  }, [applicable]);

  // Per-ambiente headline rollup — total + worst level present.
  const perAmbiente = useMemo(() => {
    const groups = new Map<string, ValutazioneRischio[]>();
    for (const r of applicable) {
      const list = groups.get(r.ambiente_id);
      if (list) list.push(r);
      else groups.set(r.ambiente_id, [r]);
    }
    const rows: Array<{
      ambienteId: string;
      nome: string;
      total: number;
      worst: LivelloRischio | null;
    }> = [];
    // Iterate in ambienti order so the table reads top-to-bottom in the
    // same order as the Ambienti tab; ambienti without rischi still appear
    // so "0" shows up (a known-empty environment is information).
    for (const a of ambienti) {
      const list = groups.get(a.id) ?? [];
      let worst: LivelloRischio | null = null;
      const order: Record<LivelloRischio, number> = {
        ACCETTABILE: 1,
        MODESTO: 2,
        GRAVE: 3,
        GRAVISSIMO: 4,
      };
      for (const r of list) {
        if (!r.livello_rischio) continue;
        if (!worst || order[r.livello_rischio] > order[worst]) {
          worst = r.livello_rischio;
        }
      }
      rows.push({
        ambienteId: a.id,
        nome: a.nome ?? "Ambiente",
        total: list.length,
        worst,
      });
    }
    return rows;
  }, [applicable, ambienti, ambienteById]);

  const editorHref = `/assessments/risk/${aziendaId}`;

  if (total === 0) {
    return (
      <Panel accent="violet">
        <PanelHeader
          icon={ShieldAlert}
          title="Valutazioni del rischio"
          accent="violet"
        />
        <div className="space-y-4 p-6">
          <EmptyState
            icon={ShieldAlert}
            title="Nessun rischio registrato"
            body="Apri la valutazione per iniziare."
          />
          <div className="flex justify-center">
            <Link
              href={editorHref}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-[13px] font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
            >
              <ShieldAlert className="h-3.5 w-3.5" strokeWidth={2} />
              Apri valutazione
              <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} />
            </Link>
          </div>
        </div>
      </Panel>
    );
  }

  const subtitle =
    total +
    " rischi valutati" +
    (critici > 0 ? " · " + critici + " critici" : "");

  return (
    <Panel accent="violet">
      <PanelHeader
        icon={ShieldAlert}
        title="Valutazioni del rischio"
        subtitle={subtitle}
        accent="violet"
      />

      <div className="space-y-5 p-6">
        {/* Header CTA — primary action moved here from the editor inline. */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-[#e5edf5] bg-gradient-to-b from-white to-[#fbfcfe] px-4 py-3">
          <div>
            <p className="text-[14px] font-semibold text-[#061b31]">
              Valutazione rischi
            </p>
            <p className="mt-0.5 text-[12px] text-[#64748d]">
              Apri la pagina dedicata per modificare P/D, applicabilità e i
              pericoli specifici per ogni ambiente.
            </p>
          </div>
          <Link
            href={editorHref}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-3.5 py-2 text-[13px] font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
          >
            Apri valutazione
            <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} />
          </Link>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile label="Totale rischi" value={total} />
          <StatTile
            label="Accettabili"
            value={counts.ACCETTABILE}
            tone="ok"
          />
          <StatTile
            label="Gravi"
            value={counts.GRAVE}
            tone={counts.GRAVE > 0 ? "warn" : "default"}
          />
          <StatTile
            label="Gravissimi"
            value={counts.GRAVISSIMO}
            tone={counts.GRAVISSIMO > 0 ? "danger" : "default"}
          />
        </div>

        {/* Stacked level bar */}
        <div className="space-y-2">
          <div className="flex h-2 w-full overflow-hidden rounded-full bg-[#f6f9fc]">
            {LIVELLO_ORDER.map((l) => {
              const c = counts[l];
              if (c === 0) return null;
              return (
                <div
                  key={l}
                  className={LIVELLO_BAR[l]}
                  style={{ width: `${(c / total) * 100}%` }}
                />
              );
            })}
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[12px] text-[#64748d]">
            {LIVELLO_ORDER.map((l) => {
              const c = counts[l];
              if (c === 0) return null;
              return (
                <span key={l} className="inline-flex items-center gap-1.5">
                  <span
                    className={
                      "inline-block h-2 w-2 rounded-full " + LIVELLO_DOT[l]
                    }
                  />
                  <span>{LIVELLO_LABEL[l]}</span>
                  <span className="tnum text-[#273951]">{c}</span>
                </span>
              );
            })}
          </div>
        </div>

        {/* P / D distribution mini-bars */}
        <div className="grid gap-4 sm:grid-cols-2">
          <DistributionBar
            label="Distribuzione P (probabilità)"
            buckets={pdDistribution.buckets}
            counts={pdDistribution.p}
            total={total}
          />
          <DistributionBar
            label="Distribuzione D (danno)"
            buckets={pdDistribution.buckets}
            counts={pdDistribution.d}
            total={total}
          />
        </div>

        {/* Per-ambiente rollup */}
        {perAmbiente.length > 0 && (
          <section className="space-y-2">
            <div className="flex items-center gap-2">
              <Layers
                className="h-3.5 w-3.5 text-[#64748d]"
                strokeWidth={1.75}
              />
              <h4 className="text-[14px] font-medium text-[#061b31]">
                Per ambiente
              </h4>
            </div>
            <ul className="divide-y divide-[#eef2f7] rounded-md border border-[#e5edf5] bg-white">
              {perAmbiente.map((row) => (
                <li
                  key={row.ambienteId}
                  className="flex items-center justify-between gap-3 px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-[14px] font-medium text-[#061b31]">
                      {row.nome}
                    </p>
                    <p className="text-[12px] text-[#64748d]">
                      {row.total === 0
                        ? "Nessun rischio applicabile"
                        : `${row.total} rischi applicabili`}
                    </p>
                  </div>
                  {row.worst && (
                    <span className="inline-flex shrink-0 items-center gap-1.5 text-[12px] text-[#273951]">
                      <span
                        className={
                          "inline-block h-2 w-2 rounded-full " +
                          LIVELLO_DOT[row.worst]
                        }
                      />
                      {LIVELLO_LABEL[row.worst]}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </Panel>
  );
}

interface DistributionBarProps {
  label: string;
  buckets: number[];
  counts: Record<number, number>;
  total: number;
}

function DistributionBar({
  label,
  buckets,
  counts,
  total,
}: DistributionBarProps) {
  return (
    <div className="space-y-2 rounded-md border border-[#e5edf5] bg-white p-3">
      <p className="type-eyebrow">{label}</p>
      <div className="space-y-1.5">
        {buckets.map((b) => {
          const c = counts[b] ?? 0;
          const pct = total === 0 ? 0 : Math.round((c / total) * 100);
          return (
            <div key={b} className="flex items-center gap-2 text-[12px]">
              <span className="w-3 shrink-0 font-medium text-[#273951] tnum">
                {b}
              </span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#f0f4f9]">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="tnum w-10 shrink-0 text-right text-[#64748d]">
                {c}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
