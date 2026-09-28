import { getImageProps } from "next/image";

/**
 * The hero's scale model of a workshop, with risk callouts pinned to it.
 *
 * Art-directed through one `<picture>`: a portrait render on phones, the wide
 * render from tablet up. A single `<img>` means the browser fetches exactly one
 * of the two, so it can load eagerly at high priority — it is the hero's LCP.
 *
 * Callouts appear only from `xl`, where `.hero-model` (globals.css) places the
 * full, uncropped wide render. Every coordinate below is in the render's own
 * 1200×679 design units, expressed as a percentage of the box, so the labels
 * stay on their pins at any width. Below `xl` the render is cropped to the
 * model and the legend underneath carries the same information.
 *
 * The four values are a worked example of `I = 2·D + P` and must stay
 * arithmetically right: an RSPP reading the hero will check them.
 */

const W = 1200;
const H = 679;

const x = (v: number) => `${((v / W) * 100).toFixed(2)}%`;
const y = (v: number) => `${((v / H) * 100).toFixed(2)}%`;

/** Pin heads in the wide render, measured from the image itself. */
const PINS = {
  milling: { cx: 731.7, cy: 127.1 },
  drill: { cx: 811, cy: 143.8 },
  lathe: { cx: 552.7, cy: 212.2 },
  welding: { cx: 937.9, cy: 252.5 },
} as const;

/** Leader lines: up (or down) from the pin's ring, then across to its label. */
const LEADERS = [
  `M${PINS.milling.cx} ${PINS.milling.cy - 12} V26 H714`,
  `M${PINS.drill.cx} ${PINS.drill.cy - 12} V26 H830`,
  `M${PINS.lathe.cx} ${PINS.lathe.cy - 12} V134 H536`,
  `M${PINS.welding.cx} ${PINS.welding.cy + 12} V575`,
];

const RISK = {
  accettabile: "#15be53",
  modesto: "#f59e0b",
  grave: "#f97316",
  gravissimo: "#ef4444",
} as const;

/** The 3–12 scale, one cell per value, coloured by band. */
const SCALE = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((value) => ({
  value,
  color:
    value <= 4
      ? RISK.accettabile
      : value <= 6
        ? RISK.modesto
        : value <= 8
          ? RISK.grave
          : RISK.gravissimo,
}));

const LEGEND = [
  { range: "3–4", label: "Accettabile", color: RISK.accettabile },
  { range: "5–6", label: "Modesto", color: RISK.modesto },
  { range: "7–8", label: "Grave", color: RISK.grave },
  { range: "9–12", label: "Gravissimo", color: RISK.gravissimo },
];

const ALT =
  "Modello in scala di un'officina meccanica: spilli colorati segnano i pericoli rilevati sui macchinari, dal verde dell'accettabile al rosso del gravissimo.";

function Chip({
  color,
  name,
  value,
  style,
}: {
  color: string;
  name: string;
  value: string;
  style: React.CSSProperties;
}) {
  return (
    <div
      className="absolute flex h-7 -translate-y-1/2 items-center gap-2 rounded-md border border-white/18 bg-[#061930]/90 px-2.5 font-plex text-[12px] whitespace-nowrap text-white"
      style={style}
    >
      <span className="size-2 rounded-full" style={{ background: color }} />
      <span>{name}</span>
      <span className="text-[#a5c8ff]">{value}</span>
    </div>
  );
}

export function HeroModel() {
  const common = { alt: ALT, sizes: "(min-width: 1280px) 1240px, 100vw" };
  const {
    props: { srcSet: wide },
  } = getImageProps({
    ...common,
    src: "/landing/modello-officina.webp",
    width: 2400,
    height: 1357,
  });
  const {
    props: { srcSet: tall, ...rest },
  } = getImageProps({
    ...common,
    src: "/landing/modello-officina-verticale.webp",
    width: 1200,
    height: 1500,
  });

  return (
    <div className="flex flex-col gap-5">
      {/* Edge to edge below lg: the render's navy is not the section's navy,
          and a box inset in the gutter showed its sides as faint vertical
          seams. At the viewport edges there is nothing to seam against. */}
      <div className="hero-model relative -mx-6 aspect-[4/5] w-[calc(100%+3rem)] sm:-mx-7 sm:w-[calc(100%+3.5rem)] md:aspect-[870/679] lg:mx-0 lg:w-full xl:aspect-[1200/679]">
        <picture>
          <source media="(min-width: 768px)" srcSet={wide} sizes={common.sizes} />
          <img
            {...rest}
            srcSet={tall}
            alt={ALT}
            loading="eager"
            fetchPriority="high"
            className="hero-model-img absolute inset-0 h-full w-full object-cover md:object-right xl:object-center"
          />
        </picture>

        {/* Decorative restatement of what the alt text and the legend say;
            hidden from assistive tech so it is not read twice. */}
        <div aria-hidden className="pointer-events-none absolute inset-0 hidden xl:block">
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="absolute inset-0 h-full w-full overflow-visible"
          >
            <g fill="none" stroke="rgba(255,255,255,0.55)" strokeWidth={1}>
              {LEADERS.map((d) => (
                <path key={d} d={d} vectorEffect="non-scaling-stroke" />
              ))}
            </g>
            <g fill="none" stroke="rgba(255,255,255,0.85)" strokeWidth={1.25}>
              {Object.values(PINS).map((p) => (
                <circle
                  key={`${p.cx}-${p.cy}`}
                  cx={p.cx}
                  cy={p.cy}
                  r={12}
                  vectorEffect="non-scaling-stroke"
                />
              ))}
            </g>
            <g fill="#ffffff">
              <circle cx={714} cy={26} r={2.5} />
              <circle cx={830} cy={26} r={2.5} />
              <circle cx={536} cy={134} r={2.5} />
            </g>
          </svg>

          <Chip
            color={RISK.modesto}
            name="Fresatrice"
            value="I 6 · modesto"
            style={{ right: x(W - 714), top: y(26) }}
          />
          <Chip
            color={RISK.grave}
            name="Trapano"
            value="I 7 · grave"
            style={{ left: x(830), top: y(26) }}
          />
          <Chip
            color={RISK.accettabile}
            name="Tornio"
            value="I 4 · accettabile"
            style={{ right: x(W - 536), top: y(134) }}
          />

          <div
            className="absolute w-[268px] rounded-[10px] border border-white/18 bg-[#061930]/94 px-4 py-3.5 shadow-[0_24px_40px_-20px_rgba(0,0,0,0.6)]"
            style={{ left: x(760), top: y(575) }}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-2">
                <span
                  className="size-[9px] rounded-full"
                  style={{ background: RISK.gravissimo }}
                />
                <span className="text-[14.5px] font-medium text-white">Saldatura</span>
              </span>
              <span className="rounded border border-[#ef4444]/50 bg-[#ef4444]/18 px-1.5 py-0.5 font-plex text-[11px] text-[#ffcdc6]">
                Gravissimo
              </span>
            </div>
            <p className="mt-0.5 text-[12.5px] whitespace-nowrap text-white/66">
              Esempio · fumi e radiazioni ottiche
            </p>
            <div className="mt-3 flex items-baseline justify-between font-plex">
              <span className="text-[13px] text-[#a5c8ff]">I = 2·4 + 2 = 10</span>
              <span className="text-[11px] text-white/60">D 4 · P 2</span>
            </div>
            <div className="mt-2.5 grid grid-cols-10 gap-0.5">
              {SCALE.map((cell) => (
                <span
                  key={cell.value}
                  className="h-2 rounded-[1px]"
                  style={{
                    background: cell.color,
                    opacity: cell.value === 10 ? 1 : 0.35,
                    boxShadow: cell.value === 10 ? "0 0 0 1.5px #ffffff" : undefined,
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Below xl the callouts would not fit; the legend teaches the pin
          colours instead, in text as well as colour. */}
      <div className="xl:hidden">
        <p className="font-plex text-[11.5px] text-white/64">
          Esempio · indice I = 2·D + P su ogni pericolo rilevato
        </p>
        <ul className="mt-2.5 grid grid-cols-2 gap-x-4 gap-y-2 font-plex text-[12px] text-white/84 sm:grid-cols-4">
          {LEGEND.map((level) => (
            <li key={level.label} className="flex items-center gap-2">
              <span
                aria-hidden
                className="size-[9px] rounded-full"
                style={{ background: level.color }}
              />
              {level.range} · {level.label}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
