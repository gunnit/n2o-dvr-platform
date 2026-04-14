"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Building2,
  MapPin,
  ClipboardList,
  FileText,
  ArrowLeft,
  Users,
  Warehouse,
  Wrench,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  Azienda,
  Persona,
  Ambiente,
  Attrezzatura,
  DocumentoGenerato,
  ValutazioneRischio,
} from "@/types";
import { apiCall } from "@/lib/api-client";
import { DescriptionEditor } from "@/components/ai/description-editor";
import { MeasuresPanel } from "@/components/ai/measures-panel";

const surveyStatusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  in_progress: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
};

const surveyStatusLabels: Record<string, string> = {
  draft: "Bozza",
  in_progress: "In corso",
  completed: "Completato",
};

const docStatusColors: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  generating: "bg-yellow-100 text-yellow-700",
  ready: "bg-green-100 text-green-700",
  error: "bg-red-100 text-red-700",
};

const docStatusLabels: Record<string, string> = {
  pending: "In attesa",
  generating: "In generazione",
  ready: "Pronto",
  error: "Errore",
};

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <span className="text-sm">{value || "-"}</span>
    </div>
  );
}

function PersonaRoleBadges({ persona }: { persona: Persona }) {
  const roles: { key: keyof Persona; label: string }[] = [
    { key: "ruolo_datore_lavoro", label: "DdL" },
    { key: "ruolo_rspp", label: "RSPP" },
    { key: "ruolo_rls", label: "RLS" },
    { key: "ruolo_preposto", label: "Preposto" },
    { key: "ruolo_primo_soccorso", label: "Primo Soccorso" },
    { key: "ruolo_antincendio", label: "Antincendio" },
  ];

  const activeRoles = roles.filter((r) => persona[r.key] === true);
  if (activeRoles.length === 0) return <span className="text-muted-foreground">-</span>;

  return (
    <div className="flex flex-wrap gap-1">
      {activeRoles.map((r) => (
        <Badge key={r.key} variant="secondary" className="text-xs">
          {r.label}
        </Badge>
      ))}
    </div>
  );
}

export default function AziendaDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [persone, setPersone] = useState<Persona[]>([]);
  const [ambienti, setAmbienti] = useState<Ambiente[]>([]);
  const [attrezzature, setAttrezzature] = useState<Attrezzatura[]>([]);
  const [rischi, setRischi] = useState<ValutazioneRischio[]>([]);
  const [documenti, setDocumenti] = useState<DocumentoGenerato[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedRisk, setExpandedRisk] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [az, per, amb, att, ris, doc] = await Promise.all([
        apiCall<Azienda>(`/api/v1/aziende/${id}`),
        apiCall<Persona[]>(`/api/v1/aziende/${id}/persone`).catch(() => []),
        apiCall<Ambiente[]>(`/api/v1/aziende/${id}/ambienti`).catch(() => []),
        apiCall<Attrezzatura[]>(`/api/v1/aziende/${id}/attrezzature`).catch(() => []),
        apiCall<ValutazioneRischio[]>(`/api/v1/aziende/${id}/rischi`).catch(() => []),
        apiCall<DocumentoGenerato[]>(`/api/v1/aziende/${id}/documents`).catch(() => []),
      ]);
      setAzienda(az);
      setPersone(per);
      setAmbienti(amb);
      setAttrezzature(att);
      setRischi(ris);
      setDocumenti(doc);
    } catch {
      setError("Errore nel caricamento dei dati");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="space-y-6">
        <p className="text-muted-foreground">Caricamento...</p>
      </div>
    );
  }

  if (error || !azienda) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" nativeButton={false} render={<Link href="/aziende" />}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Torna alle aziende
        </Button>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-destructive">{error || "Azienda non trovata"}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" nativeButton={false} render={<Link href="/aziende" />}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">
                {azienda.ragione_sociale}
              </h1>
              <Badge className={surveyStatusColors[azienda.survey_status]}>
                {surveyStatusLabels[azienda.survey_status]}
              </Badge>
            </div>
            <p className="text-muted-foreground">
              {azienda.sede_operativa_citta || azienda.sede_legale_citta || "Sede non specificata"}
              {azienda.codice_ateco ? ` \u00b7 ATECO ${azienda.codice_ateco}` : ""}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" nativeButton={false} render={<Link href={`/survey/${id}`} />}>
            <ClipboardList className="mr-2 h-4 w-4" />
            Inizia Sopralluogo
          </Button>
          <Button
            onClick={async () => {
              try {
                await apiCall(`/api/v1/aziende/${id}/documents/batch`, {
                  method: "POST",
                });
                fetchData();
              } catch {
                // silently handle
              }
            }}
          >
            <FileText className="mr-2 h-4 w-4" />
            Genera Documenti
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="panoramica">
        <TabsList>
          <TabsTrigger value="panoramica">
            <Building2 className="mr-1.5 h-3.5 w-3.5" />
            Panoramica
          </TabsTrigger>
          <TabsTrigger value="persone">
            <Users className="mr-1.5 h-3.5 w-3.5" />
            Persone
            {persone.length > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-[10px]">
                {persone.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="ambienti">
            <Warehouse className="mr-1.5 h-3.5 w-3.5" />
            Ambienti
            {ambienti.length > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-[10px]">
                {ambienti.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="attrezzature">
            <Wrench className="mr-1.5 h-3.5 w-3.5" />
            Attrezzature
            {attrezzature.length > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-[10px]">
                {attrezzature.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="rischi">
            <ShieldAlert className="mr-1.5 h-3.5 w-3.5" />
            Rischi
            {rischi.length > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-[10px]">
                {rischi.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="documenti">
            <FileText className="mr-1.5 h-3.5 w-3.5" />
            Documenti
            {documenti.length > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-[10px]">
                {documenti.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Panoramica Tab */}
        <TabsContent value="panoramica">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Building2 className="h-4 w-4 text-muted-foreground" />
                  Dati Azienda
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-2">
                <InfoRow label="Ragione Sociale" value={azienda.ragione_sociale} />
                <InfoRow label="Codice ATECO" value={azienda.codice_ateco} />
                <InfoRow label="Attivit&agrave;" value={azienda.attivita} />
                <InfoRow label="Orario di Lavoro" value={azienda.orario_lavoro} />
                <InfoRow
                  label="Metratura Totale"
                  value={azienda.metratura_totale ? `${azienda.metratura_totale} mq` : null}
                />
                <InfoRow
                  label="Zona Sismica"
                  value={azienda.zona_sismica ? `Zona ${azienda.zona_sismica}` : null}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <MapPin className="h-4 w-4 text-muted-foreground" />
                  Sedi
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">
                    Sede Legale
                  </p>
                  <p className="text-sm">
                    {azienda.sede_legale_via || "-"}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {azienda.sede_legale_citta || "-"}
                  </p>
                </div>
                <Separator />
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">
                    Sede Operativa
                  </p>
                  <p className="text-sm">
                    {azienda.sede_operativa_via || "-"}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {azienda.sede_operativa_citta || "-"}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="text-sm">Descrizione</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <DescriptionEditor
                  aziendaId={azienda.id}
                  value={azienda.descrizione_attivita ?? ""}
                  initialProvenance={
                    azienda.descrizione_attivita ? "edited" : "none"
                  }
                  onChange={async (text) => {
                    // Optimistic local update
                    setAzienda({ ...azienda, descrizione_attivita: text });
                    try {
                      await apiCall<Azienda>(`/api/v1/aziende/${azienda.id}`, {
                        method: "PUT",
                        body: JSON.stringify({ descrizione_attivita: text }),
                      });
                    } catch {
                      // ignore; user can retry
                    }
                  }}
                />
                {azienda.contesto_territoriale && (
                  <div>
                    <p className="mb-1 text-xs font-medium text-muted-foreground">
                      Contesto Territoriale
                    </p>
                    <p className="text-sm leading-relaxed">
                      {azienda.contesto_territoriale}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Persone Tab */}
        <TabsContent value="persone">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Personale</CardTitle>
            </CardHeader>
            <CardContent>
              {persone.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Nessuna persona registrata. Avvia il sopralluogo per aggiungere il personale.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nominativo</TableHead>
                      <TableHead>Mansione</TableHead>
                      <TableHead>Contratto</TableHead>
                      <TableHead>Sesso</TableHead>
                      <TableHead>Ruoli</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {persone.map((p) => (
                      <TableRow key={p.id}>
                        <TableCell className="font-medium">{p.nominativo}</TableCell>
                        <TableCell>{p.mansione || "-"}</TableCell>
                        <TableCell>{p.tipologia_contrattuale || "-"}</TableCell>
                        <TableCell>{p.sesso || "-"}</TableCell>
                        <TableCell>
                          <PersonaRoleBadges persona={p} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Ambienti Tab */}
        <TabsContent value="ambienti">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Ambienti di Lavoro</CardTitle>
            </CardHeader>
            <CardContent>
              {ambienti.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Nessun ambiente registrato. Avvia il sopralluogo per aggiungere gli ambienti.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nome</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Superficie</TableHead>
                      <TableHead>Attivit&agrave;</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {ambienti.map((a) => (
                      <TableRow key={a.id}>
                        <TableCell className="font-medium">{a.nome}</TableCell>
                        <TableCell>{a.tipo}</TableCell>
                        <TableCell>
                          {a.superficie_mq ? `${a.superficie_mq} mq` : "-"}
                        </TableCell>
                        <TableCell className="max-w-[300px] truncate">
                          {a.descrizione_attivita || "-"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Attrezzature Tab */}
        <TabsContent value="attrezzature">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Attrezzature</CardTitle>
            </CardHeader>
            <CardContent>
              {attrezzature.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Nessuna attrezzatura registrata. Avvia il sopralluogo per aggiungere le attrezzature.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Descrizione</TableHead>
                      <TableHead>Marcatura CE</TableHead>
                      <TableHead>Verifiche Periodiche</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {attrezzature.map((a) => (
                      <TableRow key={a.id}>
                        <TableCell className="font-medium">{a.descrizione}</TableCell>
                        <TableCell>
                          {a.marcatura_ce ? (
                            <span className="flex items-center gap-1 text-green-600">
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              S&igrave;
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-red-600">
                              <XCircle className="h-3.5 w-3.5" />
                              No
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          {a.verifiche_periodiche ? (
                            <span className="flex items-center gap-1 text-green-600">
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              S&igrave;
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-red-600">
                              <XCircle className="h-3.5 w-3.5" />
                              No
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Rischi Tab — AI measures panel per risk (US-2.6) */}
        <TabsContent value="rischi">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">
                Valutazioni del rischio
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {rischi.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Nessun rischio registrato. Completa il sopralluogo per
                  valutare i rischi.
                </p>
              ) : (
                rischi
                  .filter((r) => r.applicabile)
                  .map((r) => {
                    const isOpen = expandedRisk === r.id;
                    return (
                      <div
                        key={r.id}
                        className="rounded-lg border border-input"
                      >
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedRisk(isOpen ? null : r.id)
                          }
                          className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left hover:bg-muted/50"
                        >
                          <div className="flex flex-1 flex-wrap items-center gap-2">
                            <span className="text-sm font-medium">
                              {r.categoria_rischio}
                            </span>
                            {r.pericolo && (
                              <span className="text-xs text-muted-foreground">
                                - {r.pericolo}
                              </span>
                            )}
                            {r.livello_rischio && (
                              <Badge
                                variant="secondary"
                                className={
                                  r.livello_rischio === "ACCETTABILE"
                                    ? "bg-emerald-100 text-emerald-800"
                                    : r.livello_rischio === "MODESTO"
                                    ? "bg-amber-100 text-amber-800"
                                    : r.livello_rischio === "GRAVE"
                                    ? "bg-orange-100 text-orange-800"
                                    : "bg-red-100 text-red-800"
                                }
                              >
                                {r.livello_rischio} (I={r.indice_i})
                              </Badge>
                            )}
                          </div>
                          {isOpen ? (
                            <ChevronUp className="h-4 w-4 flex-shrink-0" />
                          ) : (
                            <ChevronDown className="h-4 w-4 flex-shrink-0" />
                          )}
                        </button>
                        {isOpen && (
                          <div className="border-t border-input p-4">
                            <MeasuresPanel
                              aziendaId={azienda.id}
                              rischioId={r.id}
                              initialText={r.misure_prevenzione ?? ""}
                              onSave={async (text) => {
                                await apiCall(
                                  `/api/v1/aziende/${azienda.id}/ambienti/${r.ambiente_id}/rischi/${r.id}`,
                                  {
                                    method: "PUT",
                                    body: JSON.stringify({
                                      misure_prevenzione: text,
                                    }),
                                  }
                                );
                                // refresh so the new text shows under initialText
                                fetchData();
                              }}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Documenti Tab */}
        <TabsContent value="documenti">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Documenti Generati</CardTitle>
            </CardHeader>
            <CardContent>
              {documenti.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Nessun documento generato. Clicca &quot;Genera Documenti&quot; per iniziare.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Documento</TableHead>
                      <TableHead>Versione</TableHead>
                      <TableHead>Stato</TableHead>
                      <TableHead>Data Creazione</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {documenti.map((d) => (
                      <TableRow key={d.id}>
                        <TableCell className="font-medium">
                          {d.tipo_documento}
                        </TableCell>
                        <TableCell>v{d.versione}</TableCell>
                        <TableCell>
                          <Badge className={docStatusColors[d.status]}>
                            {docStatusLabels[d.status]}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {new Date(d.created_at).toLocaleDateString("it-IT")}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
