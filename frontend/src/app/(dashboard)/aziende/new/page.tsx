"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { AlertTriangle, Check, Loader2, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  validatePartitaIva,
  validateCodiceAteco,
  type AziendaFieldErrors,
} from "@/lib/validators/azienda";
import type {
  AziendaAutofillFieldMeta,
  AziendaAutofillResponse,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// All form fields the page sends to POST /aziende. Kept as a Record so the
// AI autofill response can be merged generically (one assignment per key)
// without listing every field again. Numeric / date fields are stored as
// strings here and cast at submit time.
type AziendaFormState = {
  ragione_sociale: string;
  partita_iva: string;
  codice_fiscale: string;
  forma_giuridica: string;
  attivita: string;
  codice_ateco: string;
  sede_legale_via: string;
  sede_legale_citta: string;
  cap_legale: string;
  provincia_legale: string;
  sede_operativa_via: string;
  sede_operativa_citta: string;
  cap_operativa: string;
  provincia_operativa: string;
  pec: string;
  email: string;
  telefono: string;
  sito_web: string;
  capitale_sociale: string;
  rea: string;
  data_costituzione: string;
  numero_dipendenti_dichiarati: string;
  orario_lavoro: string;
  metratura_totale: string;
  zona_sismica: string;
};

const EMPTY_FORM: AziendaFormState = {
  ragione_sociale: "",
  partita_iva: "",
  codice_fiscale: "",
  forma_giuridica: "",
  attivita: "",
  codice_ateco: "",
  sede_legale_via: "",
  sede_legale_citta: "",
  cap_legale: "",
  provincia_legale: "",
  sede_operativa_via: "",
  sede_operativa_citta: "",
  cap_operativa: "",
  provincia_operativa: "",
  pec: "",
  email: "",
  telefono: "",
  sito_web: "",
  capitale_sociale: "",
  rea: "",
  data_costituzione: "",
  numero_dipendenti_dichiarati: "",
  orario_lavoro: "",
  metratura_totale: "",
  zona_sismica: "",
};

type AiMeta = Partial<Record<keyof AziendaFormState, AziendaAutofillFieldMeta>>;

// Result of /api/v1/lookup/seismic-zone — kept in lockstep with the survey
// step-azienda type so any backend shape change surfaces in both places.
interface SeismicLookupResult {
  comune_query: string;
  comune_matched: string | null;
  zona: number | null;
  found: boolean;
  source: string;
  regione?: string | null;
}

type SeismicLookupState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "found"; comune: string; zona: number; regione?: string | null }
  | { kind: "not_found"; comune: string };

const FORMA_GIURIDICA_OPTIONS = [
  "SRL",
  "SRLS",
  "SPA",
  "SAPA",
  "SNC",
  "SAS",
  "SCARL",
  "SCRL",
  "Ditta Individuale",
  "Società Semplice",
  "Cooperativa",
  "Consorzio",
];


function AiBadge({ meta }: { meta: AziendaAutofillFieldMeta }) {
  const tone =
    meta.confidence === "high"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : meta.confidence === "medium"
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : "bg-orange-50 text-orange-700 border-orange-200";
  const label =
    meta.confidence === "high"
      ? "Verificato"
      : meta.confidence === "medium"
      ? "Verifica"
      : "Da verificare";
  return (
    <span
      title={`Suggerito da ${meta.source}${meta.source_url ? ` — ${meta.source_url}` : ""}. ${
        meta.confidence === "high"
          ? "Fonte autoritativa."
          : "Controlla il valore prima di salvare."
      }`}
      className={`inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${tone}`}
    >
      <Sparkles className="h-2.5 w-2.5" strokeWidth={2.5} />
      {label}
    </span>
  );
}


export default function NewAziendaPage() {
  const router = useRouter();
  const { data: session, status } = useSession();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const role = (session?.user as any)?.role as string | undefined;
  const [form, setForm] = useState<AziendaFormState>(EMPTY_FORM);
  const [aiMeta, setAiMeta] = useState<AiMeta>({});
  const [aiLoading, setAiLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<AziendaFieldErrors>({});
  // Feedback 04/05 #2: Dati Amministrativi (capitale, REA, data costituzione,
  // dipendenti dichiarati) is optional and OFF by default — most clients
  // don't have these on hand at survey time. When OFF the section is
  // collapsed and the four fields are forced to null on submit.
  const [adminOpen, setAdminOpen] = useState(false);
  // Feedback 04/05 #1: Zona Sismica autofill — mirrors the survey wizard's
  // step-azienda but here behind an explicit "Compila zona sismica"
  // button (no onBlur magic on the standalone form).
  const [seismicLookup, setSeismicLookup] = useState<SeismicLookupState>({
    kind: "idle",
  });

  // US-5.1: non-admins cannot create clients. Bounce them with a toast.
  useEffect(() => {
    if (status === "loading") return;
    if (role && role !== "admin") {
      toast.error("Solo gli amministratori possono creare nuovi clienti");
      router.replace("/dashboard");
    }
  }, [role, status, router]);

  function setField<K extends keyof AziendaFormState>(name: K, value: string) {
    setForm((prev) => ({ ...prev, [name]: value }));
    // Clear the AI badge as soon as the operator touches the field — the
    // value is now their own, not AI-suggested.
    setAiMeta((prev) => {
      if (!prev[name]) return prev;
      const next = { ...prev };
      delete next[name];
      return next;
    });
  }

  function validateField(name: "partita_iva" | "codice_ateco", value: string) {
    const msg =
      name === "partita_iva"
        ? validatePartitaIva(value)
        : validateCodiceAteco(value);
    setFieldErrors((prev) => {
      const next = { ...prev };
      if (msg) {
        next[name] = msg;
      } else {
        delete next[name];
      }
      return next;
    });
  }

  async function handleSeismicLookup() {
    const comune = form.sede_operativa_citta.trim() || form.sede_legale_citta.trim();
    if (!comune) return;
    setSeismicLookup({ kind: "loading" });
    try {
      const sessionRes = await fetch("/api/auth/session");
      const sess = await sessionRes.json();
      const token = sess?.accessToken;
      const qs = new URLSearchParams({ comune });
      const res = await fetch(
        `${API_URL}/api/v1/lookup/seismic-zone?${qs.toString()}`,
        {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        },
      );
      if (!res.ok) {
        throw new Error(`Lookup error: ${res.status}`);
      }
      const data: SeismicLookupResult = await res.json();
      if (data.found && data.zona != null && data.comune_matched) {
        setForm((prev) => ({ ...prev, zona_sismica: String(data.zona) }));
        setSeismicLookup({
          kind: "found",
          comune: data.comune_matched,
          zona: data.zona,
          regione: data.regione ?? null,
        });
        toast.success(
          `Zona sismica compilata: Zona ${data.zona} (${data.comune_matched})`,
        );
      } else {
        setSeismicLookup({ kind: "not_found", comune });
        toast.error("Comune non trovato. Inseriscilo manualmente.");
      }
    } catch {
      setSeismicLookup({ kind: "not_found", comune });
      toast.error("Comune non trovato. Inseriscilo manualmente.");
    }
  }

  async function handleAutofill() {
    if (aiLoading) return;
    const piva = form.partita_iva.trim();
    if (!/^\d{11}$/.test(piva)) {
      toast.error("Inserisci una P.IVA di 11 cifre prima di compilare con AI");
      return;
    }
    setAiLoading(true);
    try {
      const sessionRes = await fetch("/api/auth/session");
      const sessionData = await sessionRes.json();
      const token = sessionData?.accessToken;
      if (!token) {
        toast.error("Sessione scaduta, effettua nuovamente il login");
        return;
      }

      const res = await fetch(`${API_URL}/api/v1/aziende/autofill`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ partita_iva: piva }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Errore: ${res.status}`);
      }
      const data: AziendaAutofillResponse = await res.json();

      // Apply: only fill EMPTY fields (preserve operator edits) and stamp
      // a meta entry for each filled field. ``values`` is keyed by Azienda
      // field names, which line up with our form state — narrow at the
      // boundary.
      setForm((prev) => {
        const next = { ...prev };
        for (const [key, raw] of Object.entries(data.values)) {
          if (raw == null) continue;
          const k = key as keyof AziendaFormState;
          if (!(k in next)) continue;
          if (next[k] !== "") continue; // don't overwrite operator edits
          next[k] = String(raw);
        }
        return next;
      });
      setAiMeta((prev) => {
        const next: AiMeta = { ...prev };
        for (const [key, m] of Object.entries(data.meta)) {
          const k = key as keyof AziendaFormState;
          // Only badge fields we actually applied (i.e. were empty). The
          // setForm above used the same condition; we mirror it here by
          // checking the *current* form snapshot via ref-via-state.
          // Simpler: badge unconditionally; the worst case is a stale badge
          // on a field the operator pre-filled — acceptable, and the
          // setField clear-on-edit handler will remove it on next touch.
          next[k] = m;
        }
        return next;
      });

      if (data.warnings.length > 0) {
        toast.warning(data.warnings.join(" "));
      } else {
        toast.success(
          `Compilati ${Object.keys(data.values).length} campi — verifica i dati prima di salvare.`,
        );
      }
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Errore durante la compilazione AI",
      );
    } finally {
      setAiLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    const pivaErr = validatePartitaIva(form.partita_iva);
    const atecoErr = validateCodiceAteco(form.codice_ateco);
    const nextErrors: AziendaFieldErrors = {};
    if (!form.ragione_sociale.trim()) {
      nextErrors.ragione_sociale = "Campo obbligatorio";
    }
    if (pivaErr) nextErrors.partita_iva = pivaErr;
    if (atecoErr) nextErrors.codice_ateco = atecoErr;
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      setError("Correggi gli errori segnalati prima di salvare");
      return;
    }

    setLoading(true);
    try {
      const sessionRes = await fetch("/api/auth/session");
      const sessionData = await sessionRes.json();
      const token = sessionData?.accessToken;
      if (!token) {
        setError("Sessione scaduta, effettua nuovamente il login");
        setLoading(false);
        return;
      }

      const num = (s: string) => (s.trim() === "" ? null : Number(s));
      const str = (s: string) => (s.trim() === "" ? null : s.trim());

      const body = {
        ragione_sociale: form.ragione_sociale.trim(),
        partita_iva: str(form.partita_iva),
        codice_fiscale: str(form.codice_fiscale)?.toUpperCase() ?? null,
        forma_giuridica: str(form.forma_giuridica),
        attivita: str(form.attivita),
        codice_ateco: str(form.codice_ateco),
        sede_legale_via: str(form.sede_legale_via),
        sede_legale_citta: str(form.sede_legale_citta),
        cap_legale: str(form.cap_legale),
        provincia_legale: str(form.provincia_legale)?.toUpperCase() ?? null,
        sede_operativa_via: str(form.sede_operativa_via),
        sede_operativa_citta: str(form.sede_operativa_citta),
        cap_operativa: str(form.cap_operativa),
        provincia_operativa: str(form.provincia_operativa)?.toUpperCase() ?? null,
        pec: str(form.pec),
        email: str(form.email),
        telefono: str(form.telefono),
        sito_web: str(form.sito_web),
        // When the operator left the Dati Amministrativi section
        // collapsed, force these fields to null regardless of any stale
        // values that might have been autofilled before they toggled it
        // off — the toggle is the single source of truth.
        capitale_sociale: adminOpen ? num(form.capitale_sociale) : null,
        rea: adminOpen ? str(form.rea) : null,
        data_costituzione: adminOpen ? str(form.data_costituzione) : null,
        numero_dipendenti_dichiarati: adminOpen
          ? num(form.numero_dipendenti_dichiarati)
          : null,
        orario_lavoro: str(form.orario_lavoro),
        metratura_totale: num(form.metratura_totale),
        zona_sismica: num(form.zona_sismica),
      };

      const res = await fetch(`${API_URL}/api/v1/aziende`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `Errore: ${res.status}`);
      }
      router.push("/aziende");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore nella creazione");
    } finally {
      setLoading(false);
    }
  }

  const pivaValid = /^\d{11}$/.test(form.partita_iva.trim());

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="type-h1">Nuova Azienda</h1>
        <p className="type-body mt-2">
          Registra una nuova azienda cliente. Inserisci la P.IVA e usa{" "}
          <span className="inline-flex items-center gap-1 font-medium text-primary">
            <Sparkles className="h-3.5 w-3.5" strokeWidth={2.5} />
            Compila con AI
          </span>{" "}
          per pre-compilare i campi dai registri pubblici.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Dati Azienda</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-7">
            {/* Identificazione */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <div className="flex items-center justify-between gap-2">
                  <Label htmlFor="ragione_sociale">Ragione Sociale *</Label>
                  {aiMeta.ragione_sociale && <AiBadge meta={aiMeta.ragione_sociale} />}
                </div>
                <Input
                  id="ragione_sociale"
                  value={form.ragione_sociale}
                  onChange={(e) => setField("ragione_sociale", e.target.value)}
                  placeholder="Es. N2O SRL"
                  required
                />
                {fieldErrors.ragione_sociale && (
                  <p className="text-xs text-destructive">{fieldErrors.ragione_sociale}</p>
                )}
              </div>

              <div className="space-y-2 sm:col-span-2">
                <div className="flex items-center justify-between gap-2">
                  <Label htmlFor="partita_iva">Partita IVA</Label>
                  {aiMeta.partita_iva && <AiBadge meta={aiMeta.partita_iva} />}
                </div>
                <div className="flex gap-2">
                  <Input
                    id="partita_iva"
                    value={form.partita_iva}
                    onChange={(e) => setField("partita_iva", e.target.value)}
                    onBlur={(e) => validateField("partita_iva", e.target.value)}
                    placeholder="Es. 12345678901"
                    inputMode="numeric"
                    className={`flex-1 ${fieldErrors.partita_iva ? "border-destructive" : ""}`}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleAutofill}
                    disabled={!pivaValid || aiLoading}
                    title={
                      pivaValid
                        ? "Cerca i dati dell'azienda nei registri pubblici e nel web"
                        : "Inserisci una P.IVA di 11 cifre"
                    }
                    className="shrink-0 gap-1.5"
                  >
                    {aiLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4" strokeWidth={2} />
                    )}
                    {aiLoading ? "Cerco..." : "Compila con AI"}
                  </Button>
                </div>
                {fieldErrors.partita_iva && (
                  <p className="text-xs text-destructive">{fieldErrors.partita_iva}</p>
                )}
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <Label htmlFor="codice_fiscale">Codice Fiscale</Label>
                  {aiMeta.codice_fiscale && <AiBadge meta={aiMeta.codice_fiscale} />}
                </div>
                <Input
                  id="codice_fiscale"
                  value={form.codice_fiscale}
                  onChange={(e) => setField("codice_fiscale", e.target.value.toUpperCase())}
                  placeholder="Spesso coincide con la P.IVA"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <Label htmlFor="forma_giuridica">Forma Giuridica</Label>
                  {aiMeta.forma_giuridica && <AiBadge meta={aiMeta.forma_giuridica} />}
                </div>
                <select
                  id="forma_giuridica"
                  value={form.forma_giuridica}
                  onChange={(e) => setField("forma_giuridica", e.target.value)}
                  className="h-10 w-full rounded-md border border-[#e5edf5] bg-white px-3 text-sm text-[#061b31] outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
                >
                  <option value="">Seleziona...</option>
                  {FORMA_GIURIDICA_OPTIONS.map((fg) => (
                    <option key={fg} value={fg}>
                      {fg}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2 sm:col-span-2">
                <div className="flex items-center justify-between gap-2">
                  <Label htmlFor="attivita">Attivit&agrave;</Label>
                  {aiMeta.attivita && <AiBadge meta={aiMeta.attivita} />}
                </div>
                <Input
                  id="attivita"
                  value={form.attivita}
                  onChange={(e) => setField("attivita", e.target.value)}
                  placeholder="Es. Produzione alimentare"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <Label htmlFor="codice_ateco">Codice ATECO</Label>
                  {aiMeta.codice_ateco && <AiBadge meta={aiMeta.codice_ateco} />}
                </div>
                <Input
                  id="codice_ateco"
                  value={form.codice_ateco}
                  onChange={(e) => setField("codice_ateco", e.target.value)}
                  onBlur={(e) => validateField("codice_ateco", e.target.value)}
                  placeholder="Es. 46.69.94"
                  className={fieldErrors.codice_ateco ? "border-destructive" : ""}
                />
                {fieldErrors.codice_ateco && (
                  <p className="text-xs text-destructive">{fieldErrors.codice_ateco}</p>
                )}
              </div>
            </div>

            {/* Sede Legale */}
            <div className="space-y-3 border-t border-[#e5edf5] pt-6">
              <h3 className="type-eyebrow">Sede Legale</h3>
              <div className="grid gap-4 sm:grid-cols-6">
                <div className="space-y-1.5 sm:col-span-3">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="sede_legale_via">Via / Indirizzo</Label>
                    {aiMeta.sede_legale_via && <AiBadge meta={aiMeta.sede_legale_via} />}
                  </div>
                  <Input
                    id="sede_legale_via"
                    value={form.sede_legale_via}
                    onChange={(e) => setField("sede_legale_via", e.target.value)}
                    placeholder="Es. Via dei Chiosi 4"
                  />
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="sede_legale_citta">Citt&agrave;</Label>
                    {aiMeta.sede_legale_citta && <AiBadge meta={aiMeta.sede_legale_citta} />}
                  </div>
                  <Input
                    id="sede_legale_citta"
                    value={form.sede_legale_citta}
                    onChange={(e) => setField("sede_legale_citta", e.target.value)}
                    placeholder="Es. Milano"
                  />
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="provincia_legale">Prov.</Label>
                    {aiMeta.provincia_legale && <AiBadge meta={aiMeta.provincia_legale} />}
                  </div>
                  <Input
                    id="provincia_legale"
                    value={form.provincia_legale}
                    onChange={(e) =>
                      setField("provincia_legale", e.target.value.toUpperCase().slice(0, 2))
                    }
                    placeholder="MI"
                    maxLength={2}
                  />
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="cap_legale">CAP</Label>
                    {aiMeta.cap_legale && <AiBadge meta={aiMeta.cap_legale} />}
                  </div>
                  <Input
                    id="cap_legale"
                    value={form.cap_legale}
                    onChange={(e) => setField("cap_legale", e.target.value.replace(/\D/g, "").slice(0, 5))}
                    placeholder="20121"
                    inputMode="numeric"
                    maxLength={5}
                  />
                </div>
              </div>
            </div>

            {/* Sede Operativa */}
            <div className="space-y-3 border-t border-[#e5edf5] pt-6">
              <h3 className="type-eyebrow">Sede Operativa</h3>
              <div className="grid gap-4 sm:grid-cols-6">
                <div className="space-y-1.5 sm:col-span-3">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="sede_operativa_via">Via / Indirizzo</Label>
                    {aiMeta.sede_operativa_via && <AiBadge meta={aiMeta.sede_operativa_via} />}
                  </div>
                  <Input
                    id="sede_operativa_via"
                    value={form.sede_operativa_via}
                    onChange={(e) => setField("sede_operativa_via", e.target.value)}
                    placeholder="Es. Via Milano 5"
                  />
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="sede_operativa_citta">Citt&agrave;</Label>
                    {aiMeta.sede_operativa_citta && <AiBadge meta={aiMeta.sede_operativa_citta} />}
                  </div>
                  <Input
                    id="sede_operativa_citta"
                    value={form.sede_operativa_citta}
                    onChange={(e) => setField("sede_operativa_citta", e.target.value)}
                    placeholder="Es. Milano"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="provincia_operativa">Prov.</Label>
                  <Input
                    id="provincia_operativa"
                    value={form.provincia_operativa}
                    onChange={(e) =>
                      setField("provincia_operativa", e.target.value.toUpperCase().slice(0, 2))
                    }
                    placeholder="MI"
                    maxLength={2}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="cap_operativa">CAP</Label>
                  <Input
                    id="cap_operativa"
                    value={form.cap_operativa}
                    onChange={(e) =>
                      setField("cap_operativa", e.target.value.replace(/\D/g, "").slice(0, 5))
                    }
                    placeholder="20121"
                    inputMode="numeric"
                    maxLength={5}
                  />
                </div>
              </div>
            </div>

            {/* Contatti */}
            <div className="space-y-3 border-t border-[#e5edf5] pt-6">
              <h3 className="type-eyebrow">Contatti</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="pec">PEC</Label>
                    {aiMeta.pec && <AiBadge meta={aiMeta.pec} />}
                  </div>
                  <Input
                    id="pec"
                    type="email"
                    value={form.pec}
                    onChange={(e) => setField("pec", e.target.value)}
                    placeholder="azienda@pec.it"
                  />
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="email">Email</Label>
                    {aiMeta.email && <AiBadge meta={aiMeta.email} />}
                  </div>
                  <Input
                    id="email"
                    type="email"
                    value={form.email}
                    onChange={(e) => setField("email", e.target.value)}
                    placeholder="info@azienda.it"
                  />
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="telefono">Telefono</Label>
                    {aiMeta.telefono && <AiBadge meta={aiMeta.telefono} />}
                  </div>
                  <Input
                    id="telefono"
                    value={form.telefono}
                    onChange={(e) => setField("telefono", e.target.value)}
                    placeholder="+39 02 1234567"
                  />
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="sito_web">Sito Web</Label>
                    {aiMeta.sito_web && <AiBadge meta={aiMeta.sito_web} />}
                  </div>
                  <Input
                    id="sito_web"
                    type="url"
                    value={form.sito_web}
                    onChange={(e) => setField("sito_web", e.target.value)}
                    placeholder="https://www.azienda.it"
                  />
                </div>
              </div>
            </div>

            {/* Dati amministrativi — optional, off by default. The toggle
                lives in the section header so the operator can choose to
                expand only when they actually have visura/CCIAA data on hand. */}
            <div className="space-y-3 border-t border-[#e5edf5] pt-6">
              <label className="flex cursor-pointer items-center gap-2.5">
                <input
                  type="checkbox"
                  checked={adminOpen}
                  onChange={(e) => setAdminOpen(e.target.checked)}
                  className="h-4 w-4 cursor-pointer rounded border-[#cbd5e1] text-primary focus:ring-2 focus:ring-primary/20"
                />
                <span className="type-eyebrow">Compila Dati Amministrativi</span>
                <span className="text-[12px] text-[#64748d]">
                  (capitale sociale, REA, data costituzione, n° dipendenti — opzionale)
                </span>
              </label>
              {adminOpen && (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <Label htmlFor="capitale_sociale">Capitale Sociale (€)</Label>
                      {aiMeta.capitale_sociale && <AiBadge meta={aiMeta.capitale_sociale} />}
                    </div>
                    <Input
                      id="capitale_sociale"
                      type="number"
                      step="0.01"
                      min="0"
                      value={form.capitale_sociale}
                      onChange={(e) => setField("capitale_sociale", e.target.value)}
                      placeholder="10000"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <Label htmlFor="rea">REA</Label>
                      {aiMeta.rea && <AiBadge meta={aiMeta.rea} />}
                    </div>
                    <Input
                      id="rea"
                      value={form.rea}
                      onChange={(e) => setField("rea", e.target.value)}
                      placeholder="Es. MI-1234567"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <Label htmlFor="data_costituzione">Data Costituzione</Label>
                      {aiMeta.data_costituzione && <AiBadge meta={aiMeta.data_costituzione} />}
                    </div>
                    <Input
                      id="data_costituzione"
                      type="date"
                      value={form.data_costituzione}
                      onChange={(e) => setField("data_costituzione", e.target.value)}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <Label htmlFor="numero_dipendenti_dichiarati">N° Dipendenti</Label>
                      {aiMeta.numero_dipendenti_dichiarati && (
                        <AiBadge meta={aiMeta.numero_dipendenti_dichiarati} />
                      )}
                    </div>
                    <Input
                      id="numero_dipendenti_dichiarati"
                      type="number"
                      min="0"
                      value={form.numero_dipendenti_dichiarati}
                      onChange={(e) =>
                        setField("numero_dipendenti_dichiarati", e.target.value)
                      }
                      placeholder="Es. 12"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Operativi */}
            <div className="grid gap-4 border-t border-[#e5edf5] pt-6 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="orario_lavoro">Orario di Lavoro</Label>
                <Input
                  id="orario_lavoro"
                  value={form.orario_lavoro}
                  onChange={(e) => setField("orario_lavoro", e.target.value)}
                  placeholder="Es. 08:00 - 17:00"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="metratura_totale">Metratura Totale (mq)</Label>
                <Input
                  id="metratura_totale"
                  type="number"
                  step="0.1"
                  min="0"
                  value={form.metratura_totale}
                  onChange={(e) => setField("metratura_totale", e.target.value)}
                  placeholder="Es. 250"
                  className="tnum"
                />
              </div>
              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <Label htmlFor="zona_sismica">Zona Sismica</Label>
                  {seismicLookup.kind === "found" && (
                    <Badge
                      variant="secondary"
                      className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100 text-[10px]"
                      title={`Compilata dal lookup comune "${seismicLookup.comune}" (OPCM 3519/2006).`}
                    >
                      <Check className="mr-1 h-2.5 w-2.5" />
                      {seismicLookup.regione
                        ? `${seismicLookup.comune} · ${seismicLookup.regione}`
                        : seismicLookup.comune}
                    </Badge>
                  )}
                </div>
                <div className="flex gap-2">
                  <select
                    id="zona_sismica"
                    value={form.zona_sismica}
                    onChange={(e) => {
                      setField("zona_sismica", e.target.value);
                      // Operator hand-edit clears the lookup badge.
                      if (seismicLookup.kind === "found") {
                        setSeismicLookup({ kind: "idle" });
                      }
                    }}
                    className="h-10 w-full min-w-0 rounded-md border border-[#e5edf5] bg-white px-3 py-2 text-sm text-[#061b31] outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
                  >
                    <option value="">Seleziona zona</option>
                    <option value="1">Zona 1 - Alta pericolosit&agrave;</option>
                    <option value="2">Zona 2 - Media pericolosit&agrave;</option>
                    <option value="3">Zona 3 - Bassa pericolosit&agrave;</option>
                    <option value="4">Zona 4 - Molto bassa pericolosit&agrave;</option>
                  </select>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleSeismicLookup}
                    disabled={
                      seismicLookup.kind === "loading" ||
                      !(form.sede_operativa_citta.trim() || form.sede_legale_citta.trim())
                    }
                    title={
                      form.sede_operativa_citta.trim() || form.sede_legale_citta.trim()
                        ? "Compila la zona sismica dal comune della sede"
                        : "Inserisci prima la città della sede"
                    }
                    className="shrink-0 whitespace-nowrap"
                  >
                    {seismicLookup.kind === "loading" ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "Compila zona sismica"
                    )}
                  </Button>
                </div>
                {seismicLookup.kind === "not_found" && (
                  <p className="flex items-start gap-1 text-[11px] text-amber-700">
                    <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" />
                    Comune non trovato. Inseriscilo manualmente.
                  </p>
                )}
              </div>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="flex gap-3 border-t border-[#e5edf5] pt-6">
              <Button type="submit" disabled={loading}>
                {loading ? "Salvataggio..." : "Salva Azienda"}
              </Button>
              <Button type="button" variant="outline" onClick={() => router.back()}>
                Annulla
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
