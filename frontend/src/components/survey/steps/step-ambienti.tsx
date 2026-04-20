"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ImagePlus, Loader2, Plus, Trash2, X } from "lucide-react";
import { useApi } from "@/hooks/use-api";
import type { Ambiente } from "@/types";

// Server-side photo record attached to an ambiente.
// The orchestrator will move this to types/index.ts later.
interface AmbienteFoto {
  id: string;
  ambiente_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

interface StepAmbientiProps {
  aziendaId: string;
  ambienti: Ambiente[];
  onChange: (ambienti: Ambiente[]) => void;
}

const TIPI_AMBIENTE = [
  "Ufficio",
  "Magazzino",
  "Cucina",
  "Laboratorio",
  "Officina",
  "Sala Corsi",
  "Esterno",
  "Bagno/Spogliatoio",
];

const MAX_FOTO = 10;
const MAX_FOTO_SIZE_BYTES = 10 * 1024 * 1024;
const ALLOWED_FOTO_TYPES = ["image/jpeg", "image/png", "image/heic"];
const ALLOWED_FOTO_EXTENSIONS = [".jpg", ".jpeg", ".png", ".heic"];
const INVALID_FOTO_MESSAGE =
  "Formato non supportato o file troppo grande (max 10 MB)";

function createEmptyAmbiente(aziendaId: string): Ambiente {
  return {
    id: crypto.randomUUID(),
    azienda_id: aziendaId,
    nome: "",
    tipo: "",
    superficie_mq: null,
    preposto_id: null,
    descrizione_attivita: null,
  };
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

type FileRejectReason = "format" | "empty" | "oversize";

function validateFotoFile(file: File): FileRejectReason | null {
  const nameLower = file.name.toLowerCase();
  const extOk = ALLOWED_FOTO_EXTENSIONS.some((ext) => nameLower.endsWith(ext));
  const typeOk = ALLOWED_FOTO_TYPES.includes(file.type);
  if (!typeOk && !extOk) return "format";
  if (file.size === 0) return "empty";
  if (file.size > MAX_FOTO_SIZE_BYTES) return "oversize";
  return null;
}

// ---------------------------------------------------------------------------
// <AmbienteFotoGrid> — isolated per-ambiente so each grid owns its own queue,
// loading indicator, and retry-on-reconnect wiring without re-rendering its
// siblings whenever a single upload completes.
// ---------------------------------------------------------------------------

interface AmbienteFotoGridProps {
  aziendaId: string;
  ambienteId: string;
}

function AmbienteFotoGrid({ aziendaId, ambienteId }: AmbienteFotoGridProps) {
  const { apiFetch, isAuthenticated } = useApi();
  const [foto, setFoto] = useState<AmbienteFoto[]>([]);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [uploading, setUploading] = useState(false);
  // Files that failed to upload due to a network error and should be retried
  // when `online` fires. One retry attempt is acceptable for US-1.3.
  const pendingRetryRef = useRef<File[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const basePath = `/api/v1/aziende/${aziendaId}/ambienti/${ambienteId}/foto`;

  // Load existing photos on mount. A 404 here means the ambiente is still
  // client-only (unsaved) — we surface the helper text instead of the grid.
  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const items = await apiFetch<AmbienteFoto[]>(basePath);
        if (!cancelled) {
          setFoto(items);
          setAvailable(true);
        }
      } catch (err) {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : "";
          if (msg.toLowerCase().includes("not found") || msg.includes("404")) {
            setAvailable(false);
          } else {
            // Network error or other failure — keep the grid visible so the
            // user can still try to attach photos; on network errors the
            // online listener will retry.
            setAvailable(true);
          }
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiFetch, isAuthenticated, basePath]);

  const uploadOne = useCallback(
    async (file: File): Promise<AmbienteFoto | null> => {
      const fd = new FormData();
      fd.append("file", file);
      try {
        const created = await apiFetch<AmbienteFoto>(basePath, {
          method: "POST",
          body: fd,
          headers: {},
        });
        return created;
      } catch (err) {
        // Heuristic: if the browser is offline OR fetch threw a bare network
        // error, queue this file for retry when connectivity is restored.
        const offline =
          typeof navigator !== "undefined" && navigator.onLine === false;
        const msg = err instanceof Error ? err.message : "";
        const looksLikeNetwork =
          msg.toLowerCase().includes("failed to fetch") ||
          msg.toLowerCase().includes("networkerror") ||
          msg.toLowerCase().includes("load failed");
        if (offline || looksLikeNetwork) {
          pendingRetryRef.current.push(file);
          return null;
        }
        // Server-side rejection (validation/limit) — surface to the user.
        toast.error(msg || "Errore durante l'upload della foto");
        return null;
      }
    },
    [apiFetch, basePath]
  );

  const uploadMany = useCallback(
    async (files: File[]) => {
      if (files.length === 0) return;
      setUploading(true);
      const results: AmbienteFoto[] = [];
      for (const f of files) {
        // Re-check 10-photo ceiling as we go (server also enforces)
        if (foto.length + results.length >= MAX_FOTO) {
          toast.error("Massimo 10 foto per ambiente");
          break;
        }
        const created = await uploadOne(f);
        if (created) results.push(created);
      }
      if (results.length > 0) {
        setFoto((prev) => [...results, ...prev]);
      }
      setUploading(false);
    },
    [foto.length, uploadOne]
  );

  // Retry any queued files once connectivity returns.
  useEffect(() => {
    function retry() {
      const queued = pendingRetryRef.current;
      if (queued.length === 0) return;
      pendingRetryRef.current = [];
      void uploadMany(queued);
    }
    window.addEventListener("online", retry);
    return () => window.removeEventListener("online", retry);
  }, [uploadMany]);

  const handlePick = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? []);
      e.target.value = "";
      if (files.length === 0) return;

      const accepted: File[] = [];
      for (const f of files) {
        // H-03 (US-1.3): surface a distinct toast per failure mode so the
        // oversize branch no longer "silently rejects" 11 MB+ JPGs. The
        // original unified path relied on `fileIsValid` being false-y, but
        // the failure message didn't encode *why* — here we map every
        // reject reason to an operator-facing Italian string.
        const reason = validateFotoFile(f);
        if (reason === "oversize") {
          toast.error(
            `"${f.name}" è troppo grande (${formatBytes(f.size)}). Max ${MAX_FOTO_SIZE_BYTES / (1024 * 1024)} MB.`,
          );
          continue;
        }
        if (reason === "empty") {
          toast.error(`"${f.name}" è vuoto e non può essere caricato.`);
          continue;
        }
        if (reason === "format") {
          toast.error(INVALID_FOTO_MESSAGE);
          continue;
        }
        accepted.push(f);
      }
      // Client-side 10-photo ceiling (server also enforces)
      const capacity = Math.max(0, MAX_FOTO - foto.length);
      if (accepted.length > capacity) {
        toast.error("Massimo 10 foto per ambiente");
      }
      void uploadMany(accepted.slice(0, capacity));
    },
    [foto.length, uploadMany]
  );

  const handleDelete = useCallback(
    async (fotoId: string) => {
      try {
        await apiFetch(`${basePath}/${fotoId}`, { method: "DELETE" });
        setFoto((prev) => prev.filter((f) => f.id !== fotoId));
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : "Errore durante l'eliminazione"
        );
      }
    },
    [apiFetch, basePath]
  );

  if (available === false) {
    return (
      <div className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">
        Salva l&apos;ambiente prima di caricare foto.
      </div>
    );
  }

  const full = foto.length >= MAX_FOTO;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">Foto</Label>
        <span className="text-xs text-muted-foreground">
          {foto.length} / {MAX_FOTO}
        </span>
      </div>

      {uploading && (
        <div className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Caricamento in corso
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/heic"
        multiple
        capture="environment"
        onChange={handlePick}
        className="hidden"
      />

      {foto.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {foto.map((f) => (
            <div
              key={f.id}
              className="group relative w-[110px] rounded-md border bg-muted/20 p-1.5"
            >
              <div className="relative flex h-[80px] w-full items-center justify-center overflow-hidden rounded bg-muted">
                <ImagePlus className="h-6 w-6 text-muted-foreground/50" />
                <button
                  type="button"
                  onClick={() => handleDelete(f.id)}
                  aria-label="Elimina foto"
                  className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-background/90 text-destructive shadow-sm transition hover:bg-destructive hover:text-destructive-foreground"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
              <p
                className="mt-1 truncate text-[10px] font-medium"
                title={f.filename}
              >
                {f.filename}
              </p>
              <p className="text-[10px] text-muted-foreground">
                {formatBytes(f.size_bytes)}
              </p>
            </div>
          ))}
        </div>
      )}

      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={full}
        onClick={() => inputRef.current?.click()}
      >
        <ImagePlus className="mr-2 h-4 w-4" />
        {full ? "Massimo 10 foto raggiunto" : "Aggiungi foto"}
      </Button>
    </div>
  );
}

export function StepAmbienti({
  aziendaId,
  ambienti,
  onChange,
}: StepAmbientiProps) {
  const { apiFetch } = useApi();
  const basePath = `/api/v1/aziende/${aziendaId}/ambienti`;

  // Track which rows have been POSTed to the server. Rows loaded from the
  // survey endpoint are all persisted; locally-added rows start unpersisted
  // and flip to persisted after the first successful create. We use a ref
  // (not state) so that updates inside async callbacks don't trigger renders,
  // and because we never read the value during render.
  const persistedIdsRef = useRef<Set<string>>(
    new Set(ambienti.map((a) => a.id))
  );

  const addAmbiente = useCallback(() => {
    onChange([...ambienti, createEmptyAmbiente(aziendaId)]);
  }, [ambienti, onChange, aziendaId]);

  const removeAmbiente = useCallback(
    async (index: number) => {
      const target = ambienti[index];
      const next = ambienti.filter((_, i) => i !== index);
      onChange(next);
      if (!target) return;
      if (persistedIdsRef.current.has(target.id)) {
        try {
          await apiFetch(`${basePath}/${target.id}`, { method: "DELETE" });
          persistedIdsRef.current.delete(target.id);
        } catch (err) {
          toast.error(
            err instanceof Error ? err.message : "Errore nella rimozione"
          );
          onChange(ambienti);
        }
      }
    },
    [ambienti, onChange, apiFetch, basePath]
  );

  const updateAmbiente = useCallback(
    async (index: number, fields: Partial<Ambiente>) => {
      const updated = ambienti.map((a, i) =>
        i === index ? { ...a, ...fields } : a
      );
      onChange(updated);

      const row = updated[index];
      if (!row || !row.nome?.trim()) {
        // Not ready to persist — server requires a non-empty nome.
        return;
      }
      try {
        const payload = {
          nome: row.nome,
          tipo: row.tipo,
          superficie_mq: row.superficie_mq,
          descrizione_attivita: row.descrizione_attivita,
        };
        if (persistedIdsRef.current.has(row.id)) {
          const saved = await apiFetch<Ambiente>(`${basePath}/${row.id}`, {
            method: "PUT",
            body: JSON.stringify(payload),
          });
          onChange(
            updated.map((a, i) => (i === index ? { ...a, ...saved } : a))
          );
        } else {
          const created = await apiFetch<Ambiente>(basePath, {
            method: "POST",
            body: JSON.stringify(payload),
          });
          onChange(updated.map((a, i) => (i === index ? created : a)));
          persistedIdsRef.current.delete(row.id);
          persistedIdsRef.current.add(created.id);
        }
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : "Errore nel salvataggio"
        );
      }
    },
    [ambienti, onChange, apiFetch, basePath]
  );

  return (
    <div className="space-y-6">
      <div>
        <div className="mb-6">
          <h3 className="font-heading text-xl font-bold text-on-surface">
            Ambienti di Lavoro
          </h3>
          <p className="mt-1 text-sm text-on-surface-variant">
            Definisci gli ambienti di lavoro dell&apos;azienda
          </p>
        </div>
        <div className="space-y-6">
          {ambienti.length === 0 && (
            <p className="py-8 text-center text-muted-foreground">
              Nessun ambiente aggiunto. Clicca &quot;Aggiungi Ambiente&quot; per
              iniziare.
            </p>
          )}

          {ambienti.map((ambiente, index) => (
            <div key={ambiente.id}>
              {index > 0 && <Separator className="mb-6" />}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium">
                    Ambiente {index + 1}
                    {ambiente.nome ? ` - ${ambiente.nome}` : ""}
                  </h3>
                  <Button
                    variant="destructive"
                    size="icon-sm"
                    onClick={() => removeAmbiente(index)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  {/* Nome */}
                  <div className="space-y-2">
                    <Label htmlFor={`amb-nome-${index}`}>
                      Nome Ambiente *
                    </Label>
                    <Input
                      id={`amb-nome-${index}`}
                      value={ambiente.nome}
                      onChange={(e) =>
                        updateAmbiente(index, {
                          nome: e.target.value,
                        })
                      }
                      placeholder="Es. Ufficio Piano Terra"
                    />
                  </div>

                  {/* Tipo */}
                  <div className="space-y-2">
                    <Label htmlFor={`amb-tipo-${index}`}>
                      Tipo
                    </Label>
                    <select
                      id={`amb-tipo-${index}`}
                      value={ambiente.tipo}
                      onChange={(e) =>
                        updateAmbiente(index, {
                          tipo: e.target.value,
                        })
                      }
                      className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                    >
                      <option value="">Seleziona tipo</option>
                      {TIPI_AMBIENTE.map((tipo) => (
                        <option key={tipo} value={tipo}>
                          {tipo}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Superficie */}
                  <div className="space-y-2">
                    <Label htmlFor={`amb-superficie-${index}`}>
                      Superficie (mq)
                    </Label>
                    <Input
                      id={`amb-superficie-${index}`}
                      type="number"
                      value={ambiente.superficie_mq ?? ""}
                      onChange={(e) =>
                        updateAmbiente(index, {
                          superficie_mq: e.target.value
                            ? Number(e.target.value)
                            : null,
                        })
                      }
                      placeholder="Es. 50"
                    />
                  </div>
                </div>

                {/* Descrizione Attivita */}
                <div className="space-y-2">
                  <Label htmlFor={`amb-desc-${index}`}>
                    Descrizione Attivita
                  </Label>
                  <textarea
                    id={`amb-desc-${index}`}
                    value={ambiente.descrizione_attivita ?? ""}
                    onChange={(e) =>
                      updateAmbiente(index, {
                        descrizione_attivita:
                          e.target.value || null,
                      })
                    }
                    rows={2}
                    placeholder="Descrivi le attivita svolte in questo ambiente..."
                    className="w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  />
                </div>

                {/* Foto uploads (US-1.3) */}
                <AmbienteFotoGrid
                  aziendaId={aziendaId}
                  ambienteId={ambiente.id}
                />
              </div>
            </div>
          ))}

          <Button
            variant="outline"
            onClick={addAmbiente}
            className="w-full"
          >
            <Plus className="mr-2 h-4 w-4" />
            Aggiungi Ambiente
          </Button>
        </div>
      </div>
    </div>
  );
}
