"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { markHydrated } from "@/components/landing/hydration";
import { useSkipMotion } from "@/components/landing/use-skip-motion";

/**
 * Fades and lifts its children in once they enter the viewport, then stops
 * observing.
 *
 * The hidden state lives in globals.css (`.reveal`), behind
 * `scripting: enabled` and `prefers-reduced-motion: no-preference`. The
 * server-rendered HTML is therefore readable as it stands: a visitor without
 * JavaScript, a crawler, or a page whose bundle never hydrated sees every
 * section. It used to ship `opacity: 0` inline, which left all seven section
 * headings invisible in those cases — the content must never depend on the
 * animation to be readable.
 */
export function Reveal({
  children,
  className,
  delay = 0,
  as: Tag = "div",
  id,
}: {
  children: ReactNode;
  className?: string;
  /** Stagger, in ms, applied once the element reveals. */
  delay?: number;
  as?: "div" | "section" | "article" | "figure" | "li";
  /** Set when the revealed element is itself a scroll anchor. */
  id?: string;
}) {
  const ref = useRef<HTMLElement>(null);
  const skipMotion = useSkipMotion();
  const [entered, setEntered] = useState(false);
  const shown = skipMotion || entered;

  useEffect(() => {
    markHydrated();
  }, []);

  useEffect(() => {
    if (skipMotion) return;
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          setEntered(true);
          observer.disconnect();
        }
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.06 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [skipMotion]);

  return (
    <Tag
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ref={ref as any}
      id={id}
      className={className ? `reveal ${className}` : "reveal"}
      data-revealed={shown || undefined}
      style={delay ? stagger(delay) : undefined}
    >
      {children}
    </Tag>
  );
}

function stagger(ms: number): CSSProperties {
  return { "--reveal-delay": `${ms}ms` } as CSSProperties & Record<"--reveal-delay", string>;
}
