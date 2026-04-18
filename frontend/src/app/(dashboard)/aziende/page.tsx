"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { Building2, MapPin, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Azienda } from "@/types";
import { useApi } from "@/hooks/use-api";

const statusColors: Record<string, string> = {
  draft: "bg-[#f6f9fc] text-[#273951] border border-[#e5edf5]",
  in_progress:
    "bg-[rgba(0,61,116,0.08)] text-primary border border-[rgba(0,61,116,0.2)]",
  completed:
    "bg-[rgba(21,190,83,0.2)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
};

const statusLabels: Record<string, string> = {
  draft: "Bozza",
  in_progress: "In corso",
  completed: "Completato",
};

export default function AziendePage() {
  const { apiFetch, isAuthenticated } = useApi();
  const { data: session } = useSession();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const role = (session?.user as any)?.role as string | undefined;
  const isAdmin = role === "admin";
  const [aziende, setAziende] = useState<Azienda[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) return;
    apiFetch<Azienda[]>("/api/v1/aziende")
      .then(setAziende)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [apiFetch, isAuthenticated]);

  return (
    <div className="space-y-10">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="type-h1">Aziende</h1>
          <p className="type-body mt-2">Gestione clienti</p>
        </div>
        {isAdmin && (
          <Link
            href="/aziende/new"
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
          >
            <Plus className="h-4 w-4" strokeWidth={2} />
            Nuova Azienda
          </Link>
        )}
      </div>

      {loading ? (
        <p className="type-body">Caricamento...</p>
      ) : aziende.length === 0 ? (
        <div className="rounded-md border border-[#e5edf5] bg-white p-14 text-center shadow-stripe-ambient">
          <Building2 className="mx-auto mb-4 h-10 w-10 text-[#c2c6d2]" strokeWidth={1.5} />
          <p className="type-body">Nessuna azienda registrata</p>
          {isAdmin && (
            <Link
              href="/aziende/new"
              className="mt-5 inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
            >
              <Plus className="h-4 w-4" strokeWidth={2} />
              Aggiungi la prima azienda
            </Link>
          )}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {aziende.map((azienda) => (
            <Link
              key={azienda.id}
              href={`/aziende/${azienda.id}`}
              className="group rounded-md border border-[#e5edf5] bg-white p-5 shadow-stripe-ambient transition-[box-shadow,transform] duration-200 hover:shadow-stripe-elevated hover:-translate-y-0.5"
            >
              <div className="mb-4 flex items-start justify-between gap-3">
                <h3 className="font-heading text-[16px] font-medium leading-[1.25] tracking-[-0.01em] text-[#061b31]">
                  {azienda.ragione_sociale}
                </h3>
                <Badge className={statusColors[azienda.survey_status]}>
                  {statusLabels[azienda.survey_status]}
                </Badge>
              </div>
              <div className="flex items-center gap-1.5 text-[13px] text-[#64748d]">
                <MapPin className="h-3.5 w-3.5" strokeWidth={1.75} />
                {azienda.sede_operativa_citta ||
                  azienda.sede_legale_citta ||
                  "Sede non specificata"}
              </div>
              {azienda.codice_ateco && (
                <p className="mt-1.5 text-[11px] uppercase tracking-wider font-medium text-[#64748d]">
                  ATECO · <span className="tnum normal-case tracking-normal">{azienda.codice_ateco}</span>
                </p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
