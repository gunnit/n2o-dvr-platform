"use client";

import { useMemo, useState } from "react";
import { Users, Search } from "lucide-react";

import {
  EmptyState,
  Panel,
  PanelHeader,
  StatTile,
  StatusPill,
} from "@/components/aziende/tabs/_shared";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  Ambiente,
  AttrezzaturaSpecialeCode,
  Persona,
} from "@/types";

interface PersoneTabProps {
  persone: Persona[];
  ambienti: Ambiente[];
}

type RoleKey =
  | "datore_lavoro"
  | "rspp"
  | "rls"
  | "medico_competente"
  | "preposto"
  | "primo_soccorso"
  | "antincendio";

const ROLE_DEFS: { key: RoleKey; label: string; field: keyof Persona }[] = [
  { key: "datore_lavoro", label: "DdL", field: "ruolo_datore_lavoro" },
  { key: "rspp", label: "RSPP", field: "ruolo_rspp" },
  { key: "rls", label: "RLS", field: "ruolo_rls" },
  { key: "medico_competente", label: "MC", field: "ruolo_medico_competente" },
  { key: "preposto", label: "Preposto", field: "ruolo_preposto" },
  { key: "primo_soccorso", label: "Primo Soccorso", field: "ruolo_primo_soccorso" },
  { key: "antincendio", label: "Antincendio", field: "ruolo_antincendio" },
];

const SPECIAL_LABEL: Record<AttrezzaturaSpecialeCode, string> = {
  lavori_in_quota: "Lavori in quota",
  carrello_elevatore: "Carrello elevatore",
  ple: "PLE",
  gru: "Gru",
  ruspa_escavatore: "Ruspa/Escavatore",
  patente_cde: "Patente C/D/E",
  adr: "ADR",
};

function maskCF(cf?: string | null): string {
  if (!cf) return "";
  if (cf.length < 8) return "••••••••";
  return `${cf.slice(0, 4)}••••••••${cf.slice(-4)}`;
}

function hasAnyRole(p: Persona): boolean {
  return ROLE_DEFS.some((r) => p[r.field] === true);
}

function PersonaRoleBadges({ persona }: { persona: Persona }) {
  const active = ROLE_DEFS.filter((r) => persona[r.field] === true);
  if (active.length === 0) return <span className="text-[#64748d]">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {active.map((r) => (
        <StatusPill
          key={r.key}
          className="bg-[rgba(0,61,116,0.06)] text-primary border border-[rgba(0,61,116,0.15)]"
        >
          {r.label}
        </StatusPill>
      ))}
    </div>
  );
}

function SpecialEquipmentBadges({
  codes,
}: {
  codes: AttrezzaturaSpecialeCode[];
}) {
  if (!codes || codes.length === 0)
    return <span className="text-[#64748d]">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {codes.map((code) => (
        <StatusPill
          key={code}
          className="bg-[#f6f9fc] text-[#273951] border border-[#e5edf5]"
        >
          {SPECIAL_LABEL[code] ?? code}
        </StatusPill>
      ))}
    </div>
  );
}

export default function PersoneTab({ persone, ambienti }: PersoneTabProps) {
  const [activeRole, setActiveRole] = useState<RoleKey | null>(null);
  const [query, setQuery] = useState<string>("");

  const ambienteNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const a of ambienti) map.set(a.id, a.nome);
    return map;
  }, [ambienti]);

  const totals = useMemo(() => {
    const totale = persone.length;
    const donne = persone.filter((p) => p.sesso === "F").length;
    const uomini = persone.filter((p) => p.sesso === "M").length;
    const sessoNonSpec = totale - donne - uomini;
    const minori = persone.filter((p) => p.fascia_eta === "15-18").length;
    const conAttrezzature = persone.filter(
      (p) => (p.attrezzature_speciali?.length ?? 0) > 0,
    ).length;
    const ruoliAssegnati = persone.filter(hasAnyRole).length;
    return {
      totale,
      donne,
      uomini,
      sessoNonSpec,
      minori,
      conAttrezzature,
      ruoliAssegnati,
    };
  }, [persone]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return persone.filter((p) => {
      if (activeRole) {
        const def = ROLE_DEFS.find((r) => r.key === activeRole);
        if (def && p[def.field] !== true) return false;
      }
      if (q) {
        const name = (p.nominativo ?? "").toLowerCase();
        const mansione = (p.mansione ?? "").toLowerCase();
        if (!name.includes(q) && !mansione.includes(q)) return false;
      }
      return true;
    });
  }, [persone, activeRole, query]);

  const subtitle = `${totals.totale} ${totals.totale === 1 ? "persona" : "persone"} · ${totals.ruoliAssegnati} ${totals.ruoliAssegnati === 1 ? "ruolo sicurezza assegnato" : "ruoli sicurezza assegnati"}`;

  if (persone.length === 0) {
    return (
      <Panel accent="emerald">
        <PanelHeader
          icon={Users}
          title="Personale"
          subtitle={subtitle}
          accent="emerald"
        />
        <EmptyState
          icon={Users}
          title="Nessuna persona registrata"
          body="Avvia il sopralluogo per aggiungere il personale."
        />
      </Panel>
    );
  }

  return (
    <Panel accent="emerald">
      <PanelHeader
        icon={Users}
        title="Personale"
        subtitle={subtitle}
        accent="emerald"
      />

      <div className="px-6 py-5 space-y-5">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatTile
            label="Totale persone"
            value={totals.totale}
            tone="navy"
          />
          <StatTile
            label="Donne"
            value={totals.donne}
            sublabel={`${totals.uomini} uomini · ${totals.sessoNonSpec} non specificato`}
          />
          <StatTile
            label="Minori (15-18)"
            value={totals.minori}
            tone={totals.minori > 0 ? "warn" : "default"}
          />
          <StatTile
            label="Attrezzature speciali"
            value={totals.conAttrezzature}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveRole(null)}
            className={
              "rounded-md px-3 py-1.5 text-[12.5px] font-medium transition-colors " +
              (activeRole === null
                ? "bg-primary text-white"
                : "border border-[#e5edf5] text-[#273951] hover:bg-[#f6f9fc]")
            }
          >
            Tutti
          </button>
          {ROLE_DEFS.map((r) => {
            const active = activeRole === r.key;
            return (
              <button
                key={r.key}
                type="button"
                onClick={() => setActiveRole(active ? null : r.key)}
                className={
                  "rounded-md px-3 py-1.5 text-[12.5px] font-medium transition-colors " +
                  (active
                    ? "bg-primary text-white"
                    : "border border-[#e5edf5] text-[#273951] hover:bg-[#f6f9fc]")
                }
              >
                {r.label}
              </button>
            );
          })}
        </div>

        <div className="relative max-w-sm">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[#64748d]"
            strokeWidth={1.75}
          />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Cerca per nominativo o mansione…"
            className="h-9 pl-8 text-[13px]"
          />
        </div>

        {filtered.length === 0 ? (
          <p className="px-1 py-6 text-center text-[13px] text-[#64748d]">
            Nessun risultato per i filtri selezionati.
          </p>
        ) : (
          <div className="rounded-md border border-[#e5edf5]">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nominativo</TableHead>
                  <TableHead>Mansione & attrezzature</TableHead>
                  <TableHead className="hidden md:table-cell">
                    Contratto
                  </TableHead>
                  <TableHead>Ambienti</TableHead>
                  <TableHead>Ruoli</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((p) => {
                  const cfMasked = maskCF(p.codice_fiscale);
                  const sexAge = [
                    p.sesso ?? null,
                    p.fascia_eta === "15-18"
                      ? "15-18"
                      : p.fascia_eta === ">18"
                        ? "18+"
                        : null,
                  ]
                    .filter(Boolean)
                    .join(" · ");
                  const ambNames = (p.ambiente_ids ?? [])
                    .map((aid) => ambienteNameById.get(aid))
                    .filter((n): n is string => Boolean(n));
                  const visibleAmb = ambNames.slice(0, 2);
                  const extraAmb = ambNames.length - visibleAmb.length;

                  return (
                    <TableRow key={p.id}>
                      <TableCell>
                        <div className="flex flex-col gap-0.5">
                          <span className="font-medium text-[#061b31]">
                            {p.nominativo}
                          </span>
                          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-[#64748d] tnum">
                            {cfMasked && <span>{cfMasked}</span>}
                            {sexAge && (
                              <>
                                {cfMasked && <span aria-hidden>·</span>}
                                <span>{sexAge}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-[#273951]">
                        <div className="flex flex-col gap-1">
                          <span>
                            {p.mansione || (
                              <span className="text-[#64748d]">—</span>
                            )}
                          </span>
                          {(p.attrezzature_speciali?.length ?? 0) > 0 && (
                            <SpecialEquipmentBadges
                              codes={p.attrezzature_speciali ?? []}
                            />
                          )}
                          {p.qualifiche && (
                            <span
                              title={p.qualifiche}
                              className="block max-w-[260px] truncate text-[11px] italic text-[#64748d]"
                            >
                              {p.qualifiche}
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="hidden text-[#273951] md:table-cell">
                        {p.tipologia_contrattuale || (
                          <span className="text-[#64748d]">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-[#273951]">
                        {ambNames.length === 0 ? (
                          <span className="text-[#64748d]">—</span>
                        ) : (
                          <span title={ambNames.join(", ")}>
                            {visibleAmb.join(", ")}
                            {extraAmb > 0 && (
                              <span className="text-[#64748d]">
                                {" "}+ {extraAmb} altri
                              </span>
                            )}
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        <PersonaRoleBadges persona={p} />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </Panel>
  );
}

