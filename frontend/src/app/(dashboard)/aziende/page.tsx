"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { Building2, MapPin, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Azienda } from "@/types";
import { useApi } from "@/hooks/use-api";

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  in_progress: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
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
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-3xl font-bold text-on-surface">
            Aziende
          </h1>
          <p className="mt-1 text-sm text-on-surface-variant">Gestione clienti</p>
        </div>
        {isAdmin && (
          <Link
            href="/aziende/new"
            className="flex items-center gap-2 rounded-lg bg-primary-container px-5 py-2.5 text-sm font-bold text-white shadow-lg transition-all hover:-translate-y-0.5 hover:shadow-primary-container/30"
          >
            <Plus className="h-4 w-4" strokeWidth={2.5} />
            Nuova Azienda
          </Link>
        )}
      </div>

      {loading ? (
        <p className="text-on-surface-variant">Caricamento...</p>
      ) : aziende.length === 0 ? (
        <div className="rounded-xl bg-white p-12 text-center ambient-shadow">
          <Building2 className="mx-auto mb-3 h-10 w-10 text-on-surface-variant opacity-40" />
          <p className="text-on-surface-variant">Nessuna azienda registrata</p>
          {isAdmin && (
            <Link
              href="/aziende/new"
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary-container px-5 py-2.5 text-sm font-bold text-white shadow-lg hover:-translate-y-0.5 transition-all"
            >
              <Plus className="h-4 w-4" strokeWidth={2.5} />
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
              className="group rounded-xl bg-white p-5 ambient-shadow transition-all hover:-translate-y-0.5 hover:shadow-lg"
            >
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-heading text-base font-bold text-on-surface">
                  {azienda.ragione_sociale}
                </h3>
                <Badge className={statusColors[azienda.survey_status]}>
                  {statusLabels[azienda.survey_status]}
                </Badge>
              </div>
              <div className="flex items-center gap-1.5 text-sm text-on-surface-variant">
                <MapPin className="h-3.5 w-3.5" strokeWidth={2} />
                {azienda.sede_operativa_citta ||
                  azienda.sede_legale_citta ||
                  "Sede non specificata"}
              </div>
              {azienda.codice_ateco && (
                <p className="mt-1 text-xs text-on-surface-variant">
                  ATECO: {azienda.codice_ateco}
                </p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
