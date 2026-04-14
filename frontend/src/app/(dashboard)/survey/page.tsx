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
  draft: "bg-gray-100 text-gray-700",
  in_progress: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
};

const statusLabels: Record<string, string> = {
  draft: "Bozza",
  in_progress: "In corso",
  completed: "Completato",
};

const statusIcons: Record<string, string> = {
  draft: "border-gray-200",
  in_progress: "border-blue-200",
  completed: "border-green-200",
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Sopralluogo</h1>
        <p className="text-muted-foreground">
          Seleziona un&apos;azienda per avviare o continuare il sopralluogo digitale
        </p>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Caricamento...</p>
      ) : aziende.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <ClipboardList className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="text-muted-foreground">
              Nessuna azienda registrata. Aggiungi un&apos;azienda dalla pagina Aziende per iniziare.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {aziende.map((azienda) => (
            <Link key={azienda.id} href={`/survey/${azienda.id}`}>
              <Card
                className={`transition-shadow hover:shadow-md ${statusIcons[azienda.survey_status]}`}
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-muted-foreground" />
                      <CardTitle className="text-base">
                        {azienda.ragione_sociale}
                      </CardTitle>
                    </div>
                    <Badge className={statusColors[azienda.survey_status]}>
                      {statusLabels[azienda.survey_status]}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <MapPin className="h-3.5 w-3.5" />
                    {azienda.sede_operativa_citta ||
                      azienda.sede_legale_citta ||
                      "Sede non specificata"}
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Calendar className="h-3 w-3" />
                    Aggiornato:{" "}
                    {new Date(azienda.updated_at).toLocaleDateString("it-IT", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </div>
                  {azienda.codice_ateco && (
                    <p className="text-xs text-muted-foreground">
                      ATECO: {azienda.codice_ateco}
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
