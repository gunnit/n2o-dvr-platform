"use client";

import { useCallback, useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Pencil, Plus, Trash2, Users } from "lucide-react";
import { useApi } from "@/hooks/use-api";
import type { Ambiente, AttrezzaturaSpecialeCode, Persona } from "@/types";

interface StepPersoneProps {
  aziendaId: string;
  persone: Persona[];
  ambienti: Ambiente[];
  onChange: (persone: Persona[]) => void;
}

// 12 voci confermate da Luca via email 2026-04-24 (Week 1 review).
// "IMPIEGATO" è full-time per default; "IMPIEGATO PART-TIME" è voce separata.
// "CO CO CO" = collaborazione coordinata e continuativa.
const TIPOLOGIE_CONTRATTUALI = [
  "OPERAIO",
  "OPERAIO QUALIFICATO",
  "COLLABORATORE ESTERNO",
  "VOLONTARIO",
  "TIROCINANTE",
  "STAGISTA",
  "COADIUVANTE FAMILIARE",
  "IMPIEGATO",
  "IMPIEGATO PART-TIME",
  "OPERAIO EDILE",
  "CO CO CO",
  "DATORE DI LAVORO",
];

// User feedback 2026-04-28 (#7 + #8): replace the free-text "qualifiche" field
// with a fixed flag list. Codes mirror the backend enum and stay stable across
// label tweaks.
const ATTREZZATURE_SPECIALI: { code: AttrezzaturaSpecialeCode; label: string }[] = [
  { code: "lavori_in_quota", label: "Lavori in quota" },
  { code: "carrello_elevatore", label: "Carrello elevatore" },
  { code: "ple", label: "Piattaforma di lavoro elevabile (PLE)" },
  { code: "gru", label: "Gru" },
  { code: "ruspa_escavatore", label: "Ruspa / escavatore" },
  { code: "patente_cde", label: "Guida automezzi (patente C-D-E)" },
  { code: "adr", label: "Trasporto ADR (merci pericolose)" },
];

const RUOLI = [
  { key: "ruolo_datore_lavoro" as const, label: "Datore di Lavoro (DdL)", short: "DdL" },
  { key: "ruolo_rspp" as const, label: "RSPP", short: "RSPP" },
  { key: "ruolo_rls" as const, label: "RLS", short: "RLS" },
  { key: "ruolo_medico_competente" as const, label: "Medico Competente (MC)", short: "MC" },
  { key: "ruolo_primo_soccorso" as const, label: "Primo Soccorso", short: "PS" },
  { key: "ruolo_antincendio" as const, label: "Antincendio", short: "AI" },
  { key: "ruolo_preposto" as const, label: "Preposto", short: "Preposto" },
];

const CF_REGEX = /^[A-Z0-9]{16}$/;

function createEmptyPersona(aziendaId: string): Persona {
  return {
    id: crypto.randomUUID(),
    azienda_id: aziendaId,
    nominativo: "",
    codice_fiscale: null,
    mansione: null,
    tipologia_contrattuale: null,
    sesso: null,
    fascia_eta: null,
    ruolo_rspp: false,
    ruolo_rls: false,
    ruolo_primo_soccorso: false,
    ruolo_antincendio: false,
    ruolo_preposto: false,
    ruolo_datore_lavoro: false,
    ruolo_medico_competente: false,
    qualifiche: null,
    attrezzature_speciali: [],
    ambiente_ids: [],
  };
}

function roleBadges(p: Persona) {
  return RUOLI.filter((r) => p[r.key]).map((r) => (
    <Badge key={r.key} variant="secondary" className="text-xs">
      {r.short}
    </Badge>
  ));
}

export function StepPersone({
  aziendaId,
  persone,
  ambienti,
  onChange,
}: StepPersoneProps) {
  const { apiFetch } = useApi();
  // `editing` holds the staged draft when the modal is open.
  // `editingIndex === null` means we're adding a new persona; otherwise we're editing an existing row.
  const [editing, setEditing] = useState<Persona | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [cfError, setCfError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleteDialogIndex, setDeleteDialogIndex] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  const ambienteById = useCallback(
    (id: string) => ambienti.find((a) => a.id === id),
    [ambienti],
  );

  const openAdd = useCallback(() => {
    setEditing(createEmptyPersona(aziendaId));
    setEditingIndex(null);
    setCfError(null);
    setSaveError(null);
  }, [aziendaId]);

  const openEdit = useCallback(
    (index: number) => {
      // Defensive copy so cancel discards edits cleanly.
      setEditing({ ...persone[index] });
      setEditingIndex(index);
      setCfError(null);
      setSaveError(null);
    },
    [persone],
  );

  const closeModal = useCallback(() => {
    setEditing(null);
    setEditingIndex(null);
    setCfError(null);
    setSaveError(null);
  }, []);

  const validateEditing = useCallback((p: Persona): string | null => {
    if (p.codice_fiscale && !CF_REGEX.test(p.codice_fiscale)) {
      return "Codice fiscale non valido (16 caratteri alfanumerici)";
    }
    return null;
  }, []);

  // Derive CF validity synchronously from the staged value so the Save
  // button reflects it without needing a blur event (H-01 fix).
  const cfInvalid = !!(
    editing?.codice_fiscale && !CF_REGEX.test(editing.codice_fiscale)
  );

  const saveEditing = useCallback(async () => {
    if (!editing) return;
    const err = validateEditing(editing);
    if (err) {
      setCfError(err);
      return;
    }
    if (!editing.nominativo.trim()) {
      // Required field — surface inline by keeping the modal open.
      return;
    }
    setSaveError(null);
    setSaving(true);
    try {
      // Payload matches PersonaCreate / PersonaUpdate schemas on the backend.
      const payload = {
        nominativo: editing.nominativo,
        codice_fiscale: editing.codice_fiscale,
        mansione: editing.mansione,
        tipologia_contrattuale: editing.tipologia_contrattuale,
        sesso: editing.sesso,
        fascia_eta: editing.fascia_eta,
        ruolo_rspp: editing.ruolo_rspp,
        ruolo_rls: editing.ruolo_rls,
        ruolo_primo_soccorso: editing.ruolo_primo_soccorso,
        ruolo_antincendio: editing.ruolo_antincendio,
        ruolo_preposto: editing.ruolo_preposto,
        ruolo_datore_lavoro: editing.ruolo_datore_lavoro,
        ruolo_medico_competente: editing.ruolo_medico_competente,
        qualifiche: editing.qualifiche,
        attrezzature_speciali: editing.attrezzature_speciali,
        ambiente_ids: editing.ambiente_ids,
      };
      if (editingIndex === null) {
        const created = await apiFetch<Persona>(
          `/api/v1/aziende/${aziendaId}/persone`,
          {
            method: "POST",
            body: JSON.stringify(payload),
          },
        );
        onChange([...persone, created]);
      } else {
        const existing = persone[editingIndex];
        const updated = await apiFetch<Persona>(
          `/api/v1/aziende/${aziendaId}/persone/${existing.id}`,
          {
            method: "PUT",
            body: JSON.stringify(payload),
          },
        );
        onChange(persone.map((p, i) => (i === editingIndex ? updated : p)));
      }
      closeModal();
    } catch (e) {
      setSaveError(
        e instanceof Error ? e.message : "Errore durante il salvataggio",
      );
    } finally {
      setSaving(false);
    }
  }, [
    editing,
    editingIndex,
    onChange,
    persone,
    validateEditing,
    closeModal,
    apiFetch,
    aziendaId,
  ]);

  const removePersona = useCallback(
    async (index: number) => {
      const target = persone[index];
      setDeleting(true);
      try {
        await apiFetch(
          `/api/v1/aziende/${aziendaId}/persone/${target.id}`,
          { method: "DELETE" },
        );
        onChange(persone.filter((_, i) => i !== index));
        setDeleteDialogIndex(null);
      } catch (e) {
        // Surface the failure via alert so the operator knows the server
        // rejected the delete (e.g., FK constraint). Row stays in the table.
        alert(
          e instanceof Error
            ? `Errore eliminazione: ${e.message}`
            : "Errore eliminazione",
        );
      } finally {
        setDeleting(false);
      }
    },
    [persone, onChange, apiFetch, aziendaId],
  );

  const updateEditing = useCallback((fields: Partial<Persona>) => {
    setEditing((prev) => (prev ? { ...prev, ...fields } : prev));
  }, []);

  const toggleAmbienteAssignment = useCallback(
    (ambienteId: string) => {
      setEditing((prev) => {
        if (!prev) return prev;
        const has = prev.ambiente_ids.includes(ambienteId);
        return {
          ...prev,
          ambiente_ids: has
            ? prev.ambiente_ids.filter((id) => id !== ambienteId)
            : [...prev.ambiente_ids, ambienteId],
        };
      });
    },
    [],
  );

  const toggleAttrezzaturaSpeciale = useCallback(
    (code: AttrezzaturaSpecialeCode) => {
      setEditing((prev) => {
        if (!prev) return prev;
        const has = prev.attrezzature_speciali.includes(code);
        return {
          ...prev,
          attrezzature_speciali: has
            ? prev.attrezzature_speciali.filter((c) => c !== code)
            : [...prev.attrezzature_speciali, code],
        };
      });
    },
    [],
  );

  return (
    <div className="space-y-6">
      <div>
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h3 className="font-heading text-xl font-bold text-on-surface">
              Persone
            </h3>
            <p className="mt-1 text-sm text-on-surface-variant">
              Gestisci l&apos;elenco dei dipendenti e i relativi ruoli di
              sicurezza
            </p>
          </div>
          <Button onClick={openAdd}>
            <Plus className="mr-2 h-4 w-4" />
            Aggiungi persona
          </Button>
        </div>
        <div>
          {persone.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-muted-foreground">
              <Users className="h-10 w-10 opacity-40" />
              <p>
                Nessun dipendente aggiunto. Clicca &quot;Aggiungi persona&quot;
                per iniziare.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nominativo</TableHead>
                  <TableHead>Mansione</TableHead>
                  <TableHead>Ambienti</TableHead>
                  <TableHead>Ruoli</TableHead>
                  <TableHead className="w-[100px] text-right">Azioni</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {persone.map((p, index) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">
                      {p.nominativo || (
                        <span className="text-muted-foreground italic">
                          (senza nome)
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {p.mansione ?? "—"}
                    </TableCell>
                    <TableCell>
                      {p.ambiente_ids.length === 0 ? (
                        <span className="text-muted-foreground">—</span>
                      ) : (
                        <span className="text-xs">
                          {p.ambiente_ids
                            .map((id) => ambienteById(id)?.nome ?? "?")
                            .join(", ")}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {roleBadges(p).length > 0 ? (
                          roleBadges(p)
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => openEdit(index)}
                          aria-label="Modifica"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => setDeleteDialogIndex(index)}
                          aria-label="Elimina"
                        >
                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>

      {/* Add/Edit modal */}
      <Dialog
        open={editing !== null}
        onOpenChange={(open) => {
          if (!open) closeModal();
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl lg:max-w-5xl">
          <DialogHeader>
            <DialogTitle>
              {editingIndex === null ? "Aggiungi persona" : "Modifica persona"}
            </DialogTitle>
            <DialogDescription>
              Compila i dati anagrafici e assegna ruoli, ambienti e attrezzature speciali.
            </DialogDescription>
          </DialogHeader>

          {editing && (
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="persona-nome">
                    Nominativo <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="persona-nome"
                    value={editing.nominativo}
                    onChange={(e) =>
                      updateEditing({ nominativo: e.target.value })
                    }
                    placeholder="Nome e Cognome"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="persona-cf">Codice Fiscale</Label>
                  <Input
                    id="persona-cf"
                    value={editing.codice_fiscale ?? ""}
                    onChange={(e) => {
                      const upper = e.target.value.toUpperCase();
                      updateEditing({ codice_fiscale: upper || null });
                      if (cfError) setCfError(null);
                    }}
                    onBlur={(e) => {
                      const v = e.target.value;
                      if (v && !CF_REGEX.test(v)) {
                        setCfError(
                          "Codice fiscale non valido (16 caratteri alfanumerici)",
                        );
                      }
                    }}
                    placeholder="Es. RSSMRA80A01H501U"
                    maxLength={16}
                    className={
                      cfError || cfInvalid ? "border-destructive" : ""
                    }
                  />
                  {(cfError ||
                    (cfInvalid &&
                      "Codice fiscale non valido (16 caratteri alfanumerici)")) && (
                    <p className="text-xs text-destructive">
                      {cfError ??
                        "Codice fiscale non valido (16 caratteri alfanumerici)"}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="persona-mansione">Mansione</Label>
                  <Input
                    id="persona-mansione"
                    value={editing.mansione ?? ""}
                    onChange={(e) =>
                      updateEditing({ mansione: e.target.value || null })
                    }
                    placeholder="Es. Operaio, Impiegato"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="persona-contratto">
                    Tipologia Contrattuale
                  </Label>
                  <select
                    id="persona-contratto"
                    value={editing.tipologia_contrattuale ?? ""}
                    onChange={(e) =>
                      updateEditing({
                        tipologia_contrattuale: e.target.value || null,
                      })
                    }
                    className="h-9 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  >
                    <option value="">Seleziona tipo</option>
                    {TIPOLOGIE_CONTRATTUALI.map((tipo) => (
                      <option key={tipo} value={tipo}>
                        {tipo}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="persona-sesso">Sesso</Label>
                  <select
                    id="persona-sesso"
                    value={editing.sesso ?? ""}
                    onChange={(e) =>
                      updateEditing({
                        sesso: (e.target.value as "M" | "F") || null,
                      })
                    }
                    className="h-9 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  >
                    <option value="">Seleziona</option>
                    <option value="M">Maschio</option>
                    <option value="F">Femmina</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="persona-eta">Fascia Eta</Label>
                  <select
                    id="persona-eta"
                    value={editing.fascia_eta ?? ""}
                    onChange={(e) =>
                      updateEditing({
                        fascia_eta:
                          (e.target.value as ">18" | "15-18") || null,
                      })
                    }
                    className="h-9 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  >
                    <option value="">Seleziona</option>
                    <option value=">18">Maggiorenne (&gt;18)</option>
                    <option value="15-18">Minorenne (15-18)</option>
                  </select>
                </div>
              </div>

              {/* Ambienti assegnati — multi-select (US-1.4 AC1) */}
              <div className="space-y-2">
                <Label>Ambienti assegnati</Label>
                {ambienti.length === 0 ? (
                  <p className="rounded-md border border-dashed border-input p-3 text-xs text-muted-foreground">
                    Nessun ambiente ancora dichiarato. Torna allo Step 2
                    &quot;Ambienti&quot; per aggiungerli.
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {ambienti.map((a) => {
                      const checked = editing.ambiente_ids.includes(a.id);
                      return (
                        <label
                          key={a.id}
                          className="flex items-center gap-2 rounded-lg border border-input px-3 py-1.5 text-sm transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleAmbienteAssignment(a.id)}
                            className="accent-primary"
                          />
                          {a.nome || (a.tipo ?? "Ambiente")}
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Attrezzature speciali — fixed flag list + free-text note.
                  Replaces the previous free-text "qualifiche" field per
                  user feedback 2026-04-28 (#7 + #8). */}
              <div className="space-y-2">
                <Label>Attrezzature speciali</Label>
                <div className="flex flex-wrap gap-2">
                  {ATTREZZATURE_SPECIALI.map((a) => {
                    const checked = editing.attrezzature_speciali.includes(a.code);
                    return (
                      <label
                        key={a.code}
                        className="flex items-center gap-2 rounded-lg border border-input px-3 py-1.5 text-sm transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleAttrezzaturaSpeciale(a.code)}
                          className="accent-primary"
                        />
                        {a.label}
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="persona-qualifiche">Note / altre qualifiche</Label>
                <Textarea
                  id="persona-qualifiche"
                  value={editing.qualifiche ?? ""}
                  onChange={(e) =>
                    updateEditing({ qualifiche: e.target.value || null })
                  }
                  placeholder="Attestati, patenti, corsi di formazione non elencati sopra (es. antincendio medio rischio, HACCP)"
                  rows={3}
                />
              </div>

              {/* Ruoli di sicurezza */}
              <div className="space-y-2">
                <Label>Ruoli di Sicurezza</Label>
                <div className="flex flex-wrap gap-3">
                  {RUOLI.map((ruolo) => (
                    <label
                      key={ruolo.key}
                      className="flex items-center gap-2 rounded-lg border border-input px-3 py-1.5 text-sm transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                    >
                      <input
                        type="checkbox"
                        checked={editing[ruolo.key]}
                        onChange={(e) =>
                          updateEditing({ [ruolo.key]: e.target.checked })
                        }
                        className="accent-primary"
                      />
                      {ruolo.label}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {saveError && (
            <p className="text-sm text-destructive">{saveError}</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={closeModal} disabled={saving}>
              Annulla
            </Button>
            <Button
              onClick={saveEditing}
              disabled={
                !editing ||
                !editing.nominativo.trim() ||
                cfInvalid ||
                saving
              }
            >
              {saving ? "Salvataggio..." : "Salva"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog
        open={deleteDialogIndex !== null}
        onOpenChange={(open) => {
          if (!open && !deleting) setDeleteDialogIndex(null);
        }}
      >
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>Elimina persona</DialogTitle>
            <DialogDescription>
              Sei sicuro di voler eliminare{" "}
              {deleteDialogIndex !== null &&
              persone[deleteDialogIndex]?.nominativo
                ? persone[deleteDialogIndex].nominativo
                : "questa persona"}
              ? Questa azione non può essere annullata.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogIndex(null)}
              disabled={deleting}
            >
              Annulla
            </Button>
            <Button
              variant="destructive"
              disabled={deleting}
              onClick={() => {
                if (deleteDialogIndex !== null) {
                  removePersona(deleteDialogIndex);
                }
              }}
            >
              {deleting ? "Eliminazione..." : "Elimina"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
