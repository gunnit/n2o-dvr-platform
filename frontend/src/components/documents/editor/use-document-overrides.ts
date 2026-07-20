"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiCall } from "@/lib/api-client";
import type { DocumentOverridesResponse } from "@/types";

export type OverrideSaveState = "idle" | "saving" | "saved" | "error";

/**
 * Local mirror of a document's content_overrides map with debounced,
 * serialized autosave against PATCH /documenti/{id}/overrides.
 *
 * Writes are optimistic: the local map updates immediately so the preview
 * re-renders, while the change is queued and flushed in one batched PATCH
 * shortly after (the per-paragraph typing debounce lives in
 * EditableParagraph — this batching window only coalesces commits from
 * different blocks). The server response is the full authoritative map and
 * replaces local state, with any keys committed while the request was in
 * flight re-applied on top. Failed batches are re-queued so "Riprova" (or
 * simply continuing to edit) retries them.
 *
 * Two guards against silent data loss: unmounting with a non-empty queue
 * fires one last best-effort keepalive PATCH, and a hard unload (tab
 * close, reload) while dirty triggers the browser's leave-page prompt.
 */
export function useDocumentOverrides(documentId: string) {
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [saveState, setSaveState] = useState<OverrideSaveState>("idle");

  // Queued, not-yet-persisted changes. null = delete the override.
  const pendingRef = useRef<Map<string, string | null>>(new Map());
  // Serializes PATCHes so two flushes can never race each other.
  const chainRef = useRef<Promise<boolean>>(Promise.resolve(true));
  const timerRef = useRef<number | null>(null);
  // Navigating between documents keeps this component mounted (same route
  // segment, different param) — flushes for the previous document must not
  // apply their late responses to the new one.
  const activeDocRef = useRef(documentId);
  // Mirror of saveState so the beforeunload listener never re-subscribes.
  const saveStateRef = useRef(saveState);
  useEffect(() => {
    saveStateRef.current = saveState;
  });

  /**
   * Last-chance flush of the queue on unmount. `keepalive` lets the PATCH
   * survive a page teardown right after the unmount; browsers cap
   * keepalive bodies (~64KB), so an enormous unsaved batch may be dropped
   * — acceptable for a best-effort fallback (flushAll covers deliberate
   * exits). Fire-and-forget: there is no surface left to report on.
   */
  const flushKeepalive = useCallback(() => {
    if (pendingRef.current.size === 0) return;
    const batch = Object.fromEntries(pendingRef.current);
    pendingRef.current.clear();
    void apiCall<DocumentOverridesResponse>(
      `/api/v1/documenti/${documentId}/overrides`,
      {
        method: "PATCH",
        body: JSON.stringify({ set: batch }),
        keepalive: true,
      },
    ).catch(() => {
      // Best-effort only — the editor is gone.
    });
  }, [documentId]);

  // Track the active document; on teardown either flush (real unmount) or
  // drop (switched document) whatever is still queued.
  useEffect(() => {
    activeDocRef.current = documentId;
    // The Map instance is stable (mutated, never reassigned), so this
    // capture stays valid inside the deferred cleanup below.
    const pending = pendingRef.current;
    return () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      // Deletion effects run parent -> child, so EditableParagraph unmount
      // cleanups may still commit an in-flight typing debounce into the
      // queue *after* this cleanup runs. Decide one microtask later, once
      // those commits have landed:
      // - real unmount (activeDocRef untouched): best-effort keepalive
      //   flush of everything still queued;
      // - navigation to a different document (activeDocRef re-assigned by
      //   the next effect run): drop the stale queue — flushing it now
      //   could attach the previous document's edits to the wrong id.
      queueMicrotask(() => {
        if (activeDocRef.current !== documentId) {
          pending.clear();
          return;
        }
        // Serialize behind any in-flight PATCH; a failed one re-queues its
        // batch, so the keepalive flush retries it too.
        void chainRef.current.then(() => flushKeepalive());
      });
    };
  }, [documentId, flushKeepalive]);

  // Warn before a hard unload (tab close, reload, external link) while
  // edits are queued or the last autosave is in flight / failed. Unmount
  // cleanups never run on unload, so the keepalive flush above cannot
  // cover this path.
  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      const dirty =
        pendingRef.current.size > 0 ||
        saveStateRef.current === "saving" ||
        saveStateRef.current === "error";
      if (!dirty) return;
      event.preventDefault();
      // Chrome still requires a set returnValue for the native prompt.
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, []);

  /** Seed the map from a freshly fetched preview. */
  const initialize = useCallback((initial: Record<string, string>) => {
    pendingRef.current.clear();
    setOverrides({ ...initial });
    setSaveState("idle");
  }, []);

  const doFlush = useCallback(async (): Promise<boolean> => {
    if (pendingRef.current.size === 0) return true;
    const batch = Object.fromEntries(pendingRef.current);
    pendingRef.current.clear();
    setSaveState("saving");
    try {
      const res = await apiCall<DocumentOverridesResponse>(
        `/api/v1/documenti/${documentId}/overrides`,
        { method: "PATCH", body: JSON.stringify({ set: batch }) },
      );
      // Late response for a document we already navigated away from.
      if (activeDocRef.current !== documentId) return true;
      // Server map is authoritative; re-apply anything committed mid-request.
      setOverrides(() => {
        const next = { ...res.overrides };
        for (const [addr, value] of pendingRef.current) {
          if (value === null) delete next[addr];
          else next[addr] = value;
        }
        return next;
      });
      if (pendingRef.current.size === 0) setSaveState("saved");
      return true;
    } catch {
      if (activeDocRef.current !== documentId) return true;
      // Re-queue the failed batch without clobbering newer edits.
      for (const [addr, value] of Object.entries(batch)) {
        if (!pendingRef.current.has(addr)) pendingRef.current.set(addr, value);
      }
      setSaveState("error");
      return false;
    }
  }, [documentId]);

  const scheduleFlush = useCallback(() => {
    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      timerRef.current = null;
      chainRef.current = chainRef.current.then(doFlush);
    }, 400);
  }, [doFlush]);

  /**
   * Optimistically set (or, with null, delete) one override and queue the
   * change for autosave.
   */
  const setOverride = useCallback(
    (addr: string, value: string | null) => {
      setOverrides((prev) => {
        const next = { ...prev };
        if (value === null) delete next[addr];
        else next[addr] = value;
        return next;
      });
      pendingRef.current.set(addr, value);
      setSaveState("saving");
      scheduleFlush();
    },
    [scheduleFlush],
  );

  /** Retry after a failed autosave. */
  const retrySave = useCallback(() => {
    chainRef.current = chainRef.current.then(doFlush);
  }, [doFlush]);

  /**
   * Flush everything now (used before "Salva come nuova versione" and
   * before downloads, so the server has every pending edit). Resolves true
   * when no change is left unsaved.
   */
  const flushAll = useCallback((): Promise<boolean> => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    chainRef.current = chainRef.current.then(doFlush);
    return chainRef.current;
  }, [doFlush]);

  return { overrides, saveState, initialize, setOverride, retrySave, flushAll };
}
