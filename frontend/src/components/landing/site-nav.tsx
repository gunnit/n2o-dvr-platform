"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

/**
 * Public site header.
 *
 * `overlay` sits transparent over the dark hero and turns into a frosted white
 * bar once the hero has scrolled past — the landing page only. `solid` is the
 * permanently-navy variant every other public page uses, where there is no hero
 * behind it to read against.
 */
type Variant = "overlay" | "solid";

/** `/#id` on sub-pages, bare `#id` on the landing so we never re-navigate. */
function sectionHref(id: string, onLanding: boolean) {
  return onLanding ? `#${id}` : `/#${id}`;
}

const NAV = [
  { id: "come-funziona", label: "Prodotto", priority: "low" },
  { id: "fascicolo", label: "Documenti", priority: "low" },
  { id: "consulenti", label: "Per consulenti", priority: "mid" },
  { id: "aziende", label: "Per aziende", priority: "mid" },
  { id: "metodo", label: "Metodo", priority: "low" },
] as const;

// The design hides links in two waves as the bar narrows rather than folding
// them into a burger. "Prezzi" is never hidden — it is the commercial path.
const PRIORITY_CLASS: Record<string, string> = {
  low: "hidden lg:inline-flex",
  mid: "hidden md:inline-flex",
};

export function SiteNav({ variant = "overlay" }: { variant?: Variant }) {
  const onLanding = variant === "overlay";
  const pathname = usePathname();
  // Overlay starts transparent; solid is never anything else.
  const [solid, setSolid] = useState(variant === "solid");

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

  const dark = variant === "solid";
  const frosted = solid && !dark;

  return (
    <header
      className={[
        "fixed inset-x-0 top-0 z-60 border-b transition-[background-color,border-color,backdrop-filter] duration-300",
        frosted
          ? "border-[#e5edf5] bg-white/[0.86] backdrop-blur-[14px]"
          : dark
            ? "border-white/12 bg-[#061b31]/92 backdrop-blur-[14px]"
            : "border-transparent bg-transparent",
      ].join(" ")}
    >
      {/* px-6, not px-5: every section below uses `px-6 sm:px-7`, so a 20px
          gutter here put the brand mark 4px inboard of the hero headline it
          sits directly above — the one vertical edge on the page a visitor
          can actually see out of alignment. */}
      <div className="mx-auto flex h-[68px] w-full max-w-[1160px] items-center justify-between gap-4 px-6 sm:gap-6 sm:px-7">
        <Link
          href="/"
          className={[
            "font-heading text-[15px] font-light tracking-[0.2em] whitespace-nowrap uppercase transition-colors",
            frosted ? "text-[#061b31]" : "text-white/92",
          ].join(" ")}
        >
          N2O <span className="opacity-45">·</span> DVR
        </Link>

        <nav
          aria-label="Sezioni del sito"
          className="flex items-center gap-6 lg:gap-[30px]"
        >
          {NAV.map((item) => (
            <a
              key={item.id}
              href={sectionHref(item.id, onLanding)}
              className={[
                PRIORITY_CLASS[item.priority],
                "text-[14px] whitespace-nowrap transition-colors",
                frosted
                  ? "text-[#64748d] hover:text-[#061b31]"
                  : "text-white/75 hover:text-white",
              ].join(" ")}
            >
              {item.label}
            </a>
          ))}
          {/* Hidden on phones only because the CTA beside it already goes to
              /prezzi — dropping the duplicate is what buys the CTA room to fit.
              It is also the only nav item that can be the current page, so it
              carries the wayfinding state for the whole bar. */}
          <Link
            href="/prezzi"
            aria-current={pathname === "/prezzi" ? "page" : undefined}
            className={[
              "hidden text-[14px] whitespace-nowrap transition-colors sm:inline-flex",
              pathname === "/prezzi"
                ? frosted
                  ? "font-medium text-[#061b31]"
                  : "font-medium text-white"
                : frosted
                  ? "text-[#64748d] hover:text-[#061b31]"
                  : "text-white/75 hover:text-white",
            ].join(" ")}
          >
            Prezzi
          </Link>
        </nav>

        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className={[
              "px-1.5 py-2 text-[14px] font-medium whitespace-nowrap transition-colors",
              frosted
                ? "text-[#003d74] hover:text-[#1b5594]"
                : "text-white/85 hover:text-white",
            ].join(" ")}
          >
            Accedi
          </Link>
          <Link
            href="/prezzi"
            className={[
              "rounded-[4px] px-3 py-[9px] text-[14px] font-medium whitespace-nowrap transition-colors sm:px-4",
              frosted
                ? "bg-[#003d74] text-white hover:bg-[#1b5594]"
                : "bg-white text-[#061b31] hover:bg-[#e5edf5]",
            ].join(" ")}
          >
            {/* Phones cannot fit the full label beside the brand and "Accedi". */}
            <span className="sm:hidden">Attiva</span>
            <span className="hidden sm:inline">Attiva un piano</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
