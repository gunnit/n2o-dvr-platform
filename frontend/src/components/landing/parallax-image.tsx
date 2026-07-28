"use client";

import Image from "next/image";
import { useEffect, useRef } from "react";

/**
 * An image that drifts against the scroll. `speed` is the fraction of the
 * element's distance from the viewport centre that it translates by, so 0.06 is
 * a barely-there editorial drift and 0.14 is a hero.
 *
 * The transform is written straight to the node inside rAF rather than through
 * state: this runs on every scroll frame and a re-render per frame would cost
 * more than the effect is worth. Disabled entirely under reduced motion.
 */
export function ParallaxImage({
  src,
  alt,
  width,
  height,
  speed = 0.06,
  priority = false,
  sizes,
  className,
  wrapperClassName,
}: {
  src: string;
  alt: string;
  width: number;
  height: number;
  speed?: number;
  priority?: boolean;
  sizes?: string;
  className?: string;
  wrapperClassName?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let queued = false;
    const apply = () => {
      queued = false;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight;
      // Skip work for anything comfortably off-screen.
      if (rect.bottom < -200 || rect.top > vh + 200) return;
      const centre = rect.top + rect.height / 2 - vh / 2;
      el.style.transform = `translate3d(0, ${(-centre * speed).toFixed(2)}px, 0)`;
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
  }, [speed]);

  return (
    <div ref={ref} className={wrapperClassName} style={{ willChange: "transform" }}>
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        priority={priority}
        sizes={sizes}
        className={className}
      />
    </div>
  );
}
