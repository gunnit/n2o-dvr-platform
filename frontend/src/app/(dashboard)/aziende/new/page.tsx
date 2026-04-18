"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PARTITA_IVA_REGEX = /^\d{11}$/;
const ATECO_REGEX = /^\d{2}(\.\d{2}(\.\d{1,2})?)?$/;

export default function NewAziendaPage() {
  const router = useRouter();
  const { data: session, status } = useSession();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const role = (session?.user as any)?.role as string | undefined;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // US-5.1: non-admins cannot create clients. Bounce them with a toast.
  useEffect(() => {
    if (status === "loading") return;
    if (role && role !== "admin") {
      toast.error("Solo gli amministratori possono creare nuovi clienti");
      router.replace("/dashboard");
    }
  }, [role, status, router]);

  function validateField(name: string, value: string) {
    if (name === "partita_iva" && value && !PARTITA_IVA_REGEX.test(value.trim())) {
      setFieldErrors((p) => ({ ...p, partita_iva: "La partita IVA deve essere di 11 cifre" }));
    } else if (name === "codice_ateco" && value && !ATECO_REGEX.test(value.trim())) {
      setFieldErrors((p) => ({ ...p, codice_ateco: "Formato non valido (es. 56.10.11)" }));
    } else {
      setFieldErrors((p) => {
        const next = { ...p };
        delete next[name];
        return next;
      });
    }
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    const formData = new FormData(e.currentTarget);

    // Block on validation errors
    if (Object.keys(fieldErrors).length > 0) {
      setError("Correggi gli errori segnalati prima di salvare");
      return;
    }

    setLoading(true);

    try {
      const sessionRes = await fetch("/api/auth/session");
      const session = await sessionRes.json();
      const token = session?.accessToken;

      if (!token) {
        setError("Sessione scaduta, effettua nuovamente il login");
        setLoading(false);
        return;
      }

      const metratura = formData.get("metratura_totale") as string;
      const zonaSismica = formData.get("zona_sismica") as string;

      const res = await fetch(`${API_URL}/api/v1/aziende`, {
        method: "POST",
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

      router.push("/aziende");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore nella creazione");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="type-h1">Nuova Azienda</h1>
        <p className="type-body mt-2">Registra una nuova azienda cliente</p>
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
                  placeholder="Es. N2O SRL"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="partita_iva">Partita IVA</Label>
                <Input
                  id="partita_iva"
                  name="partita_iva"
                  placeholder="Es. 12345678901"
                  onBlur={(e) => validateField("partita_iva", e.target.value)}
                  className={fieldErrors.partita_iva ? "border-destructive" : ""}
                />
                {fieldErrors.partita_iva && (
                  <p className="text-xs text-destructive">{fieldErrors.partita_iva}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="codice_ateco">Codice ATECO</Label>
                <Input
                  id="codice_ateco"
                  name="codice_ateco"
                  placeholder="Es. 46.69.94"
                  onBlur={(e) => validateField("codice_ateco", e.target.value)}
                  className={fieldErrors.codice_ateco ? "border-destructive" : ""}
                />
                {fieldErrors.codice_ateco && (
                  <p className="text-xs text-destructive">{fieldErrors.codice_ateco}</p>
                )}
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="attivita">Attivit&agrave;</Label>
                <Input
                  id="attivita"
                  name="attivita"
                  placeholder="Es. Produzione alimentare"
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
                    placeholder="Es. Via dei Chiosi 4"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="sede_legale_citta">Citt&agrave;</Label>
                  <Input
                    id="sede_legale_citta"
                    name="sede_legale_citta"
                    placeholder="Es. Milano (MI)"
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
                    placeholder="Es. Via Milano 5"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="sede_operativa_citta">Citt&agrave;</Label>
                  <Input
                    id="sede_operativa_citta"
                    name="sede_operativa_citta"
                    placeholder="Es. Milano (MI)"
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
                  placeholder="Es. 08:00 - 17:00"
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
                  placeholder="Es. 250"
                  className="tnum"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="zona_sismica">Zona Sismica</Label>
                <select
                  id="zona_sismica"
                  name="zona_sismica"
                  className="h-10 w-full min-w-0 rounded-md border border-[#e5edf5] bg-white px-3 py-2 text-sm text-[#061b31] outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
                  defaultValue=""
                >
                  <option value="">Seleziona zona</option>
                  <option value="1">Zona 1 - Alta pericolosit&agrave;</option>
                  <option value="2">Zona 2 - Media pericolosit&agrave;</option>
                  <option value="3">Zona 3 - Bassa pericolosit&agrave;</option>
                  <option value="4">Zona 4 - Molto bassa pericolosit&agrave;</option>
                </select>
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
