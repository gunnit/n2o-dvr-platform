"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  ArrowDown,
  ArrowUp,
  ImagePlus,
  Loader2,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { useApi } from "@/hooks/use-api";
import type { Ambiente } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

// Suggested ambiente types — used as datalist hints. The input accepts any
// free-text value, so this list just speeds up the common cases. Ordered
// roughly by frequency in Italian workplace surveys.
const TIPI_AMBIENTE = [
  "Ufficio",
  "Ufficio direzionale",
  "Open space",
  "Sala riunioni",
  "Sala corsi / Aula formazione",
  "Reception / Accoglienza",
  "Sala d'attesa",
  "Magazzino",
  "Deposito",
  "Archivio",
  "Area carico/scarico",
  "Cucina",
  "Cucina industriale",
  "Sala mensa / Refettorio",
  "Bar / Caffetteria",
  "Laboratorio",
  "Laboratorio chimico",
  "Laboratorio analisi",
  "Officina",
  "Officina meccanica",
  "Officina elettrica",
  "Capannone produttivo",
  "Reparto produzione",
  "Linea di assemblaggio",
  "Showroom / Sala esposizione",
  "Negozio / Punto vendita",
  "Studio medico / Ambulatorio",
  "Aula scolastica",
  "Palestra",
  "Bagno / Servizi igienici",
  "Spogliatoio",
  "Locale tecnico",
  "Centrale termica",
  "Cabina elettrica",
  "Sala server / CED",
  "Area esterna / Cortile",
  "Parcheggio",
  "Cantiere",
];

const MAX_FOTO = 10;
const MAX_FOTO_SIZE_BYTES = 10 * 1024 * 1024;
const ALLOWED_FOTO_TYPES = ["image/jpeg", "image/png", "image/heic"];
const ALLOWED_FOTO_EXTENSIONS = [".jpg", ".jpeg", ".png", ".heic"];
const INVALID_FOTO_MESSAGE =
  "Formato non supportato o file troppo grande (max 10 MB)";

function createEmptyAmbiente(aziendaId: string, ordine: number): Ambiente {
  return {
    id: crypto.randomUUID(),
    azienda_id: aziendaId,
    nome: "",
    tipo: "",
    superficie_mq: null,
    preposto_id: null,
    descrizione_attivita: null,
    ordine,
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

// Resize + recompress JPG/PNG so we don't blow Render's request timeout on
// 8-12 MB iPhone photos. Feedback 2026-04-29 #4/#5/#11: uploads silently
// stalled around the 4th file because Safari surfaces "load failed" on
// timeouts and our handler queued them for retry instead of compressing.
// HEIC and small files (<1.5 MB) skip — Canvas can't decode HEIC and small
// files don't justify the CPU cost.
const COMPRESS_SKIP_BYTES = 1.5 * 1024 * 1024;
const COMPRESS_MAX_DIMENSION = 2000;
const COMPRESS_QUALITY = 0.85;

async function compressFotoIfNeeded(file: File): Promise<File> {
  if (file.size <= COMPRESS_SKIP_BYTES) return file;
  const nameLower = file.name.toLowerCase();
  if (nameLower.endsWith(".heic") || file.type === "image/heic") return file;

  try {
    const bitmap = await createImageBitmap(file);
    const { width, height } = bitmap;
    const longest = Math.max(width, height);
    const scale = longest > COMPRESS_MAX_DIMENSION
      ? COMPRESS_MAX_DIMENSION / longest
      : 1;
    const targetW = Math.round(width * scale);
    const targetH = Math.round(height * scale);

    const canvas = document.createElement("canvas");
    canvas.width = targetW;
    canvas.height = targetH;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      bitmap.close?.();
      return file;
    }
    ctx.drawImage(bitmap, 0, 0, targetW, targetH);
    bitmap.close?.();

    const blob: Blob | null = await new Promise((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", COMPRESS_QUALITY)
    );
    if (!blob || blob.size >= file.size) return file;

    // Preserve original basename, force .jpg extension since output is JPEG.
    const base = file.name.replace(/\.[^.]+$/, "");
    return new File([blob], `${base}.jpg`, {
      type: "image/jpeg",
      lastModified: file.lastModified,
    });
  } catch {
    // Any decode/encode failure — fall back to original file.
    return file;
  }
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
  // Feedback issue #7 (2026-05-14): inline thumbnails of uploaded photos.
  // Maps foto.id -> object URL. The backend exposes the bytes behind an
  // auth-gated endpoint (no public signed URL because photos can include
  // people and sensitive workplace layouts), so we fetch with the bearer
  // token, wrap in a blob URL, and revoke when the row goes away. The ref
  // mirrors state so the unmount cleanup sees the live URL map.
  const [previewUrls, setPreviewUrls] = useState<Record<string, string>>({});
  const previewUrlsRef = useRef<Record<string, string>>({});
  useEffect(() => {
    previewUrlsRef.current = previewUrls;
  }, [previewUrls]);
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

  // Feedback issue #7: lazy-load thumbnail blobs for any foto we don't have
  // a preview URL for yet. Bearer-auth is required, so we can't just point
  // <img src> at the endpoint directly. We fetch the bytes, wrap in a blob
  // URL, and stash in state. Revocation runs on unmount + on row deletion.
  useEffect(() => {
    if (!isAuthenticated || foto.length === 0) return;
    let cancelled = false;
    (async () => {
      // Refresh the token via the same path useApi uses — avoids reimplementing
      // the NextAuth session round-trip inline.
      const sessionRes = await fetch("/api/auth/session").catch(() => null);
      const sess = sessionRes ? await sessionRes.json().catch(() => null) : null;
      const token = sess?.accessToken;
      if (!token) return;
      const needed = foto.filter((f) => !previewUrls[f.id]);
      for (const f of needed) {
        if (cancelled) break;
        try {
          const res = await fetch(`${API_URL}${basePath}/${f.id}/content`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (!res.ok) continue;
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          if (cancelled) {
            URL.revokeObjectURL(url);
            break;
          }
          setPreviewUrls((prev) => ({ ...prev, [f.id]: url }));
        } catch {
          // Network blip — leave the icon fallback; next foto-list update retries.
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [foto, isAuthenticated, basePath, previewUrls]);

  // Revoke all blob URLs when the grid unmounts (ambiente switch / page leave).
  useEffect(() => {
    return () => {
      Object.values(previewUrlsRef.current).forEach((u) =>
        URL.revokeObjectURL(u),
      );
    };
  }, []);

  const uploadOne = useCallback(
    async (file: File): Promise<AmbienteFoto | null> => {
      const compressed = await compressFotoIfNeeded(file);
      const fd = new FormData();
      fd.append("file", compressed);
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
          // Tell the operator the file is queued — previously the failure was
          // swallowed and only the first few uploads visibly succeeded, which
          // surfaced as "non mi fa caricare più di 3 foto" (feedback #5).
          toast.warning(
            offline
              ? `"${file.name}": offline, riprovo al ripristino della connessione`
              : `"${file.name}": rete instabile, riprovo automaticamente`,
          );
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
        // Free the blob URL for the deleted photo so we don't leak memory
        // when the operator deletes + re-uploads many times in one session.
        setPreviewUrls((prev) => {
          const url = prev[fotoId];
          if (url) URL.revokeObjectURL(url);
          const next = { ...prev };
          delete next[fotoId];
          return next;
        });
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
          {foto.map((f) => {
            const previewUrl = previewUrls[f.id];
            return (
              <div
                key={f.id}
                className="group relative w-[110px] rounded-md border bg-muted/20 p-1.5"
              >
                <div className="relative flex h-[80px] w-full items-center justify-center overflow-hidden rounded bg-muted">
                  {previewUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={previewUrl}
                      alt={f.filename}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <ImagePlus className="h-6 w-6 text-muted-foreground/50" />
                  )}
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
            );
          })}
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

  // Bug A fix — serialize per-row writes. The autosave previously fired one
  // POST per keystroke against an unpersisted row; multiple POSTs landed in
  // flight before the first response could mark the row persisted, so each
  // POST created a fresh row. We now keep a per-row promise chain: a POST is
  // attempted at most once per row, and any concurrent updates queue behind
  // it as PUTs against the server-assigned id.
  const inflightCreateRef = useRef<Map<string, Promise<Ambiente | null>>>(
    new Map()
  );
  // Latest pending payload per local row id — coalesced so that even if many
  // keystrokes land while a POST is in flight, only the most recent payload
  // is PUT after creation resolves.
  const pendingPutRef = useRef<Map<string, Partial<Ambiente>>>(new Map());
  // Stable React keys for the rendered rows. The row's `id` flips from the
  // client-generated UUID to the server-assigned UUID once the POST resolves;
  // using `ambiente.id` directly as the React key caused the surrounding
  // <div> to unmount/remount the moment the swap happened, dropping focus
  // from the <input> the operator was mid-typing into. That's the "first
  // letter, then Enter, second attempt works" bug (feedback #569776fc /
  // #d1cb66c9). The default key is the current id; the swap handler stores
  // the original id under the new id so the rendered key stays stable.
  // Stored in state (not a ref) so the React Compiler is happy reading it
  // during render, and so the swap batches with the onChange that triggers
  // the re-render — both updates land in the same render pass.
  const [clientKeyMap, setClientKeyMap] = useState<Map<string, string>>(
    () => new Map(),
  );
  const getClientKey = (id: string) => clientKeyMap.get(id) ?? id;
  const swapClientKey = useCallback((oldId: string, newId: string) => {
    if (oldId === newId) return;
    setClientKeyMap((prev) => {
      const next = new Map(prev);
      const stable = next.get(oldId) ?? oldId;
      next.delete(oldId);
      next.set(newId, stable);
      return next;
    });
  }, []);
  // Always-current snapshot of the ambienti array. Async callbacks below
  // patch by row id (not index) and need the latest list at resolve time so
  // that out-of-order resolutions don't clobber sibling rows.
  const ambientiRef = useRef<Ambiente[]>(ambienti);
  useEffect(() => {
    ambientiRef.current = ambienti;
  }, [ambienti]);

  const addAmbiente = useCallback(() => {
    // New row goes to the end of the list visually; the server picks the
    // canonical `ordine` on POST (max+1) and the response replaces this
    // placeholder. We seed `ordine` here so the local list stays sorted
    // by ordine even before the round-trip completes.
    const nextOrdine = ambienti.length
      ? Math.max(...ambienti.map((a) => a.ordine ?? 0)) + 1
      : 0;
    onChange([...ambienti, createEmptyAmbiente(aziendaId, nextOrdine)]);
  }, [ambienti, onChange, aziendaId]);

  // Feedback #22: arrow-button reorder. We swap the two affected rows in
  // local state optimistically, then PATCH both rows so the server agrees.
  // On error we revert. We deliberately don't use dnd-kit here even though
  // the package is installed — on mobile (the primary survey device) drag
  // handles are fiddly inside a long form, whereas two icon buttons are
  // unambiguous and accessible.
  const moveAmbiente = useCallback(
    async (index: number, direction: "up" | "down") => {
      const targetIndex = direction === "up" ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= ambienti.length) return;
      const a = ambienti[index];
      const b = ambienti[targetIndex];
      if (!a || !b) return;

      const aOrdine = a.ordine ?? index;
      const bOrdine = b.ordine ?? targetIndex;

      // Build the new list with the two rows swapped *and* their `ordine`
      // values swapped, so the visual order matches the canonical sort key.
      const swapped = ambienti.map((row, i) => {
        if (i === index) return { ...b, ordine: aOrdine };
        if (i === targetIndex) return { ...a, ordine: bOrdine };
        return row;
      });
      onChange(swapped);

      // Only PATCH rows that the server actually knows about. A row that
      // hasn't been persisted yet (no nome, or POST still in flight)
      // doesn't need a network update — its `ordine` will be sent with
      // the eventual POST/PUT cycle.
      const aPersisted = persistedIdsRef.current.has(a.id);
      const bPersisted = persistedIdsRef.current.has(b.id);

      try {
        const tasks: Promise<unknown>[] = [];
        if (aPersisted) {
          tasks.push(
            apiFetch(`${basePath}/${a.id}/ordine`, {
              method: "PATCH",
              body: JSON.stringify({ ordine: bOrdine }),
            }),
          );
        }
        if (bPersisted) {
          tasks.push(
            apiFetch(`${basePath}/${b.id}/ordine`, {
              method: "PATCH",
              body: JSON.stringify({ ordine: aOrdine }),
            }),
          );
        }
        await Promise.all(tasks);
      } catch (err) {
        // Revert on failure so the UI doesn't lie about persisted state.
        onChange(ambienti);
        toast.error(
          err instanceof Error ? err.message : "Errore nel riordinamento",
        );
      }
    },
    [ambienti, onChange, apiFetch, basePath],
  );

  const removeAmbiente = useCallback(
    async (index: number) => {
      const target = ambienti[index];
      const next = ambienti.filter((_, i) => i !== index);
      onChange(next);
      if (!target) return;
      // If a POST is in flight for this row, wait for it before deleting so
      // we have the real server id (and don't leak an orphan).
      const inflight = inflightCreateRef.current.get(target.id);
      let serverId = target.id;
      if (inflight) {
        const created = await inflight.catch(() => null);
        if (created) serverId = created.id;
      }
      pendingPutRef.current.delete(target.id);
      if (persistedIdsRef.current.has(serverId)) {
        try {
          await apiFetch(`${basePath}/${serverId}`, { method: "DELETE" });
          persistedIdsRef.current.delete(serverId);
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
      const localId = row.id;
      const payload = {
        nome: row.nome,
        tipo: row.tipo,
        superficie_mq: row.superficie_mq,
        descrizione_attivita: row.descrizione_attivita,
      };

      // Path A: row already persisted on the server — straight PUT.
      // Don't merge the response back into local state: the operator may
      // have typed more characters while the PUT was in flight, and
      // overwriting with the (now-stale) server echo would clobber them.
      if (persistedIdsRef.current.has(localId)) {
        try {
          await apiFetch<Ambiente>(`${basePath}/${localId}`, {
            method: "PUT",
            body: JSON.stringify(payload),
          });
        } catch (err) {
          toast.error(
            err instanceof Error ? err.message : "Errore nel salvataggio"
          );
        }
        return;
      }

      // Path B: row not yet persisted. If a POST is already in flight for
      // this local id, just stash the latest payload — it will be flushed
      // as a PUT once the POST resolves with the server id.
      if (inflightCreateRef.current.has(localId)) {
        pendingPutRef.current.set(localId, payload);
        return;
      }

      // Path C: first POST for this row. We register the promise BEFORE
      // awaiting so any concurrent keystroke takes Path B above instead of
      // firing a second POST. Subsequent edits queued while we await are
      // flushed once we know the server id.
      const createPromise: Promise<Ambiente | null> = (async () => {
        try {
          const created = await apiFetch<Ambiente>(basePath, {
            method: "POST",
            body: JSON.stringify(payload),
          });
          persistedIdsRef.current.delete(localId);
          persistedIdsRef.current.add(created.id);
          // Preserve the React key across the id swap so the <input> the
          // operator is typing into doesn't unmount.
          swapClientKey(localId, created.id);
          // Swap ONLY the id in the wizard state — never overwrite the
          // other fields with the server response. The server's `nome`
          // is whatever we POSTed at the first keystroke (`"M"`); the
          // operator has typed many more characters since, and replacing
          // the row wholesale would snap the input back to the stale
          // first-letter value. Drain via pendingPutRef handles the
          // server-side catch-up.
          onChange(
            ambientiRef.current.map((a) =>
              a.id === localId ? { ...a, id: created.id } : a,
            ),
          );
          return created;
        } catch (err) {
          toast.error(
            err instanceof Error ? err.message : "Errore nel salvataggio"
          );
          return null;
        }
      })();
      inflightCreateRef.current.set(localId, createPromise);

      const created = await createPromise;
      inflightCreateRef.current.delete(localId);

      // Drain any payload that was coalesced while POST was in flight.
      // Same reasoning as Path A: don't merge the PUT response into local
      // state — newer keystrokes during the round-trip would be lost.
      const queued = pendingPutRef.current.get(localId);
      pendingPutRef.current.delete(localId);
      if (created && queued) {
        try {
          await apiFetch<Ambiente>(`${basePath}/${created.id}`, {
            method: "PUT",
            body: JSON.stringify(queued),
          });
        } catch (err) {
          toast.error(
            err instanceof Error ? err.message : "Errore nel salvataggio"
          );
        }
      }
    },
    [ambienti, onChange, apiFetch, basePath, swapClientKey]
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
        <datalist id="ambiente-tipi-suggestions">
          {TIPI_AMBIENTE.map((tipo) => (
            <option key={tipo} value={tipo} />
          ))}
        </datalist>
        <div className="space-y-6">
          {ambienti.length === 0 && (
            <p className="py-8 text-center text-muted-foreground">
              Nessun ambiente aggiunto. Clicca &quot;Aggiungi Ambiente&quot; per
              iniziare.
            </p>
          )}

          {ambienti.map((ambiente, index) => (
            <div key={getClientKey(ambiente.id)}>
              {index > 0 && <Separator className="mb-6" />}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium">
                    Ambiente {index + 1}
                    {ambiente.nome ? ` - ${ambiente.nome}` : ""}
                  </h3>
                  <div className="flex items-center gap-1">
                    {/* Feedback #22: up/down to reshuffle the survey list */}
                    <Button
                      variant="outline"
                      size="icon-sm"
                      onClick={() => moveAmbiente(index, "up")}
                      disabled={index === 0}
                      aria-label="Sposta ambiente su"
                      title="Sposta su"
                    >
                      <ArrowUp className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon-sm"
                      onClick={() => moveAmbiente(index, "down")}
                      disabled={index === ambienti.length - 1}
                      aria-label="Sposta ambiente giu"
                      title="Sposta giu"
                    >
                      <ArrowDown className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="icon-sm"
                      onClick={() => removeAmbiente(index)}
                      aria-label="Elimina ambiente"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
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

                  {/* Tipo — combobox with suggestions; free text allowed */}
                  <div className="space-y-2">
                    <Label htmlFor={`amb-tipo-${index}`}>
                      Tipo
                    </Label>
                    <Input
                      id={`amb-tipo-${index}`}
                      list="ambiente-tipi-suggestions"
                      value={ambiente.tipo}
                      onChange={(e) =>
                        updateAmbiente(index, {
                          tipo: e.target.value,
                        })
                      }
                      placeholder="Scrivi o seleziona (es. Ufficio, Magazzino, Altro...)"
                    />
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
