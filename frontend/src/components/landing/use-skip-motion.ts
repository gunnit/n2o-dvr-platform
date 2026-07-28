"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * True when scroll-driven animation should be skipped entirely — either the
 * viewer asked for reduced motion, or the browser has no IntersectionObserver
 * to drive the reveals with.
 *
 * Read through `useSyncExternalStore` rather than a `useState` + effect pair:
 * the media query is external state, and subscribing to it properly is both
 * what the React Compiler wants and what makes a mid-session change to the OS
 * setting take effect without a reload.
 *
 * The server snapshot is `false` — animation on — because that is the common
 * case, so the overwhelming majority of visitors hydrate without a re-render.
 */
export function useSkipMotion(): boolean {
  const subscribe = useCallback((onChange: () => void) => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const getSnapshot = useCallback(
    () =>
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      !("IntersectionObserver" in window),
    [],
  );

  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
