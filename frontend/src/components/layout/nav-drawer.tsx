"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  useSyncExternalStore,
} from "react";

/**
 * Open/closed state for the navigation drawer, shared by the two components
 * that need it: the hamburger lives in the header, the drawer is the sidebar,
 * and they are siblings under the dashboard layout.
 *
 * Below `lg` the sidebar is an overlay; at `lg` and up it is a permanent column
 * and this state stops mattering. `isDesktop` is tracked rather than left to a
 * media query because two things cannot be expressed in CSS: whether the
 * off-screen drawer should be `inert` (a keyboard user must not tab into a menu
 * they cannot see), and whether to lock body scroll.
 */

const LG = 1024;
const QUERY = `(min-width: ${LG}px)`;

function subscribe(onChange: () => void) {
  const mq = window.matchMedia(QUERY);
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
}

type NavDrawerValue = {
  open: boolean;
  isDesktop: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
  close: () => void;
};

const NavDrawerContext = createContext<NavDrawerValue | null>(null);

export function NavDrawerProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  // `useSyncExternalStore` rather than `useState` + an effect that syncs it:
  // reading a media query is subscribing to something outside React, and the
  // effect version sets state synchronously on mount, which is the cascading
  // render `react-hooks/set-state-in-effect` exists to prevent. The server
  // snapshot is `true` so SSR and the first client paint agree on the desktop
  // layout — the common case, and the one where guessing wrong would flash an
  // `inert` sidebar over real content.
  const isDesktop = useSyncExternalStore(
    subscribe,
    () => window.matchMedia(QUERY).matches,
    () => true,
  );

  // Crossing up to desktop with the drawer open would otherwise leave the
  // backdrop armed over a sidebar that is now part of the layout. Set inside
  // the listener, not the effect body, so nothing cascades on mount.
  useEffect(() => {
    const mq = window.matchMedia(QUERY);
    const onChange = (e: MediaQueryListEvent) => {
      if (e.matches) setOpen(false);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    // The drawer scrolls its own nav; the page behind it must not scroll too.
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [open]);

  const close = useCallback(() => setOpen(false), []);
  const toggle = useCallback(() => setOpen((v) => !v), []);

  return (
    <NavDrawerContext.Provider
      value={{ open, isDesktop, setOpen, toggle, close }}
    >
      {children}
    </NavDrawerContext.Provider>
  );
}

export function useNavDrawer(): NavDrawerValue {
  const ctx = useContext(NavDrawerContext);
  if (!ctx) {
    throw new Error("useNavDrawer must be used inside <NavDrawerProvider>");
  }
  return ctx;
}
