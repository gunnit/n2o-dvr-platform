"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronDown,
  Download,
  ExternalLink,
  FileText,
  Filter,
  Pencil,
  RotateCw,
  ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";

import {
  EmptyState,
  Panel,
  PanelHeader,
  StatTile,
} from "@/components/aziende/tabs/_shared";
import {
  DocumentCard,
  DocumentCardActions,
  DocumentCardHeader,
  DocumentCardMeta,
  DocumentStatusBadge,
} from "@/components/documents/document-card";
import {
  CATEGORY_META,
  CATEGORY_ORDER,
  type DocCategory,
  docCategoryFor,
  documentTypeFor,
  documentTypeFullLabel,
  isBusyStatus,
  isEditedInline,
  isReadyStatus,
} from "@/components/documents/document-types";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { apiCall, downloadFile } from "@/lib/api-client";
import { formatRelative } from "@/lib/ui/relative-time";
import { cn } from "@/lib/utils";
import type { DocumentoGenerato } from "@/types";

type StatusFilter = "ALL" | "ready" | "in_progress" | "failed";

const FAILED_STATUSES = new Set(["failed", "error", "bozza"]);

function matchesFilter(doc: DocumentoGenerato, filter: StatusFilter): boolean {
  if (filter === "ALL") return true;
  if (filter === "ready") return isReadyStatus(doc.status);
  if (filter === "in_progress") return isBusyStatus(doc.status);
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

/**
 * One card per document *type*, headed by its newest version. This tab used to
 * render every version as its own table row, so a company with 17 documents at
 * v3 produced 51 undifferentiated rows and the thing an operator actually
 * wanted — "is the current DVR ready?" — was buried among superseded copies.
 * Older versions now live behind the `v3` disclosure on their own card.
 */
type TypeGroup = {
  key: string;
  latest: DocumentoGenerato;
  older: DocumentoGenerato[];
};

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
  const router = useRouter();
  const [downloading, setDownloading] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const total = documenti.length;
  // Status-only gating (here and on the card actions below): the download
  // endpoint serves the DB file_content, and rows minted by
  // save-edited-version (or legacy gdoc syncs) can have file_path NULL.
  const readyCount = documenti.filter((d) => isReadyStatus(d.status)).length;
  const inProgressDocs = documenti.filter((d) => isBusyStatus(d.status));
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

  // Filter first, then group: with "Falliti" active a type appears only if it
  // has a failed version, and the card is headed by that version rather than
  // by a newer successful one that the filter excluded.
  const grouped = useMemo(() => {
    const byType = new Map<string, DocumentoGenerato[]>();
    for (const doc of filtered) {
      const list = byType.get(doc.tipo_documento);
      if (list) list.push(doc);
      else byType.set(doc.tipo_documento, [doc]);
    }

    const map: Record<DocCategory, TypeGroup[]> = {
      dvr: [],
      allegati: [],
      emergenza: [],
      haccp: [],
      contratti: [],
    };
    for (const [key, versions] of byType) {
      const sorted = [...versions].sort((a, b) => b.versione - a.versione);
      map[docCategoryFor(key)].push({
        key,
        latest: sorted[0],
        older: sorted.slice(1),
      });
    }
    for (const cat of CATEGORY_ORDER) {
      map[cat].sort((a, b) =>
        a.latest.created_at < b.latest.created_at ? 1 : -1,
      );
    }
    return map;
  }, [filtered]);

  function toggleExpanded(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

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
                const groups = grouped[cat];
                if (groups.length === 0) return null;
                const meta = CATEGORY_META[cat];
                return (
                  <section key={cat}>
                    <div className="mb-3 flex items-center gap-2">
                      <span
                        className={cn("h-2 w-2 rounded-full", meta.rail)}
                        aria-hidden
                      />
                      <h4 className="font-heading text-[13px] font-semibold tracking-[-0.005em] text-[#061b31]">
                        {meta.label}
                      </h4>
                      <span className="tnum inline-flex items-center rounded-md border border-[#e5edf5] bg-[#f6f9fc] px-1.5 py-0.5 text-[11px] font-medium text-[#273951]">
                        {groups.length}
                      </span>
                      <span
                        aria-hidden
                        className="ml-1 h-px flex-1 bg-[#e5edf5]"
                      />
                    </div>

                    <div className="grid gap-3 lg:grid-cols-2">
                      {groups.map(({ key, latest, older }) => {
                        const catalogue = documentTypeFor(key);
                        const Icon = catalogue?.icon ?? FileText;
                        const ready = isReadyStatus(latest.status);
                        // HACCP schede are a .zip payload — no docx to open
                        // in the in-browser editor.
                        const canEdit = ready && key !== "haccp_forms";
                        const isDownloading = downloading === latest.id;
                        const isRegenerating = regenerating === latest.id;
                        const isOpen = expanded.has(key);

                        return (
                          <DocumentCard
                            key={key}
                            rail={meta.rail}
                            texture={meta.texture}
                            ready={ready}
                          >
                            <DocumentCardHeader
                              icon={Icon}
                              accent={meta.accent}
                              title={documentTypeFullLabel(key)}
                              eyebrow={
                                catalogue && (
                                  <>
                                    <span className="tnum">
                                      {catalogue.pages}
                                    </span>{" "}
                                    pagine
                                  </>
                                )
                              }
                              trailing={
                                <DocumentStatusBadge
                                  status={latest.status}
                                  title={latest.error_message ?? undefined}
                                />
                              }
                            />

                            <DocumentCardMeta
                              items={[
                                <span
                                  key="v"
                                  className="tnum font-semibold text-[#273951]"
                                >
                                  v{latest.versione}
                                </span>,
                                <span key="d" className="tnum">
                                  {formatDate(latest.created_at)}
                                </span>,
                                formatRelative(latest.created_at),
                                latest.generated_by_name,
                                latest.edited_in_gdocs ? (
                                  <span key="edited">
                                    <ExternalLink
                                      className="mr-1 inline h-3 w-3 align-[-2px]"
                                      strokeWidth={1.75}
                                    />
                                    Google Docs
                                  </span>
                                ) : isEditedInline(latest) ? (
                                  <span key="edited">
                                    <Pencil
                                      className="mr-1 inline h-3 w-3 align-[-2px]"
                                      strokeWidth={1.75}
                                    />
                                    Modificato
                                  </span>
                                ) : null,
                              ]}
                            />

                            {latest.stale_snapshot && (
                              <Callout
                                tone="warn"
                                dense
                                className="px-2 py-1 text-[11.5px]"
                              >
                                Sopralluogo cambiato dopo la generazione — da
                                rigenerare
                              </Callout>
                            )}

                            {latest.error_message && (
                              <p className="text-[11.5px] text-[#8a5c23]">
                                {latest.error_message}
                              </p>
                            )}

                            <DocumentCardActions>
                              {/* Download carries the primary weight and
                                  "Rigenera" drops to a quiet icon: regeneration
                                  burns metered AI credits, and as a full-width
                                  labelled button on every finished row it was
                                  the loudest control in the tab. */}
                              <Button
                                size="sm"
                                onClick={() => handleDownload(latest)}
                                disabled={!ready || isDownloading}
                              >
                                <Download />
                                Scarica
                              </Button>
                              {canEdit && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() =>
                                    router.push(`/documents/${latest.id}`)
                                  }
                                >
                                  <Pencil />
                                  Apri
                                </Button>
                              )}
                              <Button
                                size="icon-sm"
                                variant="ghost"
                                onClick={() => handleRegenerate(latest)}
                                disabled={isRegenerating}
                                title="Rigenera — consuma crediti AI"
                                aria-label={`Rigenera ${documentTypeFullLabel(key)}`}
                              >
                                <RotateCw
                                  className={isRegenerating ? "animate-spin" : ""}
                                />
                              </Button>
                              {older.length > 0 && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="ml-auto"
                                  onClick={() => toggleExpanded(key)}
                                  aria-expanded={isOpen}
                                  title={`${older.length} version${older.length === 1 ? "e" : "i"} precedent${older.length === 1 ? "e" : "i"}`}
                                >
                                  <ChevronDown
                                    className={cn(
                                      "transition-transform",
                                      isOpen && "rotate-180",
                                    )}
                                  />
                                  <span className="tnum">{older.length}</span>
                                </Button>
                              )}
                            </DocumentCardActions>

                            {isOpen && older.length > 0 && (
                              <ul className="-mt-1 flex flex-col divide-y divide-[#f1f5f9] rounded-md border border-[#eef2f7] bg-[#fbfdff]">
                                {older.map((doc) => (
                                  <li
                                    key={doc.id}
                                    className="flex items-center gap-2 px-2.5 py-1.5 text-[12px]"
                                  >
                                    <span className="tnum font-semibold text-[#273951]">
                                      v{doc.versione}
                                    </span>
                                    <span className="tnum text-[#64748d]">
                                      {formatDate(doc.created_at)}
                                    </span>
                                    {doc.generated_by_name && (
                                      <span className="truncate text-[#94a3b8]">
                                        {doc.generated_by_name}
                                      </span>
                                    )}
                                    <DocumentStatusBadge
                                      status={doc.status}
                                      className="ml-auto"
                                    />
                                    <Button
                                      size="icon-xs"
                                      variant="ghost"
                                      onClick={() => handleDownload(doc)}
                                      disabled={
                                        !isReadyStatus(doc.status) ||
                                        downloading === doc.id
                                      }
                                      title={`Scarica v${doc.versione}`}
                                      aria-label={`Scarica versione ${doc.versione}`}
                                    >
                                      <Download />
                                    </Button>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </DocumentCard>
                        );
                      })}
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
