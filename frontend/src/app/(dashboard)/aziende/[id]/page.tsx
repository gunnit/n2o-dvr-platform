"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useSession } from "next-auth/react";
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
  ShieldAlert,
  Pencil,
  Trash2,
} from "lucide-react";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import type {
  Azienda,
  Persona,
  Ambiente,
  Attrezzatura,
  DocumentoGenerato,
  ValutazioneRischio,
} from "@/types";
import { apiCall } from "@/lib/api-client";
import { DeleteAziendaDialog } from "@/components/aziende/delete-azienda-dialog";
import { NextStepsPanel } from "@/components/aziende/next-steps-panel";
import { surveyStatusMeta } from "@/lib/ui/status-map";
import { StatusPill } from "@/components/aziende/tabs/_shared";
import PanoramicaTab from "@/components/aziende/tabs/panoramica-tab";
import AmbientiTab from "@/components/aziende/tabs/ambienti-tab";
import PersoneTab from "@/components/aziende/tabs/persone-tab";
import AttrezzatureTab from "@/components/aziende/tabs/attrezzature-tab";
import RischiTab from "@/components/aziende/tabs/rischi-tab";
import DocumentiTab from "@/components/aziende/tabs/documenti-tab";

// Detail-page tab keys — shared between the trigger list and the
// deep-link helpers below. Order mirrors the wizard (M3) minus
// Sostanze and DPI which stay wizard-only for now.
type DetailTabKey =
  | "panoramica"
  | "ambienti"
  | "persone"
  | "attrezzature"
  | "rischi"
  | "documenti";

const DETAIL_TABS: ReadonlySet<DetailTabKey> = new Set([
  "panoramica",
  "ambienti",
  "persone",
  "attrezzature",
  "rischi",
  "documenti",
]);

function parseTabKey(raw: string | null | undefined): DetailTabKey {
  if (raw && DETAIL_TABS.has(raw as DetailTabKey)) return raw as DetailTabKey;
  return "panoramica";
}

export default function AziendaDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const id = params.id as string;
  const { data: session } = useSession();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const role = (session?.user as any)?.role as string | undefined;
  const isAdmin = role === "admin";

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [persone, setPersone] = useState<Persona[]>([]);
  const [ambienti, setAmbienti] = useState<Ambiente[]>([]);
  const [attrezzature, setAttrezzature] = useState<Attrezzatura[]>([]);
  const [rischi, setRischi] = useState<ValutazioneRischio[]>([]);
  const [documenti, setDocumenti] = useState<DocumentoGenerato[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [generatingDocs, setGeneratingDocs] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  // M5 — read tab from `?tab=` so deep links and the back button work,
  // and write back via router.replace on user switch.
  const [activeTab, setActiveTab] = useState<DetailTabKey>(() =>
    parseTabKey(searchParams?.get("tab")),
  );

  // Resync if the URL changes externally (e.g. browser back).
  useEffect(() => {
    const next = parseTabKey(searchParams?.get("tab"));
    setActiveTab((prev) => (prev === next ? prev : next));
  }, [searchParams]);

  const handleTabChange = useCallback(
    (value: string) => {
      const next = parseTabKey(value);
      setActiveTab(next);
      const sp = new URLSearchParams(searchParams?.toString() ?? "");
      if (next === "panoramica") {
        sp.delete("tab");
      } else {
        sp.set("tab", next);
      }
      const qs = sp.toString();
      router.replace(qs ? `/aziende/${id}?${qs}` : `/aziende/${id}`, {
        scroll: false,
      });
    },
    [id, router, searchParams],
  );

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [az, per, amb, att, ris, doc] = await Promise.all([
        apiCall<Azienda>(`/api/v1/aziende/${id}`),
        apiCall<Persona[]>(`/api/v1/aziende/${id}/persone`).catch(() => []),
        apiCall<Ambiente[]>(`/api/v1/aziende/${id}/ambienti`).catch(() => []),
        apiCall<Attrezzatura[]>(`/api/v1/aziende/${id}/attrezzature`).catch(
          () => [],
        ),
        apiCall<ValutazioneRischio[]>(`/api/v1/aziende/${id}/rischi`).catch(
          () => [],
        ),
        apiCall<DocumentoGenerato[]>(`/api/v1/aziende/${id}/documents`).catch(
          () => [],
        ),
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
      // B1 — surface the Italian "Sopralluogo incompleto: ..." gate
      // message that the API returns as 409. apiCall throws Error with
      // the server `detail` as the message, so the same toast covers
      // both the precondition gate and any other failure.
      toast.error(
        err instanceof Error
          ? err.message
          : "Generazione documenti fallita. Riprova.",
      );
    } finally {
      setGeneratingDocs(false);
    }
  };

  // B1 — disable Genera Documenti while the sopralluogo hasn't been
  // submitted at least once. Server-side gate is authoritative; this is
  // just the UX guard so the button never looks clickable when it'd 409.
  const generaDocsBlocked =
    !azienda ||
    azienda.survey_status === "draft" ||
    azienda.survey_status?.startsWith("step_") === true ||
    azienda.survey_status === "in_progress";
  const generaDocsTitle = generaDocsBlocked
    ? "Completa e firma il sopralluogo prima di generare i documenti"
    : undefined;

  // B4 — destructive action wired straight to the backend DELETE.
  // The dialog component handles the confirmation flow + spinner.
  async function handleDelete() {
    try {
      await apiCall(`/api/v1/aziende/${id}`, { method: "DELETE" });
      toast.success("Azienda eliminata");
      router.push("/aziende");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Eliminazione fallita. Riprova.",
      );
      throw err;
    }
  }

  // Persist the inline-edited descrizione_attivita from PanoramicaTab.
  // Optimistic local update so the editor doesn't flicker on save.
  const handleDescriptionChange = useCallback(
    async (text: string) => {
      if (!azienda) return;
      setAzienda({ ...azienda, descrizione_attivita: text });
      try {
        await apiCall<Azienda>(`/api/v1/aziende/${azienda.id}`, {
          method: "PUT",
          body: JSON.stringify({ descrizione_attivita: text }),
        });
      } catch (err) {
        toast.error(
          err instanceof Error
            ? err.message
            : "Salvataggio descrizione fallito. Riprova.",
        );
      }
    },
    [azienda],
  );

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
    azienda.sede_operativa_citta ||
    azienda.sede_legale_citta ||
    "Sede non specificata";

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
            {(() => {
              const meta = surveyStatusMeta(azienda.survey_status);
              return (
                <StatusPill className={meta.badge}>{meta.label}</StatusPill>
              );
            })()}
          </div>
          <p className="type-body mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
            <MapPin
              className="h-3.5 w-3.5 text-[#64748d]"
              strokeWidth={1.75}
            />
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
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {isAdmin && (
            <>
              <button
                type="button"
                onClick={() => router.push(`/aziende/${id}/edit`)}
                className="inline-flex h-10 items-center gap-2 rounded-md border border-[#e5edf5] bg-white px-3.5 text-[14px] font-medium text-[#273951] transition-colors hover:bg-[#f6f9fc]"
                title="Modifica anagrafica azienda"
              >
                <Pencil className="h-4 w-4" strokeWidth={1.75} />
                Modifica
              </button>
              <button
                type="button"
                onClick={() => setDeleteOpen(true)}
                className="inline-flex h-10 items-center gap-2 rounded-md border border-[rgba(234,34,97,0.25)] bg-white px-3.5 text-[14px] font-medium text-[#b51648] transition-colors hover:bg-[rgba(234,34,97,0.06)]"
                title="Elimina azienda"
              >
                <Trash2 className="h-4 w-4" strokeWidth={1.75} />
                Elimina
              </button>
            </>
          )}
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
            disabled={generatingDocs || generaDocsBlocked}
            title={generaDocsTitle}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-[14px] font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594] disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <FileText className="h-4 w-4" strokeWidth={1.75} />
            {generatingDocs ? "Avvio in corso..." : "Genera Documenti"}
          </button>
        </div>
      </div>

      <DeleteAziendaDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        ragioneSociale={azienda.ragione_sociale}
        onConfirm={handleDelete}
      />

      <NextStepsPanel
        azienda={azienda}
        rischi={rischi}
        documenti={documenti}
        callbacks={{
          onResumeSurvey: () => router.push(`/survey/${id}`),
          onOpenDescrizione: () => {
            handleTabChange("panoramica");
            // Wait two frames so the tab content is mounted before scrolling.
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                document
                  .getElementById("descrizione-attivita")
                  ?.scrollIntoView({ behavior: "smooth", block: "start" });
              });
            });
          },
          // When no applicable rischi exist yet, jump straight to the
          // standalone editor — the rischi tab would just show an empty
          // state with the same CTA. With rischi present the tab is the
          // right landing (it surfaces measures coverage / level
          // distribution).
          onOpenRischi: () =>
            rischi.some((r) => r.applicabile)
              ? handleTabChange("rischi")
              : router.push(`/assessments/risk/${id}`),
          onOpenAssessments: () => router.push("/assessments"),
          onOpenDocumenti: () => handleTabChange("documenti"),
          onGenerateDocs: handleGenerateDocs,
          generatingDocs,
        }}
      />

      {/* Tabs — order matches the survey wizard (M3): Ambienti precedes
           Persone. M5 keeps the active tab in sync with `?tab=`. */}
      <Tabs value={activeTab} onValueChange={handleTabChange}>
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

        <TabsContent value="panoramica" className="mt-6">
          <PanoramicaTab
            azienda={azienda}
            persone={persone}
            ambienti={ambienti}
            attrezzature={attrezzature}
            rischi={rischi}
            documenti={documenti}
            onDescriptionChange={handleDescriptionChange}
          />
        </TabsContent>

        <TabsContent value="ambienti" className="mt-6">
          <AmbientiTab
            aziendaId={azienda.id}
            ambienti={ambienti}
            attrezzature={attrezzature}
            persone={persone}
            rischi={rischi}
          />
        </TabsContent>

        <TabsContent value="persone" className="mt-6">
          <PersoneTab persone={persone} ambienti={ambienti} />
        </TabsContent>

        <TabsContent value="attrezzature" className="mt-6">
          <AttrezzatureTab
            attrezzature={attrezzature}
            ambienti={ambienti}
          />
        </TabsContent>

        <TabsContent value="rischi" className="mt-6">
          <RischiTab
            aziendaId={azienda.id}
            rischi={rischi}
            ambienti={ambienti}
            onMeasuresSaved={fetchData}
          />
        </TabsContent>

        <TabsContent value="documenti" className="mt-6">
          <DocumentiTab
            aziendaId={azienda.id}
            documenti={documenti}
            onRefresh={fetchData}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
