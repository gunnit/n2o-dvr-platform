"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { SurveyWizard } from "@/components/survey/survey-wizard";
import type { SurveyData } from "@/components/survey/survey-wizard";
import type { Azienda } from "@/types";

async function apiCall<T>(path: string, token: string | null): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`http://localhost:8000${path}`, { headers });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  if (res.status === 204) return undefined as T;
  return res.json();
}

async function getToken(): Promise<string | null> {
  try {
    const res = await fetch("/api/auth/session");
    const session = await res.json();
    return session?.accessToken ?? null;
  } catch {
    return null;
  }
}

export default function SurveyAziendaPage() {
  const params = useParams<{ aziendaId: string }>();
  const aziendaId = params.aziendaId;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [initialData, setInitialData] = useState<Partial<SurveyData> | undefined>(undefined);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const token = await getToken();

        // Load azienda data
        const aziendaData = await apiCall<Azienda>(
          `/api/v1/aziende/${aziendaId}`,
          token
        );
        setAzienda(aziendaData);

        // Try to load existing survey data
        try {
          const surveyData = await apiCall<Partial<SurveyData>>(
            `/api/v1/aziende/${aziendaId}/survey`,
            token
          );
          setInitialData({
            azienda: aziendaData,
            ...surveyData,
          });
        } catch {
          // No existing survey data — start fresh
          setInitialData({ azienda: aziendaData });
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Errore nel caricamento dei dati"
        );
      } finally {
        setLoading(false);
      }
    }

    if (aziendaId) {
      loadData();
    }
  }, [aziendaId]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Sopralluogo
          </h1>
          <p className="text-muted-foreground">Caricamento in corso...</p>
        </div>
        <div className="flex items-center justify-center py-24">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted-foreground/20 border-t-primary" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Sopralluogo
          </h1>
          <p className="text-muted-foreground">
            Errore nel caricamento dei dati
          </p>
        </div>
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Sopralluogo
        </h1>
        <p className="text-muted-foreground">
          {azienda?.ragione_sociale ?? `Azienda ${aziendaId}`}
        </p>
      </div>

      <SurveyWizard aziendaId={aziendaId} initialData={initialData} />
    </div>
  );
}
