"use client";

import { useEffect, useRef, useState } from "react";
import { useSkipMotion } from "@/components/landing/use-skip-motion";

export type Sheet = {
  code: string;
  kind: string;
  title: string;
  norm: string;
  footer: string;
  /** Skeleton bar widths, as percentages. `null` renders the 8-cell grid. */
  bars: number[] | null;
  /** The DVR sheet alone carries the four risk-level dots. */
  riskDots?: boolean;
};

/** The 17 documents, in the order the fascicolo is assembled. */
export const SHEETS: Sheet[] = [
  {
    code: "DVR",
    kind: "Principale",
    title: "Documento di Valutazione dei Rischi",
    norm: "D.Lgs. 81/2008 · art. 28",
    footer: "I = 2·D + P",
    bars: [100, 82, 64],
    riskDots: true,
  },
  {
    code: "MMC",
    kind: "Allegato",
    title: "Movimentazione manuale dei carichi",
    norm: "UNI EN ISO 11228 · NIOSH",
    footer: "PLR = CP·A·B·C·D·E·F",
    bars: [100, 72],
  },
  {
    code: "VDT",
    kind: "Allegato",
    title: "Videoterminali",
    norm: "D.Lgs. 81/2008 · art. 173–179",
    footer: "soglia 20 h / sett.",
    bars: [100, 58],
  },
  {
    code: "STRESS",
    kind: "Allegato",
    title: "Stress lavoro-correlato",
    norm: "Checklist INAIL · 76 indicatori",
    footer: "eventi sentinella · contenuto · contesto",
    bars: [100, 88, 41],
  },
  {
    code: "GESTANTI",
    kind: "Allegato",
    title: "Tutela delle lavoratrici madri",
    norm: "D.Lgs. 151/2001",
    footer: "mansioni · ricollocazione",
    bars: [100, 66],
  },
  {
    code: "INCENDIO",
    kind: "Allegato",
    title: "Rischio incendio",
    norm: "D.M. 3 settembre 2021",
    footer: "INF + SI + PI",
    bars: [100, 75],
  },
  {
    code: "MICROCLIMA",
    kind: "Allegato",
    title: "Comfort termico",
    norm: "UNI EN ISO 7730",
    footer: "PMV · PPD",
    bars: [100, 54],
  },
  {
    code: "CALDO SEVERO",
    kind: "Allegato",
    title: "Ambienti severi caldi",
    norm: "UNI EN ISO 7933",
    footer: "PHS",
    bars: [100, 62],
  },
  {
    code: "BIOLOGICO",
    kind: "Alimentare",
    title: "Rischio biologico — alimentare",
    norm: "D.Lgs. 81/2008 · Titolo X",
    footer: "gruppi 1–4",
    bars: [100, 70],
  },
  {
    code: "BIOLOGICO",
    kind: "Asilo nido",
    title: "Rischio biologico — asilo nido",
    norm: "D.Lgs. 81/2008 · Titolo X",
    footer: "variante di settore",
    bars: [100, 59],
  },
  {
    code: "BIOLOGICO",
    kind: "Odontoiatria",
    title: "Rischio biologico — odontoiatria",
    norm: "D.Lgs. 81/2008 · Titolo X",
    footer: "variante di settore",
    bars: [100, 64],
  },
  {
    code: "PEE",
    kind: "Complementare",
    title: "Piano di Emergenza ed Evacuazione",
    norm: "Aziende private",
    footer: "squadre · planimetrie · vie di esodo",
    bars: [100, 78],
  },
  {
    code: "PEE",
    kind: "Ente pubblico",
    title: "Piano di Emergenza — struttura pubblica",
    norm: "Comuni ed enti",
    footer: "affollamento · presidi",
    bars: [100, 69],
  },
  {
    code: "DUVRI",
    kind: "Complementare",
    title: "Rischi da interferenze",
    norm: "D.Lgs. 81/2008 · art. 26",
    footer: "appalti · costi della sicurezza",
    bars: [100, 73],
  },
  {
    code: "POS",
    kind: "Cantieri",
    title: "Piano Operativo di Sicurezza",
    norm: "D.Lgs. 81/2008 · Titolo IV",
    footer: "fasi di lavorazione · DPI",
    bars: [100, 85, 47],
  },
  {
    code: "HACCP",
    kind: "Alimentare",
    title: "Manuale di autocontrollo",
    norm: "Reg. CE 852/2004",
    footer: "7 principi · CCP",
    bars: [100, 80],
  },
  {
    code: "HACCP · SCHEDE",
    kind: "Modulistica",
    title: "16 schede operative HACCP",
    norm: "Registrazioni di autocontrollo",
    footer: "temperature · sanificazione · fornitori",
    bars: null,
  },
];

const RISK_DOTS = ["#15be53", "#f59e0b", "#f97316", "#ef4444"];

/** Depth, in px, between consecutive sheets in the stack. */
const SPACING = 300;

export type SheetFrame = {
  hidden: boolean;
  transform: string;
  opacity: number;
  zIndex: number;
  blur: number;
};

/**
 * The stack geometry for one scroll position — pure, so it can be tested
 * without a browser (`scripts/check-stack-geometry.mjs`). `progress` is 0..1
 * through the section's scrollable range.
 *
 * The travel window starts slightly before the first sheet and ends past the
 * last so the stack is empty at both ends of the section instead of snapping
 * into and out of existence.
 */
export function computeStackFrame(
  progress: number,
  count: number,
): { frames: SheetFrame[]; active: number } {
  const travel = -0.6 + progress * (count + 0.9);
  const frames: SheetFrame[] = [];

  for (let i = 0; i < count; i++) {
    const d = i - travel;

    if (d > 9.5 || d < -1.6) {
      frames.push({ hidden: true, transform: "", opacity: 0, zIndex: 200 - i, blur: 0 });
      continue;
    }

    const x = Math.sin(i * 1.13) * 74 + d * 16;
    const y = Math.cos(i * 0.71) * 46 + d * 10;
    const rz = Math.sin(i * 0.9) * 2.4;

    let opacity = 1;
    if (d > 5) opacity = Math.max(0, 1 - (d - 5) / 4.2);
    if (d < 0) opacity = Math.max(0, 1 + d / 1.35);

    frames.push({
      hidden: false,
      transform:
        `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0) ` +
        `rotateY(-11deg) rotateX(4deg) rotateZ(${rz.toFixed(2)}deg) ` +
        `translateZ(${(-d * SPACING).toFixed(1)}px)`,
      opacity,
      zIndex: 200 - i,
      blur: d > 3.2 ? Math.min(5, (d - 3.2) * 0.85) : 0,
    });
  }

  return { frames, active: Math.min(count - 1, Math.max(0, Math.round(travel))) };
}

function SheetCard({ sheet }: { sheet: Sheet }) {
  return (
    <div className="rounded-lg border border-white/50 bg-linear-160 from-white to-[#f6f9fc] px-[26px] pt-[26px] pb-[22px] shadow-[rgba(3,3,39,.4)_0px_28px_44px_-22px]">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[11px] tracking-[0.09em] text-[#003d74]">
          {sheet.code}
        </span>
        <span className="text-[10.5px] tracking-[0.08em] text-[#64748d] uppercase">
          {sheet.kind}
        </span>
      </div>
      <p className="mt-4 font-heading text-[19px] leading-[1.22] font-normal tracking-[-0.015em] text-[#061b31]">
        {sheet.title}
      </p>

      {sheet.bars ? (
        <div className="mt-[18px] grid gap-[7px]">
          {sheet.bars.map((width, i) => (
            <div
              key={i}
              className="h-1.5 rounded-[2px]"
              style={{
                width: `${width}%`,
                background: i === 0 ? "#e5edf5" : "#eef2f7",
              }}
            />
          ))}
        </div>
      ) : (
        <div className="mt-[18px] grid grid-cols-4 gap-[5px]">
          {Array.from({ length: 8 }, (_, i) => (
            <div key={i} className="h-3.5 rounded-[2px] bg-[#eef2f7]" />
          ))}
        </div>
      )}

      <div className="mt-5 flex items-center gap-1.5 border-t border-[#e5edf5] pt-3.5">
        {sheet.riskDots &&
          RISK_DOTS.map((color) => (
            <span
              key={color}
              aria-hidden
              className="h-[9px] w-[9px] rounded-full"
              style={{ background: color }}
            />
          ))}
        <span
          className={`font-mono text-[11px] text-[#003d74] ${sheet.riskDots ? "ml-auto" : ""}`}
        >
          {sheet.footer}
        </span>
      </div>
    </div>
  );
}

/**
 * The scroll-scrubbed fascicolo: a 17-deep stack of document sheets flying
 * toward the viewer as the section scrolls, with a running index beside it.
 *
 * Under reduced motion — or before hydration — this degrades to a plain
 * responsive grid of the same 17 cards inside a normal-height section. The
 * tall scroll container is only ever mounted when the animation will actually
 * run, so a viewer who opts out never gets four screens of empty scrolling.
 */
export function FascicoloStack() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const sheetRefs = useRef<(HTMLDivElement | null)[]>([]);
  const skipMotion = useSkipMotion();
  const [active, setActive] = useState(0);

  useEffect(() => {
    if (skipMotion) return;
    const section = sectionRef.current;
    if (!section) return;

    let queued = false;
    const apply = () => {
      queued = false;
      const rect = section.getBoundingClientRect();
      const vh = window.innerHeight;
      const total = section.offsetHeight - vh;
      const progress = Math.min(1, Math.max(0, -rect.top / Math.max(1, total)));
      const { frames, active: nextActive } = computeStackFrame(progress, SHEETS.length);

      for (let i = 0; i < frames.length; i++) {
        const el = sheetRefs.current[i];
        if (!el) continue;
        const frame = frames[i];

        if (frame.hidden) {
          el.style.opacity = "0";
          el.style.visibility = "hidden";
          continue;
        }
        el.style.visibility = "visible";
        el.style.transform = frame.transform;
        el.style.opacity = frame.opacity.toFixed(3);
        el.style.zIndex = String(frame.zIndex);
        el.style.filter = frame.blur ? `blur(${frame.blur.toFixed(2)}px)` : "none";
      }

      setActive(nextActive);
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
  }, [skipMotion]);

  const current = SHEETS[active];

  const intro = (
    <>
      <p className="mb-5 text-[12px] font-medium tracking-[0.16em] text-[#a5c8ff] uppercase">
        Il fascicolo
      </p>
      <h2 className="font-heading text-[clamp(1.9rem,3.2vw,2.6rem)] leading-[1.1] font-light tracking-[-0.028em] text-balance text-white">
        Diciassette documenti, un&apos;unica base dati.
      </h2>
    </>
  );

  if (skipMotion) {
    return (
      <section id="fascicolo" className="dark-section bg-[#061b31] py-24 sm:py-28">
        <div className="mx-auto w-full max-w-[1160px] px-6 sm:px-7">
          {intro}
          <p className="mt-5 max-w-[52ch] text-[15.5px] leading-[1.62] font-light text-white/68">
            Ogni allegato riusa gli stessi ambienti, le stesse persone e le
            stesse attrezzature del sopralluogo. Correggi un dato una volta e
            resta coerente in tutto il fascicolo.
          </p>
          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {SHEETS.map((sheet) => (
              <SheetCard key={`${sheet.code}-${sheet.title}`} sheet={sheet} />
            ))}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section
      id="fascicolo"
      ref={sectionRef}
      className="dark-section relative h-[300vh] bg-[#061b31] md:h-[420vh]"
    >
      <div className="sticky top-0 h-svh overflow-hidden">
        <div
          aria-hidden
          className="absolute inset-0 bg-[radial-gradient(ellipse_70%_60%_at_72%_46%,rgba(27,85,148,.42)_0%,rgba(6,27,49,0)_70%)]"
        />
        <div className="relative mx-auto grid h-full w-full max-w-[1160px] grid-rows-[minmax(240px,40vh)_auto] content-center items-stretch gap-[22px] px-6 pt-[84px] pb-7 sm:px-7 md:grid-cols-[minmax(0,380px)_minmax(0,1fr)] md:grid-rows-1 md:items-center md:gap-10 md:py-0">
          <div className="relative z-3 order-2 md:order-1">
            {intro}
            <p className="mt-5 hidden max-w-[44ch] text-[15.5px] leading-[1.62] font-light text-white/68 md:block">
              Ogni allegato riusa gli stessi ambienti, le stesse persone e le
              stesse attrezzature del sopralluogo. Correggi un dato una volta e
              resta coerente in tutto il fascicolo.
            </p>

            <div className="mt-0 border-t border-white/14 pt-[18px] md:mt-9 md:pt-6">
              <div className="flex items-baseline gap-2.5">
                <span className="tnum font-heading text-[46px] leading-none font-light tracking-[-0.03em] text-white">
                  {String(active + 1).padStart(2, "0")}
                </span>
                <span className="tnum text-[14px] text-white/40">
                  / {SHEETS.length}
                </span>
              </div>
              <p className="mt-3.5 mb-1 text-[16px] font-medium text-white">
                {current.title}
              </p>
              <p className="font-mono text-[12.5px] tracking-[0.02em] text-[#a5c8ff]">
                {current.norm}
              </p>
              <div className="mt-[22px] h-0.5 overflow-hidden rounded-[2px] bg-white/14">
                <div
                  className="h-full rounded-[2px] bg-[#a5c8ff] transition-[width] duration-300"
                  style={{
                    width: `${Math.max(6, ((active + 1) / SHEETS.length) * 100).toFixed(1)}%`,
                  }}
                />
              </div>
            </div>
          </div>

          <div
            aria-hidden
            className="relative order-1 min-h-[240px] md:order-2 md:h-full"
            style={{ perspective: "1250px", perspectiveOrigin: "52% 48%" }}
          >
            {SHEETS.map((sheet, i) => (
              <div
                key={`${sheet.code}-${sheet.title}`}
                ref={(el) => {
                  sheetRefs.current[i] = el;
                }}
                className="absolute top-1/2 left-1/2 -mt-[232px] -ml-[170px] w-[340px]"
                style={{ willChange: "transform, opacity" }}
              >
                <SheetCard sheet={sheet} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
