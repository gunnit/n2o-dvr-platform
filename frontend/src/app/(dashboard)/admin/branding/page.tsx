"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { AlertCircle, CheckCircle2, ImageUp, Loader2, Trash2 } from "lucide-react";

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
import { useApi } from "@/hooks/use-api";
import { fetchImageBlobUrl } from "@/lib/api-client";

interface Branding {
  id: string;
  name: string;
  has_logo: boolean;
  indirizzo: string | null;
  cap: string | null;
  citta: string | null;
  provincia: string | null;
  partita_iva: string | null;
  codice_fiscale: string | null;
  telefono: string | null;
  email: string | null;
  sito_web: string | null;
  rspp_nome: string | null;
}

type FormFields = Omit<Branding, "id" | "has_logo">;

const EMPTY_FORM: FormFields = {
  name: "",
  indirizzo: "",
  cap: "",
  citta: "",
  provincia: "",
  partita_iva: "",
  codice_fiscale: "",
  telefono: "",
  email: "",
  sito_web: "",
  rspp_nome: "",
};

function toForm(b: Branding): FormFields {
  return {
    name: b.name ?? "",
    indirizzo: b.indirizzo ?? "",
    cap: b.cap ?? "",
    citta: b.citta ?? "",
    provincia: b.provincia ?? "",
    partita_iva: b.partita_iva ?? "",
    codice_fiscale: b.codice_fiscale ?? "",
    telefono: b.telefono ?? "",
    email: b.email ?? "",
    sito_web: b.sito_web ?? "",
    rspp_nome: b.rspp_nome ?? "",
  };
}

const TEXT_FIELDS: { key: keyof FormFields; label: string; placeholder?: string; maxLength?: number }[] = [
  { key: "name", label: "Ragione sociale (studio)", placeholder: "N2O SRL", maxLength: 255 },
  { key: "indirizzo", label: "Indirizzo", placeholder: "Via Roma 1", maxLength: 255 },
  { key: "cap", label: "CAP", placeholder: "20100", maxLength: 16 },
  { key: "citta", label: "Città", placeholder: "Milano", maxLength: 255 },
  { key: "provincia", label: "Provincia", placeholder: "MI", maxLength: 8 },
  { key: "partita_iva", label: "Partita IVA", placeholder: "01234567890", maxLength: 32 },
  { key: "codice_fiscale", label: "Codice fiscale", placeholder: "01234567890", maxLength: 32 },
  { key: "telefono", label: "Telefono", placeholder: "02 1234567", maxLength: 64 },
  { key: "email", label: "Email", placeholder: "info@studio.it", maxLength: 255 },
  { key: "sito_web", label: "Sito web", placeholder: "www.studio.it", maxLength: 255 },
  { key: "rspp_nome", label: "RSPP (nominativo)", placeholder: "Mario Rossi", maxLength: 255 },
];

export default function AdminBrandingPage() {
  const { apiFetch } = useApi();
  const { data: session, status: sessionStatus } = useSession();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState<FormFields>(EMPTY_FORM);
  const [hasLogo, setHasLogo] = useState(false);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (sessionStatus !== "authenticated") return;
    const role = (session?.user as { role?: string } | undefined)?.role;
    if (role !== "admin") router.replace("/dashboard");
  }, [session, sessionStatus, router]);

  const refreshLogoPreview = useCallback(async (present: boolean) => {
    setLogoUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    if (!present) return;
    // Cache-bust so a freshly uploaded logo replaces the old preview.
    const url = await fetchImageBlobUrl(`/api/v1/organizations/me/branding/logo?t=${Date.now()}`);
    setLogoUrl(url);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const b = await apiFetch<Branding>("/api/v1/organizations/me/branding");
      setForm(toForm(b));
      setHasLogo(b.has_logo);
      await refreshLogoPreview(b.has_logo);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Caricamento non riuscito.");
    } finally {
      setLoading(false);
    }
  }, [apiFetch, refreshLogoPreview]);

  useEffect(() => {
    load();
  }, [load]);

  // Revoke the object URL on unmount to avoid leaking memory.
  useEffect(() => () => {
    if (logoUrl) URL.revokeObjectURL(logoUrl);
  }, [logoUrl]);

  function update(key: keyof FormFields, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
    setSaved(false);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const b = await apiFetch<Branding>("/api/v1/organizations/me/branding", {
        method: "PUT",
        body: JSON.stringify(form),
      });
      setForm(toForm(b));
      setHasLogo(b.has_logo);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Salvataggio non riuscito.");
    } finally {
      setSaving(false);
    }
  }

  async function onLogoSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) await uploadLogo(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function uploadLogo(file: File) {
    setUploading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const b = await apiFetch<Branding>("/api/v1/organizations/me/branding/logo", {
        method: "POST",
        body: fd,
      });
      setHasLogo(b.has_logo);
      await refreshLogoPreview(b.has_logo);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Caricamento logo non riuscito.");
    } finally {
      setUploading(false);
    }
  }

  async function removeLogo() {
    setUploading(true);
    setError(null);
    try {
      const b = await apiFetch<Branding>("/api/v1/organizations/me/branding/logo", {
        method: "DELETE",
      });
      setHasLogo(b.has_logo);
      await refreshLogoPreview(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rimozione logo non riuscita.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="type-h1">Personalizzazione</h1>
        <p className="text-muted-foreground">
          Logo e intestazione dello studio che compaiono sui documenti generati e
          nell&apos;app. Le modifiche valgono per tutta l&apos;organizzazione.
        </p>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Logo</CardTitle>
          <CardDescription>
            PNG o JPG, max 5 MB. Compare in copertina dei documenti e nella barra
            laterale. Se assente, viene usato il logo predefinito.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-6">
            <div className="flex h-24 w-44 items-center justify-center rounded-md border border-[#e5edf5] bg-[#f7fafc] p-2">
              {logoUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={logoUrl} alt="Logo studio" className="max-h-full max-w-full object-contain" />
              ) : (
                <span className="text-xs text-muted-foreground">
                  {loading ? "Caricamento…" : "Nessun logo"}
                </span>
              )}
            </div>
            <div className="flex flex-col gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg"
                onChange={onLogoSelected}
                className="hidden"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={uploading}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploading ? (
                  <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ImageUp className="mr-1 h-3.5 w-3.5" />
                )}
                {hasLogo ? "Sostituisci logo" : "Carica logo"}
              </Button>
              {hasLogo && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={uploading}
                  onClick={removeLogo}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="mr-1 h-3.5 w-3.5" />
                  Rimuovi
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Intestazione (letterhead)</CardTitle>
          <CardDescription>
            Dati dello studio stampati sui documenti generati. Solo la ragione
            sociale è obbligatoria; gli altri campi compaiono se valorizzati.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={save} className="space-y-5">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {TEXT_FIELDS.map((field) => (
                <div key={field.key} className="space-y-2">
                  <Label htmlFor={field.key}>{field.label}</Label>
                  <Input
                    id={field.key}
                    value={form[field.key] ?? ""}
                    placeholder={field.placeholder}
                    maxLength={field.maxLength}
                    required={field.key === "name"}
                    onChange={(e) => update(field.key, e.target.value)}
                  />
                </div>
              ))}
            </div>
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={saving || loading}>
                {saving && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}
                Salva intestazione
              </Button>
              {saved && (
                <span className="flex items-center gap-1 text-sm text-[#108c3d]">
                  <CheckCircle2 className="h-4 w-4" />
                  Salvato
                </span>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
