"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function NewAziendaPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const formData = new FormData(e.currentTarget);

    try {
      // Get token fresh at submit time
      const sessionRes = await fetch("/api/auth/session");
      const session = await sessionRes.json();
      const token = session?.accessToken;

      if (!token) {
        setError("Sessione scaduta, effettua nuovamente il login");
        setLoading(false);
        return;
      }

      const res = await fetch(`${API_URL}/api/v1/aziende`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ragione_sociale: formData.get("ragione_sociale"),
          sede_legale_via: formData.get("sede_legale_via") || null,
          sede_legale_citta: formData.get("sede_legale_citta") || null,
          codice_ateco: formData.get("codice_ateco") || null,
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
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="ragione_sociale">Ragione Sociale *</Label>
              <Input
                id="ragione_sociale"
                name="ragione_sociale"
                required
                placeholder="Es. N2O SRL"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sede_legale_via">Sede Legale - Via</Label>
              <Input
                id="sede_legale_via"
                name="sede_legale_via"
                placeholder="Es. Via dei Chiosi 4"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sede_legale_citta">Sede Legale - Citt&agrave;</Label>
              <Input
                id="sede_legale_citta"
                name="sede_legale_citta"
                placeholder="Es. Milano (MI)"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="codice_ateco">Codice ATECO</Label>
              <Input
                id="codice_ateco"
                name="codice_ateco"
                placeholder="Es. 46.69.94"
              />
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
