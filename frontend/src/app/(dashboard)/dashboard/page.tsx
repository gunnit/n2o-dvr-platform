"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Building2, FileCheck, FileText, Search, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Azienda } from "@/types";
import { useApi } from "@/hooks/use-api";

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  in_progress: "bg-yellow-100 text-yellow-700",
  completed: "bg-green-100 text-green-700",
};

const statusLabels: Record<string, string> = {
  draft: "Bozza",
  in_progress: "In corso",
  completed: "Completato",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = d.getFullYear();
  return `${day}/${month}/${year}`;
}

export default function DashboardPage() {
  const { apiFetch, isAuthenticated } = useApi();
  const [aziende, setAziende] = useState<Azienda[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!isAuthenticated) return;
    apiFetch<Azienda[]>("/api/v1/aziende")
      .then(setAziende)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [apiFetch, isAuthenticated]);

  const stats = useMemo(() => {
    const total = aziende.length;
    const inProgress = aziende.filter(
      (a) => a.survey_status === "in_progress"
    ).length;
    const completed = aziende.filter(
      (a) => a.survey_status === "completed"
    ).length;
    const drafts = aziende.filter(
      (a) => a.survey_status === "draft"
    ).length;

    return [
      {
        name: "Clienti attivi",
        value: total,
        icon: Building2,
        description: "Aziende registrate",
        accent: "text-blue-600",
      },
      {
        name: "Sopralluoghi in corso",
        value: inProgress,
        icon: Users,
        description: "In fase di compilazione",
        accent: "text-yellow-600",
      },
      {
        name: "Sopralluoghi completati",
        value: completed,
        icon: FileCheck,
        description: "Pronti per generazione",
        accent: "text-green-600",
      },
      {
        name: "Bozze",
        value: drafts,
        icon: FileText,
        description: "Da completare",
        accent: "text-gray-500",
      },
    ];
  }, [aziende]);

  const sortedAndFiltered = useMemo(() => {
    const sorted = [...aziende].sort(
      (a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );

    if (search.length < 2) return sorted;

    const q = search.toLowerCase();
    return sorted.filter(
      (a) =>
        a.ragione_sociale.toLowerCase().includes(q) ||
        (a.attivita && a.attivita.toLowerCase().includes(q))
    );
  }, [aziende, search]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Panoramica dell&apos;attivit&agrave;
        </p>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Caricamento...</p>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat) => (
              <Card key={stat.name}>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {stat.name}
                  </CardTitle>
                  <stat.icon className={`h-4 w-4 ${stat.accent}`} />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stat.value}</div>
                  <p className="text-xs text-muted-foreground">
                    {stat.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Aziende Clienti</CardTitle>
              </div>
              <div className="relative mt-2">
                <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Cerca per ragione sociale, attivita..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-8"
                />
              </div>
            </CardHeader>
            <CardContent>
              {sortedAndFiltered.length === 0 ? (
                <p className="py-6 text-center text-muted-foreground">
                  {aziende.length === 0
                    ? "Nessuna azienda registrata"
                    : "Nessun risultato trovato"}
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Ragione Sociale</TableHead>
                      <TableHead>Attivita</TableHead>
                      <TableHead>Citta</TableHead>
                      <TableHead>Stato</TableHead>
                      <TableHead>Ultimo Aggiornamento</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedAndFiltered.map((azienda) => (
                      <TableRow key={azienda.id}>
                        <TableCell>
                          <Link
                            href={`/aziende/${azienda.id}`}
                            className="font-medium text-primary hover:underline"
                          >
                            {azienda.ragione_sociale}
                          </Link>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {azienda.attivita || "-"}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {azienda.sede_operativa_citta ||
                            azienda.sede_legale_citta ||
                            "-"}
                        </TableCell>
                        <TableCell>
                          <Badge
                            className={statusColors[azienda.survey_status]}
                          >
                            {statusLabels[azienda.survey_status]}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {formatDate(azienda.updated_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
