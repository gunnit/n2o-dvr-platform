"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { AlertTriangle, ArrowLeft, Check, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiCall } from "@/lib/api-client";
import {
  validatePartitaIva,
  validateCodiceAteco,
  type AziendaFieldErrors,
} from "@/lib/validators/azienda";
import type { Azienda } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

/**
 * Edit page for an existing azienda. Mirrors `aziende/new` field-for-field
 * but issues a PUT and pre-fills from the loaded record. Wired from the
 * "Modifica" button in the detail header.
 */
export default function EditAziendaPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  const { data: session, status } = useSession();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const role = (session?.user as any)?.role as string | undefined;

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [loadingData, setLoadingData] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<AziendaFieldErrors>({});
  // Feedback 04/05 #1: zona sismica autofill from comune. The form is
  // otherwise uncontrolled (defaultValue + FormData), so we track only
  // the seismic state explicitly and read the city via refs to avoid
  // disturbing the rest of the form.
  const [seismicLookup, setSeismicLookup] = useState<SeismicLookupState>({
    kind: "idle",
  });
  const [zonaSismicaValue, setZonaSismicaValue] = useState<string>("");
  const sedeOperativaCittaRef = useRef<HTMLInputElement>(null);
  const sedeLegaleCittaRef = useRef<HTMLInputElement>(null);

  // Once the azienda loads, seed the controlled zona sismica (so we can
  // overwrite it after a lookup) from the persisted value.
  useEffect(() => {
    if (azienda) {
      setZonaSismicaValue(
        azienda.zona_sismica != null ? String(azienda.zona_sismica) : "",
      );
    }
  }, [azienda]);

  // US-5.1 alignment: only admins can edit aziende.
  useEffect(() => {
    if (status === "loading") return;
    if (role && role !== "admin") {
      toast.error("Solo gli amministratori possono modificare i clienti");
      router.replace(`/aziende/${id}`);
    }
  }, [role, status, router, id]);

  useEffect(() => {
    let cancelled = false;
    apiCall<Azienda>(`/api/v1/aziende/${id}`)
      .then((a) => {
        if (!cancelled) setAzienda(a);
      })
      .catch(() => {
        if (!cancelled) setLoadError("Impossibile caricare l'azienda");
      })
      .finally(() => {
        if (!cancelled) setLoadingData(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function handleSeismicLookup() {
    const comune =
      sedeOperativaCittaRef.current?.value.trim() ||
      sedeLegaleCittaRef.current?.value.trim() ||
      "";
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
        setZonaSismicaValue(String(data.zona));
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

  function validateField(
    name: "partita_iva" | "codice_ateco",
    value: string,
  ) {
    const msg =
      name === "partita_iva"
        ? validatePartitaIva(value)
        : validateCodiceAteco(value);
    setFieldErrors((prev) => {
      const next = { ...prev };
      if (msg) next[name] = msg;
      else delete next[name];
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    const formData = new FormData(e.currentTarget);

    const pivaRaw = (formData.get("partita_iva") as string) || "";
    const atecoRaw = (formData.get("codice_ateco") as string) || "";
    const pivaErr = validatePartitaIva(pivaRaw);
    const atecoErr = validateCodiceAteco(atecoRaw);
    const nextErrors: AziendaFieldErrors = { ...fieldErrors };
    if (pivaErr) nextErrors.partita_iva = pivaErr;
    else delete nextErrors.partita_iva;
    if (atecoErr) nextErrors.codice_ateco = atecoErr;
    else delete nextErrors.codice_ateco;
    setFieldErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      setError("Correggi gli errori segnalati prima di salvare");
      return;
    }

    setSaving(true);
    try {
      const sessionRes = await fetch("/api/auth/session");
      const sess = await sessionRes.json();
      const token = sess?.accessToken;

      if (!token) {
        setError("Sessione scaduta, effettua nuovamente il login");
        setSaving(false);
        return;
      }

      const metratura = formData.get("metratura_totale") as string;
      const zonaSismica = formData.get("zona_sismica") as string;

      const res = await fetch(`${API_URL}/api/v1/aziende/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ragione_sociale: formData.get("ragione_sociale"),
          partita_iva: formData.get("partita_iva") || null,
          attivita: formData.get("attivita") || null,
          codice_ateco: formData.get("codice_ateco") || null,
          sede_legale_via: formData.get("sede_legale_via") || null,
          sede_legale_citta: formData.get("sede_legale_citta") || null,
          sede_operativa_via: formData.get("sede_operativa_via") || null,
          sede_operativa_citta: formData.get("sede_operativa_citta") || null,
          orario_lavoro: formData.get("orario_lavoro") || null,
          metratura_totale: metratura ? Number(metratura) : null,
          zona_sismica: zonaSismica ? Number(zonaSismica) : null,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Errore: ${res.status}`);
      }

      toast.success("Azienda aggiornata");
      router.push(`/aziende/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore nel salvataggio");
    } finally {
      setSaving(false);
    }
  }

  if (loadingData) {
    return <p className="type-body">Caricamento...</p>;
  }

  if (loadError || !azienda) {
    return (
      <div className="space-y-4">
        <Link
          href={`/aziende/${id}`}
          className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#64748d] hover:text-[#061b31]"
        >
          <ArrowLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Torna all&apos;azienda
        </Link>
        <p className="type-body text-destructive">
          {loadError || "Azienda non trovata"}
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="space-y-2">
        <Link
          href={`/aziende/${id}`}
          className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#64748d] hover:text-[#061b31]"
        >
          <ArrowLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          {azienda.ragione_sociale}
        </Link>
        <h1 className="type-h1">Modifica Azienda</h1>
        <p className="type-body">Aggiorna i dati anagrafici del cliente</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Dati Azienda</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-7">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="ragione_sociale">Ragione Sociale *</Label>
                <Input
                  id="ragione_sociale"
                  name="ragione_sociale"
                  required
                  defaultValue={azienda.ragione_sociale}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="partita_iva">Partita IVA</Label>
                <Input
                  id="partita_iva"
                  name="partita_iva"
                  defaultValue={azienda.partita_iva ?? ""}
                  onBlur={(e) => validateField("partita_iva", e.target.value)}
                  className={fieldErrors.partita_iva ? "border-destructive" : ""}
                />
                {fieldErrors.partita_iva && (
                  <p className="text-xs text-destructive">
                    {fieldErrors.partita_iva}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="codice_ateco">Codice ATECO</Label>
                <Input
                  id="codice_ateco"
                  name="codice_ateco"
                  defaultValue={azienda.codice_ateco ?? ""}
                  onBlur={(e) => validateField("codice_ateco", e.target.value)}
                  className={fieldErrors.codice_ateco ? "border-destructive" : ""}
                />
                {fieldErrors.codice_ateco && (
                  <p className="text-xs text-destructive">
                    {fieldErrors.codice_ateco}
                  </p>
                )}
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="attivita">Attivit&agrave;</Label>
                <Input
                  id="attivita"
                  name="attivita"
                  defaultValue={azienda.attivita ?? ""}
                />
              </div>
            </div>

            <div className="space-y-3 border-t border-[#e5edf5] pt-6">
              <h3 className="type-eyebrow">Sede Legale</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="sede_legale_via">Via / Indirizzo</Label>
                  <Input
                    id="sede_legale_via"
                    name="sede_legale_via"
                    defaultValue={azienda.sede_legale_via ?? ""}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="sede_legale_citta">Citt&agrave;</Label>
                  <Input
                    ref={sedeLegaleCittaRef}
                    id="sede_legale_citta"
                    name="sede_legale_citta"
                    defaultValue={azienda.sede_legale_citta ?? ""}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-3 border-t border-[#e5edf5] pt-6">
              <h3 className="type-eyebrow">Sede Operativa</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="sede_operativa_via">Via / Indirizzo</Label>
                  <Input
                    id="sede_operativa_via"
                    name="sede_operativa_via"
                    defaultValue={azienda.sede_operativa_via ?? ""}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="sede_operativa_citta">Citt&agrave;</Label>
                  <Input
                    ref={sedeOperativaCittaRef}
                    id="sede_operativa_citta"
                    name="sede_operativa_citta"
                    defaultValue={azienda.sede_operativa_citta ?? ""}
                  />
                </div>
              </div>
            </div>

            <div className="grid gap-4 border-t border-[#e5edf5] pt-6 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="orario_lavoro">Orario di Lavoro</Label>
                <Input
                  id="orario_lavoro"
                  name="orario_lavoro"
                  defaultValue={azienda.orario_lavoro ?? ""}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="metratura_totale">Metratura Totale (mq)</Label>
                <Input
                  id="metratura_totale"
                  name="metratura_totale"
                  type="number"
                  step="0.1"
                  min="0"
                  defaultValue={azienda.metratura_totale ?? ""}
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
                    name="zona_sismica"
                    className="h-10 w-full min-w-0 rounded-md border border-[#e5edf5] bg-white px-3 py-2 text-sm text-[#061b31] outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
                    value={zonaSismicaValue}
                    onChange={(e) => {
                      setZonaSismicaValue(e.target.value);
                      if (seismicLookup.kind === "found") {
                        setSeismicLookup({ kind: "idle" });
                      }
                    }}
                  >
                    <option value="">Seleziona zona</option>
                    <option value="1">Zona 1 - Alta pericolosit&agrave;</option>
                    <option value="2">Zona 2 - Media pericolosit&agrave;</option>
                    <option value="3">Zona 3 - Bassa pericolosit&agrave;</option>
                    <option value="4">
                      Zona 4 - Molto bassa pericolosit&agrave;
                    </option>
                  </select>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleSeismicLookup}
                    disabled={seismicLookup.kind === "loading"}
                    className="shrink-0 whitespace-nowrap"
                    title="Compila la zona sismica dal comune della sede"
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
              <Button type="submit" disabled={saving}>
                {saving ? "Salvataggio..." : "Salva modifiche"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push(`/aziende/${id}`)}
              >
                Annulla
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
