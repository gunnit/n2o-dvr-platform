"use client";

import { ArrowRight, ChevronRight, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Public site header.
 *
 * `overlay` sits transparent over the dark hero and turns into a frosted white
 * bar once the hero has scrolled past — the landing page only. `solid` is the
 * permanently-navy variant every other public page uses, where there is no hero
 * behind it to read against.
 *
 * Below `lg` the section links move into a full-screen menu. They used to be
 * hidden in two waves with nothing in their place, so a phone visitor could
 * reach a section only by scrolling to it.
 */
type Variant = "overlay" | "solid";

/** `/#id` on sub-pages, bare `#id` on the landing so we never re-navigate. */
function sectionHref(id: string, onLanding: boolean) {
  return onLanding ? `#${id}` : `/#${id}`;
}

// Anchors are the section ids in app/page.tsx. `fascicolo` keeps its old id so
// links already shared to /#fascicolo still land on the documents section.
const SECTIONS = [
  { id: "come-funziona", label: "Come funziona" },
  { id: "fascicolo", label: "Documenti" },
  { id: "metodo", label: "Metodo" },
  { id: "per-chi", label: "Per chi è" },
] as const;

const LG_QUERY = "(min-width: 64rem)";

export function SiteNav({ variant = "overlay" }: { variant?: Variant }) {
  const onLanding = variant === "overlay";
  const pathname = usePathname();
  const onPrezzi = pathname === "/prezzi";
  // Overlay starts transparent; solid is never anything else.
  const [solid, setSolid] = useState(variant === "solid");
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (variant === "solid") return;

    let queued = false;
    const apply = () => {
      queued = false;
      setSolid(window.scrollY > window.innerHeight * 0.72);
    };
    const onScroll = () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(apply);
    };

    apply();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [variant]);

  const closeMenu = useCallback((restoreFocus: boolean) => {
    setMenuOpen(false);
    if (restoreFocus) {
      // After the dialog unmounts, give focus back to what opened it.
      requestAnimationFrame(() => menuButtonRef.current?.focus());
    }
  }, []);

  // While the menu is open: lock page scroll, move focus into the dialog, and
  // close it if the viewport grows past the breakpoint where it is hidden.
  useEffect(() => {
    if (!menuOpen) return;
    const root = document.documentElement;
    const previousOverflow = root.style.overflow;
    root.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    const wide = window.matchMedia(LG_QUERY);
    const onWide = () => {
      if (wide.matches) closeMenu(false);
    };
    wide.addEventListener("change", onWide);
    return () => {
      root.style.overflow = previousOverflow;
      wide.removeEventListener("change", onWide);
    };
  }, [menuOpen, closeMenu]);

  const onDialogKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeMenu(true);
      return;
    }
    if (event.key !== "Tab" || !dialogRef.current) return;
    // Keep Tab inside the dialog: it covers the whole page.
    const focusable = dialogRef.current.querySelectorAll<HTMLElement>("a[href], button");
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const dark = variant === "solid";
  const frosted = solid && !dark;

  const linkTone = frosted
    ? "text-[#64748d] hover:text-[#061b31]"
    : "text-white/78 hover:text-white";

  return (
    <>
      <a
        href="#contenuto"
        className="fixed top-3 left-3 z-80 -translate-y-24 rounded-md bg-white px-4 py-3 text-[14px] font-semibold text-[#061b31] shadow-stripe-deep transition-transform focus-visible:translate-y-0"
      >
        Salta al contenuto
      </a>
      <header
        className={[
          "fixed inset-x-0 top-0 z-60 border-b transition-[background-color,border-color,backdrop-filter] duration-300",
          // On navy (over the hero, or the solid variant) the navy focus ring
          // measured 1.61:1; `.dark-section` lifts it to ice blue.
          frosted ? "" : "dark-section",
          frosted
            ? "border-[#e5edf5] bg-white/[0.86] backdrop-blur-[14px]"
            : dark
              ? "border-white/12 bg-[#061b31]/92 backdrop-blur-[14px]"
              : "border-transparent bg-transparent",
        ].join(" ")}
      >
        {/* Same gutter as every section below (`px-6 sm:px-7`), so the brand
            mark sits on the same vertical edge as the hero headline. */}
        <div className="mx-auto flex h-[68px] w-full max-w-[1160px] items-center justify-between gap-4 px-6 sm:gap-6 sm:px-7">
          <Link
            href="/"
            className={[
              "font-heading text-[15px] font-medium tracking-[0.16em] whitespace-nowrap transition-colors",
              frosted ? "text-[#061b31]" : "text-white",
            ].join(" ")}
          >
            N2O <span className="opacity-45">·</span> DVR
          </Link>

          <nav aria-label="Sezioni del sito" className="hidden items-center gap-7 lg:flex xl:gap-8">
            {SECTIONS.map((item) => (
              <a
                key={item.id}
                href={sectionHref(item.id, onLanding)}
                className={`text-[14px] whitespace-nowrap transition-colors ${linkTone}`}
              >
                {item.label}
              </a>
            ))}
            <Link
              href="/prezzi"
              aria-current={onPrezzi ? "page" : undefined}
              className={[
                "text-[14px] whitespace-nowrap transition-colors",
                onPrezzi
                  ? frosted
                    ? "font-medium text-[#061b31]"
                    : "font-medium text-white"
                  : linkTone,
              ].join(" ")}
            >
              Prezzi
            </Link>
          </nav>

          <div className="flex items-center gap-1 sm:gap-2">
            <Link
              href="/login"
              className={[
                "inline-flex h-11 items-center px-3 text-[14px] font-medium whitespace-nowrap transition-colors",
                frosted ? "text-[#003d74] hover:text-[#1b5594]" : "text-white/88 hover:text-white",
              ].join(" ")}
            >
              Accedi
            </Link>
            <Link
              href="/prezzi"
              className={[
                "hidden h-10 items-center rounded-md px-4 text-[14px] font-semibold whitespace-nowrap transition-colors sm:inline-flex",
                frosted
                  ? "bg-[#003d74] text-white hover:bg-[#1b5594]"
                  : "bg-white text-[#061b31] hover:bg-[#e5edf5]",
              ].join(" ")}
            >
              Scegli il piano
            </Link>
            <button
              ref={menuButtonRef}
              type="button"
              aria-label="Apri il menu"
              aria-haspopup="dialog"
              aria-expanded={menuOpen}
              aria-controls="site-menu"
              onClick={() => setMenuOpen(true)}
              className={[
                "ml-1 inline-flex size-11 items-center justify-center rounded-lg border transition-colors lg:hidden",
                frosted
                  ? "border-[#e5edf5] text-[#061b31] hover:bg-[#f6f9fc]"
                  : "border-white/22 text-white hover:bg-white/12",
              ].join(" ")}
            >
              <Menu aria-hidden className="size-5" strokeWidth={1.8} />
            </button>
          </div>
        </div>
      </header>

      {/* A sibling of <header>, not a child: once the bar is frosted its
          backdrop-filter makes it the containing block for fixed-position
          descendants, which would trap a full-screen menu inside 68px. */}
      {menuOpen && (
        <div
          ref={dialogRef}
          id="site-menu"
          role="dialog"
          aria-modal="true"
          aria-label="Menu"
          onKeyDown={onDialogKeyDown}
          className="dark-section fixed inset-0 z-70 flex flex-col overflow-y-auto bg-[#061930] lg:hidden"
        >
          <div className="mx-auto flex h-[68px] w-full max-w-[1160px] shrink-0 items-center justify-between border-b border-white/10 px-6 sm:px-7">
            <Link
              href="/"
              onClick={() => closeMenu(false)}
              className="font-heading text-[15px] font-medium tracking-[0.16em] whitespace-nowrap text-white"
            >
              N2O <span className="opacity-45">·</span> DVR
            </Link>
            <button
              ref={closeButtonRef}
              type="button"
              aria-label="Chiudi il menu"
              onClick={() => closeMenu(true)}
              className="inline-flex size-11 items-center justify-center rounded-lg border border-white/22 text-white transition-colors hover:bg-white/12"
            >
              <X aria-hidden className="size-5" strokeWidth={1.8} />
            </button>
          </div>

          <nav
            aria-label="Sezioni del sito"
            className="mx-auto flex w-full max-w-[1160px] flex-col px-6 pt-3 sm:px-7"
          >
            {SECTIONS.map((item) => (
              <a
                key={item.id}
                href={sectionHref(item.id, onLanding)}
                onClick={() => closeMenu(false)}
                className="flex h-16 items-center justify-between border-b border-white/10 font-heading text-[24px] font-light tracking-[-0.015em] text-white"
              >
                {item.label}
                <ChevronRight aria-hidden className="size-[18px] text-white/50" strokeWidth={1.8} />
              </a>
            ))}
            <Link
              href="/prezzi"
              aria-current={onPrezzi ? "page" : undefined}
              onClick={() => closeMenu(false)}
              className="flex h-16 items-center justify-between border-b border-white/10 font-heading text-[24px] font-light tracking-[-0.015em] text-white"
            >
              Prezzi
              <ChevronRight aria-hidden className="size-[18px] text-white/50" strokeWidth={1.8} />
            </Link>
          </nav>

          <div className="mx-auto mt-auto flex w-full max-w-[1160px] flex-col gap-2.5 px-6 pt-8 pb-9 sm:px-7">
            <Link
              href="/prezzi"
              onClick={() => closeMenu(false)}
              className="inline-flex h-[52px] items-center justify-center gap-2.5 rounded-md bg-white text-[15px] font-semibold text-[#061b31] transition-colors hover:bg-[#e5edf5]"
            >
              Scegli il piano
              <ArrowRight aria-hidden className="size-4" strokeWidth={1.8} />
            </Link>
            <Link
              href="/login"
              onClick={() => closeMenu(false)}
              className="inline-flex h-[52px] items-center justify-center rounded-md border border-white/28 text-[15px] font-medium text-white transition-colors hover:bg-white/12"
            >
              Accedi
            </Link>
            <p className="mt-3.5 text-center text-[13px] text-white/64">
              Serve aiuto?{" "}
              <a
                href="mailto:support@dvr-sicurezza.it"
                className="text-[#a5c8ff] underline underline-offset-[3px]"
              >
                support@dvr-sicurezza.it
              </a>
            </p>
          </div>
        </div>
      )}
    </>
  );
}
