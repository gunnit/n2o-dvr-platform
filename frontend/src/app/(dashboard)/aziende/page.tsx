"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Aziende</h1>
          <p className="text-muted-foreground">Gestione clienti</p>
        </div>
        <Button render={<Link href="/aziende/new" />}>
          <Plus className="mr-2 h-4 w-4" />
          Nuova Azienda
        </Button>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Caricamento...</p>
      ) : aziende.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-muted-foreground">Nessuna azienda registrata</p>
            <Button className="mt-4" render={<Link href="/aziende/new" />}>
              Aggiungi la prima azienda
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {aziende.map((azienda) => (
            <Link key={azienda.id} href={`/aziende/${azienda.id}`}>
              <Card className="transition-shadow hover:shadow-md">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{azienda.ragione_sociale}</CardTitle>
                    <Badge className={statusColors[azienda.survey_status]}>
                      {statusLabels[azienda.survey_status]}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {azienda.sede_operativa_citta || azienda.sede_legale_citta || "Sede non specificata"}
                  </p>
                  {azienda.codice_ateco && (
                    <p className="mt-1 text-xs text-muted-foreground">
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
