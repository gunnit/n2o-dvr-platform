"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import {
  DANNO_LABELS,
  PROBABILITA_LABELS,
  SCALE,
  riskBand,
  riskIndex,
  type ScaleValue,
} from "@/components/landing/risk";
import { useSkipMotion } from "@/components/landing/use-skip-motion";

/**
 * "Prova l'indice": two radio groups set D and P, and a model of the 4×4
 * matrix — one block per combination, as tall as its index — shows where the
 * pair lands. The radios are the control; the blocks are a picture of the
 * same state (aria-hidden), clickable as a shortcut for a pointer.
 *
 * Starts on D 4 · P 2, the welding example in the hero, so the two agree.
 * Pure CSS 3D: no WebGL, nothing to load, and it stays sharp at any zoom.
 */

type Vars = CSSProperties & { [name: `--${string}`]: string | number };

const CELLS = SCALE.flatMap((danno) =>
  SCALE.map((probabilita) => {
    const index = riskIndex(danno, probabilita);
    return { danno, probabilita, index, band: riskBand(index) };
  }),
);

export function RiskMatrix() {
  const [danno, setDanno] = useState<ScaleValue>(4);
  const [probabilita, setProbabilita] = useState<ScaleValue>(2);
  const [entered, setEntered] = useState(false);
  const modelRef = useRef<HTMLDivElement>(null);
  // Reduced motion or no IntersectionObserver: the blocks simply stand.
  const skipMotion = useSkipMotion();
  const risen = skipMotion || entered;

  const index = riskIndex(danno, probabilita);
  const band = riskBand(index);

  // Blocks rise the first time the model scrolls into view; globals.css keeps
  // them standing when there is no script or motion is reduced.
  useEffect(() => {
    const el = modelRef.current;
    if (skipMotion || !el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        setEntered(true);
        observer.disconnect();
      },
      { threshold: 0.35 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [skipMotion]);

  return (
    <div className="grid items-center gap-10 lg:grid-cols-[minmax(0,440px)_minmax(0,1fr)] lg:gap-16">
      <div>
        <p className="font-plex text-[12px] text-[#003d74]">Indice di rischio · I = 2·D + P</p>
        <h3 className="mt-3 font-heading text-[26px] leading-[1.15] font-light tracking-[-0.025em] text-[#061b31] sm:text-[30px]">
          Prova il calcolo che firmerai.
        </h3>
        <p className="mt-3.5 text-[15px] leading-[1.6] text-pretty text-[#64748d]">
          Il danno pesa il doppio della probabilità. Scegli i due valori: l&apos;indice,
          il livello e la tempistica sono quelli che la piattaforma scrive nel DVR.
        </p>

        <Scale
          legend="Danno (D)"
          name="danno"
          labels={DANNO_LABELS}
          value={danno}
          onChange={setDanno}
        />
        <Scale
          legend="Probabilità (P)"
          name="probabilita"
          labels={PROBABILITA_LABELS}
          value={probabilita}
          onChange={setProbabilita}
        />

        <output
          aria-live="polite"
          className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-[#e5edf5] pt-5"
        >
          <span className="font-plex text-[18px] text-[#061b31] tnum sm:text-[20px]">
            I = 2·{danno} + {probabilita} = <strong className="font-medium">{index}</strong>
          </span>
          <span className="inline-flex items-center gap-2 rounded-[4px] border border-[#e5edf5] bg-white px-2 py-1 text-[13px] font-medium text-[#061b31]">
            <span aria-hidden className="size-2.5 rounded-full" style={{ background: band.color }} />
            {band.label}
          </span>
          <span className="text-[13.5px] text-[#64748d]">{band.timeframe}</span>
        </output>
      </div>

      <div
        ref={modelRef}
        aria-hidden
        className="risk-model"
        data-risen={risen || undefined}
      >
        <div className="risk-plane">
          <span className="risk-base" />
          {CELLS.map((cell) => {
            const selected = cell.danno === danno && cell.probabilita === probabilita;
            const style: Vars = {
              "--d": cell.danno,
              "--p": cell.probabilita,
              "--h": cell.index,
              "--top": cell.band.color,
            };
            return (
              <span
                key={`${cell.danno}-${cell.probabilita}`}
                className="risk-block"
                style={style}
                data-selected={selected || undefined}
                onClick={() => {
                  setDanno(cell.danno);
                  setProbabilita(cell.probabilita);
                }}
              >
                <span className="risk-face risk-face-west" />
                <span className="risk-face risk-face-south" />
                <span className="risk-face risk-face-top" />
              </span>
            );
          })}
        </div>
        <span className="risk-axis risk-axis-d">↖ Danno</span>
        <span className="risk-axis risk-axis-p">Probabilità ↗</span>
      </div>
    </div>
  );
}

function Scale({
  legend,
  name,
  labels,
  value,
  onChange,
}: {
  legend: string;
  name: string;
  labels: Record<ScaleValue, string>;
  value: ScaleValue;
  onChange: (value: ScaleValue) => void;
}) {
  return (
    <fieldset className="mt-6">
      <legend className="text-[13px] font-medium text-[#273951]">{legend}</legend>
      <div className="mt-2.5 grid grid-cols-2 gap-1.5 sm:grid-cols-4">
        {SCALE.map((n) => (
          <label key={n} className="risk-option">
            <input
              type="radio"
              name={name}
              value={n}
              checked={value === n}
              onChange={() => onChange(n)}
              className="sr-only"
            />
            <span className="font-plex text-[15px] tnum">{n}</span>
            <span className="text-[11.5px] leading-tight">{labels[n]}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
