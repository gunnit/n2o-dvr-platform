"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
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

// DESIGN.md §0 + §2 — N2O navy primary + success green per brand override.
const surveyStatusStyles: Record<string, string> = {
  draft:
    "bg-[#f6f9fc] text-[#273951] border border-[#e5edf5]",
  in_progress:
    "bg-[rgba(0,61,116,0.08)] text-primary border border-[rgba(0,61,116,0.2)]",
  completed:
    "bg-[rgba(21,190,83,0.2)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
};

const surveyStatusLabels: Record<string, string> = {
  draft: "Bozza",
  in_progress: "In corso",
  completed: "Completato",
};

const docStatusStyles: Record<string, string> = {
  pending:
    "bg-[#f6f9fc] text-[#273951] border border-[#e5edf5]",
  in_progress:
    "bg-[rgba(155,104,41,0.12)] text-[#9b6829] border border-[rgba(155,104,41,0.3)]",
  completed:
    "bg-[rgba(21,190,83,0.2)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
  failed:
    "bg-[rgba(234,34,97,0.08)] text-[#b51648] border border-[rgba(234,34,97,0.25)]",
};

const docStatusLabels: Record<string, string> = {
  pending: "In attesa",
  in_progress: "In generazione",
  completed: "Pronto",
  failed: "Errore",
};

// Risk-level chip palette — navy for critical, green for accettabile,
// per DESIGN.md §0 (no pink accents in safety domain).
const riskLevelStyles: Record<string, string> = {
  ACCETTABILE:
    "bg-[rgba(21,190,83,0.2)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
  MODESTO:
    "bg-[rgba(155,104,41,0.12)] text-[#9b6829] border border-[rgba(155,104,41,0.3)]",
  GRAVE:
    "bg-[rgba(0,61,116,0.12)] text-primary border border-[rgba(0,61,116,0.3)]",
  GRAVISSIMO:
    "bg-[rgba(234,34,97,0.08)] text-[#b51648] border border-[rgba(234,34,97,0.3)]",
};

function StatusPill({
  className,
  children,
}: {
  className: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={
        "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium " +
        className
      }
    >
      {children}
    </span>
  );
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return <p className="type-eyebrow">{children}</p>;
}

function InfoRow({
  label,
  value,
  tnum = false,
}: {
  label: string;
  value: string | null | undefined;
  tnum?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="type-eyebrow">{label}</span>
      <span
        className={
          "text-[14px] leading-[1.4] text-[#061b31] " + (tnum ? "tnum" : "")
        }
      >
        {value || "-"}
      </span>
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
  if (activeRoles.length === 0) return <span className="text-[#64748d]">-</span>;

  return (
    <div className="flex flex-wrap gap-1">
      {activeRoles.map((r) => (
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

type PanelAccent = "navy" | "sky" | "violet" | "emerald" | "amber" | "slate";

const PANEL_ACCENT: Record<PanelAccent, { rail: string; icon: string; bg: string }> = {
  navy: { rail: "bg-[#003d74]", icon: "text-[#003d74]", bg: "bg-[rgba(0,61,116,0.08)]" },
  sky: { rail: "bg-[#0ea5e9]", icon: "text-[#0ea5e9]", bg: "bg-[rgba(14,165,233,0.1)]" },
  violet: { rail: "bg-[#7c3aed]", icon: "text-[#7c3aed]", bg: "bg-[rgba(124,58,237,0.1)]" },
  emerald: { rail: "bg-[#059669]", icon: "text-[#059669]", bg: "bg-[rgba(5,150,105,0.1)]" },
  amber: { rail: "bg-[#d97706]", icon: "text-[#d97706]", bg: "bg-[rgba(217,119,6,0.1)]" },
  slate: { rail: "bg-[#94a3b8]", icon: "text-[#64748d]", bg: "bg-[#f6f9fc]" },
};

function Panel({
  children,
  className = "",
  accent,
}: {
  children: React.ReactNode;
  className?: string;
  accent?: PanelAccent;
}) {
  const accentClass = accent ? PANEL_ACCENT[accent].rail : "";
  return (
    <div
      className={
        "relative overflow-hidden rounded-md border border-[#e5edf5] bg-white shadow-stripe-ambient " +
        className
      }
    >
      {accent && (
        <span
          aria-hidden
          className={"absolute inset-x-0 top-0 h-[2px] " + accentClass}
        />
      )}
      {children}
    </div>
  );
}

function PanelHeader({
  icon: Icon,
  title,
  action,
  accent,
}: {
  icon?: typeof Building2;
  title: string;
  action?: React.ReactNode;
  accent?: PanelAccent;
}) {
  const accentMeta = accent ? PANEL_ACCENT[accent] : null;
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[#e5edf5] px-6 py-4">
      <div className="flex items-center gap-2.5">
        {Icon && (
          accentMeta ? (
            <span
              className={
                "inline-flex h-7 w-7 items-center justify-center rounded-md " +
                accentMeta.bg
              }
            >
              <Icon
                className={"h-3.5 w-3.5 " + accentMeta.icon}
                strokeWidth={2}
              />
            </span>
          ) : (
            <Icon className="h-4 w-4 text-[#64748d]" strokeWidth={1.75} />
          )
        )}
        <h3 className="font-heading text-[15px] font-semibold tracking-[-0.005em] text-[#061b31]">
          {title}
        </h3>
      </div>
      {action}
    </div>
  );
}

export default function AziendaDetailPage() {
  const params = useParams();
  const router = useRouter();
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
  const [generatingDocs, setGeneratingDocs] = useState(false);

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

  const handleGenerateDocs = async () => {
    setGeneratingDocs(true);
    try {
      await apiCall(`/api/v1/aziende/${id}/documents/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tipi_documento: [
            "dvr_master",
            "allegato_mmc",
            "allegato_vdt",
            "allegato_stress",
            "allegato_gestanti",
            "allegato_incendio",
            "allegato_microclima",
            "allegato_microclima_severo",
            "allegato_biologico_alimentare",
            "allegato_biologico_asilo",
            "allegato_biologico_dentisti",
            "pee_azienda",
            "pee_comune",
            "haccp",
            "haccp_forms",
            "duvri",
            "pos",
          ],
        }),
      });
      toast.success("Generazione documenti avviata");
      fetchData();
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Generazione documenti fallita. Riprova."
      );
    } finally {
      setGeneratingDocs(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <p className="type-body">Caricamento...</p>
      </div>
    );
  }

  if (error || !azienda) {
    return (
      <div className="space-y-6">
        <Link
          href="/aziende"
          className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#64748d] transition-colors hover:text-[#061b31]"
        >
          <ArrowLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Torna alle aziende
        </Link>
        <div className="rounded-md border border-[rgba(234,34,97,0.25)] bg-[rgba(234,34,97,0.04)] p-10 text-center shadow-stripe-ambient">
          <p className="text-[14px] text-[#b51648]">
            {error || "Azienda non trovata"}
          </p>
        </div>
      </div>
    );
  }

  const city =
    azienda.sede_operativa_citta || azienda.sede_legale_citta || "Sede non specificata";

  return (
    <div className="space-y-8">
      {/* Breadcrumb back */}
      <Link
        href="/aziende"
        className="-mb-2 inline-flex items-center gap-1.5 text-[13px] font-medium text-[#64748d] transition-colors hover:text-[#061b31]"
      >
        <ArrowLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
        Aziende
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-6">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="type-h1 truncate">{azienda.ragione_sociale}</h1>
            <StatusPill className={surveyStatusStyles[azienda.survey_status]}>
              {surveyStatusLabels[azienda.survey_status]}
            </StatusPill>
          </div>
          <p className="type-body mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
            <MapPin className="h-3.5 w-3.5 text-[#64748d]" strokeWidth={1.75} />
            <span>{city}</span>
            {azienda.codice_ateco && (
              <>
                <span className="text-[#c2c6d2]">·</span>
                <span className="type-eyebrow !tracking-wider">ATECO</span>
                <span className="tnum text-[13px] text-[#273951]">
                  {azienda.codice_ateco}
                </span>
              </>
            )}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => router.push(`/survey/${id}`)}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-[#e5edf5] bg-white px-4 text-[14px] font-medium text-[#273951] transition-colors hover:bg-[#f6f9fc]"
          >
            <ClipboardList className="h-4 w-4" strokeWidth={1.75} />
            Inizia Sopralluogo
          </button>
          <button
            type="button"
            onClick={handleGenerateDocs}
            disabled={generatingDocs}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-[14px] font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594] disabled:opacity-60"
          >
            <FileText className="h-4 w-4" strokeWidth={1.75} />
            {generatingDocs ? "Avvio in corso..." : "Genera Documenti"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="panoramica">
        <TabsList
          variant="line"
          className="h-auto w-full justify-start gap-6 border-b border-[#e5edf5] pb-0"
        >
          <TabsTrigger
            value="panoramica"
            className="text-[13px] font-medium text-[#64748d] data-active:text-[#061b31]"
          >
            <Building2 className="mr-1.5 h-3.5 w-3.5" />
            Panoramica
          </TabsTrigger>
          <TabsTrigger
            value="persone"
            className="text-[13px] font-medium text-[#64748d] data-active:text-[#061b31]"
          >
            <Users className="mr-1.5 h-3.5 w-3.5" />
            Persone
            {persone.length > 0 && (
              <span className="ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-sm bg-[#f6f9fc] px-1 text-[10px] font-medium text-[#273951] tnum">
                {persone.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="ambienti"
            className="text-[13px] font-medium text-[#64748d] data-active:text-[#061b31]"
          >
            <Warehouse className="mr-1.5 h-3.5 w-3.5" />
            Ambienti
            {ambienti.length > 0 && (
              <span className="ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-sm bg-[#f6f9fc] px-1 text-[10px] font-medium text-[#273951] tnum">
                {ambienti.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="attrezzature"
            className="text-[13px] font-medium text-[#64748d] data-active:text-[#061b31]"
          >
            <Wrench className="mr-1.5 h-3.5 w-3.5" />
            Attrezzature
            {attrezzature.length > 0 && (
              <span className="ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-sm bg-[#f6f9fc] px-1 text-[10px] font-medium text-[#273951] tnum">
                {attrezzature.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="rischi"
            className="text-[13px] font-medium text-[#64748d] data-active:text-[#061b31]"
          >
            <ShieldAlert className="mr-1.5 h-3.5 w-3.5" />
            Rischi
            {rischi.length > 0 && (
              <span className="ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-sm bg-[#f6f9fc] px-1 text-[10px] font-medium text-[#273951] tnum">
                {rischi.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="documenti"
            className="text-[13px] font-medium text-[#64748d] data-active:text-[#061b31]"
          >
            <FileText className="mr-1.5 h-3.5 w-3.5" />
            Documenti
            {documenti.length > 0 && (
              <span className="ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-sm bg-[#f6f9fc] px-1 text-[10px] font-medium text-[#273951] tnum">
                {documenti.length}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Panoramica Tab */}
        <TabsContent value="panoramica" className="mt-6">
          <div className="grid gap-5 md:grid-cols-2">
            <Panel accent="navy">
              <PanelHeader icon={Building2} title="Dati Azienda" accent="navy" />
              <div className="grid gap-5 p-6 sm:grid-cols-2">
                <InfoRow label="Ragione Sociale" value={azienda.ragione_sociale} />
                <InfoRow
                  label="Codice ATECO"
                  value={azienda.codice_ateco}
                  tnum
                />
                <InfoRow label="Attivita'" value={azienda.attivita} />
                <InfoRow label="Orario di Lavoro" value={azienda.orario_lavoro} />
                <InfoRow
                  label="Metratura Totale"
                  value={
                    azienda.metratura_totale
                      ? `${azienda.metratura_totale} mq`
                      : null
                  }
                  tnum
                />
                <InfoRow
                  label="Zona Sismica"
                  value={azienda.zona_sismica ? `Zona ${azienda.zona_sismica}` : null}
                />
              </div>
            </Panel>

            <Panel accent="sky">
              <PanelHeader icon={MapPin} title="Sedi" accent="sky" />
              <div className="space-y-5 p-6">
                <div>
                  <Eyebrow>Sede Legale</Eyebrow>
                  <p className="mt-1 text-[14px] text-[#061b31]">
                    {azienda.sede_legale_via || "-"}
                  </p>
                  <p className="text-[13px] text-[#64748d]">
                    {azienda.sede_legale_citta || "-"}
                  </p>
                </div>
                <div className="h-px bg-[#e5edf5]" />
                <div>
                  <Eyebrow>Sede Operativa</Eyebrow>
                  <p className="mt-1 text-[14px] text-[#061b31]">
                    {azienda.sede_operativa_via || "-"}
                  </p>
                  <p className="text-[13px] text-[#64748d]">
                    {azienda.sede_operativa_citta || "-"}
                  </p>
                </div>
              </div>
            </Panel>

            <Panel accent="violet" className="md:col-span-2">
              <PanelHeader icon={FileText} title="Descrizione" accent="violet" />
              <div className="space-y-6 p-6">
                <DescriptionEditor
                  aziendaId={azienda.id}
                  value={azienda.descrizione_attivita ?? ""}
                  initialProvenance={
                    azienda.descrizione_attivita ? "edited" : "none"
                  }
                  visuraUploadedAt={azienda.visura_uploaded_at ?? null}
                  onChange={async (text) => {
                    // Optimistic local update
                    setAzienda({ ...azienda, descrizione_attivita: text });
                    try {
                      await apiCall<Azienda>(
                        `/api/v1/aziende/${azienda.id}`,
                        {
                          method: "PUT",
                          body: JSON.stringify({
                            descrizione_attivita: text,
                          }),
                        }
                      );
                    } catch (err) {
                      toast.error(
                        err instanceof Error
                          ? err.message
                          : "Salvataggio descrizione fallito. Riprova."
                      );
                    }
                  }}
                />
                {azienda.contesto_territoriale && (
                  <div>
                    <Eyebrow>Contesto Territoriale</Eyebrow>
                    <p className="mt-2 text-[14px] leading-relaxed text-[#273951]">
                      {azienda.contesto_territoriale}
                    </p>
                  </div>
                )}
              </div>
            </Panel>
          </div>
        </TabsContent>

        {/* Persone Tab */}
        <TabsContent value="persone" className="mt-6">
          <Panel accent="emerald">
            <PanelHeader icon={Users} title="Personale" accent="emerald" />
            {persone.length === 0 ? (
              <p className="py-12 text-center text-[14px] text-[#64748d]">
                Nessuna persona registrata. Avvia il sopralluogo per aggiungere
                il personale.
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
                      <TableCell className="font-medium text-[#061b31]">
                        {p.nominativo}
                      </TableCell>
                      <TableCell className="text-[#273951]">
                        {p.mansione || "-"}
                      </TableCell>
                      <TableCell className="text-[#64748d]">
                        {p.tipologia_contrattuale || "-"}
                      </TableCell>
                      <TableCell className="text-[#64748d]">
                        {p.sesso || "-"}
                      </TableCell>
                      <TableCell>
                        <PersonaRoleBadges persona={p} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Panel>
        </TabsContent>

        {/* Ambienti Tab */}
        <TabsContent value="ambienti" className="mt-6">
          <Panel accent="amber">
            <PanelHeader icon={Warehouse} title="Ambienti di Lavoro" accent="amber" />
            {ambienti.length === 0 ? (
              <p className="py-12 text-center text-[14px] text-[#64748d]">
                Nessun ambiente registrato. Avvia il sopralluogo per aggiungere
                gli ambienti.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nome</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Superficie</TableHead>
                    <TableHead>Attivita'</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ambienti.map((a) => (
                    <TableRow key={a.id}>
                      <TableCell className="font-medium text-[#061b31]">
                        {a.nome}
                      </TableCell>
                      <TableCell className="text-[#273951]">{a.tipo}</TableCell>
                      <TableCell className="tnum text-[#273951]">
                        {a.superficie_mq ? `${a.superficie_mq} mq` : "-"}
                      </TableCell>
                      <TableCell className="max-w-[320px] truncate text-[#64748d]">
                        {a.descrizione_attivita || "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Panel>
        </TabsContent>

        {/* Attrezzature Tab */}
        <TabsContent value="attrezzature" className="mt-6">
          <Panel accent="slate">
            <PanelHeader icon={Wrench} title="Attrezzature" accent="slate" />
            {attrezzature.length === 0 ? (
              <p className="py-12 text-center text-[14px] text-[#64748d]">
                Nessuna attrezzatura registrata. Avvia il sopralluogo per
                aggiungere le attrezzature.
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
                      <TableCell className="font-medium text-[#061b31]">
                        {a.descrizione}
                      </TableCell>
                      <TableCell>
                        {a.marcatura_ce ? (
                          <span className="inline-flex items-center gap-1 text-[13px] font-medium text-[#108c3d]">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Si
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[13px] font-medium text-[#b51648]">
                            <XCircle className="h-3.5 w-3.5" />
                            No
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        {a.verifiche_periodiche ? (
                          <span className="inline-flex items-center gap-1 text-[13px] font-medium text-[#108c3d]">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Si
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[13px] font-medium text-[#b51648]">
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
          </Panel>
        </TabsContent>

        {/* Rischi Tab — AI measures panel per risk (US-2.6) */}
        <TabsContent value="rischi" className="mt-6">
          <Panel accent="violet">
            <PanelHeader icon={ShieldAlert} title="Valutazioni del rischio" accent="violet" />
            <div className="space-y-3 p-6">
              {rischi.length === 0 ? (
                <p className="py-8 text-center text-[14px] text-[#64748d]">
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
                        className="rounded-md border border-[#e5edf5] bg-white shadow-stripe-ambient"
                      >
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedRisk(isOpen ? null : r.id)
                          }
                          className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left transition-colors hover:bg-[#f6f9fc]"
                        >
                          <div className="flex flex-1 flex-wrap items-center gap-2">
                            <span className="text-[14px] font-medium text-[#061b31]">
                              {r.categoria_rischio}
                            </span>
                            {r.pericolo && (
                              <span className="text-[13px] text-[#64748d]">
                                · {r.pericolo}
                              </span>
                            )}
                            {r.livello_rischio && (
                              <StatusPill
                                className={
                                  riskLevelStyles[r.livello_rischio] ||
                                  "bg-[#f6f9fc] text-[#273951] border border-[#e5edf5]"
                                }
                              >
                                {r.livello_rischio}
                                <span className="ml-1 tnum opacity-70">
                                  I={r.indice_i}
                                </span>
                              </StatusPill>
                            )}
                          </div>
                          {isOpen ? (
                            <ChevronUp
                              className="h-4 w-4 flex-shrink-0 text-[#64748d]"
                              strokeWidth={1.75}
                            />
                          ) : (
                            <ChevronDown
                              className="h-4 w-4 flex-shrink-0 text-[#64748d]"
                              strokeWidth={1.75}
                            />
                          )}
                        </button>
                        {isOpen && (
                          <div className="border-t border-[#e5edf5] p-5">
                            <MeasuresPanel
                              aziendaId={azienda.id}
                              rischioId={r.id}
                              categoriaRischio={r.categoria_rischio}
                              initialText={r.misure_prevenzione ?? ""}
                              onSave={async (text) => {
                                try {
                                  await apiCall(
                                    `/api/v1/aziende/${azienda.id}/ambienti/${r.ambiente_id}/rischi/${r.id}`,
                                    {
                                      method: "PUT",
                                      body: JSON.stringify({
                                        misure_prevenzione: text,
                                      }),
                                    }
                                  );
                                  toast.success("Misure salvate");
                                  fetchData();
                                } catch (err) {
                                  toast.error(
                                    err instanceof Error
                                      ? err.message
                                      : "Salvataggio misure fallito. Riprova."
                                  );
                                  throw err;
                                }
                              }}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })
              )}
            </div>
          </Panel>
        </TabsContent>

        {/* Documenti Tab */}
        <TabsContent value="documenti" className="mt-6">
          <Panel accent="sky">
            <PanelHeader icon={FileText} title="Documenti Generati" accent="sky" />
            <div className="p-6">
              {documenti.length === 0 ? (
                <p className="py-8 text-center text-[14px] text-[#64748d]">
                  Nessun documento generato. Clicca &quot;Genera Documenti&quot; per iniziare.
                </p>
              ) : (
                <>
                  {documenti.some((d) => d.stale_snapshot) && (
                    <div
                      className="mb-4 flex items-start gap-2 rounded-md border border-[rgba(155,104,41,0.3)] bg-[rgba(155,104,41,0.06)] px-3 py-2.5 text-[13px] text-[#9b6829]"
                      role="status"
                    >
                      <ShieldAlert className="mt-0.5 h-4 w-4 flex-shrink-0" />
                      <span className="flex-1">
                        Il sopralluogo e&apos; stato modificato dopo
                        l&apos;ultima generazione di alcuni documenti — i
                        contenuti potrebbero essere disallineati. Rigenera i
                        documenti contrassegnati per aggiornarli.
                      </span>
                    </div>
                  )}
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
                        <TableRow
                          key={d.id}
                          className={
                            d.stale_snapshot
                              ? "bg-[rgba(155,104,41,0.04)]"
                              : ""
                          }
                        >
                          <TableCell className="font-medium text-[#061b31]">
                            <span className="flex items-center gap-2">
                              {d.tipo_documento}
                              {d.stale_snapshot && (
                                <StatusPill
                                  className="bg-[rgba(155,104,41,0.12)] text-[#9b6829] border border-[rgba(155,104,41,0.3)]"
                                >
                                  Da rigenerare
                                </StatusPill>
                              )}
                            </span>
                          </TableCell>
                          <TableCell className="tnum text-[#273951]">
                            v{d.versione}
                          </TableCell>
                          <TableCell>
                            <StatusPill className={docStatusStyles[d.status]}>
                              {docStatusLabels[d.status] ?? d.status}
                            </StatusPill>
                            {d.error_message && (
                              <div
                                className="mt-1 text-[11px] text-[#b51648]"
                                title={d.error_message}
                              >
                                {d.error_message}
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="tnum text-[#64748d]">
                            {new Date(d.created_at).toLocaleDateString("it-IT")}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </>
              )}
            </div>
          </Panel>
        </TabsContent>
      </Tabs>
    </div>
  );
}
