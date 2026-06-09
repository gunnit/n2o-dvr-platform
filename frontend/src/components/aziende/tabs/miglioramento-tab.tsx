"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Check,
  ListPlus,
  Pencil,
  Plus,
  Save,
  Sparkles,
  Target,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";

import {
  EmptyState,
  Panel,
  PanelHeader,
  StatusPill,
} from "@/components/aziende/tabs/_shared";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useApi } from "@/hooks/use-api";
import type { LivelloRischio } from "@/types";

interface MiglioramentoTabProps {
  aziendaId: string;
}

interface MisuraMiglioramento {
  id: string;
  azienda_id: string;
  pericolo_valutazione_id: string | null;
  misura: string;
  misura_miglioramento: string | null;
  procedura: string | null;
  risorse: string | null;
  responsabile: string | null;
  scadenza: string | null;
  priorita: string | null;
  ordine: number;
  created_at: string;
  updated_at: string;
}

// Editable subset that matches MisuraMiglioramentoCreate / Update on the
// backend. `ordine` is set server-side at creation; we only let the user
// drive the visible business fields here.
interface MisuraDraft {
  misura: string;
  misura_miglioramento: string;
  procedura: string;
  risorse: string;
  responsabile: string;
  scadenza: string;
  priorita: string;
}

const EMPTY_DRAFT: MisuraDraft = {
  misura: "",
  misura_miglioramento: "",
  procedura: "",
  risorse: "",
  responsabile: "",
  scadenza: "",
  priorita: "",
};

const LIVELLO_OPTIONS: { value: LivelloRischio; label: string }[] = [
  { value: "ACCETTABILE", label: "Accettabile" },
  { value: "MODESTO", label: "Modesto" },
  { value: "GRAVE", label: "Grave" },
  { value: "GRAVISSIMO", label: "Gravissimo" },
];

// #72 — the "responsabile" of a misura is one of three roles in the N2O
// workflow. Kept as a plain list so the same options drive both the inline
// editor and the create dialog. Free-text legacy/AI values are preserved by
// appending the current value as an extra option when it isn't one of these.
const RESPONSABILE_OPTIONS = ["Datore di Lavoro", "RSPP", "Preposto"];

// #71 — a small library of standard organisational measures N2O adds to most
// piani di miglioramento. One click drops the row in pre-filled; the operator
// can still edit it afterwards. `misura` is the risk/finding, the rest mirror
// the MisuraDraft fields.
const PREDEFINED_MISURE: {
  label: string;
  draft: MisuraDraft;
}[] = [
  {
    label: "Nomina telematica RLS (portale INAIL)",
    draft: {
      misura: "Comunicazione del nominativo del RLS all'INAIL",
      misura_miglioramento:
        "Inviare la nomina telematica del RLS presso il portale INAIL.",
      procedura: "",
      risorse: "",
      responsabile: "Datore di Lavoro",
      scadenza: "",
      priorita: "MODESTO",
    },
  },
  {
    label: "Formazione lavoratori (Accordo Stato-Regioni)",
    draft: {
      misura: "Formazione/aggiornamento dei lavoratori non completa",
      misura_miglioramento:
        "Erogare la formazione obbligatoria dei lavoratori ai sensi dell'Accordo Stato-Regioni 21/12/2011 e s.m.i.",
      procedura: "",
      risorse: "",
      responsabile: "Datore di Lavoro",
      scadenza: "",
      priorita: "GRAVE",
    },
  },
  {
    label: "Nomina Medico Competente / sorveglianza sanitaria",
    draft: {
      misura: "Sorveglianza sanitaria non attivata",
      misura_miglioramento:
        "Nominare il Medico Competente e attivare la sorveglianza sanitaria (artt. 18 e 41 D.Lgs. 81/2008).",
      procedura: "",
      risorse: "",
      responsabile: "Datore di Lavoro",
      scadenza: "",
      priorita: "GRAVE",
    },
  },
  {
    label: "Designazione addetti emergenze",
    draft: {
      misura: "Addetti antincendio e primo soccorso non designati/formati",
      misura_miglioramento:
        "Designare e formare gli addetti alla gestione delle emergenze (antincendio e primo soccorso).",
      procedura: "",
      risorse: "",
      responsabile: "Datore di Lavoro",
      scadenza: "",
      priorita: "GRAVE",
    },
  },
  {
    label: "Riunione periodica (art. 35)",
    draft: {
      misura: "Riunione periodica di sicurezza non effettuata",
      misura_miglioramento:
        "Convocare la riunione periodica annuale ex art. 35 D.Lgs. 81/2008.",
      procedura: "",
      risorse: "",
      responsabile: "Datore di Lavoro",
      scadenza: "",
      priorita: "MODESTO",
    },
  },
];

// Color rail for the priorita cell. Mirrors LIVELLO_BAR in rischi-tab.
const LIVELLO_BAR: Record<LivelloRischio, string> = {
  ACCETTABILE: "bg-[#15be53]",
  MODESTO: "bg-[#9b6829]",
  GRAVE: "bg-[#003d74]",
  GRAVISSIMO: "bg-[#b51648]",
};

const LIVELLO_PILL: Record<LivelloRischio, string> = {
  ACCETTABILE:
    "bg-[rgba(21,190,83,0.2)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
  MODESTO:
    "bg-[rgba(155,104,41,0.12)] text-[#9b6829] border border-[rgba(155,104,41,0.3)]",
  GRAVE:
    "bg-[rgba(0,61,116,0.12)] text-primary border border-[rgba(0,61,116,0.3)]",
  GRAVISSIMO:
    "bg-[rgba(234,34,97,0.08)] text-[#b51648] border border-[rgba(234,34,97,0.3)]",
};

const NEUTRAL_PILL =
  "bg-[#f6f9fc] text-[#273951] border border-[#e5edf5]";

function normalizeLivello(raw: string | null | undefined): LivelloRischio | null {
  if (!raw) return null;
  const upper = raw.trim().toUpperCase();
  if (
    upper === "ACCETTABILE" ||
    upper === "MODESTO" ||
    upper === "GRAVE" ||
    upper === "GRAVISSIMO"
  ) {
    return upper as LivelloRischio;
  }
  return null;
}

function PriorityCell({ priorita }: { priorita: string | null }) {
  const livello = normalizeLivello(priorita);
  if (livello) {
    const labelMap: Record<LivelloRischio, string> = {
      ACCETTABILE: "Accettabile",
      MODESTO: "Modesto",
      GRAVE: "Grave",
      GRAVISSIMO: "Gravissimo",
    };
    return (
      <div className="flex items-center gap-2">
        <span
          aria-hidden
          className={"h-3.5 w-1 rounded-full " + LIVELLO_BAR[livello]}
        />
        <StatusPill className={LIVELLO_PILL[livello]}>
          {labelMap[livello]}
        </StatusPill>
      </div>
    );
  }
  if (!priorita || priorita.trim() === "") {
    return <span className="text-[#64748d]">—</span>;
  }
  return <StatusPill className={NEUTRAL_PILL}>{priorita}</StatusPill>;
}

export default function MiglioramentoTab({ aziendaId }: MiglioramentoTabProps) {
  const { apiFetch } = useApi();

  const [rows, setRows] = useState<MisuraMiglioramento[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create dialog state
  const [createOpen, setCreateOpen] = useState(false);
  const [createDraft, setCreateDraft] = useState<MisuraDraft>(EMPTY_DRAFT);
  const [creating, setCreating] = useState(false);

  // Inline edit state — id of row currently being edited, plus its draft.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<MisuraDraft>(EMPTY_DRAFT);
  const [savingEdit, setSavingEdit] = useState(false);

  // Delete confirm state
  const [deleteRow, setDeleteRow] = useState<MisuraMiglioramento | null>(null);
  const [deleting, setDeleting] = useState(false);

  // AI batch-generation state. The endpoint can take ~10-30s for a wide
  // azienda (5 in-flight OpenAI calls server-side), so we keep the button
  // disabled and surface a spinner the whole time rather than firing the
  // request twice.
  const [generatingAi, setGeneratingAi] = useState(false);

  // #70 — after an inline save succeeds we flash a green "Salvato" badge on
  // that row for ~1.8s so the operator gets a clear visual confirmation
  // beyond the toast.
  const [savedFlashId, setSavedFlashId] = useState<string | null>(null);

  // #71 — predefined-measures picker state.
  const [predefOpen, setPredefOpen] = useState(false);
  const [addedPredef, setAddedPredef] = useState<Set<number>>(new Set());
  const [addingPredef, setAddingPredef] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<MisuraMiglioramento[]>(
        `/api/v1/aziende/${aziendaId}/misure-miglioramento`,
      );
      setRows(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Caricamento del piano di miglioramento non riuscito.",
      );
    } finally {
      setLoading(false);
    }
  }, [apiFetch, aziendaId]);

  useEffect(() => {
    load();
  }, [load]);

  // Backend already orders by (ordine, created_at). We re-sort client-side
  // for safety after optimistic inserts that don't yet know the final ordine.
  const sortedRows = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      if (a.ordine !== b.ordine) return a.ordine - b.ordine;
      return a.created_at.localeCompare(b.created_at);
    });
    return copy;
  }, [rows]);

  function startEdit(row: MisuraMiglioramento) {
    setEditingId(row.id);
    setEditDraft({
      misura: row.misura,
      misura_miglioramento: row.misura_miglioramento ?? "",
      procedura: row.procedura ?? "",
      risorse: row.risorse ?? "",
      responsabile: row.responsabile ?? "",
      scadenza: row.scadenza ?? "",
      priorita: row.priorita ?? "",
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setEditDraft(EMPTY_DRAFT);
  }

  function draftToPayload(draft: MisuraDraft) {
    // Empty optional strings become null so the backend stores absent
    // values cleanly and the UI doesn't render hollow "—".
    return {
      misura: draft.misura.trim(),
      misura_miglioramento: draft.misura_miglioramento.trim() || null,
      procedura: draft.procedura.trim() || null,
      risorse: draft.risorse.trim() || null,
      responsabile: draft.responsabile.trim() || null,
      scadenza: draft.scadenza.trim() || null,
      priorita: draft.priorita.trim() || null,
    };
  }

  async function handleCreate() {
    if (!createDraft.misura.trim()) {
      toast.error("La misura è obbligatoria.");
      return;
    }
    setCreating(true);
    try {
      const payload = draftToPayload(createDraft);
      // Place new rows at the bottom so the auto-seeded high-priority items
      // stay visually anchored at the top until the operator reorders.
      const nextOrdine =
        rows.length === 0
          ? 0
          : Math.max(...rows.map((r) => r.ordine)) + 1;
      await apiFetch<MisuraMiglioramento>(
        `/api/v1/aziende/${aziendaId}/misure-miglioramento`,
        {
          method: "POST",
          body: JSON.stringify({ ...payload, ordine: nextOrdine }),
        },
      );
      // #17a — Always refetch after a successful write instead of relying
      // on optimistic local merges. Two concurrent saves (the operator's
      // reported repro: clicking Salva twice on a slow connection) could
      // race the setRows callbacks and silently drop a row; an explicit
      // server reload makes "ciò che vedo == ciò che è salvato" the
      // single source of truth.
      setCreateDraft(EMPTY_DRAFT);
      setCreateOpen(false);
      await load();
      toast.success("Misura salvata");
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Errore durante il salvataggio",
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleSaveEdit() {
    if (!editingId) return;
    if (!editDraft.misura.trim()) {
      toast.error("La misura è obbligatoria.");
      return;
    }
    const savedId = editingId;
    setSavingEdit(true);
    const prev = rows;
    const payload = draftToPayload(editDraft);
    // Optimistic update so the row stops looking "in flight" immediately.
    setRows((curr) =>
      curr.map((r) => (r.id === editingId ? { ...r, ...payload } : r)),
    );
    try {
      await apiFetch<MisuraMiglioramento>(
        `/api/v1/aziende/${aziendaId}/misure-miglioramento/${editingId}`,
        {
          method: "PUT",
          body: JSON.stringify(payload),
        },
      );
      // #17a — Refetch after PUT so the grid reflects whatever the server
      // actually stored (incl. updated_at, server-normalized fields). The
      // earlier optimistic-only path could desync if a second save fired
      // before the first PATCH response merged back into state.
      setEditingId(null);
      setEditDraft(EMPTY_DRAFT);
      await load();
      // #70 — green confirmation flash on the just-saved row.
      setSavedFlashId(savedId);
      window.setTimeout(() => {
        setSavedFlashId((cur) => (cur === savedId ? null : cur));
      }, 1800);
      toast.success("Misura salvata");
    } catch (err) {
      setRows(prev);
      toast.error(
        err instanceof Error
          ? err.message
          : "Errore durante il salvataggio",
      );
    } finally {
      setSavingEdit(false);
    }
  }

  async function addPredefined(index: number) {
    const item = PREDEFINED_MISURE[index];
    if (!item) return;
    setAddingPredef(index);
    try {
      const payload = draftToPayload(item.draft);
      const nextOrdine =
        rows.length === 0 ? 0 : Math.max(...rows.map((r) => r.ordine)) + 1;
      await apiFetch<MisuraMiglioramento>(
        `/api/v1/aziende/${aziendaId}/misure-miglioramento`,
        {
          method: "POST",
          body: JSON.stringify({ ...payload, ordine: nextOrdine }),
        },
      );
      await load();
      setAddedPredef((curr) => new Set(curr).add(index));
      toast.success("Misura predefinita aggiunta");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Errore durante il salvataggio",
      );
    } finally {
      setAddingPredef(null);
    }
  }

  async function handleGenerateAi() {
    setGeneratingAi(true);
    try {
      const res = await apiFetch<{
        generated: number;
        skipped: number;
        pericoli_considered: number;
      }>(
        `/api/v1/aziende/${aziendaId}/misure-miglioramento/genera-da-rischi`,
        { method: "POST" },
      );
      await load();
      if (res.pericoli_considered === 0) {
        toast.info(
          "Nessun pericolo con indice ≥ 5: valuta prima i rischi, poi riprova.",
        );
      } else if (res.generated === 0 && res.skipped > 0) {
        toast.info(
          `Tutti i ${res.skipped} pericoli sopra soglia hanno già delle misure. Elimina le righe esistenti per rigenerare.`,
        );
      } else {
        toast.success(
          `${res.generated} misure generate (${res.skipped} pericoli saltati perché già coperti).`,
        );
      }
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Generazione AI non riuscita.",
      );
    } finally {
      setGeneratingAi(false);
    }
  }

  async function handleDelete() {
    if (!deleteRow) return;
    setDeleting(true);
    const prev = rows;
    setRows((curr) => curr.filter((r) => r.id !== deleteRow.id));
    try {
      await apiFetch(
        `/api/v1/aziende/${aziendaId}/misure-miglioramento/${deleteRow.id}`,
        { method: "DELETE" },
      );
      setDeleteRow(null);
      // #17a — Same refetch-after-write pattern as create/update so the
      // grid never drifts from the server after a destructive action.
      await load();
      toast.success("Misura eliminata");
    } catch (err) {
      setRows(prev);
      toast.error(
        err instanceof Error
          ? err.message
          : "Eliminazione non riuscita.",
      );
    } finally {
      setDeleting(false);
    }
  }

  const subtitle = loading
    ? "Caricamento..."
    : `${rows.length} ${rows.length === 1 ? "misura" : "misure"}`;

  return (
    <Panel accent="navy">
      <PanelHeader
        icon={Target}
        title="Piano di Miglioramento"
        subtitle={subtitle}
        accent="navy"
        action={
          <div className="flex items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => {
                setAddedPredef(new Set());
                setPredefOpen(true);
              }}
              title="Aggiungi una misura organizzativa standard"
            >
              <ListPlus className="h-3.5 w-3.5" strokeWidth={2} />
              Predefinite
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={handleGenerateAi}
              disabled={generatingAi}
              title="Genera misure di miglioramento per ogni pericolo con indice ≥ 5"
            >
              <Sparkles className="h-3.5 w-3.5" strokeWidth={2} />
              {generatingAi ? "Generazione..." : "Genera con AI"}
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() => {
                setCreateDraft(EMPTY_DRAFT);
                setCreateOpen(true);
              }}
            >
              <Plus className="h-3.5 w-3.5" strokeWidth={2} />
              Aggiungi misura
            </Button>
          </div>
        }
      />

      <div className="p-6">
        {error && (
          <div className="mb-4 rounded-md border border-[rgba(234,34,97,0.25)] bg-[rgba(234,34,97,0.04)] px-3 py-2 text-[13px] text-[#b51648]">
            {error}
          </div>
        )}

        {!loading && sortedRows.length === 0 && !error ? (
          <EmptyState
            icon={Target}
            title="Nessuna misura di miglioramento"
            body="Genera in un colpo solo le misure di prevenzione/protezione per ogni pericolo valutato con indice ≥ 5, oppure aggiungile manualmente."
            action={
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  size="sm"
                  onClick={handleGenerateAi}
                  disabled={generatingAi}
                >
                  <Sparkles className="h-3.5 w-3.5" strokeWidth={2} />
                  {generatingAi ? "Generazione..." : "Genera con AI"}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setCreateDraft(EMPTY_DRAFT);
                    setCreateOpen(true);
                  }}
                >
                  <Plus className="h-3.5 w-3.5" strokeWidth={2} />
                  Aggiungi misura
                </Button>
              </div>
            }
          />
        ) : (
          <div className="overflow-hidden rounded-md border border-[#e5edf5]">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[100px]">Priorità</TableHead>
                  <TableHead className="w-[18%]">Rischio</TableHead>
                  <TableHead className="w-[18%]">Misura di Miglioramento</TableHead>
                  <TableHead className="w-[18%]">Attività</TableHead>
                  <TableHead className="w-[10%]">Risorse</TableHead>
                  <TableHead className="w-[10%]">Responsabile</TableHead>
                  <TableHead className="w-[10%]">Scadenza</TableHead>
                  <TableHead className="w-[120px] text-right">Azioni</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && sortedRows.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={8}
                      className="py-8 text-center text-[13px] text-[#64748d]"
                    >
                      Caricamento...
                    </TableCell>
                  </TableRow>
                )}
                {sortedRows.map((row) => {
                  const isEditing = editingId === row.id;
                  return (
                    <TableRow key={row.id} className="align-top">
                      {/* Priorità */}
                      <TableCell className="py-3 whitespace-normal">
                        {isEditing ? (
                          <select
                            value={editDraft.priorita}
                            onChange={(e) =>
                              setEditDraft((d) => ({
                                ...d,
                                priorita: e.target.value,
                              }))
                            }
                            className="h-9 w-full min-w-0 rounded-md border border-[#e5edf5] bg-white px-2 text-[13px] text-[#061b31] outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
                          >
                            <option value="">—</option>
                            {LIVELLO_OPTIONS.map((o) => (
                              <option key={o.value} value={o.value}>
                                {o.label}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <PriorityCell priorita={row.priorita} />
                        )}
                      </TableCell>

                      {/* Rischio */}
                      <TableCell className="py-3 whitespace-normal">
                        {isEditing ? (
                          <Textarea
                            value={editDraft.misura}
                            onChange={(e) =>
                              setEditDraft((d) => ({
                                ...d,
                                misura: e.target.value,
                              }))
                            }
                            rows={3}
                            className="min-h-16"
                            placeholder="Descrivi il rischio identificato"
                          />
                        ) : (
                          <p className="whitespace-pre-wrap break-words text-[13px] leading-[1.5] text-[#061b31] line-clamp-3">
                            {row.misura}
                          </p>
                        )}
                      </TableCell>

                      {/* Misura di Miglioramento */}
                      <TableCell className="py-3 whitespace-normal">
                        {isEditing ? (
                          <Textarea
                            value={editDraft.misura_miglioramento}
                            onChange={(e) =>
                              setEditDraft((d) => ({
                                ...d,
                                misura_miglioramento: e.target.value,
                              }))
                            }
                            rows={3}
                            className="min-h-16"
                            placeholder="Misura di prevenzione/protezione"
                          />
                        ) : row.misura_miglioramento ? (
                          <p className="whitespace-pre-wrap break-words text-[13px] leading-[1.5] text-[#061b31] line-clamp-3">
                            {row.misura_miglioramento}
                          </p>
                        ) : (
                          <span className="text-[#64748d]">—</span>
                        )}
                      </TableCell>

                      {/* Attività */}
                      <TableCell className="py-3 whitespace-normal">
                        {isEditing ? (
                          <Textarea
                            value={editDraft.procedura}
                            onChange={(e) =>
                              setEditDraft((d) => ({
                                ...d,
                                procedura: e.target.value,
                              }))
                            }
                            rows={3}
                            className="min-h-16"
                            placeholder="Attività correlata"
                          />
                        ) : row.procedura ? (
                          <p className="whitespace-pre-wrap break-words text-[13px] leading-[1.5] text-[#273951] line-clamp-3">
                            {row.procedura}
                          </p>
                        ) : (
                          <span className="text-[#64748d]">—</span>
                        )}
                      </TableCell>

                      {/* Risorse */}
                      <TableCell className="py-3 whitespace-normal">
                        {isEditing ? (
                          <Input
                            value={editDraft.risorse}
                            onChange={(e) =>
                              setEditDraft((d) => ({
                                ...d,
                                risorse: e.target.value,
                              }))
                            }
                            className="h-9"
                            placeholder="Risorse necessarie"
                          />
                        ) : row.risorse ? (
                          <span className="block break-words text-[13px] text-[#273951]" title={row.risorse}>
                            {row.risorse}
                          </span>
                        ) : (
                          <span className="text-[#64748d]">—</span>
                        )}
                      </TableCell>

                      {/* Responsabile */}
                      <TableCell className="py-3 whitespace-normal">
                        {isEditing ? (
                          <select
                            value={editDraft.responsabile}
                            onChange={(e) =>
                              setEditDraft((d) => ({
                                ...d,
                                responsabile: e.target.value,
                              }))
                            }
                            className="h-9 w-full min-w-0 rounded-md border border-[#e5edf5] bg-white px-2 text-[13px] text-[#061b31] outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
                          >
                            <option value="">—</option>
                            {RESPONSABILE_OPTIONS.map((o) => (
                              <option key={o} value={o}>
                                {o}
                              </option>
                            ))}
                            {editDraft.responsabile &&
                              !RESPONSABILE_OPTIONS.includes(
                                editDraft.responsabile,
                              ) && (
                                <option value={editDraft.responsabile}>
                                  {editDraft.responsabile}
                                </option>
                              )}
                          </select>
                        ) : row.responsabile ? (
                          <span className="block break-words text-[13px] text-[#273951]" title={row.responsabile}>
                            {row.responsabile}
                          </span>
                        ) : (
                          <span className="text-[#64748d]">—</span>
                        )}
                      </TableCell>

                      {/* Scadenza */}
                      <TableCell className="py-3 whitespace-normal">
                        {isEditing ? (
                          <Input
                            value={editDraft.scadenza}
                            onChange={(e) =>
                              setEditDraft((d) => ({
                                ...d,
                                scadenza: e.target.value,
                              }))
                            }
                            className="h-9"
                            placeholder="Es. Entro 6 mesi"
                          />
                        ) : row.scadenza ? (
                          <span className="block break-words text-[13px] text-[#273951]" title={row.scadenza}>
                            {row.scadenza}
                          </span>
                        ) : (
                          <span className="text-[#64748d]">—</span>
                        )}
                      </TableCell>

                      {/* Actions */}
                      <TableCell className="py-3 text-right">
                        {isEditing ? (
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon-sm"
                              onClick={cancelEdit}
                              disabled={savingEdit}
                              title="Annulla"
                            >
                              <X className="h-3.5 w-3.5" strokeWidth={2} />
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              onClick={handleSaveEdit}
                              disabled={savingEdit}
                              title="Salva misura"
                            >
                              <Save className="h-3.5 w-3.5" strokeWidth={2} />
                              {savingEdit ? "Salvo..." : "Salva"}
                            </Button>
                          </div>
                        ) : savedFlashId === row.id ? (
                          <div className="flex justify-end">
                            <span className="inline-flex h-7 items-center gap-1 rounded-md bg-[rgba(21,190,83,0.12)] px-2 text-[12px] font-medium text-[#108c3d]">
                              <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                              Salvato
                            </span>
                          </div>
                        ) : (
                          <div className="flex justify-end gap-1">
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => startEdit(row)}
                              title="Modifica misura"
                            >
                              <Pencil
                                className="h-3.5 w-3.5"
                                strokeWidth={1.75}
                              />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => setDeleteRow(row)}
                              title="Elimina misura"
                              className="text-[#b51648] hover:bg-[rgba(234,34,97,0.06)] hover:text-[#b51648]"
                            >
                              <Trash2
                                className="h-3.5 w-3.5"
                                strokeWidth={1.75}
                              />
                            </Button>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Aggiungi voce al piano</DialogTitle>
            <DialogDescription>
              Compila i campi del Programma di Miglioramento (DVR §4.1).
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="misura-misura">
                Rischio <span className="text-[#b51648]">*</span>
              </Label>
              <Textarea
                id="misura-misura"
                value={createDraft.misura}
                onChange={(e) =>
                  setCreateDraft((d) => ({ ...d, misura: e.target.value }))
                }
                rows={3}
                placeholder="Descrivi il rischio identificato"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="misura-misura-miglioramento">Misura di Miglioramento</Label>
              <Textarea
                id="misura-misura-miglioramento"
                value={createDraft.misura_miglioramento}
                onChange={(e) =>
                  setCreateDraft((d) => ({
                    ...d,
                    misura_miglioramento: e.target.value,
                  }))
                }
                rows={2}
                placeholder="Misura di prevenzione/protezione"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="misura-procedura">Attività</Label>
              <Textarea
                id="misura-procedura"
                value={createDraft.procedura}
                onChange={(e) =>
                  setCreateDraft((d) => ({
                    ...d,
                    procedura: e.target.value,
                  }))
                }
                rows={2}
                placeholder="Attività correlata"
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="misura-risorse">Risorse</Label>
                <Input
                  id="misura-risorse"
                  value={createDraft.risorse}
                  onChange={(e) =>
                    setCreateDraft((d) => ({
                      ...d,
                      risorse: e.target.value,
                    }))
                  }
                  placeholder="Risorse necessarie"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="misura-responsabile">Responsabile</Label>
                <select
                  id="misura-responsabile"
                  value={createDraft.responsabile}
                  onChange={(e) =>
                    setCreateDraft((d) => ({
                      ...d,
                      responsabile: e.target.value,
                    }))
                  }
                  className="h-10 w-full min-w-0 rounded-md border border-[#e5edf5] bg-white px-3 text-sm text-[#061b31] outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
                >
                  <option value="">—</option>
                  {RESPONSABILE_OPTIONS.map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                  {createDraft.responsabile &&
                    !RESPONSABILE_OPTIONS.includes(createDraft.responsabile) && (
                      <option value={createDraft.responsabile}>
                        {createDraft.responsabile}
                      </option>
                    )}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="misura-scadenza">Scadenza</Label>
                <Input
                  id="misura-scadenza"
                  value={createDraft.scadenza}
                  onChange={(e) =>
                    setCreateDraft((d) => ({
                      ...d,
                      scadenza: e.target.value,
                    }))
                  }
                  placeholder="Es. Entro 6 mesi, 31/12/2026"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="misura-priorita">Priorità</Label>
                <select
                  id="misura-priorita"
                  value={createDraft.priorita}
                  onChange={(e) =>
                    setCreateDraft((d) => ({
                      ...d,
                      priorita: e.target.value,
                    }))
                  }
                  className="h-10 w-full min-w-0 rounded-md border border-[#e5edf5] bg-white px-3 text-sm text-[#061b31] outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
                >
                  <option value="">—</option>
                  {LIVELLO_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setCreateOpen(false)}
              disabled={creating}
            >
              Annulla
            </Button>
            <Button
              type="button"
              onClick={handleCreate}
              disabled={creating || !createDraft.misura.trim()}
            >
              {creating ? "Salvataggio..." : "Salva misura"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* #71 — Predefined measures picker */}
      <Dialog open={predefOpen} onOpenChange={setPredefOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Misure predefinite</DialogTitle>
            <DialogDescription>
              Aggiungi al piano una misura organizzativa standard. Potrai
              modificarla dopo l&apos;inserimento.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2">
            {PREDEFINED_MISURE.map((item, index) => {
              const added = addedPredef.has(index);
              return (
                <div
                  key={item.label}
                  className="flex items-start justify-between gap-3 rounded-md border border-[#e5edf5] bg-[#f9fbfd] px-3 py-2.5"
                >
                  <div className="min-w-0 space-y-0.5">
                    <p className="text-[13px] font-medium text-[#061b31]">
                      {item.label}
                    </p>
                    <p className="text-[12px] leading-[1.5] text-[#64748d] break-words">
                      {item.draft.misura_miglioramento}
                    </p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant={added ? "outline" : undefined}
                    onClick={() => addPredefined(index)}
                    disabled={added || addingPredef !== null}
                    className="flex-shrink-0"
                  >
                    {added ? (
                      <>
                        <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                        Aggiunta
                      </>
                    ) : addingPredef === index ? (
                      "Aggiungo..."
                    ) : (
                      <>
                        <Plus className="h-3.5 w-3.5" strokeWidth={2} />
                        Aggiungi
                      </>
                    )}
                  </Button>
                </div>
              );
            })}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setPredefOpen(false)}
            >
              Chiudi
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirm dialog */}
      <Dialog
        open={deleteRow !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteRow(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <div className="flex items-start gap-3">
              <span className="inline-flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md bg-[rgba(234,34,97,0.08)]">
                <Trash2 className="h-4 w-4 text-[#b51648]" strokeWidth={2} />
              </span>
              <div className="space-y-1.5">
                <DialogTitle>Eliminare misura?</DialogTitle>
                <DialogDescription>
                  La misura verrà rimossa dal Programma di Miglioramento.
                  L&apos;operazione non puo&apos; essere annullata.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setDeleteRow(null)}
              disabled={deleting}
            >
              Annulla
            </Button>
            <Button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="bg-[#b51648] text-white hover:bg-[#9b1340] focus-visible:ring-[#b51648]/30"
            >
              {deleting ? "Eliminazione..." : "Elimina"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Panel>
  );
}
