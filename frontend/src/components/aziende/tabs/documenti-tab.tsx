"use client";

import { useMemo, useState } from "react";
import {
  Download,
  ExternalLink,
  FileText,
  Files,
  Filter,
  Paperclip,
  RotateCw,
  ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";

import {
  DOWNLOADABLE_DOC_STATUSES,
  EmptyState,
  Panel,
  PanelHeader,
  StatTile,
  StatusPill,
  docStatusLabels,
  docStatusStyles,
} from "@/components/aziende/tabs/_shared";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiCall, downloadFile } from "@/lib/api-client";
import { formatRelative } from "@/lib/ui/relative-time";
import type { DocumentoGenerato } from "@/types";

const DOC_TYPE_LABELS: Record<string, string> = {
  dvr_master: "DVR Master",
  allegato_mmc: "Allegato MMC (Movimentazione Carichi)",
  allegato_vdt: "Allegato VDT (Videoterminali)",
  allegato_stress: "Allegato Stress Lavoro-Correlato",
  allegato_gestanti: "Allegato Lavoratrici Gestanti",
  allegato_incendio: "Allegato Rischio Incendio",
  allegato_microclima: "Allegato Microclima",
  allegato_microclima_severo: "Allegato Microclima Severo",
  allegato_biologico_alimentare: "Allegato Biologico Alimentare",
  allegato_biologico_asilo: "Allegato Biologico Asilo",
  allegato_biologico_dentisti: "Allegato Biologico Dentisti",
  pee_azienda: "Piano Emergenza Aziendale",
  pee_comune: "Piano Emergenza Comunale",
  haccp: "Manuale HACCP",
  haccp_forms: "Schede Autocontrollo HACCP",
  duvri: "DUVRI",
  pos: "POS (Piano Operativo Sicurezza)",
};

type Category = "master" | "allegati" | "complementari";

const DOC_CATEGORY: Record<string, Category> = {
  dvr_master: "master",
  allegato_mmc: "allegati",
  allegato_vdt: "allegati",
  allegato_stress: "allegati",
  allegato_gestanti: "allegati",
  allegato_incendio: "allegati",
  allegato_microclima: "allegati",
  allegato_microclima_severo: "allegati",
  allegato_biologico_alimentare: "allegati",
  allegato_biologico_asilo: "allegati",
  allegato_biologico_dentisti: "allegati",
  pee_azienda: "complementari",
  pee_comune: "complementari",
  haccp: "complementari",
  haccp_forms: "complementari",
  duvri: "complementari",
  pos: "complementari",
};

const CATEGORY_META: Record<
  Category,
  {
    label: string;
    icon: typeof FileText;
    accent: "navy" | "violet" | "sky";
  }
> = {
  master: { label: "DVR Master", icon: FileText, accent: "navy" },
  allegati: { label: "Allegati DVR", icon: Paperclip, accent: "violet" },
  complementari: { label: "Documenti Complementari", icon: Files, accent: "sky" },
};

const CATEGORY_ORDER: Category[] = ["master", "allegati", "complementari"];

const IN_PROGRESS_STATUSES = new Set(["pending", "in_progress", "generating"]);
const FAILED_STATUSES = new Set(["failed", "error", "bozza"]);

type StatusFilter = "ALL" | "ready" | "in_progress" | "failed";

function matchesFilter(doc: DocumentoGenerato, filter: StatusFilter): boolean {
  if (filter === "ALL") return true;
  if (filter === "ready") return DOWNLOADABLE_DOC_STATUSES.has(doc.status);
  if (filter === "in_progress") return IN_PROGRESS_STATUSES.has(doc.status);
  if (filter === "failed") return FAILED_STATUSES.has(doc.status);
  return true;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleDateString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

interface DocumentiTabProps {
  aziendaId: string;
  documenti: DocumentoGenerato[];
  onRefresh: () => void;
}

export default function DocumentiTab({
  aziendaId,
  documenti,
  onRefresh,
}: DocumentiTabProps) {
  const [downloading, setDownloading] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");

  const total = documenti.length;
  const readyCount = documenti.filter(
    (d) => DOWNLOADABLE_DOC_STATUSES.has(d.status) && d.file_path,
  ).length;
  const inProgressDocs = documenti.filter((d) =>
    IN_PROGRESS_STATUSES.has(d.status),
  );
  const inProgressCount = inProgressDocs.length;
  const staleCount = documenti.filter((d) => d.stale_snapshot).length;
  const hasStale = staleCount > 0;

  const newestCreatedAt = useMemo(() => {
    if (documenti.length === 0) return null;
    return [...documenti].sort((a, b) =>
      a.created_at < b.created_at ? 1 : -1,
    )[0].created_at;
  }, [documenti]);

  const newestInProgressAt = useMemo(() => {
    if (inProgressDocs.length === 0) return null;
    return [...inProgressDocs].sort((a, b) =>
      a.created_at < b.created_at ? 1 : -1,
    )[0].created_at;
  }, [inProgressDocs]);

  const filtered = documenti.filter((d) => matchesFilter(d, statusFilter));

  const grouped = useMemo(() => {
    const map: Record<Category, DocumentoGenerato[]> = {
      master: [],
      allegati: [],
      complementari: [],
    };
    for (const doc of filtered) {
      const cat = DOC_CATEGORY[doc.tipo_documento] ?? "complementari";
      map[cat].push(doc);
    }
    for (const cat of CATEGORY_ORDER) {
      map[cat].sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
    }
    return map;
  }, [filtered]);

  async function handleDownload(doc: DocumentoGenerato) {
    if (downloading) return;
    setDownloading(doc.id);
    try {
      await downloadFile(`/api/v1/documenti/${doc.id}/download`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Download fallito");
    } finally {
      setDownloading(null);
    }
  }

  async function handleRegenerate(doc: DocumentoGenerato) {
    if (regenerating) return;
    setRegenerating(doc.id);
    try {
      await apiCall(`/api/v1/aziende/${aziendaId}/documents/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tipi_documento: [doc.tipo_documento] }),
      });
      toast.success("Rigenerazione avviata");
      onRefresh();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Rigenerazione fallita",
      );
    } finally {
      setRegenerating(null);
    }
  }

  const subtitle =
    total === 0
      ? "Nessun documento ancora"
      : `${total} ${total === 1 ? "documento" : "documenti"}${
          newestCreatedAt
            ? ` · ultima generazione ${formatRelative(newestCreatedAt)}`
            : ""
        }`;

  const filterOptions: { value: StatusFilter; label: string }[] = [
    { value: "ALL", label: "Tutti" },
    { value: "ready", label: "Pronti" },
    { value: "in_progress", label: "In generazione" },
    { value: "failed", label: "Falliti" },
  ];

  return (
    <Panel accent="sky">
      <PanelHeader
        icon={FileText}
        title="Documenti Generati"
        subtitle={subtitle}
        accent="sky"
      />

      {total === 0 ? (
        <EmptyState
          icon={FileText}
          title="Nessun documento generato"
          body='Clicca "Genera Documenti" in alto per avviare la generazione.'
        />
      ) : (
        <div className="px-6 py-5">
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="Totale documenti" value={total} />
            <StatTile label="Pronti" value={readyCount} tone="ok" />
            <StatTile
              label="In generazione"
              value={inProgressCount}
              sublabel={
                newestInProgressAt ? formatRelative(newestInProgressAt) : undefined
              }
            />
            <StatTile
              label="Da rigenerare"
              value={staleCount}
              tone={staleCount > 0 ? "warn" : "default"}
            />
          </div>

          {hasStale && (
            <div
              className="mb-4 flex items-start gap-2 rounded-md border border-[rgba(155,104,41,0.3)] bg-[rgba(155,104,41,0.06)] px-3 py-2.5 text-[13px] text-[#9b6829]"
              role="status"
            >
              <ShieldAlert className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>
                Il sopralluogo è stato modificato dopo l&apos;ultima
                generazione di alcuni documenti — i contenuti potrebbero
                essere disallineati. Rigenera i documenti contrassegnati per
                aggiornarli.
              </span>
            </div>
          )}

          <div className="mb-4 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-[12px] text-[#64748d]">
              <Filter className="h-3.5 w-3.5" strokeWidth={1.75} />
              Filtra
            </span>
            <div className="flex flex-wrap items-center gap-1">
              {filterOptions.map((opt) => {
                const active = statusFilter === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setStatusFilter(opt.value)}
                    className={
                      "inline-flex items-center rounded-md px-2.5 py-1 text-[12px] font-medium transition-colors " +
                      (active
                        ? "bg-primary text-white"
                        : "border border-[#e5edf5] text-[#273951] hover:bg-[#f6f9fc]")
                    }
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>

          {filtered.length === 0 ? (
            <p className="px-1 py-6 text-center text-[13px] text-[#64748d]">
              Nessun documento per il filtro selezionato.
            </p>
          ) : (
            <div className="flex flex-col gap-6">
              {CATEGORY_ORDER.map((cat) => {
                const docs = grouped[cat];
                if (docs.length === 0) return null;
                const meta = CATEGORY_META[cat];
                const Icon = meta.icon;
                return (
                  <section key={cat}>
                    <div className="mb-2 flex items-center gap-2">
                      <Icon
                        className="h-3.5 w-3.5 text-[#64748d]"
                        strokeWidth={1.75}
                      />
                      <h4 className="font-heading text-[13px] font-semibold tracking-[-0.005em] text-[#061b31]">
                        {meta.label}
                      </h4>
                      <span className="tnum inline-flex items-center rounded-md border border-[#e5edf5] bg-[#f6f9fc] px-1.5 py-0.5 text-[11px] font-medium text-[#273951]">
                        {docs.length}
                      </span>
                      <span
                        aria-hidden
                        className="ml-1 h-px flex-1 bg-[#e5edf5]"
                      />
                    </div>

                    <div className="overflow-hidden rounded-md border border-[#e5edf5]">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Documento</TableHead>
                            <TableHead className="w-[80px]">Versione</TableHead>
                            <TableHead className="w-[140px]">Stato</TableHead>
                            <TableHead className="w-[180px]">Generato</TableHead>
                            <TableHead className="w-[200px] text-right">
                              Azioni
                            </TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {docs.map((doc) => {
                            const label =
                              DOC_TYPE_LABELS[doc.tipo_documento] ??
                              doc.tipo_documento;
                            const canDownload =
                              DOWNLOADABLE_DOC_STATUSES.has(doc.status) &&
                              !!doc.file_path;
                            const isDownloading = downloading === doc.id;
                            const isRegenerating = regenerating === doc.id;
                            const statusLabel =
                              docStatusLabels[doc.status] ?? doc.status;
                            const statusStyle =
                              docStatusStyles[doc.status] ??
                              docStatusStyles.pending;
                            return (
                              <TableRow key={doc.id}>
                                <TableCell>
                                  <div className="flex flex-col gap-0.5">
                                    <div className="flex items-center gap-2">
                                      <span className="text-[13px] font-medium text-[#061b31]">
                                        {label}
                                      </span>
                                      {doc.stale_snapshot && (
                                        <StatusPill className="bg-[rgba(155,104,41,0.12)] text-[#9b6829] border border-[rgba(155,104,41,0.3)]">
                                          Da rigenerare
                                        </StatusPill>
                                      )}
                                    </div>
                                    <span className="text-[11px] text-[#64748d]">
                                      {doc.edited_in_gdocs ? (
                                        <span className="inline-flex items-center gap-1">
                                          <ExternalLink
                                            className="h-3 w-3"
                                            strokeWidth={1.75}
                                          />
                                          Modificato in Google Docs
                                        </span>
                                      ) : (
                                        "—"
                                      )}
                                    </span>
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <span className="tnum text-[13px] text-[#273951]">
                                    v{doc.versione}
                                  </span>
                                </TableCell>
                                <TableCell>
                                  <div className="flex flex-col gap-1">
                                    <StatusPill className={statusStyle}>
                                      {statusLabel}
                                    </StatusPill>
                                    {doc.error_message && (
                                      <span
                                        className="text-[11px] text-[#b51648] truncate max-w-[180px]"
                                        title={doc.error_message}
                                      >
                                        {doc.error_message}
                                      </span>
                                    )}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <div className="flex flex-col gap-0.5">
                                    <span className="tnum text-[13px] text-[#273951]">
                                      {formatDate(doc.created_at)}
                                    </span>
                                    <span className="tnum text-[11px] text-[#64748d]">
                                      {formatRelative(doc.created_at)}
                                      {doc.generated_by_name
                                        ? ` · ${doc.generated_by_name}`
                                        : ""}
                                    </span>
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <div className="flex items-center justify-end gap-1">
                                    <button
                                      type="button"
                                      onClick={() => handleDownload(doc)}
                                      disabled={!canDownload || isDownloading}
                                      className="inline-flex items-center gap-1 rounded-md border border-[#e5edf5] bg-white px-2 py-1 text-[12px] font-medium text-[#273951] hover:bg-[#f6f9fc] disabled:cursor-not-allowed disabled:opacity-50"
                                    >
                                      <Download
                                        className="h-3.5 w-3.5"
                                        strokeWidth={1.75}
                                      />
                                      Scarica
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => handleRegenerate(doc)}
                                      disabled={isRegenerating}
                                      className="inline-flex items-center gap-1 rounded-md border border-[#e5edf5] bg-white px-2 py-1 text-[12px] font-medium text-[#273951] hover:bg-[#f6f9fc] disabled:cursor-not-allowed disabled:opacity-50"
                                    >
                                      <RotateCw
                                        className={
                                          "h-3.5 w-3.5 " +
                                          (isRegenerating ? "animate-spin" : "")
                                        }
                                        strokeWidth={1.75}
                                      />
                                      Rigenera
                                    </button>
                                  </div>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  </section>
                );
              })}
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
