"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  Building2,
  Calendar,
  Check,
  Loader2,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  ThumbsDown,
  Trash2,
  X,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useApi } from "@/hooks/use-api";
import { cn } from "@/lib/utils";

/**
 * DUVRI list + create/edit screen (US-4.5).
 *
 * One DUVRI per appalto. Principal (committente) data flows from the parent
 * Azienda automatically — we don't ask the operator to re-enter it. The
 * "Aggiungi appaltatore" CTA opens a Dialog form covering contractor + contract
 * details. A per-card "Dati committente aggiornati" banner surfaces when the
 * parent Azienda was modified after the Duvri was last touched.
 */

interface InterferenzaItem {
  rischio: string;
  misure: string;
  dpi?: string | null;
}

interface AppaltatoreAttrezzatura {
  tipo: string;
  descrizione?: string | null;
}

interface InterferenzaDecisione {
  rule_id: string;
  decision: "accept" | "reject";
  custom_text?: string | null;
}

interface CommittenteSnapshot {
  ragione_sociale: string | null;
  partita_iva: string | null;
  sede_legale_via: string | null;
  sede_legale_citta: string | null;
  sede_operativa_via: string | null;
  sede_operativa_citta: string | null;
}

interface DuvriResponse {
  id: string;
  azienda_id: string;
  appaltatore_ragione_sociale: string;
  appaltatore_partita_iva: string | null;
  appaltatore_referente: string | null;
  oggetto_appalto: string;
  data_inizio: string | null;
  data_fine: string | null;
  importo_appalto: number | null;
  interferenze: InterferenzaItem[];
  attrezzature_appaltatore: AppaltatoreAttrezzatura[];
  interferenze_decisioni: InterferenzaDecisione[];
  costi_sicurezza: number | null;
  note: string | null;
  created_at: string;
  updated_at: string;
  committente_outdated: boolean;
  committente_snapshot: CommittenteSnapshot | null;
}

interface InterferenceSuggestion {
  rule_id: string;
  contractor_eq: string;
  titolo: string;
  rischio: string;
  misure: string;
  dpi: string | null;
  riferimento: string;
  decision: "accept" | "reject" | null;
}

interface AnalyzeResponse {
  suggestions: InterferenceSuggestion[];
  no_interference_detected: boolean;
  contractor_equipment: string[];
}

const EQUIPMENT_LABELS: Record<string, string> = {
  muletto: "Muletto / carrello elevatore",
  transpallet_elettrico: "Transpallet elettrico",
  ponteggio: "Ponteggio",
  piattaforma_aerea: "Piattaforma aerea (PLE)",
  gru: "Gru",
  saldatrice: "Saldatrice",
  fiamma_libera: "Fiamma libera",
  prodotti_chimici: "Prodotti chimici",
  pulizie_pavimenti: "Pulizie pavimenti",
  macchinari_rumorosi: "Macchinari rumorosi",
  attrezzature_elettriche_portatili: "Attrezzature elettriche portatili",
  veicoli_trasporto: "Veicoli di trasporto",
  scavo_movimento_terra: "Scavo / movimento terra",
  lavori_in_quota: "Lavori in quota",
  demolizioni: "Demolizioni",
};

interface DuvriFormState {
  appaltatore_ragione_sociale: string;
  appaltatore_partita_iva: string;
  appaltatore_referente: string;
  oggetto_appalto: string;
  data_inizio: string;
  data_fine: string;
  importo_appalto: string;
  costi_sicurezza: string;
  note: string;
  interferenze: InterferenzaItem[];
  attrezzature_appaltatore: AppaltatoreAttrezzatura[];
}

const EMPTY_FORM: DuvriFormState = {
  appaltatore_ragione_sociale: "",
  appaltatore_partita_iva: "",
  appaltatore_referente: "",
  oggetto_appalto: "",
  data_inizio: "",
  data_fine: "",
  importo_appalto: "",
  costi_sicurezza: "",
  note: "",
  interferenze: [],
  attrezzature_appaltatore: [],
};

function toFormState(d: DuvriResponse): DuvriFormState {
  return {
    appaltatore_ragione_sociale: d.appaltatore_ragione_sociale,
    appaltatore_partita_iva: d.appaltatore_partita_iva ?? "",
    appaltatore_referente: d.appaltatore_referente ?? "",
    oggetto_appalto: d.oggetto_appalto,
    data_inizio: d.data_inizio ?? "",
    data_fine: d.data_fine ?? "",
    importo_appalto:
      d.importo_appalto != null ? String(d.importo_appalto) : "",
    costi_sicurezza:
      d.costi_sicurezza != null ? String(d.costi_sicurezza) : "",
    note: d.note ?? "",
    interferenze: d.interferenze.map((i) => ({ ...i })),
    attrezzature_appaltatore: d.attrezzature_appaltatore.map((a) => ({ ...a })),
  };
}

function toPayload(form: DuvriFormState) {
  return {
    appaltatore_ragione_sociale: form.appaltatore_ragione_sociale.trim(),
    appaltatore_partita_iva: form.appaltatore_partita_iva.trim() || null,
    appaltatore_referente: form.appaltatore_referente.trim() || null,
    oggetto_appalto: form.oggetto_appalto.trim(),
    data_inizio: form.data_inizio || null,
    data_fine: form.data_fine || null,
    importo_appalto: form.importo_appalto
      ? Number(form.importo_appalto)
      : null,
    costi_sicurezza: form.costi_sicurezza
      ? Number(form.costi_sicurezza)
      : null,
    note: form.note.trim() || null,
    interferenze: form.interferenze
      .filter((i) => i.rischio.trim() || i.misure.trim())
      .map((i) => ({
        rischio: i.rischio.trim(),
        misure: i.misure.trim(),
        dpi: (i.dpi || "").trim() || null,
      })),
    attrezzature_appaltatore: form.attrezzature_appaltatore.map((a) => ({
      tipo: a.tipo,
      descrizione: (a.descrizione || "").trim() || null,
    })),
  };
}

export default function DuvriListPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;
  const { apiFetch } = useApi();

  const [items, setItems] = useState<DuvriResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editing, setEditing] = useState<DuvriResponse | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<DuvriFormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DuvriResponse | null>(null);
  const [deleting, setDeleting] = useState(false);

  const [equipmentTypes, setEquipmentTypes] = useState<string[]>([]);
  const [analyzeTarget, setAnalyzeTarget] = useState<DuvriResponse | null>(null);
  const [analyzeData, setAnalyzeData] = useState<AnalyzeResponse | null>(null);
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [decisionPending, setDecisionPending] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<DuvriResponse[]>(
        `/api/v1/aziende/${aziendaId}/duvri`
      );
      setItems(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Caricamento non riuscito.");
    } finally {
      setLoading(false);
    }
  }, [aziendaId, apiFetch]);

  useEffect(() => {
    load();
  }, [load]);

  // Load the canonical equipment-type list once for the chips selector.
  useEffect(() => {
    apiFetch<string[]>(
      `/api/v1/aziende/${aziendaId}/duvri/_meta/equipment-types`
    )
      .then(setEquipmentTypes)
      .catch(() => {
        // Fall back to local label keys if the endpoint hiccups so the form
        // still works for new contractors.
        setEquipmentTypes(Object.keys(EQUIPMENT_LABELS));
      });
  }, [aziendaId, apiFetch]);

  const toggleEquipment = (tipo: string) => {
    setForm((f) => {
      const exists = f.attrezzature_appaltatore.some((a) => a.tipo === tipo);
      return {
        ...f,
        attrezzature_appaltatore: exists
          ? f.attrezzature_appaltatore.filter((a) => a.tipo !== tipo)
          : [...f.attrezzature_appaltatore, { tipo, descrizione: "" }],
      };
    });
  };

  const openAnalyze = async (d: DuvriResponse) => {
    setAnalyzeTarget(d);
    setAnalyzeData(null);
    setAnalyzeLoading(true);
    try {
      const res = await apiFetch<AnalyzeResponse>(
        `/api/v1/aziende/${aziendaId}/duvri/${d.id}/analyze-interferences`
      );
      setAnalyzeData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analisi non riuscita.");
    } finally {
      setAnalyzeLoading(false);
    }
  };

  const closeAnalyze = () => {
    setAnalyzeTarget(null);
    setAnalyzeData(null);
  };

  const recordDecision = async (
    rule_id: string,
    decision: "accept" | "reject"
  ) => {
    if (!analyzeTarget) return;
    setDecisionPending(rule_id);
    try {
      const updated = await apiFetch<DuvriResponse>(
        `/api/v1/aziende/${aziendaId}/duvri/${analyzeTarget.id}/interferences/decision`,
        {
          method: "POST",
          body: JSON.stringify({ rule_id, decision }),
        }
      );
      setItems((prev) =>
        prev.map((p) => (p.id === updated.id ? updated : p))
      );
      setAnalyzeTarget(updated);
      setAnalyzeData((prev) =>
        prev
          ? {
              ...prev,
              suggestions: prev.suggestions.map((s) =>
                s.rule_id === rule_id ? { ...s, decision } : s
              ),
            }
          : prev
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decisione non salvata.");
    } finally {
      setDecisionPending(null);
    }
  };

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setEditing(null);
    setCreating(true);
  };

  const openEdit = (d: DuvriResponse) => {
    setForm(toFormState(d));
    setEditing(d);
    setCreating(false);
  };

  const closeForm = () => {
    setEditing(null);
    setCreating(false);
    setForm(EMPTY_FORM);
  };

  const isFormOpen = creating || editing !== null;

  const submit = async () => {
    if (
      !form.appaltatore_ragione_sociale.trim() ||
      !form.oggetto_appalto.trim()
    ) {
      setError(
        "Ragione sociale appaltatore e oggetto appalto sono obbligatori."
      );
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload = toPayload(form);
      if (editing) {
        const updated = await apiFetch<DuvriResponse>(
          `/api/v1/aziende/${aziendaId}/duvri/${editing.id}`,
          { method: "PATCH", body: JSON.stringify(payload) }
        );
        setItems((prev) =>
          prev.map((p) => (p.id === updated.id ? updated : p))
        );
      } else {
        const created = await apiFetch<DuvriResponse>(
          `/api/v1/aziende/${aziendaId}/duvri`,
          { method: "POST", body: JSON.stringify(payload) }
        );
        setItems((prev) => [created, ...prev]);
      }
      closeForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Salvataggio non riuscito.");
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await apiFetch(
        `/api/v1/aziende/${aziendaId}/duvri/${deleteTarget.id}`,
        { method: "DELETE" }
      );
      setItems((prev) => prev.filter((p) => p.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eliminazione non riuscita.");
    } finally {
      setDeleting(false);
    }
  };

  const addInterferenza = () => {
    setForm((f) => ({
      ...f,
      interferenze: [...f.interferenze, { rischio: "", misure: "", dpi: "" }],
    }));
  };

  const updateInterferenza = (idx: number, patch: Partial<InterferenzaItem>) => {
    setForm((f) => ({
      ...f,
      interferenze: f.interferenze.map((it, i) =>
        i === idx ? { ...it, ...patch } : it
      ),
    }));
  };

  const removeInterferenza = (idx: number) => {
    setForm((f) => ({
      ...f,
      interferenze: f.interferenze.filter((_, i) => i !== idx),
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">DUVRI - Appalti</h1>
          <p className="text-sm text-muted-foreground">
            Un documento DUVRI per ogni contratto di appalto. I dati del
            committente sono ereditati automaticamente dall&apos;azienda.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-1 h-4 w-4" />
          Aggiungi appaltatore
        </Button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Caricamento DUVRI...
        </div>
      )}

      {error && !isFormOpen && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {!loading && items.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            <Building2 className="mx-auto mb-3 h-8 w-8 text-muted-foreground/50" />
            Nessun DUVRI registrato. Clicca &quot;Aggiungi appaltatore&quot; per
            iniziare.
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {items.map((d) => (
          <Card key={d.id} className={cn(d.committente_outdated && "border-amber-300")}>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <CardTitle>{d.appaltatore_ragione_sociale}</CardTitle>
                  <CardDescription className="line-clamp-2">
                    {d.oggetto_appalto}
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => openAnalyze(d)}
                  >
                    <Search className="mr-1 h-3.5 w-3.5" />
                    Analizza interferenze
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openEdit(d)}
                  >
                    <Pencil className="mr-1 h-3.5 w-3.5" />
                    Modifica
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDeleteTarget(d)}
                  >
                    <Trash2 className="mr-1 h-3.5 w-3.5" />
                    Elimina
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {d.committente_outdated && (
                <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                  <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <div>
                    <p className="font-medium">Dati committente aggiornati</p>
                    <p>
                      L&apos;azienda committente e&apos; stata modificata dopo
                      l&apos;ultimo aggiornamento di questo DUVRI. Riapri e
                      salva per ricompilare gli automatismi.
                    </p>
                  </div>
                </div>
              )}
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-medium uppercase text-muted-foreground">
                    Committente
                  </p>
                  <p>{d.committente_snapshot?.ragione_sociale ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs font-medium uppercase text-muted-foreground">
                    P. IVA appaltatore
                  </p>
                  <p>{d.appaltatore_partita_iva || "—"}</p>
                </div>
                <div>
                  <p className="text-xs font-medium uppercase text-muted-foreground">
                    Periodo
                  </p>
                  <p className="flex items-center gap-1">
                    <Calendar className="h-3 w-3 text-muted-foreground" />
                    {d.data_inizio || "—"} → {d.data_fine || "—"}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium uppercase text-muted-foreground">
                    Importo / Costi sicurezza
                  </p>
                  <p>
                    {d.importo_appalto != null ? `€ ${d.importo_appalto}` : "—"}
                    {" / "}
                    {d.costi_sicurezza != null
                      ? `€ ${d.costi_sicurezza}`
                      : "—"}
                  </p>
                </div>
              </div>
              {d.interferenze.length > 0 && (
                <div>
                  <p className="text-xs font-medium uppercase text-muted-foreground">
                    Interferenze identificate ({d.interferenze.length})
                  </p>
                  <ul className="mt-1 space-y-1">
                    {d.interferenze.slice(0, 3).map((it, i) => (
                      <li key={i} className="text-xs text-muted-foreground">
                        • <span className="font-medium">{it.rischio}</span>{" "}
                        — {it.misure.slice(0, 80)}
                        {it.misure.length > 80 ? "…" : ""}
                      </li>
                    ))}
                    {d.interferenze.length > 3 && (
                      <li className="text-xs text-muted-foreground">
                        ...e altre {d.interferenze.length - 3}
                      </li>
                    )}
                  </ul>
                </div>
              )}
              {d.interferenze.length === 0 && (
                <Badge
                  variant="outline"
                  className="border-amber-300 text-amber-700"
                >
                  Nessuna interferenza analizzata
                </Badge>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Create / edit dialog */}
      <Dialog open={isFormOpen} onOpenChange={(o) => !o && closeForm()}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Modifica DUVRI" : "Nuovo DUVRI"}
            </DialogTitle>
            <DialogDescription>
              I dati del committente sono compilati automaticamente
              dall&apos;azienda parent.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="ragione_sociale">
                  Ragione sociale appaltatore *
                </Label>
                <Input
                  id="ragione_sociale"
                  value={form.appaltatore_ragione_sociale}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      appaltatore_ragione_sociale: e.target.value,
                    })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="partita_iva">Partita IVA</Label>
                <Input
                  id="partita_iva"
                  value={form.appaltatore_partita_iva}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      appaltatore_partita_iva: e.target.value,
                    })
                  }
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="referente">Referente / Contatto</Label>
                <Input
                  id="referente"
                  value={form.appaltatore_referente}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      appaltatore_referente: e.target.value,
                    })
                  }
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="oggetto">Oggetto appalto *</Label>
                <textarea
                  id="oggetto"
                  value={form.oggetto_appalto}
                  onChange={(e) =>
                    setForm({ ...form, oggetto_appalto: e.target.value })
                  }
                  rows={3}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="inizio">Data inizio</Label>
                <Input
                  id="inizio"
                  type="date"
                  value={form.data_inizio}
                  onChange={(e) =>
                    setForm({ ...form, data_inizio: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="fine">Data fine</Label>
                <Input
                  id="fine"
                  type="date"
                  value={form.data_fine}
                  onChange={(e) =>
                    setForm({ ...form, data_fine: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="importo">Importo appalto (€)</Label>
                <Input
                  id="importo"
                  type="number"
                  step="0.01"
                  value={form.importo_appalto}
                  onChange={(e) =>
                    setForm({ ...form, importo_appalto: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="costi">Costi sicurezza interferenza (€)</Label>
                <Input
                  id="costi"
                  type="number"
                  step="0.01"
                  value={form.costi_sicurezza}
                  onChange={(e) =>
                    setForm({ ...form, costi_sicurezza: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="note">Note</Label>
                <textarea
                  id="note"
                  value={form.note}
                  onChange={(e) => setForm({ ...form, note: e.target.value })}
                  rows={2}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Attrezzature / attivita appaltatore</Label>
              <p className="text-xs text-muted-foreground">
                Seleziona le attivita che l&apos;appaltatore portera&apos; sul
                sito. Useremo questa lista per suggerire le interferenze tipiche
                tramite &quot;Analizza interferenze&quot; sulla card.
              </p>
              <div className="flex flex-wrap gap-1.5">
                {equipmentTypes.map((tipo) => {
                  const selected = form.attrezzature_appaltatore.some(
                    (a) => a.tipo === tipo
                  );
                  return (
                    <button
                      key={tipo}
                      type="button"
                      onClick={() => toggleEquipment(tipo)}
                      className={cn(
                        "rounded-full border px-2.5 py-0.5 text-xs transition-colors",
                        selected
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-input bg-background hover:bg-muted"
                      )}
                    >
                      {EQUIPMENT_LABELS[tipo] || tipo}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Interferenze identificate</Label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={addInterferenza}
                >
                  <Plus className="mr-1 h-3 w-3" />
                  Aggiungi interferenza
                </Button>
              </div>
              {form.interferenze.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  Nessuna interferenza ancora aggiunta. Useremo l&apos;analisi
                  automatica nel passo successivo (US-4.6).
                </p>
              )}
              {form.interferenze.map((it, idx) => (
                <div
                  key={idx}
                  className="space-y-2 rounded-md border border-input p-3"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-medium text-muted-foreground">
                      Interferenza #{idx + 1}
                    </p>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeInterferenza(idx)}
                      className="h-6 w-6 p-0"
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                  <Input
                    placeholder="Rischio (es. caduta materiali da quota)"
                    value={it.rischio}
                    onChange={(e) =>
                      updateInterferenza(idx, { rischio: e.target.value })
                    }
                  />
                  <textarea
                    placeholder="Misure di prevenzione e protezione"
                    value={it.misure}
                    onChange={(e) =>
                      updateInterferenza(idx, { misure: e.target.value })
                    }
                    rows={2}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  />
                  <Input
                    placeholder="DPI richiesti (opzionale)"
                    value={it.dpi || ""}
                    onChange={(e) =>
                      updateInterferenza(idx, { dpi: e.target.value })
                    }
                  />
                </div>
              ))}
            </div>
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={closeForm} disabled={saving}>
              Annulla
            </Button>
            <Button onClick={submit} disabled={saving}>
              {saving && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}
              {editing ? "Salva modifiche" : "Crea DUVRI"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Analyze interferences sheet (US-4.6) */}
      <Sheet
        open={analyzeTarget !== null}
        onOpenChange={(o) => !o && closeAnalyze()}
      >
        <SheetContent
          side="right"
          className="w-full overflow-y-auto sm:max-w-xl"
        >
          <SheetHeader>
            <SheetTitle>Analisi interferenze</SheetTitle>
            <SheetDescription>
              {analyzeTarget?.appaltatore_ragione_sociale} —{" "}
              {analyzeTarget?.oggetto_appalto}
            </SheetDescription>
          </SheetHeader>

          <div className="mt-4 space-y-4">
            {analyzeLoading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Esecuzione analisi...
              </div>
            )}

            {analyzeData && analyzeData.contractor_equipment.length === 0 && (
              <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
                <p className="font-medium">Nessuna attrezzatura selezionata</p>
                <p className="text-xs">
                  Apri &quot;Modifica&quot; e seleziona almeno
                  un&apos;attrezzatura/attivita per poter eseguire l&apos;analisi.
                </p>
              </div>
            )}

            {analyzeData &&
              analyzeData.no_interference_detected &&
              analyzeData.contractor_equipment.length > 0 && (
                <div className="rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900">
                  <p className="font-medium">Nessuna interferenza rilevata</p>
                  <p className="text-xs">
                    Le attrezzature dichiarate non corrispondono a regole note.
                    Puoi comunque aggiungere interferenze manualmente da
                    &quot;Modifica&quot;.
                  </p>
                </div>
              )}

            {analyzeData &&
              analyzeData.suggestions.map((s) => {
                const isPending = decisionPending === s.rule_id;
                return (
                  <div
                    key={s.rule_id}
                    className={cn(
                      "rounded-md border p-3",
                      s.decision === "accept" &&
                        "border-emerald-300 bg-emerald-50/30",
                      s.decision === "reject" &&
                        "border-slate-300 bg-slate-50/50 opacity-70"
                    )}
                  >
                    <div className="mb-2 flex flex-wrap items-center gap-1.5">
                      <span className="text-sm font-medium">{s.titolo}</span>
                      <Badge variant="outline" className="text-[11px]">
                        {EQUIPMENT_LABELS[s.contractor_eq] || s.contractor_eq}
                      </Badge>
                      {s.decision === "accept" && (
                        <Badge className="bg-emerald-100 text-emerald-800 text-[11px] hover:bg-emerald-100">
                          <Check className="mr-1 h-2.5 w-2.5" />
                          Accettata
                        </Badge>
                      )}
                      {s.decision === "reject" && (
                        <Badge className="bg-slate-100 text-slate-700 text-[11px] hover:bg-slate-100">
                          <ThumbsDown className="mr-1 h-2.5 w-2.5" />
                          Rifiutata
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium">Rischio: </span>
                      {s.rischio}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      <span className="font-medium">Misure: </span>
                      {s.misure}
                    </p>
                    {s.dpi && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        <span className="font-medium">DPI: </span>
                        {s.dpi}
                      </p>
                    )}
                    <p className="mt-1 text-[11px] italic text-muted-foreground">
                      Rif. {s.riferimento}
                    </p>
                    <div className="mt-2 flex gap-2">
                      {s.decision !== "accept" && (
                        <Button
                          size="sm"
                          onClick={() => recordDecision(s.rule_id, "accept")}
                          disabled={isPending}
                        >
                          {isPending ? (
                            <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Check className="mr-1 h-3.5 w-3.5" />
                          )}
                          Accetta
                        </Button>
                      )}
                      {s.decision !== "reject" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => recordDecision(s.rule_id, "reject")}
                          disabled={isPending}
                        >
                          <ThumbsDown className="mr-1 h-3.5 w-3.5" />
                          Rifiuta
                        </Button>
                      )}
                      {s.decision && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            recordDecision(
                              s.rule_id,
                              s.decision === "accept" ? "reject" : "accept"
                            )
                          }
                          disabled={isPending}
                        >
                          <RotateCcw className="mr-1 h-3.5 w-3.5" />
                          Cambia
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
          </div>
        </SheetContent>
      </Sheet>

      {/* Delete confirmation */}
      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminare il DUVRI?</DialogTitle>
            <DialogDescription>
              Il DUVRI per <strong>{deleteTarget?.appaltatore_ragione_sociale}</strong>{" "}
              verra&apos; eliminato definitivamente. L&apos;azione non puo&apos;
              essere annullata.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setDeleteTarget(null)}
              disabled={deleting}
            >
              Annulla
            </Button>
            <Button onClick={confirmDelete} disabled={deleting}>
              {deleting && (
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              )}
              Elimina
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
