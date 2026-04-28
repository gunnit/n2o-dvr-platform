"use client";

import { useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Filter,
  Layers,
  MapPin,
  ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";
import {
  EmptyState,
  Panel,
  PanelHeader,
  StatTile,
  StatusPill,
  riskLevelStyles,
} from "@/components/aziende/tabs/_shared";
import { MeasuresPanel } from "@/components/ai/measures-panel";
import { apiCall } from "@/lib/api-client";
import type { Ambiente, LivelloRischio, ValutazioneRischio } from "@/types";

interface RischiTabProps {
  aziendaId: string;
  rischi: ValutazioneRischio[];
  ambienti: Ambiente[];
  onMeasuresSaved: () => void;
}

type LivelloFilter = "ALL" | LivelloRischio;
type AmbienteFilter = "ALL" | string;

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

const SEGMENT_ACTIVE = "bg-primary text-white";
const SEGMENT_IDLE =
  "border border-[#e5edf5] text-[#273951] hover:bg-[#f6f9fc]";

function segmentClass(active: boolean) {
  return (
    "inline-flex items-center rounded-md px-3 py-1.5 text-[12px] font-medium transition-colors " +
    (active ? SEGMENT_ACTIVE : SEGMENT_IDLE)
  );
}

export default function RischiTab({
  aziendaId,
  rischi,
  ambienti,
  onMeasuresSaved,
}: RischiTabProps) {
  const [livelloFilter, setLivelloFilter] = useState<LivelloFilter>("ALL");
  const [ambienteFilter, setAmbienteFilter] = useState<AmbienteFilter>("ALL");
  const [expandedRisk, setExpandedRisk] = useState<string | null>(null);

  const applicable = useMemo(
    () => rischi.filter((r) => r.applicabile),
    [rischi]
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

  const filtered = useMemo(() => {
    return applicable.filter((r) => {
      if (livelloFilter !== "ALL" && r.livello_rischio !== livelloFilter)
        return false;
      if (ambienteFilter !== "ALL" && r.ambiente_id !== ambienteFilter)
        return false;
      return true;
    });
  }, [applicable, livelloFilter, ambienteFilter]);

  const grouped = useMemo(() => {
    const groups = new Map<string, ValutazioneRischio[]>();
    for (const r of filtered) {
      const key = r.categoria_rischio || "Altro";
      const list = groups.get(key);
      if (list) list.push(r);
      else groups.set(key, [r]);
    }
    return Array.from(groups.entries()).sort(([a], [b]) =>
      a.localeCompare(b, "it")
    );
  }, [filtered]);

  const useAmbienteSelect = ambienti.length > 5;

  if (total === 0) {
    return (
      <Panel accent="violet">
        <PanelHeader
          icon={ShieldAlert}
          title="Valutazioni del rischio"
          accent="violet"
        />
        <EmptyState
          icon={ShieldAlert}
          title="Nessun rischio registrato"
          body="Completa il sopralluogo per valutare i rischi."
        />
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

        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-[#64748d]">
              <Filter className="h-3.5 w-3.5" strokeWidth={1.75} />
              Livello
            </span>
            <button
              type="button"
              className={segmentClass(livelloFilter === "ALL")}
              onClick={() => setLivelloFilter("ALL")}
            >
              Tutti
            </button>
            {LIVELLO_ORDER.map((l) => (
              <button
                key={l}
                type="button"
                className={segmentClass(livelloFilter === l)}
                onClick={() => setLivelloFilter(l)}
              >
                {LIVELLO_LABEL[l]}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-[#64748d]">
              <MapPin className="h-3.5 w-3.5" strokeWidth={1.75} />
              Ambiente
            </span>
            {useAmbienteSelect ? (
              <select
                value={ambienteFilter}
                onChange={(e) => setAmbienteFilter(e.target.value)}
                className="rounded-md border border-[#e5edf5] bg-white px-3 py-1.5 text-[12px] text-[#273951] hover:bg-[#f6f9fc] focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                <option value="ALL">Tutti</option>
                {ambienti.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.nome}
                  </option>
                ))}
              </select>
            ) : (
              <>
                <button
                  type="button"
                  className={segmentClass(ambienteFilter === "ALL")}
                  onClick={() => setAmbienteFilter("ALL")}
                >
                  Tutti
                </button>
                {ambienti.map((a) => (
                  <button
                    key={a.id}
                    type="button"
                    className={segmentClass(ambienteFilter === a.id)}
                    onClick={() => setAmbienteFilter(a.id)}
                  >
                    {a.nome}
                  </button>
                ))}
              </>
            )}
          </div>
        </div>

        {filtered.length === 0 ? (
          <p className="rounded-md border border-dashed border-[#e5edf5] bg-[#f6f9fc] px-4 py-6 text-center text-[13px] text-[#64748d]">
            Nessun rischio per i filtri selezionati. Reimposta i filtri per
            vedere tutti i rischi.
          </p>
        ) : (
          <div className="space-y-5">
            {grouped.map(([categoria, items]) => (
              <section key={categoria} className="space-y-2">
                <div className="flex items-center gap-2">
                  <Layers
                    className="h-3.5 w-3.5 text-[#64748d]"
                    strokeWidth={1.75}
                  />
                  <h4 className="text-[14px] font-medium text-[#061b31]">
                    {categoria}
                  </h4>
                  <span className="inline-flex items-center rounded-md border border-[#e5edf5] bg-[#f6f9fc] px-2 py-0.5 text-[11px] font-medium text-[#273951] tnum">
                    {items.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {items.map((r) => {
                    const isOpen = expandedRisk === r.id;
                    const ambiente = ambienteById.get(r.ambiente_id);
                    const ambienteNome = ambiente?.nome ?? "—";
                    const headline = r.pericolo ?? r.rischio ?? "—";
                    return (
                      <div
                        key={r.id}
                        className="rounded-md border border-[#e5edf5] bg-white shadow-stripe-ambient"
                      >
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedRisk(isOpen ? null : r.id)
                          }
                          className="flex w-full items-start justify-between gap-3 px-5 py-3.5 text-left transition-colors hover:bg-[#f6f9fc]"
                        >
                          <div className="min-w-0 flex-1 space-y-1">
                            <p className="type-eyebrow">{ambienteNome}</p>
                            <p className="text-[14px] font-medium text-[#061b31]">
                              {headline}
                            </p>
                            {r.condizioni_esposizione && (
                              <p className="line-clamp-1 text-[12px] text-[#64748d]">
                                {r.condizioni_esposizione}
                              </p>
                            )}
                          </div>
                          <div className="flex flex-shrink-0 items-center gap-3">
                            {r.probabilita_p != null &&
                              r.danno_d != null &&
                              r.indice_i != null && (
                                <span className="tnum hidden text-[12px] text-[#64748d] sm:inline">
                                  P{r.probabilita_p} · D{r.danno_d} · I=
                                  {r.indice_i}
                                </span>
                              )}
                            {r.livello_rischio && (
                              <StatusPill
                                className={
                                  riskLevelStyles[r.livello_rischio] ||
                                  "bg-[#f6f9fc] text-[#273951] border border-[#e5edf5]"
                                }
                              >
                                {r.livello_rischio}
                              </StatusPill>
                            )}
                            {isOpen ? (
                              <ChevronUp
                                className="h-4 w-4 text-[#64748d]"
                                strokeWidth={1.75}
                              />
                            ) : (
                              <ChevronDown
                                className="h-4 w-4 text-[#64748d]"
                                strokeWidth={1.75}
                              />
                            )}
                          </div>
                        </button>
                        {isOpen && (
                          <div className="border-t border-[#e5edf5] p-5">
                            <MeasuresPanel
                              aziendaId={aziendaId}
                              rischioId={r.id}
                              categoriaRischio={r.categoria_rischio}
                              initialText={r.misure_prevenzione ?? ""}
                              onSave={async (text) => {
                                try {
                                  await apiCall(
                                    `/api/v1/aziende/${aziendaId}/ambienti/${r.ambiente_id}/rischi/${r.id}`,
                                    {
                                      method: "PUT",
                                      body: JSON.stringify({
                                        misure_prevenzione: text,
                                      }),
                                    }
                                  );
                                  toast.success("Misure salvate");
                                  onMeasuresSaved();
                                } catch (err) {
                                  toast.error(
                                    err instanceof Error
                                      ? err.message
                                      : "Salvataggio misure fallito. Riprova."
                                  );
                                  throw err;
                                }
                              }}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </Panel>
  );
}
