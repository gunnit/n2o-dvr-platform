"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ClipboardList,
  Building2,
  MapPin,
  Calendar,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Azienda } from "@/types";
import { apiCall } from "@/lib/api-client";

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

const statusIcons: Record<string, string> = {
  draft: "",
  in_progress: "ring-1 ring-primary/15",
  completed: "ring-1 ring-[rgba(21,190,83,0.3)]",
};

export default function SurveyPage() {
  const [aziende, setAziende] = useState<Azienda[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiCall<Azienda[]>("/api/v1/aziende")
      .then(setAziende)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="type-h1">Sopralluogo</h1>
        <p className="type-body mt-2">
          Seleziona un&apos;azienda per avviare o continuare il sopralluogo digitale
        </p>
      </div>

      {loading ? (
        <p className="type-body">Caricamento...</p>
      ) : aziende.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-14">
            <ClipboardList className="mb-4 h-10 w-10 text-[#c2c6d2]" strokeWidth={1.5} />
            <p className="type-body max-w-md text-center">
              Nessuna azienda registrata. Aggiungi un&apos;azienda dalla pagina Aziende per iniziare.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {aziende.map((azienda) => (
            <Link key={azienda.id} href={`/survey/${azienda.id}`}>
              <Card
                className={`transition-[box-shadow,transform] duration-200 hover:shadow-stripe-elevated hover:-translate-y-0.5 ${statusIcons[azienda.survey_status]}`}
              >
                <CardHeader>
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 min-w-0">
                      <Building2 className="h-4 w-4 shrink-0 text-[#64748d]" strokeWidth={1.75} />
                      <CardTitle className="truncate">
                        {azienda.ragione_sociale}
                      </CardTitle>
                    </div>
                    <Badge className={statusColors[azienda.survey_status]}>
                      {statusLabels[azienda.survey_status]}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex items-center gap-1.5 text-[13px] text-[#64748d]">
                    <MapPin className="h-3.5 w-3.5" strokeWidth={1.75} />
                    {azienda.sede_operativa_citta ||
                      azienda.sede_legale_citta ||
                      "Sede non specificata"}
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider font-medium text-[#64748d]">
                    <Calendar className="h-3 w-3" strokeWidth={1.75} />
                    <span className="tnum normal-case tracking-normal">
                      {new Date(azienda.updated_at).toLocaleDateString("it-IT", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                  {azienda.codice_ateco && (
                    <p className="text-[11px] uppercase tracking-wider font-medium text-[#64748d]">
                      ATECO · <span className="tnum normal-case tracking-normal">{azienda.codice_ateco}</span>
                    </p>
                  )}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
