"use client";

import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Plus,
  Trash2,
  Check,
  Sparkles,
  Loader2,
  X,
  Camera,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import type { Ambiente, AmbienteFoto, Attrezzatura } from "@/types";

interface StepAttrezzatureProps {
  aziendaId: string;
  ambienti: Ambiente[];
  attrezzature: Attrezzatura[];
  onChange: (attrezzature: Attrezzatura[]) => void;
}

const EQUIPMENT_BY_TYPE: Record<string, string[]> = {
  Ufficio: [
    "Scrivania",
    "Sedia ergonomica",
    "Monitor/Schermo",
    "Tastiera",
    "Mouse",
    "Stampante",
    "Scaffalatura ufficio",
    "Climatizzatore",
  ],
  Magazzino: [
    "Scaffalatura industriale",
    "Transpallet manuale",
    "Transpallet elettrico",
    "Muletto/Carrello elevatore",
    "Scala portatile",
    "Nastro trasportatore",
  ],
  Produzione: [
    "Tornio",
    "Fresa",
    "Pressa",
    "Saldatrice",
    "Compressore",
    "Trapano a colonna",
    "Nastro trasportatore",
    "Carroponte",
  ],
  Officina: [
    "Tornio",
    "Fresa",
    "Trapano a colonna",
    "Mola da banco",
    "Sega a nastro",
    "Saldatrice",
    "Compressore",
    "Pressa idraulica",
    "Carrello elevatore",
    "Transpallet",
    "Ponte sollevatore",
    "Nastro trasportatore",
    "Carroponte",
    "Banco da lavoro",
    "Aspiratore/Estrattore fumi",
  ],
  Cucina: [
    "Forno industriale",
    "Piano cottura",
    "Frigorifero industriale",
    "Abbattitore",
    "Affettatrice",
    "Lavastoviglie industriale",
    "Cappa aspirante",
  ],
  Laboratorio: [
    "Cappa chimica",
    "Centrifuga",
    "Microscopio",
    "Autoclave",
    "Bilancia di precisione",
    "Agitatore magnetico",
  ],
  Esterno: [
    "Escavatore",
    "Gru",
    "Betoniera",
    "Ponteggio",
    "Trabattello",
    "Martello demolitore",
  ],
  Negozio: [
    "Registratore di cassa",
    "Scaffalatura espositiva",
    "Scala portatile",
    "Frigorifero espositore",
  ],
};

function createEmptyAttrezzatura(
  aziendaId: string,
  ambienteId: string,
): Attrezzatura {
  return {
    id: crypto.randomUUID(),
    azienda_id: aziendaId,
    ambiente_id: ambienteId,
    descrizione: "",
    marcatura_ce: false,
    verifiche_periodiche: false,
  };
}

interface AISuggestion {
  descrizione: string;
  motivazione: string;
}

export function StepAttrezzature({
  aziendaId,
  ambienti,
  attrezzature,
  onChange,
}: StepAttrezzatureProps) {
  const { apiFetch } = useApi();
  const [selectedAmbienteIndex, setSelectedAmbienteIndex] = useState(0);

  const selectedAmbiente = ambienti[selectedAmbienteIndex];

  const basePath = `/api/v1/aziende/${aziendaId}/attrezzature`;

  // Phase 5.3 — AI-suggested equipment per ambiente. Cleared when the
  // operator switches ambiente so suggestions for "Cucina" don't leak into
  // "Ufficio". Loading flag is per-ambiente too — clicking generate twice
  // before the first response lands is a no-op.
  const [aiSuggestionsByAmbiente, setAiSuggestionsByAmbiente] = useState<
    Record<string, AISuggestion[]>
  >({});
  const [aiLoadingByAmbiente, setAiLoadingByAmbiente] = useState<
    Record<string, boolean>
  >({});
  // Photo-vision extraction has its own loading flag so the user can see
  // which AI source is running. Counts are lazy-fetched on ambiente focus
  // so we know when to disable the "Estrai dalle foto" button.
  const [photoExtractLoadingByAmbiente, setPhotoExtractLoadingByAmbiente] =
    useState<Record<string, boolean>>({});
  const [fotoCountByAmbiente, setFotoCountByAmbiente] = useState<
    Record<string, number>
  >({});

  // H5 fix: persist attrezzature to the backend so the DVR generator sees them.
  // Local state (onChange) is still updated optimistically; on failure we roll
  // back and surface the error.
  const persistCreate = useCallback(
    async (payload: {
      ambiente_id: string;
      descrizione: string;
      marcatura_ce: boolean;
      verifiche_periodiche: boolean;
    }) => {
      return await apiFetch<Attrezzatura>(basePath, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    [apiFetch, basePath]
  );

  const persistUpdate = useCallback(
    async (id: string, fields: Partial<Attrezzatura>) => {
      return await apiFetch<Attrezzatura>(`${basePath}/${id}`, {
        method: "PUT",
        body: JSON.stringify(fields),
      });
    },
    [apiFetch, basePath]
  );

  const persistDelete = useCallback(
    async (id: string) => {
      await apiFetch<void>(`${basePath}/${id}`, { method: "DELETE" });
    },
    [apiFetch, basePath]
  );

  // Custom rows need lazy persistence: create on first save when descrizione
  // becomes non-empty; afterwards switch to PUT. persistedIds is the set of
  // ids that exist server-side (i.e. have been POSTed at least once).
  const [persistedIds, setPersistedIds] = useState<Set<string>>(() => {
    // Initial server-loaded rows are persisted. Locally-minted rows from
    // toggleSuggested / addCustomAttrezzatura are added below on POST success.
    return new Set(attrezzature.map((a) => a.id));
  });

  // Serialize concurrent saves per row id. Without this, fast keystrokes can
  // fire two POSTs before the first one resolves and updates persistedIds —
  // creating duplicate rows on the server. One promise chain per id.
  const inFlightRef = useRef<Map<string, Promise<unknown>>>(new Map());

  // Feedback #76 ("mi duplica i nomi delle attrezzature nel riepilogo"):
  // double-clicking a suggested / AI chip fired two POSTs. The add guards
  // below read `selectedDescriptions` (memoized derived state) which only
  // refreshes on the *next* render, so both click events passed the stale
  // "already selected?" check and each created a server row. This is a
  // synchronous in-flight set keyed by `${ambienteId}::${descrizione}` — a
  // second add for the same item is a no-op while the first create is still
  // pending, regardless of React's render timing.
  const addingKeysRef = useRef<Set<string>>(new Set());

  // Mirror current attrezzature in a ref so commit reads always see the latest
  // state. Fixes the "marcatura CE flag scompare" bug (feedback 2026-04-28 #6):
  // event handlers called updateLocal then commitAttrezzatura on the same tick,
  // and the captured `attrezzature` prop was the pre-update array — the commit
  // PUT'd the old value back, server echoed it, and the optimistic toggle
  // visually reverted.
  const attrezzatureRef = useRef(attrezzature);
  useEffect(() => {
    attrezzatureRef.current = attrezzature;
  }, [attrezzature]);

  // Get suggested equipment list for the currently selected environment type
  const suggestedEquipment = useMemo(() => {
    if (!selectedAmbiente) return [];
    return EQUIPMENT_BY_TYPE[selectedAmbiente.tipo] ?? [];
  }, [selectedAmbiente]);

  // Phase 2.3 — equipment is now per-ambiente, so all "selected" lookups
  // must scope to the currently visible ambiente. Switching ambienti hides
  // the previous ambiente's selections instead of folding them together.
  const ambienteAttrezzature = useMemo(
    () =>
      selectedAmbiente
        ? attrezzature.filter((a) => a.ambiente_id === selectedAmbiente.id)
        : [],
    [attrezzature, selectedAmbiente]
  );

  const selectedDescriptions = useMemo(
    () => new Set(ambienteAttrezzature.map((a) => a.descrizione)),
    [ambienteAttrezzature]
  );

  // Toggle a suggested equipment item on/off (within the current ambiente)
  const toggleSuggested = useCallback(
    async (descrizione: string) => {
      if (!selectedAmbiente) return;
      const ambienteId = selectedAmbiente.id;
      if (selectedDescriptions.has(descrizione)) {
        const target = attrezzature.find(
          (a) => a.ambiente_id === ambienteId && a.descrizione === descrizione,
        );
        if (!target) return;
        const next = attrezzature.filter((a) => a.id !== target.id);
        onChange(next);
        try {
          await persistDelete(target.id);
        } catch (e) {
          toast.error(
            e instanceof Error ? e.message : "Errore nella rimozione"
          );
          onChange(attrezzature);
        }
      } else {
        // #76: collapse a double-click into a single create. The key is
        // added synchronously so a same-tick second click bails here.
        const addKey = `${ambienteId}::${descrizione}`;
        if (addingKeysRef.current.has(addKey)) return;
        addingKeysRef.current.add(addKey);
        const optimistic: Attrezzatura = {
          id: crypto.randomUUID(),
          azienda_id: aziendaId,
          ambiente_id: ambienteId,
          descrizione,
          marcatura_ce: false,
          verifiche_periodiche: false,
        };
        onChange([...attrezzature, optimistic]);
        try {
          const created = await persistCreate({
            ambiente_id: ambienteId,
            descrizione,
            marcatura_ce: false,
            verifiche_periodiche: false,
          });
          // Swap the optimistic row for the server row in the *latest*
          // array (attrezzatureRef), not the captured closure — otherwise a
          // concurrent add gets clobbered and its temp row is left orphaned,
          // which a later edit re-POSTs as a duplicate.
          onChange(
            attrezzatureRef.current.map((a) =>
              a.id === optimistic.id ? created : a,
            ),
          );
          setPersistedIds((prev) => {
            const next = new Set(prev);
            next.add(created.id);
            return next;
          });
        } catch (e) {
          toast.error(
            e instanceof Error ? e.message : "Errore nel salvataggio"
          );
          onChange(
            attrezzatureRef.current.filter((a) => a.id !== optimistic.id),
          );
        } finally {
          addingKeysRef.current.delete(addKey);
        }
      }
    },
    [
      attrezzature,
      onChange,
      aziendaId,
      selectedAmbiente,
      selectedDescriptions,
      persistCreate,
      persistDelete,
    ]
  );

  // Bulk select/deselect all suggested items for the current ambiente.
  // Feedback 2026-05-08 (#ac32b03f) and 2026-05-12 (#3bfc481c): the previous
  // implementation called toggleSuggested in a loop, but each iteration
  // captured a stale `attrezzature` via toggleSuggested's useCallback closure
  // (React doesn't re-render between awaits inside one event handler), so
  // every onChange overwrote the previous one and only the last item stuck.
  // Maintain a running list seeded from attrezzatureRef and emit onChange
  // after each item so the UI stays responsive.
  const [bulkBusy, setBulkBusy] = useState(false);
  const toggleAllSuggested = useCallback(async () => {
    if (!selectedAmbiente || suggestedEquipment.length === 0) return;
    const ambienteId = selectedAmbiente.id;
    const allSelected = suggestedEquipment.every((item) =>
      selectedDescriptions.has(item),
    );

    setBulkBusy(true);
    try {
      if (allSelected) {
        // Deselect all suggested for this ambiente.
        const toDelete = attrezzatureRef.current.filter(
          (a) =>
            a.ambiente_id === ambienteId &&
            suggestedEquipment.includes(a.descrizione),
        );
        for (const target of toDelete) {
          const running = attrezzatureRef.current.filter(
            (a) => a.id !== target.id,
          );
          onChange(running);
          try {
            await persistDelete(target.id);
          } catch (e) {
            toast.error(
              e instanceof Error ? e.message : "Errore nella rimozione",
            );
            // Re-insert the row so local state matches server.
            onChange(attrezzatureRef.current.concat(target));
          }
        }
      } else {
        // Select all not-yet-selected suggested items.
        const existingDescriptions = new Set(
          attrezzatureRef.current
            .filter((a) => a.ambiente_id === ambienteId)
            .map((a) => a.descrizione),
        );
        const toAdd = suggestedEquipment.filter(
          (item) => !existingDescriptions.has(item),
        );
        for (const descrizione of toAdd) {
          try {
            const created = await persistCreate({
              ambiente_id: ambienteId,
              descrizione,
              marcatura_ce: false,
              verifiche_periodiche: false,
            });
            onChange([...attrezzatureRef.current, created]);
            setPersistedIds((prev) => {
              const next = new Set(prev);
              next.add(created.id);
              return next;
            });
          } catch (e) {
            toast.error(
              e instanceof Error ? e.message : "Errore nel salvataggio",
            );
          }
        }
      }
    } finally {
      setBulkBusy(false);
    }
  }, [
    selectedAmbiente,
    suggestedEquipment,
    selectedDescriptions,
    onChange,
    persistCreate,
    persistDelete,
  ]);

  // Feedback issue #8 (2026-05-14): bulk-toggle marcatura CE across every
  // named attrezzatura in the current ambiente. Mirrors toggleAllSuggested
  // — single optimistic onChange hop followed by per-row PUT. Skips rows
  // that aren't persisted yet (no descrizione → not on the server).
  const toggleAllMarcaturaCe = useCallback(async () => {
    if (!selectedAmbiente) return;
    const ambienteId = selectedAmbiente.id;
    const rows = attrezzatureRef.current.filter(
      (a) =>
        a.ambiente_id === ambienteId &&
        (a.descrizione?.trim() ?? "").length > 0,
    );
    if (rows.length === 0) return;
    const allOn = rows.every((a) => a.marcatura_ce);
    const targetCe = !allOn;
    const targetIds = new Set(rows.map((r) => r.id));

    setBulkBusy(true);
    try {
      onChange(
        attrezzatureRef.current.map((a) =>
          targetIds.has(a.id) && a.marcatura_ce !== targetCe
            ? { ...a, marcatura_ce: targetCe }
            : a,
        ),
      );
      for (const r of rows) {
        if (r.marcatura_ce === targetCe) continue;
        if (!persistedIds.has(r.id)) continue;
        try {
          await persistUpdate(r.id, { marcatura_ce: targetCe });
        } catch (e) {
          toast.error(
            e instanceof Error ? e.message : "Errore nel salvataggio",
          );
        }
      }
    } finally {
      setBulkBusy(false);
    }
  }, [selectedAmbiente, onChange, persistUpdate, persistedIds]);

  // Feedback #34 (2026-05-18): bulk-toggle "verifiche periodiche" with the
  // same pattern as toggleAllMarcaturaCe. The field exists on the model but
  // the UI was previously removed.
  const toggleAllVerifichePeriodiche = useCallback(async () => {
    if (!selectedAmbiente) return;
    const ambienteId = selectedAmbiente.id;
    const rows = attrezzatureRef.current.filter(
      (a) =>
        a.ambiente_id === ambienteId &&
        (a.descrizione?.trim() ?? "").length > 0,
    );
    if (rows.length === 0) return;
    const allOn = rows.every((a) => a.verifiche_periodiche);
    const target = !allOn;
    const targetIds = new Set(rows.map((r) => r.id));

    setBulkBusy(true);
    try {
      onChange(
        attrezzatureRef.current.map((a) =>
          targetIds.has(a.id) && a.verifiche_periodiche !== target
            ? { ...a, verifiche_periodiche: target }
            : a,
        ),
      );
      for (const r of rows) {
        if (r.verifiche_periodiche === target) continue;
        if (!persistedIds.has(r.id)) continue;
        try {
          await persistUpdate(r.id, { verifiche_periodiche: target });
        } catch (e) {
          toast.error(
            e instanceof Error ? e.message : "Errore nel salvataggio",
          );
        }
      }
    } finally {
      setBulkBusy(false);
    }
  }, [selectedAmbiente, onChange, persistUpdate, persistedIds]);

  // Custom equipment = items whose descrizione is NOT in ANY suggested list
  const allSuggestedNames = useMemo(() => {
    const names = new Set<string>();
    for (const items of Object.values(EQUIPMENT_BY_TYPE)) {
      for (const item of items) {
        names.add(item);
      }
    }
    return names;
  }, []);

  // Custom rows scoped to the current ambiente.
  const customAttrezzature = useMemo(
    () =>
      ambienteAttrezzature.filter(
        (a) => !allSuggestedNames.has(a.descrizione)
      ),
    [ambienteAttrezzature, allSuggestedNames]
  );

  const addCustomAttrezzatura = useCallback(async () => {
    if (!selectedAmbiente) return;
    // Add optimistically; defer server create until the descrizione is
    // populated and the field blurs (commitAttrezzatura handles that).
    const newRow = createEmptyAttrezzatura(aziendaId, selectedAmbiente.id);
    onChange([...attrezzature, newRow]);
    // Autofocus the new descrizione input once React has rendered it.
    // Without this, the empty row also briefly surfaces in "Attrezzature
    // selezionate" as "Senza nome" and operators don't realize the editable
    // input is in the section below.
    requestAnimationFrame(() => {
      const el = document.getElementById(
        `att-desc-${newRow.id}`,
      ) as HTMLInputElement | null;
      el?.focus();
    });
  }, [attrezzature, onChange, aziendaId, selectedAmbiente]);

  // Phase 5.3 — fetch AI suggestions for the current ambiente.
  const fetchAISuggestions = useCallback(async () => {
    if (!selectedAmbiente) return;
    const ambienteId = selectedAmbiente.id;
    setAiLoadingByAmbiente((prev) => ({ ...prev, [ambienteId]: true }));
    try {
      const response = await apiFetch<{ items: AISuggestion[] }>(
        `${basePath}/suggerisci/${ambienteId}`,
        { method: "POST" },
      );
      const existing = new Set(
        attrezzature
          .filter((a) => a.ambiente_id === ambienteId)
          .map((a) => a.descrizione.toLowerCase().trim()),
      );
      const filtered = response.items.filter(
        (i) => !existing.has(i.descrizione.toLowerCase().trim()),
      );
      setAiSuggestionsByAmbiente((prev) => ({
        ...prev,
        [ambienteId]: filtered,
      }));
      if (filtered.length === 0) {
        toast.info(
          "L'AI non ha trovato attrezzature aggiuntive da suggerire.",
        );
      }
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : "Errore nella generazione AI",
      );
    } finally {
      setAiLoadingByAmbiente((prev) => ({ ...prev, [ambienteId]: false }));
    }
  }, [apiFetch, attrezzature, basePath, selectedAmbiente]);

  // Lazy-fetch the photo count for the visible ambiente so we can enable or
  // disable the "Estrai dalle foto" button. Only fetched once per ambiente
  // per page-life — re-uploads in step-ambienti during the same session are
  // rare and a stale 0 just means the button stays disabled until refresh.
  useEffect(() => {
    if (!selectedAmbiente) return;
    const ambienteId = selectedAmbiente.id;
    if (fotoCountByAmbiente[ambienteId] !== undefined) return;
    let cancelled = false;
    void (async () => {
      try {
        const photos = await apiFetch<AmbienteFoto[]>(
          `/api/v1/aziende/${aziendaId}/ambienti/${ambienteId}/foto`,
        );
        if (cancelled) return;
        setFotoCountByAmbiente((prev) => ({
          ...prev,
          [ambienteId]: photos.length,
        }));
      } catch {
        // Silent fail — button stays disabled, no toast spam on every step
        // switch. Operator can refresh if needed.
        if (!cancelled) {
          setFotoCountByAmbiente((prev) => ({ ...prev, [ambienteId]: 0 }));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedAmbiente, aziendaId, fotoCountByAmbiente, apiFetch]);

  // Vision extraction: send the ambiente's photos to the AI to identify
  // visible equipment. Replaces the existing AI suggestion chip list for
  // this ambiente — both buttons share the same UI so only one set of
  // chips is visible at a time.
  const extractFromPhotos = useCallback(async () => {
    if (!selectedAmbiente) return;
    const ambienteId = selectedAmbiente.id;
    setPhotoExtractLoadingByAmbiente((prev) => ({
      ...prev,
      [ambienteId]: true,
    }));
    try {
      const response = await apiFetch<{
        items: AISuggestion[];
        photos_used: number;
      }>(`${basePath}/estrai-foto/${ambienteId}`, { method: "POST" });
      const existing = new Set(
        attrezzature
          .filter((a) => a.ambiente_id === ambienteId)
          .map((a) => a.descrizione.toLowerCase().trim()),
      );
      const filtered = response.items.filter(
        (i) => !existing.has(i.descrizione.toLowerCase().trim()),
      );
      setAiSuggestionsByAmbiente((prev) => ({
        ...prev,
        [ambienteId]: filtered,
      }));
      if (filtered.length === 0) {
        toast.info(
          response.photos_used === 0
            ? "Nessuna foto utilizzabile per l'estrazione."
            : "L'AI non ha identificato attrezzature nelle foto.",
        );
      } else {
        toast.success(
          `Identificate ${filtered.length} attrezzature da ${response.photos_used} foto.`,
        );
      }
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : "Errore nell'estrazione dalle foto",
      );
    } finally {
      setPhotoExtractLoadingByAmbiente((prev) => ({
        ...prev,
        [ambienteId]: false,
      }));
    }
  }, [apiFetch, attrezzature, basePath, selectedAmbiente]);

  // Add a single AI suggestion as a real attrezzatura, then remove it from
  // the suggestion list so it doesn't appear twice.
  const acceptAISuggestion = useCallback(
    async (suggestion: AISuggestion) => {
      if (!selectedAmbiente) return;
      const ambienteId = selectedAmbiente.id;
      // #76: same double-click guard as toggleSuggested. AI/photo chips
      // produced the duplicates seen in production (uppercase names).
      const addKey = `${ambienteId}::${suggestion.descrizione}`;
      if (addingKeysRef.current.has(addKey)) return;
      addingKeysRef.current.add(addKey);
      const optimistic: Attrezzatura = {
        id: crypto.randomUUID(),
        azienda_id: aziendaId,
        ambiente_id: ambienteId,
        descrizione: suggestion.descrizione,
        marcatura_ce: false,
        verifiche_periodiche: false,
      };
      onChange([...attrezzature, optimistic]);
      // Drop from AI suggestions immediately so the chip disappears.
      setAiSuggestionsByAmbiente((prev) => {
        const next = { ...prev };
        next[ambienteId] = (next[ambienteId] ?? []).filter(
          (s) => s.descrizione !== suggestion.descrizione,
        );
        return next;
      });
      try {
        const created = await persistCreate({
          ambiente_id: ambienteId,
          descrizione: suggestion.descrizione,
          marcatura_ce: false,
          verifiche_periodiche: false,
        });
        // Replace the optimistic row in the latest array (see toggleSuggested).
        onChange(
          attrezzatureRef.current.map((a) =>
            a.id === optimistic.id ? created : a,
          ),
        );
        setPersistedIds((prev) => {
          const next = new Set(prev);
          next.add(created.id);
          return next;
        });
      } catch (e) {
        toast.error(
          e instanceof Error ? e.message : "Errore nel salvataggio",
        );
        onChange(
          attrezzatureRef.current.filter((a) => a.id !== optimistic.id),
        );
      } finally {
        addingKeysRef.current.delete(addKey);
      }
    },
    [
      attrezzature,
      onChange,
      aziendaId,
      selectedAmbiente,
      persistCreate,
    ],
  );

  const dismissAISuggestions = useCallback(() => {
    if (!selectedAmbiente) return;
    const ambienteId = selectedAmbiente.id;
    setAiSuggestionsByAmbiente((prev) => {
      const next = { ...prev };
      delete next[ambienteId];
      return next;
    });
  }, [selectedAmbiente]);

  const removeAttrezzatura = useCallback(
    async (id: string) => {
      const target = attrezzature.find((a) => a.id === id);
      const next = attrezzature.filter((a) => a.id !== id);
      onChange(next);
      if (!target) return;
      // With lazy persistence (commit-on-blur), a row may have a non-empty
      // descrizione locally but no server row yet. persistedIds is the
      // source of truth for "exists on server".
      if (!persistedIds.has(id)) return;
      try {
        await persistDelete(id);
      } catch (e) {
        toast.error(
          e instanceof Error ? e.message : "Errore nella rimozione"
        );
        onChange(attrezzature);
      }
    },
    [attrezzature, onChange, persistDelete, persistedIds]
  );

  // Local-only update — touches React state, no API call. Use for keystrokes.
  const updateLocal = useCallback(
    (id: string, fields: Partial<Attrezzatura>) => {
      onChange(
        attrezzature.map((a) => (a.id === id ? { ...a, ...fields } : a))
      );
    },
    [attrezzature, onChange]
  );

  // Persist current state of a row to the backend. POST on first commit
  // (lazy create), PUT thereafter. Serialised per row id so rapid commits
  // don't double-create.
  const commitAttrezzatura = useCallback(
    async (id: string) => {
      const row = attrezzatureRef.current.find((a) => a.id === id);
      if (!row || !row.descrizione?.trim()) {
        // Empty descrizione → nothing to persist (and never-persisted rows
        // stay client-only, ready to be removed cleanly).
        return;
      }

      const previous = inFlightRef.current.get(id) ?? Promise.resolve();
      const next = previous
        .catch(() => undefined)
        .then(async () => {
          // Re-read the row after awaiting — it may have changed.
          const fresh = attrezzatureRef.current.find((a) => a.id === id);
          if (!fresh || !fresh.descrizione?.trim()) return;
          try {
            if (persistedIds.has(id)) {
              const saved = await persistUpdate(id, {
                descrizione: fresh.descrizione,
                marcatura_ce: fresh.marcatura_ce,
                verifiche_periodiche: fresh.verifiche_periodiche,
              });
              onChange(
                attrezzatureRef.current.map((a) =>
                  a.id === id ? { ...a, ...saved } : a
                )
              );
            } else {
              const created = await persistCreate({
                ambiente_id: fresh.ambiente_id,
                descrizione: fresh.descrizione,
                marcatura_ce: fresh.marcatura_ce,
                verifiche_periodiche: fresh.verifiche_periodiche,
              });
              onChange(
                attrezzatureRef.current.map((a) =>
                  a.id === id ? { ...created } : a
                )
              );
              setPersistedIds((prev) => {
                const updated = new Set(prev);
                updated.delete(id);
                updated.add(created.id);
                return updated;
              });
            }
          } catch (e) {
            toast.error(
              e instanceof Error ? e.message : "Errore nel salvataggio"
            );
          }
        });

      inFlightRef.current.set(id, next);
      try {
        await next;
      } finally {
        if (inFlightRef.current.get(id) === next) {
          inFlightRef.current.delete(id);
        }
      }
    },
    [attrezzature, onChange, persistCreate, persistUpdate, persistedIds]
  );

  if (ambienti.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-on-surface-variant">
          Aggiungi almeno un ambiente di lavoro nel passo 3 prima di
          procedere con le attrezzature.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="mb-6">
          <h3 className="font-heading text-xl font-bold text-on-surface">
            Attrezzature
          </h3>
          <p className="mt-1 text-sm text-on-surface-variant">
            Seleziona un ambiente per visualizzare le attrezzature suggerite in
            base alla tipologia. Ogni attrezzatura appartiene a un solo
            ambiente: cambiando ambiente cambia l&apos;elenco visualizzato.
          </p>
        </div>
        <div>
          <div className="space-y-3">
            <Label>Seleziona Ambiente</Label>
            <div className="flex flex-wrap gap-2">
              {ambienti.map((amb, idx) => (
                <button
                  key={amb.id}
                  type="button"
                  onClick={() => setSelectedAmbienteIndex(idx)}
                  className={cn(
                    "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
                    idx === selectedAmbienteIndex
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-input bg-background text-foreground hover:bg-muted"
                  )}
                >
                  {amb.nome || `Ambiente ${idx + 1}`}
                  {amb.tipo ? ` (${amb.tipo})` : ""}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Suggested equipment */}
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <CardTitle className="text-base">
                Attrezzature suggerite
                {selectedAmbiente?.tipo
                  ? ` - ${selectedAmbiente.tipo}`
                  : ""}
              </CardTitle>
              <CardDescription>
                {suggestedEquipment.length > 0
                  ? "Clicca per aggiungere o rimuovere un'attrezzatura dall'elenco"
                  : "Nessun suggerimento disponibile per questo tipo di ambiente. Usa la sezione sottostante per aggiungere attrezzature manualmente."}
              </CardDescription>
            </div>
            {suggestedEquipment.length > 0 &&
              (() => {
                const allSelected = suggestedEquipment.every((item) =>
                  selectedDescriptions.has(item),
                );
                return (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={toggleAllSuggested}
                    disabled={bulkBusy}
                  >
                    {bulkBusy ? (
                      <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    ) : null}
                    {allSelected ? "Deseleziona tutto" : "Seleziona tutto"}
                  </Button>
                );
              })()}
          </div>
        </CardHeader>
        {suggestedEquipment.length > 0 && (
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {suggestedEquipment.map((item) => {
                const isSelected = selectedDescriptions.has(item);
                return (
                  <button
                    key={item}
                    type="button"
                    onClick={() => toggleSuggested(item)}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                      isSelected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input bg-background text-foreground hover:bg-muted"
                    )}
                  >
                    {isSelected && <Check className="h-3.5 w-3.5" />}
                    {item}
                  </button>
                );
              })}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Phase 5.3 — AI-generated equipment suggestions */}
      {selectedAmbiente && (() => {
        const ambienteId = selectedAmbiente.id;
        const aiLoading = aiLoadingByAmbiente[ambienteId] === true;
        const photoLoading =
          photoExtractLoadingByAmbiente[ambienteId] === true;
        const anyLoading = aiLoading || photoLoading;
        const aiSuggestions = aiSuggestionsByAmbiente[ambienteId] ?? [];
        const hasSuggestions = aiSuggestions.length > 0;
        const fotoCount = fotoCountByAmbiente[ambienteId];
        const fotoCountKnown = fotoCount !== undefined;
        const hasPhotos = (fotoCount ?? 0) > 0;
        const photoButtonTitle = !fotoCountKnown
          ? "Caricamento foto in corso..."
          : !hasPhotos
            ? "Carica almeno una foto nell'ambiente (passo 3) prima di estrarre con AI."
            : `Estrai attrezzature dalle ${fotoCount} foto caricate per questo ambiente.`;

        return (
          <Card className="border-violet-300 bg-violet-100">
            <CardHeader className="pb-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Sparkles className="h-4 w-4 text-violet-600" />
                    Suggerisci con AI
                  </CardTitle>
                  <CardDescription>
                    L&apos;AI propone attrezzature tipiche per {" "}
                    <span className="font-medium">
                      {selectedAmbiente.nome ||
                        `Ambiente ${selectedAmbienteIndex + 1}`}
                    </span>
                    . Clicca su una proposta per aggiungerla.
                  </CardDescription>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {hasSuggestions && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={dismissAISuggestions}
                    >
                      <X className="mr-1 h-3.5 w-3.5" />
                      Chiudi
                    </Button>
                  )}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={fetchAISuggestions}
                    disabled={anyLoading}
                    className="border-violet-300 text-violet-700 hover:bg-violet-100"
                  >
                    {aiLoading ? (
                      <>
                        <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                        Generazione...
                      </>
                    ) : (
                      <>
                        <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                        {hasSuggestions ? "Rigenera" : "Genera con AI"}
                      </>
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={extractFromPhotos}
                    disabled={anyLoading || !hasPhotos}
                    title={photoButtonTitle}
                    className="border-violet-300 text-violet-700 hover:bg-violet-100"
                  >
                    {photoLoading ? (
                      <>
                        <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                        Analisi foto...
                      </>
                    ) : (
                      <>
                        <Camera className="mr-1.5 h-3.5 w-3.5" />
                        Estrai dalle foto
                        {hasPhotos ? ` (${fotoCount})` : ""}
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardHeader>
            {hasSuggestions && (
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {aiSuggestions.map((s) => (
                    <button
                      key={s.descrizione}
                      type="button"
                      onClick={() => acceptAISuggestion(s)}
                      title={s.motivazione}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-violet-300 bg-white px-3 py-2 text-sm font-medium text-violet-800 transition-colors hover:bg-violet-50"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      {s.descrizione}
                    </button>
                  ))}
                </div>
              </CardContent>
            )}
          </Card>
        );
      })()}

      {/* Selected equipment details — scoped to current ambiente. Rows with
          an empty descrizione are still being edited in the "Attrezzature
          personalizzate" section below, so we hide them here to avoid the
          duplicate "Senza nome" placeholder that confused operators into
          thinking the name wasn't editable. */}
      {(() => {
        const namedAttrezzature = ambienteAttrezzature.filter((a) =>
          a.descrizione?.trim(),
        );
        if (namedAttrezzature.length === 0) return null;
        const allCeOn =
          namedAttrezzature.length > 0 &&
          namedAttrezzature.every((a) => a.marcatura_ce);
        const allVerOn =
          namedAttrezzature.length > 0 &&
          namedAttrezzature.every((a) => a.verifiche_periodiche);
        return (
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-base">
                  Attrezzature selezionate ({namedAttrezzature.length})
                </CardTitle>
                <CardDescription>
                  Imposta marcatura CE e verifiche periodiche per ogni
                  attrezzatura
                </CardDescription>
              </div>
              {namedAttrezzature.length > 1 && (
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={toggleAllMarcaturaCe}
                    disabled={bulkBusy}
                  >
                    {bulkBusy ? (
                      <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    ) : null}
                    {allCeOn
                      ? "Deseleziona tutte CE"
                      : "Seleziona tutte CE"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={toggleAllVerifichePeriodiche}
                    disabled={bulkBusy}
                  >
                    {bulkBusy ? (
                      <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    ) : null}
                    {allVerOn
                      ? "Deseleziona tutte verifiche"
                      : "Seleziona tutte verifiche"}
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {namedAttrezzature.map((att) => (
              <div
                key={att.id}
                className="flex flex-wrap items-center gap-3 rounded-lg border border-input p-3"
              >
                <span className="min-w-[160px] flex-1 text-sm font-medium">
                  {att.descrizione}
                </span>

                <label className="flex items-center gap-2 rounded-lg border border-input px-3 py-1.5 text-sm transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                  <input
                    type="checkbox"
                    checked={att.marcatura_ce}
                    onChange={(e) => {
                      updateLocal(att.id, { marcatura_ce: e.target.checked });
                      void commitAttrezzatura(att.id);
                    }}
                    className="accent-primary"
                  />
                  Marcatura CE
                </label>

                <label className="flex items-center gap-2 rounded-lg border border-input px-3 py-1.5 text-sm transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                  <input
                    type="checkbox"
                    checked={att.verifiche_periodiche}
                    onChange={(e) => {
                      updateLocal(att.id, {
                        verifiche_periodiche: e.target.checked,
                      });
                      void commitAttrezzatura(att.id);
                    }}
                    className="accent-primary"
                  />
                  Verifiche periodiche
                </label>

                <Button
                  variant="destructive"
                  size="icon-sm"
                  onClick={() => removeAttrezzatura(att.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
        );
      })()}

      {/* Custom equipment */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Attrezzature personalizzate
          </CardTitle>
          <CardDescription>
            Aggiungi attrezzature non presenti nei suggerimenti
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {customAttrezzature.length > 0 && (
            <>
              {customAttrezzature.map((att, index) => (
                <div key={att.id}>
                  {index > 0 && <Separator className="mb-4" />}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium">
                        Personalizzata
                        {att.descrizione ? ` - ${att.descrizione}` : ""}
                      </h3>
                      <Button
                        variant="destructive"
                        size="icon-sm"
                        onClick={() => removeAttrezzatura(att.id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor={`att-desc-${att.id}`}>
                        Descrizione *
                      </Label>
                      <Input
                        id={`att-desc-${att.id}`}
                        value={att.descrizione}
                        onChange={(e) =>
                          updateLocal(att.id, {
                            descrizione: e.target.value,
                          })
                        }
                        onBlur={() => void commitAttrezzatura(att.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            (e.target as HTMLInputElement).blur();
                          }
                        }}
                        placeholder="Es. Carrello elevatore, Trapano a colonna"
                      />
                    </div>

                    <div className="flex flex-wrap gap-4">
                      <label className="flex items-center gap-2 rounded-lg border border-input px-4 py-2 text-sm transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                        <input
                          type="checkbox"
                          checked={att.marcatura_ce}
                          onChange={(e) => {
                            updateLocal(att.id, {
                              marcatura_ce: e.target.checked,
                            });
                            void commitAttrezzatura(att.id);
                          }}
                          className="accent-primary"
                        />
                        Marcatura CE
                      </label>
                      <label className="flex items-center gap-2 rounded-lg border border-input px-4 py-2 text-sm transition-colors hover:bg-muted has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                        <input
                          type="checkbox"
                          checked={att.verifiche_periodiche}
                          onChange={(e) => {
                            updateLocal(att.id, {
                              verifiche_periodiche: e.target.checked,
                            });
                            void commitAttrezzatura(att.id);
                          }}
                          className="accent-primary"
                        />
                        Verifiche periodiche
                      </label>
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}

          <Button
            variant="outline"
            onClick={addCustomAttrezzatura}
            className="w-full"
          >
            <Plus className="mr-2 h-4 w-4" />
            Aggiungi Attrezzatura
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
