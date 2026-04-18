"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { SurveyWizard } from "@/components/survey/survey-wizard";
import type { SurveyData } from "@/components/survey/survey-wizard";
import type { Azienda } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiCall<T>(path: string, token: string | null): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { headers });
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

        // Try to load existing survey data. The backend returns the shape
        // defined in `app/schemas/survey.py::SurveyResponse`, which uses
        // `sostanze_chimiche` and `rischi` — the wizard's SurveyData shape
        // uses `sostanze` and `valutazioni`. Normalise here (B-03 fix for
        // the "Riepilogo shows 0 valutazioni / 0 sostanze" regression).
        try {
          const surveyData = await apiCall<
            Partial<SurveyData> & {
              sostanze_chimiche?: SurveyData["sostanze"];
              rischi?: SurveyData["valutazioni"];
            }
          >(`/api/v1/aziende/${aziendaId}/survey`, token);
          setInitialData({
            azienda: aziendaData,
            persone: surveyData.persone ?? [],
            ambienti: surveyData.ambienti ?? [],
            attrezzature: surveyData.attrezzature ?? [],
            sostanze:
              surveyData.sostanze ?? surveyData.sostanze_chimiche ?? [],
            valutazioni:
              surveyData.valutazioni ?? surveyData.rischi ?? [],
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
          <h1 className="type-h1">
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
          <h1 className="type-h1">
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
        <h1 className="type-h1">
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
