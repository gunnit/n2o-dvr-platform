"use client";

import { useMemo, useState } from "react";
import {
  Layers,
  MapPin,
  ShieldAlert,
  User,
  Users,
  Warehouse,
  Wrench,
} from "lucide-react";
import {
  EmptyState,
  Panel,
  PanelHeader,
  StatTile,
  StatusPill,
  riskLevelStyles,
} from "@/components/aziende/tabs/_shared";
import {
  canonicalTipoLabel,
  normalizeAmbienteTipo,
  type CanonicalTipo,
} from "@/lib/ambiente-tipo";
import type {
  Ambiente,
  Attrezzatura,
  LivelloRischio,
  Persona,
  ValutazioneRischio,
} from "@/types";

interface AmbientiTabProps {
  aziendaId: string;
  ambienti: Ambiente[];
  attrezzature: Attrezzatura[];
  persone: Persona[];
  rischi: ValutazioneRischio[];
}

const NUM_FORMAT = new Intl.NumberFormat("it-IT");
const RISK_LEVELS: LivelloRischio[] = [
  "ACCETTABILE",
  "MODESTO",
  "GRAVE",
  "GRAVISSIMO",
];

export default function AmbientiTab({
  ambienti,
  attrezzature,
  persone,
  rischi,
}: AmbientiTabProps) {
  const [activeTipo, setActiveTipo] = useState<CanonicalTipo | null>(null);

  const totalSurface = useMemo(
    () => ambienti.reduce((sum, a) => sum + (a.superficie_mq ?? 0), 0),
    [ambienti],
  );

  const seriousRisks = useMemo(
    () =>
      rischi.filter(
        (r) =>
          r.applicabile &&
          (r.livello_rischio === "GRAVE" ||
            r.livello_rischio === "GRAVISSIMO"),
      ).length,
    [rischi],
  );

  const equipmentWithoutCe = useMemo(
    () => attrezzature.filter((e) => !e.marcatura_ce).length,
    [attrezzature],
  );

  const tipiPresent = useMemo(() => {
    const set = new Set<CanonicalTipo>();
    for (const a of ambienti) set.add(normalizeAmbienteTipo(a.tipo));
    return Array.from(set);
  }, [ambienti]);

  const filteredAmbienti = useMemo(() => {
    if (!activeTipo) return ambienti;
    return ambienti.filter(
      (a) => normalizeAmbienteTipo(a.tipo) === activeTipo,
    );
  }, [ambienti, activeTipo]);

  const personaById = useMemo(() => {
    const map = new Map<string, Persona>();
    for (const p of persone) map.set(p.id, p);
    return map;
  }, [persone]);

  const headerSubtitle =
    ambienti.length === 0
      ? "Nessun ambiente"
      : `${NUM_FORMAT.format(ambienti.length)} ambienti · ${NUM_FORMAT.format(totalSurface)} mq`;

  return (
    <Panel accent="amber">
      <PanelHeader
        icon={Warehouse}
        title="Ambienti di Lavoro"
        subtitle={headerSubtitle}
        accent="amber"
      />

      {ambienti.length === 0 ? (
        <EmptyState
          icon={Warehouse}
          title="Nessun ambiente registrato"
          body="Avvia il sopralluogo per aggiungere gli ambienti."
        />
      ) : (
        <div className="flex flex-col gap-5 p-6">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile
              label="Totale ambienti"
              value={NUM_FORMAT.format(ambienti.length)}
            />
            <StatTile
              label="Superficie totale"
              value={NUM_FORMAT.format(totalSurface)}
              sublabel="mq"
            />
            <StatTile
              label="Rischi gravi"
              value={NUM_FORMAT.format(seriousRisks)}
              tone={seriousRisks > 0 ? "warn" : "default"}
            />
            <StatTile
              label="Attrezzature totali"
              value={NUM_FORMAT.format(attrezzature.length)}
              sublabel={
                equipmentWithoutCe > 0
                  ? `${NUM_FORMAT.format(equipmentWithoutCe)} senza marcatura CE`
                  : undefined
              }
              tone={equipmentWithoutCe > 0 ? "danger" : "default"}
            />
          </div>

          {tipiPresent.length > 1 && (
            <div className="flex flex-wrap items-center gap-2">
              <FilterChip
                active={activeTipo === null}
                onClick={() => setActiveTipo(null)}
              >
                Tutti
              </FilterChip>
              {tipiPresent.map((tipo) => (
                <FilterChip
                  key={tipo}
                  active={activeTipo === tipo}
                  onClick={() => setActiveTipo(tipo)}
                >
                  {canonicalTipoLabel(tipo)}
                </FilterChip>
              ))}
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filteredAmbienti.map((a) => {
              const tipo = normalizeAmbienteTipo(a.tipo);
              const ambienteRischi = rischi.filter(
                (r) => r.ambiente_id === a.id && r.applicabile,
              );
              const ambienteAttrezzature = attrezzature.filter(
                (e) => e.ambiente_id === a.id,
              );
              const ambientePersone = persone.filter((p) =>
                p.ambiente_ids.includes(a.id),
              );
              const preposto = a.preposto_id
                ? personaById.get(a.preposto_id)
                : null;

              const riskCounts: Record<string, number> = {};
              for (const r of ambienteRischi) {
                if (!r.livello_rischio) continue;
                riskCounts[r.livello_rischio] =
                  (riskCounts[r.livello_rischio] ?? 0) + 1;
              }

              return (
                <article
                  key={a.id}
                  className="flex flex-col gap-3 rounded-md border border-[#e5edf5] bg-white p-5 shadow-stripe-ambient"
                >
                  <header className="flex items-start justify-between gap-3">
                    <h4 className="text-[15px] font-medium leading-tight text-[#061b31]">
                      {a.nome}
                    </h4>
                    <StatusPill className="bg-[#f6f9fc] text-[#273951] border border-[#e5edf5] shrink-0">
                      {canonicalTipoLabel(tipo)}
                    </StatusPill>
                  </header>

                  {a.descrizione_attivita && (
                    <p className="line-clamp-2 text-[13px] text-[#64748d]">
                      {a.descrizione_attivita}
                    </p>
                  )}

                  <div className="tnum flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[12px] text-[#64748d]">
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5" strokeWidth={1.75} />
                      {a.superficie_mq != null
                        ? `${NUM_FORMAT.format(a.superficie_mq)} mq`
                        : "—"}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Users className="h-3.5 w-3.5" strokeWidth={1.75} />
                      {NUM_FORMAT.format(ambientePersone.length)} persone
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Wrench className="h-3.5 w-3.5" strokeWidth={1.75} />
                      {NUM_FORMAT.format(ambienteAttrezzature.length)} attrezz.
                    </span>
                    {preposto && (
                      <span className="inline-flex items-center gap-1">
                        <User className="h-3.5 w-3.5" strokeWidth={1.75} />
                        {preposto.nominativo}
                      </span>
                    )}
                  </div>

                  <div className="mt-auto flex flex-wrap items-center gap-1.5 border-t border-[#f0f4f9] pt-3">
                    {ambienteRischi.length === 0 ? (
                      <span className="inline-flex items-center gap-1 text-[12px] text-[#64748d]">
                        <Layers className="h-3.5 w-3.5" strokeWidth={1.75} />
                        Nessun rischio valutato
                      </span>
                    ) : (
                      <>
                        <ShieldAlert
                          className="h-3.5 w-3.5 text-[#64748d]"
                          strokeWidth={1.75}
                        />
                        {RISK_LEVELS.map((level) => {
                          const count = riskCounts[level] ?? 0;
                          if (count === 0) return null;
                          return (
                            <StatusPill
                              key={level}
                              className={riskLevelStyles[level]}
                            >
                              <span className="tnum">
                                {level} {NUM_FORMAT.format(count)}
                              </span>
                            </StatusPill>
                          );
                        })}
                      </>
                    )}
                  </div>
                </article>
              );
            })}
          </div>

          {filteredAmbienti.length === 0 && (
            <p className="px-2 py-6 text-center text-[13px] text-[#64748d]">
              Nessun ambiente per il filtro selezionato.
            </p>
          )}
        </div>
      )}
    </Panel>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  const base =
    "inline-flex h-7 items-center rounded-md px-3 text-[12px] font-medium transition-colors";
  const styles = active
    ? "bg-primary text-white"
    : "border border-[#e5edf5] text-[#273951] hover:bg-[#f6f9fc]";
  return (
    <button type="button" onClick={onClick} className={`${base} ${styles}`}>
      {children}
    </button>
  );
}
