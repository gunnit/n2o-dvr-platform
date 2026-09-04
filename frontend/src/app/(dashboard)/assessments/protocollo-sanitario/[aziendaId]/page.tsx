"use client";

/**
 * Protocollo sanitario aziendale per mansione (segnalazione 2026-08-25).
 *
 * One card per distinct mansione of the azienda's persone. The card shows
 * the rischi specifici + DPI aggregated from the persone (read-only), lets
 * the operator record accertamenti, periodicità, correlated occupational
 * diseases and notes, and can ask the AI for a proposal to apply or
 * discard. Saved protocols feed DVR §4.3.
 *
 * Per mansione, never per person: this page never receives a name.
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Stethoscope, Users } from "lucide-react";
import { toast } from "sonner";

import { buttonVariants } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { EmptyStateCard } from "@/components/ui/empty-state";
import { useApi } from "@/hooks/use-api";
import type { Azienda } from "@/types";

import { MansioneCard } from "@/components/assessments/protocollo-sanitario/mansione-card";
import type {
  MansioniOverview,
  ProtocolloProposta,
  ProtocolloSanitario,
  ProtocolloUpsert,
} from "@/components/assessments/protocollo-sanitario/types";

export default function ProtocolloSanitarioPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;
  const { apiFetch } = useApi();

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [overview, setOverview] = useState<MansioniOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const base = `/api/v1/aziende/${aziendaId}/protocollo-sanitario/mansioni`;

  const reload = useCallback(async () => {
    const data = await apiFetch<MansioniOverview>(`${base}`);
    setOverview(data);
    return data;
  }, [apiFetch, base]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [az, ov] = await Promise.all([
          apiFetch<Azienda>(`/api/v1/aziende/${aziendaId}`),
          apiFetch<MansioniOverview>(`${base}`),
        ]);
        if (cancelled) return;
        setAzienda(az);
        setOverview(ov);
        setLoadError(null);
      } catch (err) {
        if (!cancelled)
          setLoadError(
            err instanceof Error ? err.message : "Impossibile caricare il protocollo",
          );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    if (aziendaId) load();
    return () => {
      cancelled = true;
    };
  }, [aziendaId, apiFetch, base]);

  const handleSave = useCallback(
    async (body: ProtocolloUpsert) => {
      try {
        await apiFetch<ProtocolloSanitario>(`${base}`, {
          method: "PUT",
          body: JSON.stringify(body),
        });
        toast.success(`Protocollo salvato per "${body.mansione}".`);
        await reload();
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : "Salvataggio non riuscito",
        );
        throw err;
      }
    },
    [apiFetch, base, reload],
  );

  const handleSuggest = useCallback(
    async (mansione: string) => {
      try {
        const p = await apiFetch<ProtocolloProposta>(
          `${base}/suggerisci`,
          { method: "POST", body: JSON.stringify({ mansione }) },
        );
        toast.success("Proposta AI pronta: rivedila e applicala se corretta.");
        return p;
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : "Proposta AI non disponibile",
        );
        throw err;
      }
    },
    [apiFetch, base],
  );

  const handleDelete = useCallback(
    async (protocolloId: string) => {
      try {
        await apiFetch<void>(`${base}/${protocolloId}`, {
          method: "DELETE",
        });
        toast.success("Protocollo eliminato.");
        await reload();
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : "Eliminazione non riuscita",
        );
        throw err;
      }
    },
    [apiFetch, base, reload],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="type-h1">Protocollo sanitario aziendale</h1>
          <p className="type-body mt-2">
            {azienda ? (
              <>
                <span className="font-medium text-[#273951]">
                  {azienda.ragione_sociale}
                </span>
                {" · "}
              </>
            ) : null}
            Accertamenti, periodicità e malattie professionali correlate per
            ogni mansione (art. 41 D.Lgs. 81/2008 · D.M. 9 aprile 2008).
          </p>
        </div>
        <Link
          href={`/aziende/${aziendaId}`}
          className={buttonVariants({ variant: "outline", size: "sm" })}
        >
          Torna all&apos;azienda
        </Link>
      </div>

      <Callout tone="info" dense>
        Il protocollo è definito per <strong>mansione</strong>, mai per
        persona: i rischi e i DPI mostrati sono l&apos;unione dei flag delle
        persone che svolgono quel ruolo. &ldquo;Compila con AI&rdquo; propone
        accertamenti, periodicità e malattie dalla tabella di riferimento; il
        Medico Competente resta il titolare del protocollo.
      </Callout>

      {loadError && (
        <Callout tone="danger" title="Errore di caricamento">
          {loadError}
        </Callout>
      )}

      {loading ? (
        <p className="text-sm text-[#64748d]">Caricamento mansioni…</p>
      ) : overview && overview.items.length === 0 ? (
        <EmptyStateCard
          icon={Users}
          title="Nessuna mansione censita"
          body="Il protocollo si costruisce sulle mansioni delle persone dell'azienda. Aggiungi le persone con la loro mansione e i flag di rischi specifici e DPI, poi torna qui."
          action={
            <Link
              href={`/aziende/${aziendaId}`}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              Vai all&apos;azienda
            </Link>
          }
        />
      ) : overview ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Stethoscope className="h-4 w-4 text-[#64748d]" strokeWidth={1.75} />
            <span className="tnum text-[12px] text-[#64748d]">
              {overview.items.length} mansion
              {overview.items.length === 1 ? "e" : "i"} ·{" "}
              {overview.items.filter((i) => i.protocollo).length} con protocollo
              salvato
            </span>
          </div>
          {overview.items.map((item) => (
            <MansioneCard
              // Remount on save/delete so the card re-derives its state
              // from the server row rather than from stale local edits.
              key={`${item.mansione}:${item.protocollo?.updated_at ?? "new"}`}
              item={item}
              periodicitaOptions={overview.periodicita_options}
              onSave={handleSave}
              onSuggest={handleSuggest}
              onDelete={handleDelete}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
