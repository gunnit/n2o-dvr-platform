"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useSkipMotion } from "@/components/landing/use-skip-motion";

/**
 * Fades and lifts its children in once they enter the viewport, then stops
 * observing. Renders visible immediately when the viewer prefers reduced motion
 * or the browser has no IntersectionObserver — the content must never depend on
 * the animation to be readable.
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
  as?: "div" | "section" | "article" | "figure";
  /** Set when the revealed element is itself a scroll anchor. */
  id?: string;
}) {
  const ref = useRef<HTMLElement>(null);
  const skipMotion = useSkipMotion();
  const [entered, setEntered] = useState(false);
  const shown = skipMotion || entered;

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
      className={className}
      style={
        skipMotion
          ? undefined
          : {
              opacity: shown ? 1 : 0,
              transform: shown ? "none" : "translateY(22px)",
              transition:
                "opacity .8s cubic-bezier(.16,1,.3,1), transform .8s cubic-bezier(.16,1,.3,1)",
              transitionDelay: shown && delay ? `${delay}ms` : undefined,
            }
      }
    >
      {children}
    </Tag>
  );
}
