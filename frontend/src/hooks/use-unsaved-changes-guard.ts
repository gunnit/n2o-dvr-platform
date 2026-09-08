"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

/**
 * Warns before unsaved edits are lost (UI/UX audit 2026-09-07, F4).
 *
 * Two exits are covered. A full unload — reload, close, typed URL — goes
 * through `beforeunload`, where the browser shows its own prompt. In-app
 * navigation has no such event in the App Router, so same-origin link clicks
 * are intercepted while `dirty` and held in `pendingHref`; the caller shows
 * its dialog and calls `confirmLeave` (navigates to the held link) or
 * `cancelLeave`. Next's `<Link>` skips its own navigation when the click's
 * default is prevented, so nothing else has to know about the guard.
 *
 * Not covered: the browser back button and non-link navigations such as the
 * logout button. Both are rare on a page whose exits are links.
 */
export function useUnsavedChangesGuard(dirty: boolean) {
  const router = useRouter();
  const [pendingHref, setPendingHref] = useState<string | null>(null);
  // Listeners are registered once; they read the latest flag through a ref.
  const dirtyRef = useRef(dirty);
  useEffect(() => {
    dirtyRef.current = dirty;
  }, [dirty]);

  useEffect(() => {
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!dirtyRef.current) return;
      event.preventDefault();
      // Legacy browsers need a non-undefined returnValue to show the prompt.
      event.returnValue = "";
    };
    const onClick = (event: MouseEvent) => {
      if (!dirtyRef.current || event.defaultPrevented) return;
      // Modified clicks open a new tab or window; the page stays.
      if (
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }
      const target = event.target as Element | null;
      const anchor = target?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!anchor) return;
      if (anchor.target === "_blank" || anchor.hasAttribute("download")) return;
      const url = new URL(anchor.getAttribute("href") ?? "", window.location.href);
      if (url.origin !== window.location.origin) return;
      if (
        url.pathname === window.location.pathname &&
        url.search === window.location.search
      ) {
        return; // in-page anchor
      }
      event.preventDefault();
      setPendingHref(url.pathname + url.search + url.hash);
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    // Capture phase: runs before Next's Link handler sees the click.
    document.addEventListener("click", onClick, true);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      document.removeEventListener("click", onClick, true);
    };
  }, []);

  const confirmLeave = useCallback(() => {
    const href = pendingHref;
    setPendingHref(null);
    if (href) {
      dirtyRef.current = false;
      router.push(href);
    }
  }, [pendingHref, router]);

  const cancelLeave = useCallback(() => setPendingHref(null), []);

  return { pendingHref, confirmLeave, cancelLeave };
}
