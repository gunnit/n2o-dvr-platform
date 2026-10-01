"use client";

import Image from "next/image";
import { useEffect, useRef, useState, type CSSProperties } from "react";
import modello from "@/components/landing/assets/officina-modello.webp";
import profondita from "@/components/landing/assets/officina-profondita.webp";
import type { DepthRenderer } from "@/components/landing/hero-depth-gl";
import {
  CARD_DELAY_MS,
  HERO_PINS,
  SCAN_MS,
  msToReach,
  scanAt,
  type HeroPin,
} from "@/components/landing/hero-scene";
import { riskBand, riskIndex, type RiskBand } from "@/components/landing/risk";
import { useSkipMotion } from "@/components/landing/use-skip-motion";

/**
 * The hero's scale model, live.
 *
 * Server-rendered as a plain image with its four risk pins and callouts in
 * place — that is the whole hero without JavaScript, and for anyone who asked
 * for reduced motion. With JavaScript, the pins start hidden (globals.css,
 * `scripting: enabled`), a WebGL layer is loaded once the image has painted,
 * and a survey scan sweeps the model, raising each pin as it passes. After
 * that the model answers the pointer and the scroll with real parallax.
 *
 * The image is always the LCP element and always underneath: if WebGL is
 * missing, slow or lost, the pins still rise on the same timetable and the
 * picture simply does not move.
 */

/** Pins in the order the sweep reaches them. */
const ORDER = [...HERO_PINS].sort((a, b) => a.scan - b.scan);
const LAST = ORDER[ORDER.length - 1];
const CARD_PIN = HERO_PINS.find((pin) => pin.placement.kind === "card") ?? LAST;

/** Parallax reach, in UV per unit of depth (see hero-depth-gl.ts). */
const POINTER_X = 0.016;
const POINTER_Y = 0.011;
const SCROLL_TILT = 0.016;
/** The whole stage drifts this far, in px, for the same inputs. */
const SHIFT_X = 7;
const SHIFT_Y = 5;
const SCROLL_DRIFT = 56;

/** How long the pins wait for WebGL before rising without the scan. */
const GL_GRACE_MS = 900;
/** Whatever happens, everything is shown by then. */
const FAILSAFE_MS = 6500;

function pinRisk(pin: HeroPin): { index: number; band: RiskBand } {
  const index = riskIndex(pin.danno, pin.probabilita);
  return { index, band: riskBand(index) };
}

const ALT =
  "Modello in scala di un'officina meccanica con quattro pericoli segnalati da spilli colorati: " +
  HERO_PINS.map((pin) => {
    const { index, band } = pinRisk(pin);
    return `${pin.name.toLowerCase()}, indice ${index}, ${band.label.toLowerCase()}`;
  }).join("; ") +
  ".";

const pct = (v: number) => `${(v * 100).toFixed(2)}%`;

/** Inline styles that set CSS custom properties. */
type Vars = CSSProperties & { [name: `--${string}`]: string | number };

export function HeroStage() {
  const stageRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // Number of pins raised so far, in sweep order. Starts at zero; the CSS
  // keeps everything visible when there is no script to raise them.
  const [raisedSoFar, setRaised] = useState(0);
  const [cardShown, setCardOn] = useState(false);
  const [live, setLive] = useState(false);
  // Reduced motion (or no IntersectionObserver): the finished state, no scan.
  const skipMotion = useSkipMotion();
  const raised = skipMotion ? ORDER.length : raisedSoFar;
  const cardOn = skipMotion || cardShown;

  useEffect(() => {
    // Lets globals.css stop holding content back for a script that runs.
    document.documentElement.dataset.hydrated = "";

    const stage = stageRef.current;
    const image = imageRef.current;
    const canvas = canvasRef.current;
    if (!stage || !image || !canvas) return;

    if (skipMotion) return;

    const showAll = () => {
      setRaised(ORDER.length);
      setCardOn(true);
    };

    let disposed = false;
    let renderer: DepthRenderer | null = null;
    let raf = 0;
    let last = 0;
    let scanStart = -1;
    let timelineStarted = false;
    let inView = true;
    let scroll = 0;
    let heroHeight = 1;
    const timers: number[] = [];
    const target = { x: 0, y: 0 };
    const current = { x: 0, y: 0 };

    const later = (fn: () => void, ms: number) => {
      timers.push(window.setTimeout(fn, ms));
    };
    later(showAll, FAILSAFE_MS);

    const startTimeline = (withScan: boolean) => {
      if (timelineStarted || disposed) return;
      timelineStarted = true;
      ORDER.forEach((pin, i) => later(() => setRaised((n) => Math.max(n, i + 1)), msToReach(pin.scan)));
      later(() => setCardOn(true), msToReach(LAST.scan) + CARD_DELAY_MS);
      if (withScan) {
        scanStart = performance.now();
        request();
      }
    };

    const request = () => {
      if (!raf) raf = requestAnimationFrame(tick);
    };

    const tick = (now: number) => {
      raf = 0;
      const dt = last ? Math.min(64, now - last) : 16;
      last = now;
      let again = false;

      const ease = 1 - Math.exp(-dt / 140);
      current.x += (target.x - current.x) * ease;
      current.y += (target.y - current.y) * ease;
      if (Math.abs(target.x - current.x) > 0.0015 || Math.abs(target.y - current.y) > 0.0015) {
        again = true;
      } else {
        current.x = target.x;
        current.y = target.y;
      }

      let scan = 0;
      let scanAmount = 0;
      if (scanStart >= 0) {
        const elapsed = now - scanStart;
        scan = scanAt(elapsed / SCAN_MS);
        // Full strength while sweeping, then fade the trail out.
        scanAmount = elapsed < SCAN_MS ? 1 : Math.max(0, 1 - (elapsed - SCAN_MS) / 600);
        if (scanAmount > 0) again = true;
        else scanStart = -1;
      }

      // The stage drifts as one piece; the depth offset moves its layers
      // against each other. Pointer right = camera right = near things left.
      stage.style.setProperty("--hero-shift-x", `${(-current.x * SHIFT_X).toFixed(2)}px`);
      stage.style.setProperty(
        "--hero-shift-y",
        `${(-current.y * SHIFT_Y + scroll * SCROLL_DRIFT).toFixed(2)}px`,
      );
      if (renderer && inView) {
        renderer.render({
          offsetX: -current.x * POINTER_X,
          offsetY: -current.y * POINTER_Y + scroll * SCROLL_TILT,
          scan,
          scanAmount,
        });
      }
      if (again) request();
    };

    // --- Inputs ------------------------------------------------------------
    const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    const onPointer = (event: PointerEvent) => {
      if (!inView) return;
      target.x = Math.max(-1, Math.min(1, (event.clientX / window.innerWidth) * 2 - 1));
      target.y = Math.max(-1, Math.min(1, (event.clientY / window.innerHeight) * 2 - 1));
      request();
    };
    const onPointerOut = (event: PointerEvent) => {
      if (event.relatedTarget) return; // still inside the window
      target.x = 0;
      target.y = 0;
      request();
    };
    const onScroll = () => {
      const next = Math.max(0, Math.min(1, window.scrollY / heroHeight));
      if (next === scroll) return;
      scroll = next;
      request();
    };
    const measure = () => {
      const hero = stage.closest("section");
      heroHeight = Math.max(1, hero?.offsetHeight ?? window.innerHeight);
      onScroll();
    };

    if (finePointer) {
      window.addEventListener("pointermove", onPointer, { passive: true });
      document.addEventListener("pointerout", onPointerOut, { passive: true });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", measure, { passive: true });
    measure();

    const visibility = new IntersectionObserver(([entry]) => {
      inView = entry.isIntersecting;
      if (inView) request();
    });
    visibility.observe(stage);

    let resizeQueued = false;
    const resizer = new ResizeObserver(() => {
      if (resizeQueued) return;
      resizeQueued = true;
      requestAnimationFrame(() => {
        resizeQueued = false;
        if (renderer?.resize()) {
          renderer.setImage(image);
          request();
        }
      });
    });
    // A wider stage can make the browser pick a sharper srcset candidate.
    const onImageLoad = () => {
      renderer?.setImage(image);
      request();
    };

    // --- Boot: image first, then WebGL in idle time --------------------------
    const boot = async () => {
      later(() => startTimeline(false), GL_GRACE_MS);
      try {
        const [{ createDepthRenderer }, depth] = await Promise.all([
          import("@/components/landing/hero-depth-gl"),
          loadImage(profondita.src),
          image.decode(),
        ]);
        if (disposed) return;
        renderer = createDepthRenderer(canvas, image, depth, {
          onLost: () => {
            renderer = null;
            setLive(false);
          },
          allowSoftware: "__n2oHeroSoftwareGL" in window,
        });
        if (!renderer) return;
        resizer.observe(canvas);
        image.addEventListener("load", onImageLoad);
        renderer.render({ offsetX: 0, offsetY: scroll * SCROLL_TILT, scan: 0, scanAmount: 0 });
        setLive(true);
        startTimeline(true);
        request();
      } catch {
        // No module, no depth map, or no decode: the image stays as it is and
        // the pins rise on the grace timer.
      }
    };

    // Safari has no requestIdleCallback; a short timeout is close enough.
    let cancelIdle = () => {};
    const whenIdle = () => {
      if (typeof window.requestIdleCallback === "function") {
        const handle = window.requestIdleCallback(() => void boot(), { timeout: 600 });
        cancelIdle = () => window.cancelIdleCallback(handle);
      } else {
        const handle = window.setTimeout(() => void boot(), 120);
        cancelIdle = () => window.clearTimeout(handle);
      }
    };
    if (image.complete && image.naturalWidth) whenIdle();
    else image.addEventListener("load", whenIdle, { once: true });

    return () => {
      disposed = true;
      if (raf) cancelAnimationFrame(raf);
      timers.forEach((t) => window.clearTimeout(t));
      cancelIdle();
      window.removeEventListener("pointermove", onPointer);
      document.removeEventListener("pointerout", onPointerOut);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", measure);
      image.removeEventListener("load", whenIdle);
      image.removeEventListener("load", onImageLoad);
      visibility.disconnect();
      resizer.disconnect();
      renderer?.dispose();
      renderer = null;
    };
  }, [skipMotion]);

  return (
    <figure className="hero-model">
      <div ref={stageRef} className="hero-stage">
        <div className="hero-stage-media">
          <Image
            ref={imageRef}
            src={modello}
            alt={ALT}
            loading="eager"
            fetchPriority="high"
            // Full-bleed below lg; from lg the column plus its bleed, capped at
            // 820px (globals.css, .hero-model).
            sizes="(min-width: 1024px) min(820px, calc(100vw - 440px)), 100vw"
          />
          <canvas ref={canvasRef} aria-hidden data-live={live || undefined} />
        </div>

        {/* Decorative restatement of the alt text and the legend below. */}
        <div aria-hidden className="hero-overlay">
          <svg viewBox="0 0 1000 700" preserveAspectRatio="none" className="hero-leaders">
            {HERO_PINS.map((pin) => (
              <path
                key={pin.id}
                d={leaderPath(pin)}
                pathLength={1}
                data-on={isRaised(pin, raised) || undefined}
                className={pin.placement.kind === "card" ? "hero-leader-card" : undefined}
              />
            ))}
          </svg>

          {HERO_PINS.map((pin) => (
            <Pin key={pin.id} pin={pin} on={isRaised(pin, raised)} />
          ))}

          {HERO_PINS.filter((pin) => pin.placement.kind !== "card").map((pin) => (
            <Chip key={pin.id} pin={pin} on={isRaised(pin, raised)} />
          ))}

          <ExampleCard pin={CARD_PIN} on={cardOn} />
        </div>
      </div>

      <figcaption className="hero-legend">
        <span className="hero-legend-title">Esempio · indice I = 2·D + P su ogni pericolo</span>
        <ul>
          {HERO_PINS.map((pin) => {
            const { index, band } = pinRisk(pin);
            return (
              <li key={pin.id}>
                <span aria-hidden className="hero-dot" style={{ background: band.color }} />
                {pin.name} <span className="hero-legend-value">I {index}</span>
                <span className="sr-only">, {band.label.toLowerCase()}</span>
              </li>
            );
          })}
        </ul>
      </figcaption>
    </figure>
  );
}

function isRaised(pin: HeroPin, raised: number) {
  return ORDER.indexOf(pin) < raised;
}

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const img = new window.Image();
    img.decoding = "async";
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

/** Leader in the overlay's 1000×700 units: from the pin to its label. */
function leaderPath(pin: HeroPin) {
  const hx = pin.head.x * 1000;
  const hy = pin.head.y * 700;
  const { placement } = pin;
  const py = placement.y * 700;
  switch (placement.kind) {
    case "above":
      return `M${hx} ${hy} V${py}`;
    case "left":
    case "right":
      return `M${hx} ${hy} V${py} H${placement.x * 1000}`;
    case "card":
      return `M${pin.base.x * 1000} ${pin.base.y * 700} V${py}`;
  }
}

function Pin({ pin, on }: { pin: HeroPin; on: boolean }) {
  const { band } = pinRisk(pin);
  const style: Vars = {
    "--x": pct(pin.head.x),
    "--top": pct(pin.head.y),
    "--bottom": pct(pin.base.y),
    "--c": band.color,
  };
  return (
    <span className="hero-pin" style={style} data-on={on || undefined}>
      {/* Clipped at the base, so the pin rises out of the machine. */}
      <span className="hero-pin-clip">
        <span className="hero-pin-rise">
          <span className="hero-pin-stem" />
          <span className="hero-pin-head" />
        </span>
      </span>
      <span className="hero-pin-ring" />
    </span>
  );
}

function Chip({ pin, on }: { pin: HeroPin; on: boolean }) {
  const { index, band } = pinRisk(pin);
  const { placement } = pin;
  const style: Vars =
    placement.kind === "left"
      ? { "--y": pct(placement.y), "--right": pct(1 - placement.x) }
      : { "--y": pct(placement.y), "--left": pct(placement.x) };
  return (
    <span className="hero-chip" data-side={placement.kind} style={style} data-on={on || undefined}>
      <span className="hero-dot" style={{ background: band.color }} />
      <span>{pin.name}</span>
      <span className="hero-chip-value">
        I {index} · {band.label.toLowerCase()}
      </span>
    </span>
  );
}

function ExampleCard({ pin, on }: { pin: HeroPin; on: boolean }) {
  const { index, band } = pinRisk(pin);
  const style: Vars = { "--left": pct(pin.placement.x), "--top": pct(pin.placement.y) };
  return (
    <span className="hero-card" style={style} data-on={on || undefined}>
      <span className="hero-card-head">
        <span className="hero-card-name">
          <span className="hero-dot" style={{ background: band.color }} />
          {pin.name}
        </span>
        <span className="hero-card-band" style={{ "--c": band.color } as Vars}>
          {band.label}
        </span>
      </span>
      {pin.hazard ? <span className="hero-card-hazard">Esempio · {pin.hazard.toLowerCase()}</span> : null}
      <span className="hero-card-formula">
        <span>
          I = 2·{pin.danno} + {pin.probabilita} = {index}
        </span>
        <span className="hero-card-dp">
          D {pin.danno} · P {pin.probabilita}
        </span>
      </span>
      <span className="hero-card-scale">
        {Array.from({ length: 10 }, (_, i) => i + 3).map((value, i) => (
          <span
            key={value}
            data-hit={value === index || undefined}
            data-band={riskBand(value).key}
            style={{ "--i": i } as Vars}
          />
        ))}
      </span>
    </span>
  );
}
