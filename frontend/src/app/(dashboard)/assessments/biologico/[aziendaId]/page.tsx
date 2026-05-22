"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  BiologicoForm,
  type BiologicoResult,
  type BiologicoState,
} from "@/components/assessments/biologico/biologico-form";
import type { Azienda } from "@/types";

/**
 * Valutazione Rischio Biologico — settori alimentare / asilo / dentisti.
 * US-3.15, D.Lgs. 81/2008 Titolo X + Reg. CE 852/2004 (alimentare).
 *
 * Next.js 16 — params is a Promise (unwrap via React.use).
 */
export default function BiologicoAssessmentPage({
  params,
}: {
  params: Promise<{ aziendaId: string }>;
}) {
  const { aziendaId } = use(params);

  const [azienda, setAzienda] = useState<Azienda | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [state, setState] = useState<BiologicoState | null>(null);
  const [result, setResult] = useState<BiologicoResult | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [savedSummary, setSavedSummary] = useState<
    { settore: string; livello: string | null; updated_at: string }[]
  >([]);

  // --------------------------------------------------------------- Azienda
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const apiUrl =
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        let token: string | null = null;
        try {
          const s = await fetch("/api/auth/session");
          const session = await s.json();
          token = session?.accessToken ?? null;
        } catch {
          /* noop */
        }
        const headers = token
          ? {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            }
          : { "Content-Type": "application/json" };
        const [azRes, valRes] = await Promise.all([
          fetch(`${apiUrl}/api/v1/aziende/${aziendaId}`, { headers }),
          fetch(
            `${apiUrl}/api/v1/aziende/${aziendaId}/biologico-valutazioni`,
            { headers },
          ),
        ]);
        if (!azRes.ok) throw new Error(`Errore ${azRes.status}`);
        const data = (await azRes.json()) as Azienda;
        if (!cancelled) setAzienda(data);
        if (valRes.ok) {
          const rows = (await valRes.json()) as Array<{
            settore: string;
            livello_rischio: string | null;
            created_at: string;
          }>;
          if (!cancelled) {
            setSavedSummary(
              rows.map((r) => ({
                settore: r.settore,
                livello: r.livello_rischio,
                updated_at: r.created_at,
              })),
            );
          }
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error
              ? err.message
              : "Impossibile caricare l'azienda",
          );
        }
      }
    }
    if (aziendaId) load();
    return () => {
      cancelled = true;
    };
  }, [aziendaId]);

  const pageSubtitle = useMemo(() => {
    if (loadError) return `Azienda ${aziendaId} (metadati non disponibili)`;
    if (azienda) return azienda.ragione_sociale ?? `Azienda ${aziendaId}`;
    return "Caricamento…";
  }, [azienda, aziendaId, loadError]);

  // --------------------------------------------------------------- Save
  const save = useCallback(async () => {
    if (!state || !result) return;
    setSaving(true);
    setSaveMessage(null);

    // The Biologico assessment persistence endpoint is still being built
    // (Wave 1.2). In the meantime we keep the draft in localStorage (handled
    // by the form component) and attempt a best-effort POST — if the endpoint
    // returns 404 we surface a non-blocking notice so operators know the
    // draft is safe locally.
    try {
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      let token: string | null = null;
      try {
        const s = await fetch("/api/auth/session");
        const session = await s.json();
        token = session?.accessToken ?? null;
      } catch {
        /* noop */
      }

      const risposteList = Object.entries(state.risposte).map(
        ([id, risposta]) => ({ id, risposta }),
      );

      const body = {
        settore: state.settore,
        risposte_checklist: risposteList,
        protocollo_sanitario: state.protocolloSanitario || null,
        livello_rischio: result.livello,
      };

      const res = await fetch(
        `${apiUrl}/api/v1/aziende/${aziendaId}/biologico-valutazioni`,
        {
          method: "POST",
          headers: token
            ? {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              }
            : { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`API ${res.status}: ${txt}`);
      }
      const saved = (await res.json()) as {
        settore: string;
        livello_rischio: string | null;
        created_at: string;
      };
      // Refresh the "valutazioni archiviate" summary so the new save appears.
      setSavedSummary((prev) => {
        const filtered = prev.filter((r) => r.settore !== saved.settore);
        return [
          ...filtered,
          {
            settore: saved.settore,
            livello: saved.livello_rischio,
            updated_at: saved.created_at,
          },
        ];
      });
      setSaveMessage(
        `Valutazione salvata: livello ${result.livello} (rapporto ${(
          result.ratio * 100
        ).toFixed(0)}%).`,
      );
      setDirty(false);
    } catch (err) {
      setSaveMessage(
        err instanceof Error
          ? `Errore salvataggio: ${err.message}. La bozza resta in locale.`
          : "Errore sconosciuto. La bozza resta in locale.",
      );
    } finally {
      setSaving(false);
    }
  }, [aziendaId, state, result]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
            <Badge variant="secondary">Allegato Rischio Biologico</Badge>
            <span>D.Lgs. 81/2008 · Titolo X</span>
            {dirty && (
              <Badge
                variant="outline"
                className="border-amber-500/40 bg-amber-500/10 text-amber-800"
              >
                Modifiche non salvate
              </Badge>
            )}
          </div>
          <h1 className="mt-2 type-h1">
            Valutazione Rischio Biologico
          </h1>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>
      </div>

      {savedSummary.length > 0 && (
        <Card className="border-emerald-200/60 bg-emerald-50/40">
          <CardContent className="py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-emerald-800">
              Valutazioni archiviate
            </p>
            <ul className="mt-2 grid grid-cols-1 gap-2 text-xs sm:grid-cols-3">
              {savedSummary.map((s) => (
                <li
                  key={s.settore}
                  className="flex items-center justify-between rounded-md bg-background px-3 py-2 ring-1 ring-border"
                >
                  <span className="capitalize">{s.settore}</span>
                  {s.livello ? (
                    <Badge variant="outline">{s.livello}</Badge>
                  ) : (
                    <Badge variant="secondary">—</Badge>
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <BiologicoForm
        aziendaId={aziendaId}
        onStateChange={setState}
        onResultChange={setResult}
        onDirtyChange={setDirty}
      />

      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div>
            <p className="text-sm font-medium">Salva valutazione</p>
            <p className="text-xs text-muted-foreground">
              {result
                ? `Livello corrente: ${result.livello}. ${
                    result.unanswered.length > 0
                      ? `Controlli ancora senza risposta: ${result.unanswered.length}.`
                      : "Tutti i controlli sono stati valutati."
                  }`
                : "Compila la checklist per attivare il salvataggio."}
            </p>
            {saveMessage && (
              <p
                className={cn(
                  "mt-1 text-xs",
                  saveMessage.startsWith("Errore")
                    ? "text-destructive"
                    : "text-emerald-700",
                )}
              >
                {saveMessage}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button disabled={!state || !result || saving} onClick={save}>
              {saving ? "Salvataggio…" : "Salva valutazione"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <p className="text-[11px] text-muted-foreground">
        Bozza salvata in locale (chiave: <code>biologico-draft-{aziendaId}</code>)
      </p>
    </div>
  );
}
