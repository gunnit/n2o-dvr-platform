"use client";

/**
 * POS info cards — Soggetti di riferimento, Modalità organizzative,
 * Organizzazione logistica, and an Anagrafica/Dipendenti read-only summary.
 *
 * Driven by Luca Marchetti's 2026-05-25 annotated POS template ("Elementi
 * fondamentali dei POS" email). The yellow-highlighted paragraphs map onto
 * three editable cards (this file) and one read-only summary that links
 * back to the Azienda + Persone pages for the operator to update.
 *
 * Save strategy mirrors the DPI matrix on the parent page: optimistic
 * setState + debounced PUT to /api/v1/aziende/{id}/pos/{pos_id}. We send
 * only the fields this card owns so other surfaces (DPI matrix, phase
 * builder) don't get clobbered by a stale-copy round-trip.
 */

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ExternalLink } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import type { Azienda, Persona } from "@/types";

/** Subset of `Pos` carrying the editable fields these cards own. */
export interface PosInfoFields {
  // Soggetti di riferimento
  committente: string | null;
  progettista_responsabile: string | null;
  direttore_lavori: string | null;
  direttore_operativo_edilizia: string | null;
  direttore_operativo_impianti: string | null;
  responsabile_lavori: string | null;
  coordinatore_progettazione: string | null;
  coordinatore_sicurezza: string | null; // CSE
  // Modalità organizzative
  orario_lavoro_cantiere: string | null;
  turni_descrizione: string | null;
  riunioni_coordinamento: string | null;
  // Organizzazione logistica
  monoblocchi_installati: boolean;
  monoblocchi_dettagli: string | null;
  modalita_pasti: string | null;
}

interface PosInfoCardsProps {
  aziendaId: string;
  posId: string;
  initial: PosInfoFields;
}

const EMPTY_PERSONE: Persona[] = [];

const SOGGETTI_FIELDS: Array<{
  key: keyof PosInfoFields;
  label: string;
  hint?: string;
}> = [
  { key: "committente", label: "Committente" },
  { key: "progettista_responsabile", label: "Progettista responsabile" },
  { key: "direttore_lavori", label: "Direttore dei lavori" },
  {
    key: "direttore_operativo_edilizia",
    label: "Direttore operativo edilizia / strutture",
  },
  {
    key: "direttore_operativo_impianti",
    label: "Direttore operativo impianti",
  },
  { key: "responsabile_lavori", label: "Responsabile dei lavori" },
  {
    key: "coordinatore_progettazione",
    label: "Coordinatore sicurezza progettazione (CSP)",
  },
  {
    key: "coordinatore_sicurezza",
    label: "Coordinatore sicurezza esecuzione (CSE)",
  },
];

/** Anagrafica + dipendenti read-only summary card. */
export function PosAnagraficaSummary({
  aziendaId,
}: {
  aziendaId: string;
}) {
  const { apiFetch, isAuthenticated } = useApi();
  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [persone, setPersone] = useState<Persona[]>(EMPTY_PERSONE);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const [a, p] = await Promise.all([
          apiFetch<Azienda>(`/api/v1/aziende/${aziendaId}`),
          apiFetch<Persona[]>(`/api/v1/aziende/${aziendaId}/persone`),
        ]);
        if (cancelled) return;
        setAzienda(a);
        setPersone(p);
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [aziendaId, apiFetch, isAuthenticated]);

  const sede = [
    azienda?.sede_legale_via,
    azienda?.sede_legale_citta,
    azienda?.cap_legale,
    azienda?.provincia_legale,
  ]
    .filter(Boolean)
    .join(", ");

  const personeOperative = persone.filter(
    (p) =>
      p.ruolo_primo_soccorso ||
      p.ruolo_antincendio ||
      p.ruolo_preposto ||
      p.mansione,
  );

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle>Anagrafica e dipendenti (riepilogo)</CardTitle>
          <CardDescription>
            Dati ripresi dall&apos;anagrafica azienda e dalle persone. Modificali
            dalle rispettive schermate; verranno stampati così come sono nel
            POS.
          </CardDescription>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Link
            href={`/aziende/${aziendaId}`}
            className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
          >
            Modifica azienda <ExternalLink className="h-3 w-3" />
          </Link>
          <Link
            href={`/aziende/${aziendaId}?tab=persone`}
            className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
          >
            Modifica persone <ExternalLink className="h-3 w-3" />
          </Link>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {!loaded ? (
          <p className="text-sm text-muted-foreground">Caricamento…</p>
        ) : !azienda ? (
          <p className="text-sm text-muted-foreground">
            Anagrafica non disponibile.
          </p>
        ) : (
          <div className="grid gap-2 text-sm sm:grid-cols-2">
            <SummaryRow label="Impresa" value={azienda.ragione_sociale} />
            <SummaryRow label="Sede legale" value={sede || "—"} />
            <SummaryRow label="Telefono" value={azienda.telefono ?? "—"} />
            <SummaryRow label="PEC" value={azienda.pec ?? "—"} />
            <SummaryRow
              label="Datore di lavoro"
              value={
                roleHolders(persone, (p) => p.ruolo_datore_lavoro) || "—"
              }
            />
            <SummaryRow
              label="RSPP"
              value={
                roleHolders(persone, (p) => p.ruolo_rspp, true) || "—"
              }
            />
            <SummaryRow
              label="Medico competente"
              value={
                roleHolders(
                  persone,
                  (p) => p.ruolo_medico_competente,
                  true,
                ) || "—"
              }
            />
            <SummaryRow
              label="RLS"
              value={roleHolders(persone, (p) => p.ruolo_rls) || "—"}
            />
          </div>
        )}

        <div>
          <p className="mb-2 text-sm font-medium text-[#273951]">
            Dipendenti operativi
          </p>
          {personeOperative.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nessun dipendente con mansione o ruolo operativo registrato.
            </p>
          ) : (
            <div className="overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nominativo</TableHead>
                    <TableHead>Mansione</TableHead>
                    <TableHead className="text-center">Primo Soccorso</TableHead>
                    <TableHead className="text-center">Antincendio</TableHead>
                    <TableHead className="text-center">Preposto</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {personeOperative.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="font-medium">
                        {p.nominativo}
                      </TableCell>
                      <TableCell>{p.mansione ?? "—"}</TableCell>
                      <TableCell className="text-center">
                        {p.ruolo_primo_soccorso ? (
                          <Badge variant="secondary">SÌ</Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            —
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        {p.ruolo_antincendio ? (
                          <Badge variant="secondary">SÌ</Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            —
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        {p.ruolo_preposto ? (
                          <Badge variant="secondary">SÌ</Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            —
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <span className="min-w-[10rem] text-[#64748d]">{label}</span>
      <span className="text-[#061b31]">{value}</span>
    </div>
  );
}

function roleHolders(
  persone: Persona[],
  predicate: (p: Persona) => boolean,
  withEsternoTag = false,
): string {
  const matches = persone.filter(predicate);
  if (!matches.length) return "";
  return matches
    .map((p) => {
      if (withEsternoTag && p.is_esterno) return `${p.nominativo} (esterno)`;
      return p.nominativo;
    })
    .join(", ");
}

/** Editable cards (soggetti / modalità / logistica). */
export function PosInfoEditor({
  aziendaId,
  posId,
  initial,
}: PosInfoCardsProps) {
  const { apiFetch } = useApi();
  const [values, setValues] = useState<PosInfoFields>(initial);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Re-sync when the parent reloads (e.g. after PhaseBuilder save returns
  // a fresh row).
  useEffect(() => {
    setValues(initial);
  }, [initial]);

  const persist = useCallback(
    async (next: PosInfoFields) => {
      try {
        await apiFetch(`/api/v1/aziende/${aziendaId}/pos/${posId}`, {
          method: "PUT",
          body: JSON.stringify(next),
        });
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Salvataggio non riuscito.";
        toast.error(msg);
      }
    },
    [apiFetch, aziendaId, posId],
  );

  const update = useCallback(
    <K extends keyof PosInfoFields>(key: K, value: PosInfoFields[K]) => {
      setValues((prev) => {
        const next = { ...prev, [key]: value };
        if (saveTimer.current) clearTimeout(saveTimer.current);
        saveTimer.current = setTimeout(() => void persist(next), 600);
        return next;
      });
    },
    [persist],
  );

  return (
    <div className="flex flex-col gap-6">
      {/* Card: Soggetti di riferimento */}
      <Card>
        <CardHeader>
          <CardTitle>Soggetti di riferimento</CardTitle>
          <CardDescription>
            Indica i soggetti previsti dall&apos;Allegato XV punto 3.2.1 b
            (Committente, progettista, direttore lavori, CSP, CSE …). I
            campi vuoti vengono omessi dal POS stampato.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            {SOGGETTI_FIELDS.map((f) => (
              <div key={f.key} className="space-y-1">
                <Label htmlFor={`pos-${String(f.key)}`}>{f.label}</Label>
                <Input
                  id={`pos-${String(f.key)}`}
                  value={(values[f.key] as string | null) ?? ""}
                  onChange={(e) =>
                    update(
                      f.key,
                      (e.target.value || null) as PosInfoFields[typeof f.key],
                    )
                  }
                />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Card: Modalità organizzative */}
      <Card>
        <CardHeader>
          <CardTitle>Modalità organizzative</CardTitle>
          <CardDescription>
            Orario di lavoro effettivo del cantiere, eventuali turni e
            descrizione delle riunioni di coordinamento previste.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="pos-orario">Orario di lavoro</Label>
            <Textarea
              id="pos-orario"
              placeholder="Es. 07:00–12:00 / 13:00–18:00, dal lunedì al venerdì"
              value={values.orario_lavoro_cantiere ?? ""}
              onChange={(e) =>
                update("orario_lavoro_cantiere", e.target.value || null)
              }
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="pos-turni">Turni</Label>
            <Textarea
              id="pos-turni"
              placeholder="Eventuali turni saranno concordati con la D.L. e con il CSE."
              value={values.turni_descrizione ?? ""}
              onChange={(e) =>
                update("turni_descrizione", e.target.value || null)
              }
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="pos-riunioni">Riunioni di coordinamento</Label>
            <Textarea
              id="pos-riunioni"
              placeholder="Periodiche riunioni con informazione e formazione ai lavoratori; presenza del CSE in occasione di inizio lavori, primo ingresso lavoratori, ecc."
              value={values.riunioni_coordinamento ?? ""}
              onChange={(e) =>
                update("riunioni_coordinamento", e.target.value || null)
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* Card: Organizzazione logistica */}
      <Card>
        <CardHeader>
          <CardTitle>Organizzazione logistica</CardTitle>
          <CardDescription>
            Servizi logistici di cantiere: monoblocchi, modalità di
            consumazione dei pasti.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={values.monoblocchi_installati}
                onChange={(e) =>
                  update("monoblocchi_installati", e.target.checked)
                }
              />
              <span>Saranno installati monoblocchi in cantiere</span>
            </label>
            {values.monoblocchi_installati && (
              <Textarea
                aria-label="Dettagli monoblocchi"
                placeholder="Numero e tipologia (spogliatoi, ufficio, servizi igienici, refettorio…)"
                value={values.monoblocchi_dettagli ?? ""}
                onChange={(e) =>
                  update("monoblocchi_dettagli", e.target.value || null)
                }
              />
            )}
            {!values.monoblocchi_installati && (
              <p className="text-xs text-muted-foreground">
                Nel POS sarà stampato: &quot;Non saranno installati monoblocchi
                in cantiere.&quot;
              </p>
            )}
          </div>
          <div className="space-y-1">
            <Label htmlFor="pos-pasti">Modalità consumazione pasti</Label>
            <Textarea
              id="pos-pasti"
              placeholder="Es. le maestranze si recheranno in un apposito esercizio commerciale esterno al cantiere"
              value={values.modalita_pasti ?? ""}
              onChange={(e) =>
                update("modalita_pasti", e.target.value || null)
              }
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
