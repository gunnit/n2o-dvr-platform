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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Copy,
  HardHat,
  Loader2,
  ShieldAlert,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import type {
  DpiCatalogResponse,
  MansioneSorveglianza,
  Persona,
  RischiSpecificiCatalogResponse,
} from "@/types";

interface StepDpiRischiProps {
  aziendaId: string;
  persone: Persona[];
  mansioniSorveglianza: MansioneSorveglianza[];
  onChange: (rows: MansioneSorveglianza[]) => void;
}

// Distinct mansioni from persone, trimmed, deduped, sorted.
// Empty / whitespace mansioni are skipped — the step renders an empty state
// in that case so the operator knows to fill mansioni first.
function distinctMansioni(persone: Persona[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const p of persone) {
    const m = (p.mansione ?? "").trim();
    if (!m || seen.has(m)) continue;
    seen.add(m);
    out.push(m);
  }
  return out.sort((a, b) => a.localeCompare(b, "it"));
}

// Build a map mansione_nome -> row, returning a synthetic (unsaved) row
// when missing so the UI always has something to render per mansione.
function buildRowsByMansione(
  mansioni: string[],
  rows: MansioneSorveglianza[],
  aziendaId: string
): Map<string, MansioneSorveglianza> {
  const byNome = new Map<string, MansioneSorveglianza>();
  for (const r of rows) byNome.set(r.mansione_nome, r);

  const out = new Map<string, MansioneSorveglianza>();
  const nowIso = new Date().toISOString();
  for (const nome of mansioni) {
    const existing = byNome.get(nome);
    if (existing) {
      out.set(nome, existing);
    } else {
      out.set(nome, {
        // Placeholder id — replaced with server-returned id after first PUT.
        id: `pending-${nome}`,
        azienda_id: aziendaId,
        mansione_nome: nome,
        dpi_codes: [],
        rischi_specifici_codes: [],
        note: null,
        created_at: nowIso,
        updated_at: nowIso,
      });
    }
  }
  return out;
}

export function StepDpiRischi({
  aziendaId,
  persone,
  mansioniSorveglianza,
  onChange,
}: StepDpiRischiProps) {
  const { apiFetch } = useApi();

  const [dpiCatalog, setDpiCatalog] = useState<DpiCatalogResponse | null>(null);
  const [rischiCatalog, setRischiCatalog] =
    useState<RischiSpecificiCatalogResponse | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  // Phase 5.1 + 5.2 — track AI generation per mansione so two mansioni
  // can be in flight at once without their loading state colliding.
  const [aiLoadingByMansione, setAiLoadingByMansione] = useState<
    Record<string, boolean>
  >({});

  const mansioni = useMemo(() => distinctMansioni(persone), [persone]);
  const [selectedMansione, setSelectedMansione] = useState<string | null>(null);

  // Default-select the first mansione as the operator reaches this step.
  useEffect(() => {
    if (mansioni.length > 0 && !selectedMansione) {
      setSelectedMansione(mansioni[0]);
    } else if (
      selectedMansione &&
      !mansioni.includes(selectedMansione) &&
      mansioni.length > 0
    ) {
      // Previously-selected mansione disappeared from persone — fall back.
      setSelectedMansione(mansioni[0]);
    }
  }, [mansioni, selectedMansione]);

  // Fetch both catalogs once. 5 KB combined so no incremental loading.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setCatalogLoading(true);
        const [dpi, rischi] = await Promise.all([
          apiFetch<DpiCatalogResponse>("/api/v1/lookup/dpi-catalog"),
          apiFetch<RischiSpecificiCatalogResponse>(
            "/api/v1/lookup/rischi-specifici-catalog"
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
              : "Errore caricamento catalogo DPI/rischi"
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

  const rowsByMansione = useMemo(
    () => buildRowsByMansione(mansioni, mansioniSorveglianza, aziendaId),
    [mansioni, mansioniSorveglianza, aziendaId]
  );

  // Debounced per-mansione upsert. Multiple checkbox toggles coalesce into
  // one PUT 800ms after the last edit.
  const saveTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map()
  );

  useEffect(() => {
    const timers = saveTimersRef.current;
    return () => {
      for (const h of timers.values()) clearTimeout(h);
    };
  }, []);

  const scheduleSave = useCallback(
    (row: MansioneSorveglianza) => {
      const timers = saveTimersRef.current;
      const key = row.mansione_nome;
      const existing = timers.get(key);
      if (existing) clearTimeout(existing);
      const handle = setTimeout(async () => {
        timers.delete(key);
        try {
          const saved = await apiFetch<MansioneSorveglianza>(
            `/api/v1/aziende/${aziendaId}/mansioni-sorveglianza`,
            {
              method: "PUT",
              body: JSON.stringify({
                mansione_nome: row.mansione_nome,
                dpi_codes: row.dpi_codes,
                rischi_specifici_codes: row.rischi_specifici_codes,
                note: row.note,
              }),
            }
          );
          // Replace placeholder id with server id.
          onChange(
            Array.from(rowsByMansione.values()).map((r) =>
              r.mansione_nome === saved.mansione_nome ? saved : r
            )
          );
        } catch (err) {
          toast.error(
            err instanceof Error ? err.message : "Salvataggio fallito"
          );
        }
      }, 800);
      timers.set(key, handle);
    },
    [apiFetch, aziendaId, onChange, rowsByMansione]
  );

  const updateRow = useCallback(
    (mansioneNome: string, patch: Partial<MansioneSorveglianza>) => {
      const current = rowsByMansione.get(mansioneNome);
      if (!current) return;
      const merged = { ...current, ...patch };
      const next = Array.from(rowsByMansione.values()).map((r) =>
        r.mansione_nome === mansioneNome ? merged : r
      );
      onChange(next);
      scheduleSave(merged);
    },
    [rowsByMansione, onChange, scheduleSave]
  );

  const toggleDpi = useCallback(
    (mansioneNome: string, code: string) => {
      const row = rowsByMansione.get(mansioneNome);
      if (!row) return;
      const has = row.dpi_codes.includes(code);
      updateRow(mansioneNome, {
        dpi_codes: has
          ? row.dpi_codes.filter((c) => c !== code)
          : [...row.dpi_codes, code],
      });
    },
    [rowsByMansione, updateRow]
  );

  const toggleRischio = useCallback(
    (mansioneNome: string, code: string) => {
      const row = rowsByMansione.get(mansioneNome);
      if (!row) return;
      const has = row.rischi_specifici_codes.includes(code);
      updateRow(mansioneNome, {
        rischi_specifici_codes: has
          ? row.rischi_specifici_codes.filter((c) => c !== code)
          : [...row.rischi_specifici_codes, code],
      });
    },
    [rowsByMansione, updateRow]
  );

  // Phase 5.1 + 5.2 — ask the AI to propose DPI + rischi codes for the
  // current mansione, then merge them into the row. Merge (not replace)
  // so the operator's prior ticks survive and the AI never silently
  // removes a deliberate selection.
  const flagWithAi = useCallback(
    async (mansioneNome: string) => {
      const row = rowsByMansione.get(mansioneNome);
      if (!row) return;
      setAiLoadingByMansione((prev) => ({ ...prev, [mansioneNome]: true }));
      try {
        const result = await apiFetch<{
          dpi_codes: string[];
          rischi_specifici_codes: string[];
          motivazione: string;
        }>(
          `/api/v1/aziende/${aziendaId}/mansioni-sorveglianza/suggerisci`,
          {
            method: "POST",
            body: JSON.stringify({ mansione_nome: mansioneNome }),
          },
        );

        const existingDpi = new Set(row.dpi_codes);
        const existingRischi = new Set(row.rischi_specifici_codes);
        const addedDpi = result.dpi_codes.filter((c) => !existingDpi.has(c));
        const addedRischi = result.rischi_specifici_codes.filter(
          (c) => !existingRischi.has(c),
        );

        if (addedDpi.length === 0 && addedRischi.length === 0) {
          toast.info(
            `L'AI non ha trovato suggerimenti aggiuntivi per "${mansioneNome}".`,
          );
          return;
        }

        updateRow(mansioneNome, {
          dpi_codes: [...row.dpi_codes, ...addedDpi],
          rischi_specifici_codes: [
            ...row.rischi_specifici_codes,
            ...addedRischi,
          ],
        });
        toast.success(
          `AI: +${addedDpi.length} DPI, +${addedRischi.length} rischi. ${result.motivazione}`,
          { duration: 9000 },
        );
      } catch (err) {
        toast.error(
          err instanceof Error
            ? err.message
            : "Errore nella generazione AI",
        );
      } finally {
        setAiLoadingByMansione((prev) => ({
          ...prev,
          [mansioneNome]: false,
        }));
      }
    },
    [apiFetch, aziendaId, rowsByMansione, updateRow],
  );

  const copyFromOther = useCallback(
    (toMansione: string, fromMansione: string) => {
      const source = rowsByMansione.get(fromMansione);
      if (!source) return;
      updateRow(toMansione, {
        dpi_codes: [...source.dpi_codes],
        rischi_specifici_codes: [...source.rischi_specifici_codes],
      });
      toast.success(`Flag copiati da "${fromMansione}"`);
    },
    [rowsByMansione, updateRow]
  );

  // ---------- empty states ----------
  if (mansioni.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
        <Stethoscope className="h-8 w-8 text-[#64748d]" strokeWidth={1.5} />
        <p className="text-[14px] text-[#273951]">
          Nessuna mansione definita.
        </p>
        <p className="max-w-md text-[13px] text-[#64748d]">
          Aggiungi persone con mansione nel passo 2 per abilitare la flaggatura
          dei DPI e dei rischi specifici per mansione.
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

  const currentRow = selectedMansione
    ? rowsByMansione.get(selectedMansione)
    : null;
  const otherMansioni = mansioni.filter((m) => m !== selectedMansione);

  // Count persone sharing each mansione to show the context chip.
  const personeCountByMansione = mansioni.reduce<Record<string, number>>(
    (acc, m) => {
      acc[m] = persone.filter((p) => (p.mansione ?? "").trim() === m).length;
      return acc;
    },
    {}
  );

  return (
    <div className="space-y-6">
      {/* Heading */}
      <div>
        <h3 className="font-heading text-xl font-bold text-[#061b31]">
          DPI & Rischi Specifici
        </h3>
        <p className="mt-1 text-sm text-[#64748d]">
          Flagga, per ogni mansione, i DPI in uso e i rischi specifici (D.Lgs.
          81/08) a cui i lavoratori sono esposti. Il Medico del Lavoro usa
          questi dati per definire il protocollo delle visite mediche.
        </p>
      </div>

      {/* Mansione selector */}
      <div className="space-y-2">
        <span className="type-eyebrow">Seleziona Mansione</span>
        <div className="flex flex-wrap gap-2">
          {mansioni.map((nome) => {
            const row = rowsByMansione.get(nome);
            const total =
              (row?.dpi_codes.length ?? 0) +
              (row?.rischi_specifici_codes.length ?? 0);
            const isActive = nome === selectedMansione;
            return (
              <button
                key={nome}
                type="button"
                onClick={() => setSelectedMansione(nome)}
                className={cn(
                  "inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors",
                  isActive
                    ? "border-primary bg-primary text-white"
                    : "border-[#e5edf5] bg-white text-[#273951] hover:bg-[#f6f9fc]"
                )}
              >
                <span>{nome}</span>
                <Badge
                  variant="outline"
                  className={cn(
                    "h-4 rounded-sm px-1 text-[10px] tnum",
                    isActive
                      ? "border-white/30 bg-white/10 text-white"
                      : "border-[#e5edf5] bg-[#f6f9fc] text-[#64748d]"
                  )}
                >
                  {personeCountByMansione[nome]}p · {total} flag
                </Badge>
              </button>
            );
          })}
        </div>
      </div>

      {currentRow && selectedMansione && (
        <>
          {/* Header card with counts + copy action */}
          <Card>
            <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-1">
                <CardTitle className="text-base">{selectedMansione}</CardTitle>
                <CardDescription>
                  {personeCountByMansione[selectedMansione]} person
                  {personeCountByMansione[selectedMansione] === 1 ? "a" : "e"}{" "}
                  con questa mansione · {currentRow.dpi_codes.length} DPI ·{" "}
                  {currentRow.rischi_specifici_codes.length} rischi
                </CardDescription>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {/* Phase 5.1 + 5.2 — Flegga con AI */}
                <button
                  type="button"
                  onClick={() => flagWithAi(selectedMansione)}
                  disabled={aiLoadingByMansione[selectedMansione] === true}
                  className="inline-flex h-8 items-center gap-2 rounded-md border border-violet-300 bg-violet-50 px-3 text-xs font-medium text-violet-800 transition-colors hover:bg-violet-100 disabled:opacity-60 dark:border-violet-700 dark:bg-violet-950/40 dark:text-violet-200 dark:hover:bg-violet-900/40"
                >
                  {aiLoadingByMansione[selectedMansione] ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Generazione...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3.5 w-3.5" />
                      Flegga con AI
                    </>
                  )}
                </button>
                {otherMansioni.length > 0 && (
                  <DropdownMenu>
                    <DropdownMenuTrigger
                      className="inline-flex h-8 items-center gap-2 rounded-md border border-[#e5edf5] bg-white px-3 text-xs font-medium text-[#273951] transition-colors hover:bg-[#f6f9fc]"
                    >
                      <Copy className="h-3.5 w-3.5" />
                      Copia da altra mansione
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      {otherMansioni.map((other) => {
                        const src = rowsByMansione.get(other);
                        const count =
                          (src?.dpi_codes.length ?? 0) +
                          (src?.rischi_specifici_codes.length ?? 0);
                        return (
                          <DropdownMenuItem
                            key={other}
                            onClick={() =>
                              copyFromOther(selectedMansione, other)
                            }
                            disabled={count === 0}
                          >
                            <span className="mr-2">{other}</span>
                            <Badge
                              variant="outline"
                              className="h-4 rounded-sm px-1 text-[10px] tnum"
                            >
                              {count}
                            </Badge>
                          </DropdownMenuItem>
                        );
                      })}
                    </DropdownMenuContent>
                  </DropdownMenu>
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
                {currentRow.dpi_codes.length} su {" "}
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
                      const checked = currentRow.dpi_codes.includes(item.code);
                      return (
                        <button
                          key={item.code}
                          type="button"
                          onClick={() =>
                            toggleDpi(selectedMansione, item.code)
                          }
                          className={cn(
                            "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[12.5px] transition-colors",
                            checked
                              ? "border-primary bg-[rgba(0,61,116,0.08)] text-primary"
                              : "border-[#e5edf5] bg-white text-[#273951] hover:bg-[#f6f9fc]"
                          )}
                        >
                          <span
                            aria-hidden
                            className={cn(
                              "flex h-3.5 w-3.5 items-center justify-center rounded-sm border",
                              checked
                                ? "border-primary bg-primary text-white"
                                : "border-[#c2c6d2] bg-white"
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
                {currentRow.rischi_specifici_codes.length} su {" "}
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
                        currentRow.rischi_specifici_codes.includes(item.code);
                      return (
                        <button
                          key={item.code}
                          type="button"
                          onClick={() =>
                            toggleRischio(selectedMansione, item.code)
                          }
                          className={cn(
                            "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[12.5px] transition-colors",
                            checked
                              ? "border-primary bg-[rgba(0,61,116,0.08)] text-primary"
                              : "border-[#e5edf5] bg-white text-[#273951] hover:bg-[#f6f9fc]"
                          )}
                        >
                          <span
                            aria-hidden
                            className={cn(
                              "flex h-3.5 w-3.5 items-center justify-center rounded-sm border",
                              checked
                                ? "border-primary bg-primary text-white"
                                : "border-[#c2c6d2] bg-white"
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
