"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  HardHat,
  Loader2,
  ShieldAlert,
  Sparkles,
  Stethoscope,
  Users2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import type {
  DpiCatalogResponse,
  DpiRischiSuggerito,
  Persona,
  RischiSpecificiCatalogResponse,
} from "@/types";

interface StepDpiRischiProps {
  aziendaId: string;
  persone: Persona[];
  onChange: (persone: Persona[]) => void;
}

// Sort persone by mansione, then by nominativo, so colleagues with the
// same role are visually grouped in the selector and the operator can
// scan the list for the right person quickly.
function sortPersone(persone: Persona[]): Persona[] {
  return [...persone].sort((a, b) => {
    const ma = (a.mansione ?? "").trim().toLowerCase();
    const mb = (b.mansione ?? "").trim().toLowerCase();
    if (ma !== mb) return ma.localeCompare(mb, "it");
    return (a.nominativo ?? "").localeCompare(b.nominativo ?? "", "it");
  });
}

export function StepDpiRischi({
  aziendaId,
  persone,
  onChange,
}: StepDpiRischiProps) {
  const { apiFetch } = useApi();

  const [dpiCatalog, setDpiCatalog] = useState<DpiCatalogResponse | null>(null);
  const [rischiCatalog, setRischiCatalog] =
    useState<RischiSpecificiCatalogResponse | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  // Track AI generation per persona so two persone can be in flight at
  // once without their loading state colliding.
  const [aiLoadingByPersona, setAiLoadingByPersona] = useState<
    Record<string, boolean>
  >({});

  const sortedPersone = useMemo(() => sortPersone(persone), [persone]);
  const [selectedPersonaId, setSelectedPersonaId] = useState<string | null>(
    null,
  );

  // Default-select the first persona when the operator reaches this step.
  useEffect(() => {
    if (sortedPersone.length > 0 && !selectedPersonaId) {
      setSelectedPersonaId(sortedPersone[0].id);
    } else if (
      selectedPersonaId &&
      !sortedPersone.some((p) => p.id === selectedPersonaId) &&
      sortedPersone.length > 0
    ) {
      setSelectedPersonaId(sortedPersone[0].id);
    }
  }, [sortedPersone, selectedPersonaId]);

  // Fetch both catalogs once. ~5 KB combined.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setCatalogLoading(true);
        const [dpi, rischi] = await Promise.all([
          apiFetch<DpiCatalogResponse>("/api/v1/lookup/dpi-catalog"),
          apiFetch<RischiSpecificiCatalogResponse>(
            "/api/v1/lookup/rischi-specifici-catalog",
          ),
        ]);
        if (cancelled) return;
        setDpiCatalog(dpi);
        setRischiCatalog(rischi);
      } catch (err) {
        if (!cancelled) {
          toast.error(
            err instanceof Error
              ? err.message
              : "Errore caricamento catalogo DPI/rischi",
          );
        }
      } finally {
        if (!cancelled) setCatalogLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiFetch]);

  // Latest persone prop, mirrored in a ref so the debounced save's success
  // branch always merges into the freshest list — without it, a PUT for
  // persona A in flight while the operator toggles persona B would
  // overwrite B's pending tick with A's stale snapshot.
  const latestPersoneRef = useRef(persone);
  useEffect(() => {
    latestPersoneRef.current = persone;
  }, [persone]);

  // Debounced per-persona PUT. Multiple checkbox toggles coalesce into
  // one request 800ms after the last edit.
  const saveTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map(),
  );

  useEffect(() => {
    const timers = saveTimersRef.current;
    return () => {
      for (const h of timers.values()) clearTimeout(h);
    };
  }, []);

  const scheduleSave = useCallback(
    (persona: Persona) => {
      const timers = saveTimersRef.current;
      const key = persona.id;
      const existing = timers.get(key);
      if (existing) clearTimeout(existing);
      const handle = setTimeout(async () => {
        timers.delete(key);
        try {
          const saved = await apiFetch<Persona>(
            `/api/v1/aziende/${aziendaId}/persone/${persona.id}`,
            {
              method: "PUT",
              body: JSON.stringify({
                dpi_codes: persona.dpi_codes,
                rischi_specifici_codes: persona.rischi_specifici_codes,
                dpi_rischi_note: persona.dpi_rischi_note,
              }),
            },
          );
          // Merge the saved persona into the freshest array (ref, not
          // closure) so concurrent edits on other persone aren't clobbered.
          onChange(
            latestPersoneRef.current.map((p) =>
              p.id === saved.id ? saved : p,
            ),
          );
        } catch (err) {
          toast.error(
            err instanceof Error ? err.message : "Salvataggio fallito",
          );
        }
      }, 800);
      timers.set(key, handle);
    },
    [apiFetch, aziendaId, onChange],
  );

  const updatePersona = useCallback(
    (personaId: string, patch: Partial<Persona>) => {
      const current = latestPersoneRef.current.find((p) => p.id === personaId);
      if (!current) return;
      const merged: Persona = { ...current, ...patch };
      onChange(
        latestPersoneRef.current.map((p) =>
          p.id === personaId ? merged : p,
        ),
      );
      scheduleSave(merged);
    },
    [onChange, scheduleSave],
  );

  const toggleDpi = useCallback(
    (personaId: string, code: string) => {
      const current = latestPersoneRef.current.find((p) => p.id === personaId);
      if (!current) return;
      const has = current.dpi_codes.includes(code);
      updatePersona(personaId, {
        dpi_codes: has
          ? current.dpi_codes.filter((c) => c !== code)
          : [...current.dpi_codes, code],
      });
    },
    [updatePersona],
  );

  const toggleRischio = useCallback(
    (personaId: string, code: string) => {
      const current = latestPersoneRef.current.find((p) => p.id === personaId);
      if (!current) return;
      const has = current.rischi_specifici_codes.includes(code);
      updatePersona(personaId, {
        rischi_specifici_codes: has
          ? current.rischi_specifici_codes.filter((c) => c !== code)
          : [...current.rischi_specifici_codes, code],
      });
    },
    [updatePersona],
  );

  // Ask the AI to propose DPI + rischi codes for the selected persona,
  // then merge them into the persona's flags. Merge (not replace) so
  // operator-chosen ticks survive and the AI never silently removes a
  // deliberate selection.
  const flagWithAi = useCallback(
    async (personaId: string) => {
      const current = latestPersoneRef.current.find((p) => p.id === personaId);
      if (!current) return;
      setAiLoadingByPersona((prev) => ({ ...prev, [personaId]: true }));
      try {
        const result = await apiFetch<DpiRischiSuggerito>(
          `/api/v1/aziende/${aziendaId}/persone/${personaId}/dpi-rischi/suggerisci`,
          { method: "POST" },
        );

        const existingDpi = new Set(current.dpi_codes);
        const existingRischi = new Set(current.rischi_specifici_codes);
        const addedDpi = result.dpi_codes.filter((c) => !existingDpi.has(c));
        const addedRischi = result.rischi_specifici_codes.filter(
          (c) => !existingRischi.has(c),
        );

        if (addedDpi.length === 0 && addedRischi.length === 0) {
          toast.info(
            `L'AI non ha trovato suggerimenti aggiuntivi per "${current.nominativo}".`,
          );
          return;
        }

        updatePersona(personaId, {
          dpi_codes: [...current.dpi_codes, ...addedDpi],
          rischi_specifici_codes: [
            ...current.rischi_specifici_codes,
            ...addedRischi,
          ],
        });
        toast.success(
          `AI: +${addedDpi.length} DPI, +${addedRischi.length} rischi. ${result.motivazione}`,
          { duration: 9000 },
        );
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : "Errore nella generazione AI",
        );
      } finally {
        setAiLoadingByPersona((prev) => ({ ...prev, [personaId]: false }));
      }
    },
    [apiFetch, aziendaId, updatePersona],
  );

  // Feedback issue #9 (2026-05-14): the "Copia da altra persona" dropdown
  // was removed — operators preferred the bulk "Applica a tutti con stessa
  // mansione" action below and the per-person copy added clutter.

  // Bulk-apply: copy the source persona's flags to all other persone
  // sharing the same mansione. Useful for aziende with many workers in
  // the same role — the operator flags one and replicates.
  const applyToSameMansione = useCallback(
    (sourcePersonaId: string) => {
      const source = latestPersoneRef.current.find(
        (p) => p.id === sourcePersonaId,
      );
      if (!source) return;
      const mansione = (source.mansione ?? "").trim().toLowerCase();
      if (!mansione) {
        toast.error(
          "La persona non ha una mansione definita — imposta la mansione nel passo Persone per usare questa azione.",
        );
        return;
      }
      const targets = latestPersoneRef.current.filter(
        (p) =>
          p.id !== sourcePersonaId &&
          (p.mansione ?? "").trim().toLowerCase() === mansione,
      );
      if (targets.length === 0) {
        toast.info(
          `Nessun'altra persona con mansione "${source.mansione}" da aggiornare.`,
        );
        return;
      }
      for (const target of targets) {
        updatePersona(target.id, {
          dpi_codes: [...source.dpi_codes],
          rischi_specifici_codes: [...source.rischi_specifici_codes],
        });
      }
      toast.success(
        `Flag applicati a ${targets.length} ${targets.length === 1 ? "persona" : "persone"} con mansione "${source.mansione}".`,
      );
    },
    [updatePersona],
  );

  // ---------- empty states ----------
  if (sortedPersone.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
        <Stethoscope className="h-8 w-8 text-[#64748d]" strokeWidth={1.5} />
        <p className="text-[14px] text-[#273951]">Nessuna persona definita.</p>
        <p className="max-w-md text-[13px] text-[#64748d]">
          Aggiungi persone nel passo Persone per abilitare la flaggatura dei DPI
          e dei rischi specifici per ciascun lavoratore.
        </p>
      </div>
    );
  }

  if (catalogLoading || !dpiCatalog || !rischiCatalog) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#e5edf5] border-t-primary" />
      </div>
    );
  }

  const currentPersona = selectedPersonaId
    ? sortedPersone.find((p) => p.id === selectedPersonaId)
    : null;
  const otherPersone = sortedPersone.filter(
    (p) => p.id !== selectedPersonaId,
  );

  return (
    <div className="space-y-6">
      {/* Heading */}
      <div>
        <h3 className="font-heading text-xl font-bold text-[#061b31]">
          DPI & Rischi Specifici
        </h3>
        <p className="mt-1 text-sm text-[#64748d]">
          Per ogni lavoratore, flagga i DPI in uso e i rischi specifici
          (D.Lgs. 81/08) a cui è esposto. Il Medico del Lavoro usa questi dati
          per definire il protocollo delle visite mediche. Due persone con la
          stessa mansione possono avere flag diversi se le loro attrezzature
          speciali o gli ambienti differiscono.
        </p>
      </div>

      {/* Persona selector */}
      <div className="space-y-2">
        <span className="type-eyebrow">Seleziona Lavoratore</span>
        <div className="flex flex-wrap gap-2">
          {sortedPersone.map((p) => {
            const total =
              (p.dpi_codes?.length ?? 0) +
              (p.rischi_specifici_codes?.length ?? 0);
            const isActive = p.id === selectedPersonaId;
            const mansione = (p.mansione ?? "").trim() || "—";
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => setSelectedPersonaId(p.id)}
                className={cn(
                  "inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors",
                  isActive
                    ? "border-primary bg-primary text-white"
                    : "border-[#e5edf5] bg-white text-[#273951] hover:bg-[#f6f9fc]",
                )}
              >
                <span>{p.nominativo}</span>
                <Badge
                  variant="outline"
                  className={cn(
                    "h-4 rounded-sm px-1 text-[10px]",
                    isActive
                      ? "border-white/30 bg-white/10 text-white"
                      : "border-[#e5edf5] bg-[#f6f9fc] text-[#64748d]",
                  )}
                >
                  {mansione} · {total} flag
                </Badge>
              </button>
            );
          })}
        </div>
      </div>

      {currentPersona && (
        <>
          {/* Header card with counts + actions */}
          <Card>
            <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-1">
                <CardTitle className="text-base">
                  {currentPersona.nominativo}
                </CardTitle>
                <CardDescription>
                  {currentPersona.mansione || "Mansione non definita"} ·{" "}
                  {currentPersona.dpi_codes?.length ?? 0} DPI ·{" "}
                  {currentPersona.rischi_specifici_codes?.length ?? 0} rischi
                </CardDescription>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => flagWithAi(currentPersona.id)}
                  disabled={aiLoadingByPersona[currentPersona.id] === true}
                  className="inline-flex h-8 items-center gap-2 rounded-md border border-violet-300 bg-violet-50 px-3 text-xs font-medium text-violet-800 transition-colors hover:bg-violet-100 disabled:opacity-60"
                >
                  {aiLoadingByPersona[currentPersona.id] ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Generazione...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3.5 w-3.5" />
                      Flagga con AI
                    </>
                  )}
                </button>
                {currentPersona.mansione &&
                  otherPersone.some(
                    (p) =>
                      (p.mansione ?? "").trim().toLowerCase() ===
                      currentPersona.mansione!.trim().toLowerCase(),
                  ) && (
                    <button
                      type="button"
                      onClick={() => applyToSameMansione(currentPersona.id)}
                      className="inline-flex h-8 items-center gap-2 rounded-md border border-[#e5edf5] bg-white px-3 text-xs font-medium text-[#273951] transition-colors hover:bg-[#f6f9fc]"
                    >
                      <Users2 className="h-3.5 w-3.5" />
                      Applica a tutti con stessa mansione
                    </button>
                  )}
              </div>
            </CardHeader>
          </Card>

          {/* DPI section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <HardHat className="h-4 w-4 text-primary" />
                DPI in uso
              </CardTitle>
              <CardDescription>
                {currentPersona.dpi_codes?.length ?? 0} su{" "}
                {dpiCatalog.groups.reduce((n, g) => n + g.items.length, 0)}{" "}
                selezionati
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {dpiCatalog.groups.map((group) => (
                <div key={group.area}>
                  <h4 className="mb-2 type-eyebrow">{group.area}</h4>
                  <div className="flex flex-wrap gap-2">
                    {group.items.map((item) => {
                      const checked =
                        currentPersona.dpi_codes?.includes(item.code) ?? false;
                      return (
                        <button
                          key={item.code}
                          type="button"
                          onClick={() =>
                            toggleDpi(currentPersona.id, item.code)
                          }
                          className={cn(
                            "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[12.5px] transition-colors",
                            checked
                              ? "border-primary bg-[rgba(0,61,116,0.08)] text-primary"
                              : "border-[#e5edf5] bg-white text-[#273951] hover:bg-[#f6f9fc]",
                          )}
                        >
                          <span
                            aria-hidden
                            className={cn(
                              "flex h-3.5 w-3.5 items-center justify-center rounded-sm border",
                              checked
                                ? "border-primary bg-primary text-white"
                                : "border-[#c2c6d2] bg-white",
                            )}
                          >
                            {checked && (
                              <svg
                                viewBox="0 0 12 12"
                                className="h-2.5 w-2.5"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth={2.5}
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              >
                                <polyline points="2.5 6 5 8.5 9.5 4" />
                              </svg>
                            )}
                          </span>
                          <span>{item.etichetta}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Rischi specifici section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ShieldAlert className="h-4 w-4 text-primary" />
                Rischi Specifici D.Lgs. 81/08
              </CardTitle>
              <CardDescription>
                {currentPersona.rischi_specifici_codes?.length ?? 0} su{" "}
                {rischiCatalog.groups.reduce((n, g) => n + g.items.length, 0)}{" "}
                selezionati
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {rischiCatalog.groups.map((group) => (
                <div key={group.macro}>
                  <h4 className="mb-2 type-eyebrow">{group.macro}</h4>
                  <div className="flex flex-wrap gap-2">
                    {group.items.map((item) => {
                      const checked =
                        currentPersona.rischi_specifici_codes?.includes(
                          item.code,
                        ) ?? false;
                      return (
                        <button
                          key={item.code}
                          type="button"
                          onClick={() =>
                            toggleRischio(currentPersona.id, item.code)
                          }
                          className={cn(
                            "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[12.5px] transition-colors",
                            checked
                              ? "border-primary bg-[rgba(0,61,116,0.08)] text-primary"
                              : "border-[#e5edf5] bg-white text-[#273951] hover:bg-[#f6f9fc]",
                          )}
                        >
                          <span
                            aria-hidden
                            className={cn(
                              "flex h-3.5 w-3.5 items-center justify-center rounded-sm border",
                              checked
                                ? "border-primary bg-primary text-white"
                                : "border-[#c2c6d2] bg-white",
                            )}
                          >
                            {checked && (
                              <svg
                                viewBox="0 0 12 12"
                                className="h-2.5 w-2.5"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth={2.5}
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              >
                                <polyline points="2.5 6 5 8.5 9.5 4" />
                              </svg>
                            )}
                          </span>
                          <span>{item.etichetta}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
