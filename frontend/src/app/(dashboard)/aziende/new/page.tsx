"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PARTITA_IVA_REGEX = /^\d{11}$/;
const ATECO_REGEX = /^\d{2}(\.\d{2}(\.\d{1,2})?)?$/;

export default function NewAziendaPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

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
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Nuova Azienda</h1>
        <p className="text-muted-foreground">Registra una nuova azienda cliente</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Dati Azienda</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
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

            <div className="space-y-3">
              <h3 className="text-sm font-semibold">Sede Legale</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="sede_legale_via">Via / Indirizzo</Label>
                  <Input
                    id="sede_legale_via"
                    name="sede_legale_via"
                    placeholder="Es. Via dei Chiosi 4"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sede_legale_citta">Citt&agrave;</Label>
                  <Input
                    id="sede_legale_citta"
                    name="sede_legale_citta"
                    placeholder="Es. Milano (MI)"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-semibold">Sede Operativa</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="sede_operativa_via">Via / Indirizzo</Label>
                  <Input
                    id="sede_operativa_via"
                    name="sede_operativa_via"
                    placeholder="Es. Via Milano 5"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sede_operativa_citta">Citt&agrave;</Label>
                  <Input
                    id="sede_operativa_citta"
                    name="sede_operativa_citta"
                    placeholder="Es. Milano (MI)"
                  />
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="orario_lavoro">Orario di Lavoro</Label>
                <Input
                  id="orario_lavoro"
                  name="orario_lavoro"
                  placeholder="Es. 08:00 - 17:00"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="metratura_totale">Metratura Totale (mq)</Label>
                <Input
                  id="metratura_totale"
                  name="metratura_totale"
                  type="number"
                  step="0.1"
                  min="0"
                  placeholder="Es. 250"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="zona_sismica">Zona Sismica</Label>
                <select
                  id="zona_sismica"
                  name="zona_sismica"
                  className="h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
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
            <div className="flex gap-3">
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
