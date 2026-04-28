"use client";

import { useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Layers,
  ListChecks,
  Search,
  Wrench,
  XCircle,
} from "lucide-react";
import {
  EmptyState,
  Panel,
  PanelHeader,
  StatTile,
  StatusPill,
} from "@/components/aziende/tabs/_shared";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  canonicalTipoLabel,
  normalizeAmbienteTipo,
} from "@/lib/ambiente-tipo";
import type { Ambiente, Attrezzatura } from "@/types";

interface AttrezzatureTabProps {
  attrezzature: Attrezzatura[];
  ambienti: Ambiente[];
}

const NUM_FORMAT = new Intl.NumberFormat("it-IT");
const UNASSIGNED_KEY = "__unassigned__";

type ViewMode = "grouped" | "list";

function ConformitaCell({ ok }: { ok: boolean }) {
  return ok ? (
    <span className="inline-flex items-center gap-1 text-[13px] font-medium text-[#108c3d]">
      <CheckCircle2 className="h-3.5 w-3.5" />
      Sì
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-[13px] font-medium text-[#b51648]">
      <XCircle className="h-3.5 w-3.5" />
      No
    </span>
  );
}

export default function AttrezzatureTab({
  attrezzature,
  ambienti,
}: AttrezzatureTabProps) {
  const [query, setQuery] = useState<string>("");
  const [viewMode, setViewMode] = useState<ViewMode>("grouped");

  const ambienteById = useMemo(() => {
    const map = new Map<string, Ambiente>();
    for (const a of ambienti) map.set(a.id, a);
    return map;
  }, [ambienti]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return attrezzature;
    return attrezzature.filter((e) =>
      (e.descrizione ?? "").toLowerCase().includes(q),
    );
  }, [attrezzature, query]);

  const total = attrezzature.length;
  const ceCount = useMemo(
    () => attrezzature.filter((e) => e.marcatura_ce).length,
    [attrezzature],
  );
  const verificheCount = useMemo(
    () => attrezzature.filter((e) => e.verifiche_periodiche).length,
    [attrezzature],
  );
  const senzaCe = total - ceCount;
  const senzaVerifiche = total - verificheCount;

  const ambientiCovered = useMemo(() => {
    const set = new Set<string>();
    for (const e of attrezzature) {
      if (ambienteById.has(e.ambiente_id)) set.add(e.ambiente_id);
    }
    return set.size;
  }, [attrezzature, ambienteById]);

  const grouped = useMemo(() => {
    const groups = new Map<string, Attrezzatura[]>();
    for (const e of filtered) {
      const key = ambienteById.has(e.ambiente_id)
        ? e.ambiente_id
        : UNASSIGNED_KEY;
      const list = groups.get(key);
      if (list) list.push(e);
      else groups.set(key, [e]);
    }
    const ordered = Array.from(groups.entries())
      .map(([key, items]) => ({
        key,
        ambiente: key === UNASSIGNED_KEY ? null : (ambienteById.get(key) ?? null),
        items,
      }))
      .sort((a, b) => {
        if (a.key === UNASSIGNED_KEY) return 1;
        if (b.key === UNASSIGNED_KEY) return -1;
        return (a.ambiente?.nome ?? "").localeCompare(b.ambiente?.nome ?? "");
      });
    return ordered;
  }, [filtered, ambienteById]);

  const cePct = total === 0 ? null : Math.round((ceCount / total) * 100);
  const verifichePct =
    total === 0 ? null : Math.round((verificheCount / total) * 100);

  const tonePercentage = (pct: number | null): "default" | "ok" | "warn" | "danger" => {
    if (pct === null) return "default";
    if (pct === 100) return "ok";
    if (pct >= 80) return "warn";
    return "danger";
  };

  const headerSubtitle =
    total === 0
      ? "Nessuna attrezzatura"
      : `${NUM_FORMAT.format(total)} attrezzature · ${NUM_FORMAT.format(ambientiCovered)} ambienti coperti`;

  const hasNonConformi = senzaCe > 0 || senzaVerifiche > 0;

  return (
    <Panel accent="slate">
      <PanelHeader
        icon={Wrench}
        title="Attrezzature"
        subtitle={headerSubtitle}
        accent="slate"
      />

      {total === 0 ? (
        <EmptyState
          icon={Wrench}
          title="Nessuna attrezzatura registrata"
          body="Avvia il sopralluogo per aggiungere le attrezzature."
        />
      ) : (
        <div className="flex flex-col gap-5 p-6">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="Totale" value={NUM_FORMAT.format(total)} />
            <StatTile
              label="Marcatura CE"
              value={cePct === null ? "—" : `${cePct}%`}
              sublabel={`${NUM_FORMAT.format(ceCount)} / ${NUM_FORMAT.format(total)} conformi`}
              tone={tonePercentage(cePct)}
            />
            <StatTile
              label="Verifiche periodiche"
              value={verifichePct === null ? "—" : `${verifichePct}%`}
              sublabel={`${NUM_FORMAT.format(verificheCount)} / ${NUM_FORMAT.format(total)} conformi`}
              tone={tonePercentage(verifichePct)}
            />
            <StatTile
              label="Senza CE"
              value={NUM_FORMAT.format(senzaCe)}
              sublabel={senzaCe > 0 ? "Da regolarizzare" : "Tutte conformi"}
              tone={senzaCe > 0 ? "danger" : "ok"}
            />
          </div>

          {hasNonConformi && (
            <div
              className="flex items-start gap-2 rounded-md border border-[rgba(234,34,97,0.25)] bg-[rgba(234,34,97,0.04)] px-3 py-2.5 text-[13px] text-[#b51648]"
              role="status"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>
                {senzaCe > 0 && (
                  <>
                    <span className="tnum font-medium">
                      {NUM_FORMAT.format(senzaCe)}
                    </span>{" "}
                    {senzaCe === 1
                      ? "attrezzatura senza marcatura CE"
                      : "attrezzature senza marcatura CE"}
                  </>
                )}
                {senzaCe > 0 && senzaVerifiche > 0 && ", "}
                {senzaVerifiche > 0 && (
                  <>
                    <span className="tnum font-medium">
                      {NUM_FORMAT.format(senzaVerifiche)}
                    </span>{" "}
                    senza verifiche periodiche aggiornate
                  </>
                )}
                . Verificare conformità ai sensi del D.Lgs. 81/2008.
              </span>
            </div>
          )}

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1 sm:max-w-sm">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#64748d]"
                strokeWidth={1.75}
              />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Cerca per descrizione…"
                className="h-9 w-full rounded-md border border-[#e5edf5] bg-white pl-8 pr-3 text-[13px] text-[#061b31] placeholder:text-[#94a3b8] focus:border-primary focus:outline-none focus:ring-2 focus:ring-[rgba(0,61,116,0.15)]"
              />
            </div>

            <div className="inline-flex items-center rounded-md border border-[#e5edf5] bg-white p-0.5">
              <ViewToggle
                active={viewMode === "grouped"}
                onClick={() => setViewMode("grouped")}
                icon={Layers}
                label="Per ambiente"
              />
              <ViewToggle
                active={viewMode === "list"}
                onClick={() => setViewMode("list")}
                icon={ListChecks}
                label="Lista"
              />
            </div>
          </div>

          {filtered.length === 0 ? (
            <p className="px-2 py-6 text-center text-[13px] text-[#64748d]">
              Nessuna attrezzatura corrisponde alla ricerca.
            </p>
          ) : viewMode === "grouped" ? (
            <div className="flex flex-col gap-5">
              {grouped.map((group) => {
                const tipo = group.ambiente
                  ? normalizeAmbienteTipo(group.ambiente.tipo)
                  : null;
                const groupLabel = group.ambiente
                  ? group.ambiente.nome
                  : "Altre / Non assegnate";
                return (
                  <section
                    key={group.key}
                    className="flex flex-col gap-2"
                  >
                    <header className="flex flex-wrap items-center gap-2">
                      <h4 className="text-[14px] font-medium text-[#061b31]">
                        {groupLabel}
                      </h4>
                      {tipo && (
                        <StatusPill className="bg-[#f6f9fc] text-[#273951] border border-[#e5edf5]">
                          {canonicalTipoLabel(tipo)}
                        </StatusPill>
                      )}
                      <span className="tnum text-[12px] text-[#64748d]">
                        ({NUM_FORMAT.format(group.items.length)}{" "}
                        {group.items.length === 1
                          ? "attrezzatura"
                          : "attrezzature"}
                        )
                      </span>
                    </header>

                    <div className="overflow-hidden">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Descrizione</TableHead>
                            <TableHead className="w-32">CE</TableHead>
                            <TableHead className="w-32">Verifiche</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {group.items.map((e) => (
                            <TableRow key={e.id}>
                              <TableCell className="text-[13px] text-[#061b31]">
                                {e.descrizione}
                              </TableCell>
                              <TableCell>
                                <ConformitaCell ok={e.marcatura_ce} />
                              </TableCell>
                              <TableCell>
                                <ConformitaCell ok={e.verifiche_periodiche} />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </section>
                );
              })}
            </div>
          ) : (
            <div className="overflow-hidden rounded-md border border-[#e5edf5]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Descrizione</TableHead>
                    <TableHead>Ambiente</TableHead>
                    <TableHead className="w-28">CE</TableHead>
                    <TableHead className="w-28">Verifiche</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((e) => {
                    const ambiente = ambienteById.get(e.ambiente_id);
                    return (
                      <TableRow key={e.id}>
                        <TableCell className="text-[13px] text-[#061b31]">
                          {e.descrizione}
                        </TableCell>
                        <TableCell className="text-[13px] text-[#273951]">
                          {ambiente?.nome ?? (
                            <span className="text-[#64748d]">
                              Non assegnata
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          <ConformitaCell ok={e.marcatura_ce} />
                        </TableCell>
                        <TableCell>
                          <ConformitaCell ok={e.verifiche_periodiche} />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}

function ViewToggle({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: typeof Layers;
  label: string;
}) {
  const base =
    "inline-flex h-7 items-center gap-1.5 rounded-[5px] px-2.5 text-[12px] font-medium transition-colors";
  const styles = active
    ? "bg-primary text-white"
    : "text-[#273951] hover:bg-[#f6f9fc]";
  return (
    <button type="button" onClick={onClick} className={`${base} ${styles}`}>
      <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
      {label}
    </button>
  );
}
