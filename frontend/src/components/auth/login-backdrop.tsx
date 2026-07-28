"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useReducedMotion } from "framer-motion";

/**
 * The fascicolo the platform composes, in the order the generator builds it.
 * Illustrative only — this panel is the marketing surface of the login screen
 * and never reflects a real account's documents (there is no session yet).
 */
const DOCS = [
  "DVR · Documento di Valutazione dei Rischi",
  "Allegato Rischio Incendio",
  "Allegato Movimentazione Manuale dei Carichi",
  "Allegato Videoterminali",
  "Allegato Stress Lavoro-Correlato",
  "Allegato Rischio Chimico",
  "Allegato Rischio Biologico",
  "Allegato Microclima",
  "Allegato Gestanti e Puerpere",
  "DUVRI · Rischi da Interferenza",
  "POS · Piano Operativo di Sicurezza",
  "PEE · Piano Gestione Emergenze",
  "Manuale HACCP",
];

/** Rows visible in the panel window at any time. */
const WINDOW = 5;

/** Fixed frame used when the visitor prefers reduced motion. */
const STATIC_READY = 4;

function useFascicoloProgress(enabled: boolean) {
  const [ready, setReady] = useState(STATIC_READY);

  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => {
      setReady((r) => (r >= DOCS.length ? 0 : r + 1));
    }, 1000);
    return () => clearInterval(id);
  }, [enabled]);

  return enabled ? ready : STATIC_READY;
}

/**
 * Pointer parallax on the hero photo. Skipped for coarse pointers (no hover to
 * drive it) and when reduced motion is requested.
 */
function usePointerParallax(enabled: boolean) {
  const ref = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (!enabled) return;
    if (!window.matchMedia("(pointer: fine)").matches) return;

    const onMove = (e: PointerEvent) => {
      const img = ref.current;
      if (!img) return;
      const x = (e.clientX / window.innerWidth - 0.5) * -18;
      const y = (e.clientY / window.innerHeight - 0.5) * -12;
      // Keep the overscan scale here rather than in a `scale-*` class: Tailwind
      // v4 emits the standalone `scale` property, which would compound with
      // this transform instead of replacing it.
      img.style.transform = `scale(1.06) translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
    };

    window.addEventListener("pointermove", onMove);
    return () => window.removeEventListener("pointermove", onMove);
  }, [enabled]);

  return ref;
}

function DocRow({
  name,
  state,
}: {
  name: string;
  state: "done" | "active" | "queued";
}) {
  return (
    <div className="grid grid-cols-[16px_minmax(0,1fr)_auto] items-center gap-3 border-t border-white/8 py-2.5">
      {state === "done" && (
        <span className="flex text-[#a5c8ff]">
          <svg width="15" height="15" viewBox="0 0 15 15" aria-hidden>
            <path
              d="M3 7.9 6 10.9 12 3.9"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      )}
      {state === "active" && (
        <span className="ml-[3px] h-[9px] w-[9px] rounded-full bg-white shadow-[0_0_0_4px_rgba(255,255,255,0.16)]" />
      )}
      {state === "queued" && (
        <span className="ml-1 h-[7px] w-[7px] rounded-full border border-white/34" />
      )}

      <span className="truncate text-[13.5px] font-light text-white/90">
        {name}
      </span>

      {state === "done" && (
        <span className="text-[11px] font-medium tracking-[0.1em] text-[#a5c8ff] uppercase">
          pronto
        </span>
      )}
      {state === "active" && (
        <span className="relative block h-[2px] w-14 overflow-hidden rounded-[2px] bg-white/20">
          <span className="auth-sweep absolute inset-y-0 left-0 w-[32%] rounded-[2px] bg-white" />
        </span>
      )}
      {state === "queued" && (
        <span className="text-[11px] tracking-[0.1em] text-white/38 uppercase">
          in coda
        </span>
      )}
    </div>
  );
}

/**
 * Left half of the login split screen: the workshop photo under N2O's navy
 * scrims, the promise headline, and an ambient "fascicolo in composizione"
 * panel. Purely presentational — no auth state reaches it.
 */
export function LoginBackdrop() {
  const reduced = useReducedMotion();
  const animate = !reduced;

  const ready = useFascicoloProgress(animate);
  const photoRef = usePointerParallax(animate);

  const start = Math.max(0, Math.min(ready - 2, DOCS.length - WINDOW));
  const rows = DOCS.slice(start, start + WINDOW).map((name, i) => {
    const idx = start + i;
    return {
      name,
      state: idx < ready ? "done" : idx === ready ? "active" : "queued",
    } as const;
  });

  return (
    <div className="dark-section relative isolate overflow-hidden bg-[#061b31] max-[900px]:min-h-[320px]">
      <div aria-hidden className="auth-ken absolute inset-0 overflow-hidden">
        <Image
          ref={photoRef}
          src="/landing/hero-officina.webp"
          alt=""
          fill
          priority
          sizes="(max-width: 900px) 100vw, 56vw"
          style={{ transform: "scale(1.06)" }}
          className="object-cover will-change-transform"
        />
      </div>

      {/* Navy scrims: horizontal for the seam, vertical for text legibility,
          plus a soft ice-blue centre lift. */}
      <div
        aria-hidden
        className="absolute inset-0 bg-[linear-gradient(102deg,rgba(6,27,49,.9)_0%,rgba(6,27,49,.5)_48%,rgba(6,27,49,.86)_100%)]"
      />
      <div
        aria-hidden
        className="absolute inset-0 bg-[linear-gradient(180deg,rgba(6,27,49,.55)_0%,rgba(6,27,49,.1)_34%,rgba(6,27,49,.92)_100%)]"
      />
      <div
        aria-hidden
        className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_46%,rgba(165,200,255,.1)_0%,rgba(6,27,49,0)_72%)]"
      />

      <div className="relative z-2 flex h-full flex-col justify-between gap-12 px-[46px] pt-9 pb-8 max-[1080px]:px-[30px] max-[1080px]:pt-[30px] max-[1080px]:pb-[26px]">
        <div className="flex items-center justify-between gap-5">
          <Link
            href="/"
            className="font-heading text-[15px] font-light tracking-[0.2em] whitespace-nowrap text-white/92 uppercase transition-colors hover:text-white"
          >
            N2O <span className="opacity-45">·</span> DVR
          </Link>
          <span className="text-[11.5px] font-medium tracking-[0.15em] whitespace-nowrap text-white/50 uppercase">
            Sicurezza sul lavoro
          </span>
        </div>

        <div>
          <p className="landing-rise mb-[22px] text-[11.5px] font-medium tracking-[0.16em] text-[#a5c8ff] uppercase">
            Il tuo ambiente di lavoro
          </p>
          <h2
            className="landing-rise font-heading max-w-[15ch] text-[clamp(2rem,3.4vw,3.05rem)] leading-[1.05] font-light tracking-[-0.035em] text-balance text-white max-[900px]:max-w-none"
            style={{ animationDelay: "70ms" }}
          >
            Il fascicolo è dove l&apos;hai lasciato.
          </h2>
          <p
            className="landing-rise mt-[22px] max-w-[44ch] text-[15.5px] leading-[1.6] font-light text-white/74"
            style={{ animationDelay: "150ms" }}
          >
            Sopralluoghi, valutazioni e documenti restano allineati tra una
            sessione e l&apos;altra. Nessun dato da ricopiare.
          </p>

          <div
            aria-hidden
            className="landing-rise mt-10 max-w-[520px] rounded-lg border border-white/15 bg-white/6 px-5 pt-[18px] pb-1.5 backdrop-blur-[12px] max-[900px]:mt-[26px]"
            style={{ animationDelay: "240ms" }}
          >
            <div className="flex items-baseline justify-between gap-4">
              <p className="text-[11.5px] font-medium tracking-[0.14em] text-white/62 uppercase">
                Fascicolo in composizione
              </p>
              <p className="font-heading tnum text-[14px] tracking-[-0.01em] text-white">
                {String(ready).padStart(2, "0")} / {DOCS.length}
              </p>
            </div>

            <div className="mt-3 h-[2px] overflow-hidden rounded-[2px] bg-white/14">
              <div
                className="h-full rounded-[2px] bg-[#a5c8ff] transition-[width] duration-[800ms] ease-[cubic-bezier(.16,1,.3,1)]"
                style={{ width: `${Math.round((ready / DOCS.length) * 100)}%` }}
              />
            </div>

            <div className="mt-1.5 max-[900px]:hidden">
              {rows.map((row) => (
                <DocRow key={row.name} name={row.name} state={row.state} />
              ))}
            </div>
          </div>
        </div>

        {/* /55 rather than the mock's /45: at 12px the lighter value lands at
            ~4.0:1 on the navy, under AA for this compliance line. */}
        <p className="text-[12px] font-light text-white/55">
          {`© ${new Date().getFullYear()} N2O SRL · Conforme al D.Lgs. 81/2008`}
        </p>
      </div>
    </div>
  );
}
