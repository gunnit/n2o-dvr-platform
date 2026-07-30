"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  FileText,
  RefreshCw,
  Download,
  Loader2,
  History,
  Lock,
  User as UserIcon,
  Pencil,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Label } from "@/components/ui/label";
import { formatRelative } from "@/lib/ui/relative-time";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  CATEGORY_META,
  CATEGORY_ORDER,
  documentTypes,
  isBusyStatus,
  isEditedInline,
  isReadyStatus,
} from "@/components/documents/document-types";
import {
  DocumentCard,
  DocumentCardActions,
  DocumentCardHeader,
  DocumentCardMeta,
  DocumentStatusBadge,
} from "@/components/documents/document-card";
import { VersionHistory } from "@/components/documents/version-history";
import type { Azienda, DocumentoGenerato } from "@/types";
import { apiCall, downloadFile } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { useTenantVocabulary } from "@/hooks/use-tenant-vocabulary";
import { useEntitlementsContext } from "@/components/billing/entitlements-provider";
import { isDocTypeGated } from "@/hooks/use-entitlements";
import { usePermissions } from "@/hooks/use-permissions";
import { DOCUMENTS_GENERATE } from "@/lib/permissions";
import { Select } from "@/components/ui/select";
import { aziendaOptionLabel } from "@/lib/ui/azienda-label";
import { EmptyStateCard } from "@/components/ui/empty-state";

export default function DocumentsPage() {
  const vocab = useTenantVocabulary();
  // Plan gating is advisory here: `isDocTypeGated` returns false whenever we
  // cannot be sure (no entitlements loaded, backend still in shadow mode), and
  // the backend's 402 remains the only authority (INV-5).
  const { entitlements } = useEntitlementsContext();
  // The *other* visibility axis: a field operator collects the data, an
  // office operator finalises it. Reading and downloading stay open to both —
  // only the act of producing a new version is role-gated.
  const { can } = usePermissions();
  const canGenerate = can(DOCUMENTS_GENERATE);
  const [aziende, setAziende] = useState<Azienda[]>([]);
  const [selectedAziendaId, setSelectedAziendaId] = useState<string>("");
  const [documenti, setDocumenti] = useState<DocumentoGenerato[]>([]);
  const [loadingAziende, setLoadingAziende] = useState(true);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [generatingAll, setGeneratingAll] = useState(false);
  const [generatingTypes, setGeneratingTypes] = useState<Set<string>>(new Set());
  const [historyTipo, setHistoryTipo] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const router = useRouter();

  // Fetch aziende list
  useEffect(() => {
    apiCall<Azienda[]>("/api/v1/aziende")
      .then(setAziende)
      .catch(() => {})
      .finally(() => setLoadingAziende(false));
  }, []);

  // Fetch documents for selected azienda
  const fetchDocumenti = useCallback(async () => {
    if (!selectedAziendaId) {
      setDocumenti([]);
      return;
    }
    setLoadingDocs(true);
    try {
      const docs = await apiCall<DocumentoGenerato[]>(
        `/api/v1/aziende/${selectedAziendaId}/documents`
      );
      setDocumenti(docs);
    } catch {
      setDocumenti([]);
    } finally {
      setLoadingDocs(false);
    }
  }, [selectedAziendaId]);

  useEffect(() => {
    fetchDocumenti();
  }, [fetchDocumenti]);

  // Poll for status when documents are generating
  useEffect(() => {
    const hasGenerating = documenti.some(
      (d) => d.status === "pending" || d.status === "generating" || d.status === "in_progress"
    );

    if (hasGenerating && selectedAziendaId) {
      pollRef.current = setInterval(() => {
        apiCall<DocumentoGenerato[]>(
          `/api/v1/aziende/${selectedAziendaId}/documents`
        )
          .then(setDocumenti)
          .catch(() => {});
      }, 3000);
    }

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [documenti, selectedAziendaId]);

  function getDocStatus(typeKey: string): DocumentoGenerato | undefined {
    return documenti
      .filter((d) => d.tipo_documento === typeKey)
      .sort((a, b) => b.versione - a.versione)[0];
  }

  // US-4.1 AC2: PEE cards are blocked until the DVR Master has a successful
  // generation. We derive the flag from the latest DVR row's status.
  const DVR_DEPENDENT_TYPES = new Set(["pee_azienda", "pee_comune"]);
  const latestDvr = getDocStatus("dvr_master");
  const dvrReady =
    latestDvr?.status === "completed" || latestDvr?.status === "ready";

  const [generateError, setGenerateError] = useState<string | null>(null);

  // US-4.4: HACCP forms subset selection dialog. Renders once when the
  // operator clicks "Genera" on the haccp_forms card. Default = all 16
  // selected so "OK" with no edits matches the legacy behaviour.
  const HACCP_FORM_CODES: { code: string; title: string }[] = [
    { code: "SA-01", title: "Pulizia e sanificazione" },
    { code: "SA-02", title: "Controllo temperature frigoriferi" },
    { code: "SA-03", title: "Controllo temperature congelatori" },
    { code: "SA-04", title: "Controllo cottura alimenti" },
    { code: "SA-05", title: "Controllo scongelamento" },
    { code: "SA-06", title: "Controllo ricevimento merci" },
    { code: "SA-07", title: "Conservazione e stoccaggio" },
    { code: "SA-08", title: "Controllo derattizzazione e disinfestazione" },
    { code: "SA-09", title: "Manutenzione attrezzature e impianti" },
    { code: "SA-10", title: "Acqua potabile" },
    { code: "SA-11", title: "Formazione del personale" },
    { code: "SA-12", title: "Stato di salute degli operatori" },
    { code: "SA-13", title: "Tracciabilità e rintracciabilità" },
    { code: "SA-14", title: "Gestione non conformità" },
    { code: "SA-15", title: "Allergeni" },
    { code: "SA-16", title: "Riesame del piano HACCP" },
  ];
  const [haccpDialogOpen, setHaccpDialogOpen] = useState(false);
  const [haccpSelected, setHaccpSelected] = useState<Set<string>>(
    new Set(HACCP_FORM_CODES.map((f) => f.code)),
  );

  async function postGenerate(typeKey: string, options?: Record<string, unknown>) {
    setGenerateError(null);
    setGeneratingTypes((prev) => new Set(prev).add(typeKey));
    try {
      await apiCall(`/api/v1/aziende/${selectedAziendaId}/documents/generate`, {
        method: "POST",
        body: JSON.stringify({
          tipo_documento: typeKey,
          ...(options ? { options } : {}),
        }),
      });
      await fetchDocumenti();
    } catch (err) {
      setGenerateError(
        err instanceof Error ? err.message : "Generazione non riuscita",
      );
    } finally {
      setGeneratingTypes((prev) => {
        const next = new Set(prev);
        next.delete(typeKey);
        return next;
      });
    }
  }

  async function handleGenerate(typeKey: string) {
    if (!selectedAziendaId) return;
    // Short-circuit on DVR-dependent types so we surface the Italian message
    // immediately without a round-trip. Backend guard is still authoritative.
    if (DVR_DEPENDENT_TYPES.has(typeKey) && !dvrReady) {
      setGenerateError("Genera prima il DVR Master");
      return;
    }
    // The card's button is already disabled in this case; the guard is here for
    // the keyboard/programmatic path, not as the paywall.
    if (isDocTypeGated(entitlements, typeKey)) {
      setGenerateError(
        "Questo tipo di documento non è incluso nel tuo piano. Passa a un piano superiore per generarlo.",
      );
      return;
    }
    // US-4.4: open the subset dialog instead of firing immediately.
    if (typeKey === "haccp_forms") {
      // Default to all selected each time the dialog opens so the operator
      // never starts in a "nothing selected" state by accident.
      setHaccpSelected(new Set(HACCP_FORM_CODES.map((f) => f.code)));
      setHaccpDialogOpen(true);
      return;
    }
    await postGenerate(typeKey);
  }

  function toggleHaccpForm(code: string) {
    setHaccpSelected((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  async function confirmHaccpGenerate() {
    const codes = HACCP_FORM_CODES
      .map((f) => f.code)
      .filter((c) => haccpSelected.has(c));
    setHaccpDialogOpen(false);
    if (codes.length === 0) {
      setGenerateError("Seleziona almeno una scheda da generare");
      return;
    }
    await postGenerate("haccp_forms", { selected_codes: codes });
  }

  async function handleGenerateAll() {
    if (!selectedAziendaId) return;
    setGenerateError(null);
    // Asking the backend for types this plan does not include earns a 402 for
    // the whole batch. Send what the tenant is entitled to instead.
    const tipi = documentTypes
      .map((d) => d.key)
      .filter((key) => !isDocTypeGated(entitlements, key));
    if (tipi.length === 0) {
      setGenerateError(
        "Nessun tipo di documento incluso nel tuo piano. Aggiorna il piano per generare i documenti.",
      );
      return;
    }
    setGeneratingAll(true);
    try {
      await apiCall(`/api/v1/aziende/${selectedAziendaId}/documents/batch`, {
        method: "POST",
        body: JSON.stringify({ tipi_documento: tipi }),
      });
      await fetchDocumenti();
    } catch (err) {
      // Swallowing this used to make a quota rejection look like a no-op: the
      // spinner stopped, nothing appeared, and no message explained why.
      setGenerateError(
        err instanceof Error ? err.message : "Generazione non riuscita",
      );
    } finally {
      setGeneratingAll(false);
    }
  }

  const selectedAzienda = aziende.find((a) => a.id === selectedAziendaId);

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="type-h1">Documenti</h1>
          <p className="type-body mt-2">
            {vocab.documentsLead}
          </p>
        </div>
        {selectedAziendaId && canGenerate && (
          <button
            type="button"
            onClick={handleGenerateAll}
            disabled={generatingAll}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {generatingAll ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" strokeWidth={2.5} />
            )}
            Genera Tutti
          </button>
        )}
      </div>

      {/* Azienda Selector */}
      <div className="rounded-md border border-[#e5edf5] bg-white p-6 shadow-stripe-ambient">
        <div className="space-y-2">
          <Label htmlFor="azienda-select">Seleziona Azienda</Label>
          {loadingAziende ? (
            <p className="text-sm text-[#64748d]">Caricamento aziende...</p>
          ) : aziende.length === 0 ? (
            <p className="text-sm text-[#64748d]">
              Nessuna azienda registrata. Aggiungi un&apos;azienda per iniziare.
            </p>
          ) : (
            <Select
              id="azienda-select"
              value={selectedAziendaId}
              onChange={(e) => setSelectedAziendaId(e.target.value)}
              className="max-w-md"
            >
              <option value="">— Seleziona un&apos;azienda —</option>
              {aziende.map((a) => (
                <option key={a.id} value={a.id}>
                  {aziendaOptionLabel(a)}
                </option>
              ))}
            </Select>
          )}
        </div>
      </div>

      {/* Document Grid */}
      {!selectedAziendaId ? (
        <EmptyStateCard
          icon={FileText}
          title="Nessuna azienda selezionata"
          body="Scegli un cliente qui sopra per vedere i documenti già pronti e generare quelli mancanti."
        />
      ) : loadingDocs ? (
        <p className="text-muted-foreground">Caricamento documenti...</p>
      ) : (
        <>
          {selectedAzienda && (
            <p className="text-sm text-muted-foreground">
              Documenti per <span className="font-medium text-foreground">{selectedAzienda.ragione_sociale}</span>
            </p>
          )}
          {generateError && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {generateError}
              <button
                type="button"
                onClick={() => setGenerateError(null)}
                className="ml-2 underline"
              >
                Chiudi
              </button>
            </div>
          )}
          <div className="space-y-8">
          {CATEGORY_ORDER.map((category) => {
            const items = documentTypes.filter((d) => d.category === category);
            if (items.length === 0) return null;
            const catMeta = CATEGORY_META[category];
            return (
              <div key={category} className="space-y-3">
                <div className="flex items-baseline gap-3 border-b border-dashed border-[#e5edf5] pb-2">
                  <span className={cn("h-2 w-2 rounded-full", catMeta.rail)} />
                  <h3 className="font-heading text-[14px] font-semibold text-[#061b31]">
                    {catMeta.label}
                  </h3>
                  <span className="tnum text-[12px] text-[#94a3b8]">
                    {items.length} document{items.length === 1 ? "o" : "i"}
                  </span>
                </div>

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {items.map((docType) => {
                    const existing = getDocStatus(docType.key);
                    const isGenerating = generatingTypes.has(docType.key);
                    const status = existing?.status;
                    const versionCount = documenti.filter(
                      (d) => d.tipo_documento === docType.key,
                    ).length;
                    // US-4.1: visually mark PEE cards as blocked when the DVR
                    // Master has not yet been generated. The generate button
                    // stays clickable so the Italian error message can still
                    // surface; the block itself is enforced by the backend.
                    const blockedByDvr =
                      DVR_DEPENDENT_TYPES.has(docType.key) && !dvrReady;
                    // Plan lock. Unlike the DVR dependency — which the operator
                    // can clear themselves, so its button stays clickable — this
                    // one cannot be cleared from this page, so the button is
                    // disabled and the way out is a link to /billing.
                    const gatedByPlan = isDocTypeGated(entitlements, docType.key);
                    const ActionIcon = docType.icon;
                    const isReady = Boolean(status && isReadyStatus(status));
                    const isBusy =
                      isGenerating || Boolean(status && isBusyStatus(status));

                    return (
                      <DocumentCard
                        key={docType.key}
                        rail={catMeta.rail}
                        texture={catMeta.texture}
                        ready={isReady}
                        dimmed={blockedByDvr || gatedByPlan}
                      >
                        <DocumentCardHeader
                          icon={ActionIcon}
                          accent={catMeta.accent}
                          title={docType.name}
                          eyebrow={
                            <>
                              <span className="tnum">{docType.pages}</span>{" "}
                              pagine · complessità{" "}
                              {docType.complexity.toLowerCase()}
                            </>
                          }
                          trailing={
                            status ? (
                              <DocumentStatusBadge
                                status={status}
                                title={
                                  status === "bozza" && existing?.error_message
                                    ? existing.error_message
                                    : undefined
                                }
                              />
                            ) : (
                              <span className="rounded-md border border-dashed border-[#e5edf5] px-2 py-[3px] text-[11.5px] font-medium text-[#94a3b8] whitespace-nowrap">
                                Mai generato
                              </span>
                            )
                          }
                        />

                        {blockedByDvr && (
                          <Callout tone="warn" dense className="px-2 py-1 text-[11.5px]">
                            Genera prima il DVR Master
                          </Callout>
                        )}

                        {gatedByPlan && (
                          <Callout
                            tone="warn"
                            dense
                            className="px-2 py-1.5 text-[11.5px]"
                            icon={<Lock className="h-3 w-3" strokeWidth={2} />}
                            action={
                              <Link
                                href="/billing"
                                className="font-semibold underline underline-offset-2"
                              >
                                Passa a un piano superiore
                              </Link>
                            }
                          >
                            Non incluso nel piano
                          </Callout>
                        )}

                        {existing && (
                          <DocumentCardMeta
                            items={[
                              <span
                                key="v"
                                className="tnum font-semibold text-[#273951]"
                              >
                                v{existing.versione}
                              </span>,
                              formatRelative(existing.created_at),
                              existing.generated_by_name && (
                                <span key="author">
                                  <UserIcon
                                    className="mr-1 inline h-3 w-3 align-[-2px]"
                                    strokeWidth={1.75}
                                  />
                                  {existing.generated_by_name}
                                </span>
                              ),
                              isEditedInline(existing) && (
                                <span
                                  key="edited"
                                  className="inline-flex items-center gap-1 text-[#273951]"
                                  title="Versione creata con modifiche fatte nell'editor del browser"
                                >
                                  <Pencil
                                    className="h-2.5 w-2.5"
                                    strokeWidth={2}
                                  />
                                  Modificato
                                </span>
                              ),
                            ]}
                          />
                        )}

                        {status === "bozza" && existing?.error_message && (
                          <p className="text-[11.5px] text-[#8a5c23]">
                            {existing.error_message}
                          </p>
                        )}

                        <DocumentCardActions>
                          {/* Action weight follows what the operator actually
                              wants and what the tenant pays for. On a ready
                              document the download is the goal, so it carries
                              the primary weight; "Rigenera" burns AI credits
                              (metered — see app/billing) and drops to a quiet
                              icon, where it used to be the loudest control on
                              every finished card. */}
                          {isReady && (
                            <Button
                              size="sm"
                              onClick={async () => {
                                try {
                                  await downloadFile(
                                    `/api/v1/documenti/${existing!.id}/download`,
                                  );
                                } catch (e) {
                                  alert(
                                    (e as Error).message || "Download fallito",
                                  );
                                }
                              }}
                            >
                              <Download />
                              Scarica
                            </Button>
                          )}
                          {/* In-browser preview + inline editing. HACCP
                              schede are a .zip payload with no docx to
                              preview, so they stay download-only. */}
                          {isReady && docType.key !== "haccp_forms" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                router.push(`/documents/${existing!.id}`)
                              }
                              aria-label={`Modifica ${docType.name} nel browser`}
                            >
                              <Pencil />
                              Modifica
                            </Button>
                          )}
                          {/* Hidden, not disabled: a greyed-out "Genera" on
                              every card invites a field operator to keep
                              clicking. The download actions above stay. */}
                          {canGenerate && (
                            <Button
                              size={isReady ? "icon-sm" : "sm"}
                              variant={isReady ? "ghost" : "default"}
                              onClick={() => handleGenerate(docType.key)}
                              disabled={isBusy || gatedByPlan}
                              title={
                                gatedByPlan
                                  ? "Il tuo piano non include questo tipo di documento"
                                  : isReady
                                    ? "Rigenera — consuma crediti AI"
                                    : undefined
                              }
                              aria-label={
                                isReady
                                  ? `Rigenera ${docType.name}`
                                  : undefined
                              }
                            >
                              {isBusy ? (
                                <Loader2 className="animate-spin" />
                              ) : (
                                <RefreshCw />
                              )}
                              {isReady
                                ? null
                                : existing?.status === "bozza"
                                  ? "Riprova"
                                  : "Genera"}
                            </Button>
                          )}
                          {versionCount > 0 && (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="ml-auto"
                              onClick={() => setHistoryTipo(docType.key)}
                              title={`Storia versioni (${versionCount})`}
                              aria-label={`Storia versioni ${docType.name}`}
                            >
                              <History />
                              <span className="tnum">v{versionCount}</span>
                            </Button>
                          )}
                        </DocumentCardActions>
                      </DocumentCard>
                    );
                  })}
                </div>
              </div>
            );
          })}
          </div>
        </>
      )}

      {/* US-4.4: HACCP forms subset selection. Defaults to all 16 + index. */}
      <Dialog open={haccpDialogOpen} onOpenChange={setHaccpDialogOpen}>
        <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Schede HACCP da generare</DialogTitle>
            <DialogDescription>
              Seleziona le schede da includere nel pacchetto .zip. Tutte le
              schede sono pre-selezionate; deseleziona quelle non necessarie.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {haccpSelected.size} di {HACCP_FORM_CODES.length} selezionate
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    setHaccpSelected(
                      new Set(HACCP_FORM_CODES.map((f) => f.code)),
                    )
                  }
                >
                  Seleziona tutte
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setHaccpSelected(new Set())}
                >
                  Deseleziona tutte
                </Button>
              </div>
            </div>
            <div className="grid gap-1.5 sm:grid-cols-2">
              {HACCP_FORM_CODES.map((f) => {
                const checked = haccpSelected.has(f.code);
                return (
                  <label
                    key={f.code}
                    className="flex items-start gap-2 rounded-md border border-input p-2 text-xs transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleHaccpForm(f.code)}
                      className="mt-0.5 accent-primary"
                    />
                    <span>
                      <span className="font-mono font-semibold">{f.code}</span>{" "}
                      <span className="text-muted-foreground">— {f.title}</span>
                    </span>
                  </label>
                );
              })}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setHaccpDialogOpen(false)}>
              Annulla
            </Button>
            <Button
              onClick={confirmHaccpGenerate}
              disabled={haccpSelected.size === 0}
            >
              Genera ({haccpSelected.size})
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <VersionHistory
        open={historyTipo !== null}
        onOpenChange={(open) => {
          if (!open) setHistoryTipo(null);
        }}
        tipoDocumento={historyTipo ?? ""}
        tipoDocumentoLabel={
          (historyTipo && documentTypes.find((d) => d.key === historyTipo)?.name) ||
          ""
        }
        aziendaId={selectedAziendaId}
        aziendaLabel={selectedAzienda?.ragione_sociale ?? ""}
        versions={
          historyTipo
            ? documenti
                .filter((d) => d.tipo_documento === historyTipo)
                .sort((a, b) => b.versione - a.versione)
            : []
        }
        onRestored={fetchDocumenti}
      />
    </div>
  );
}
