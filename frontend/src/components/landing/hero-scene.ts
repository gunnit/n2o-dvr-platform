/**
 * Everything the hero needs to know about its scale model, in one place.
 *
 * Coordinates are fractions of the stage, which shows `officina-modello.webp`
 * (1800×1260) uncropped at its own 10:7 aspect, so a fraction of the image is
 * a fraction of the box at every width. The image and its depth map are built
 * from the approved render by scripts/build-hero-depth.py, which removes the
 * baked-in pins (so they can be drawn, and animated, live) and prints the
 * numbers below; re-run it, and update them, if the render changes.
 *
 * The four examples are a worked use of `I = 2·D + P` and must stay
 * arithmetically right: an RSPP reading the hero will check them, and
 * tests/landing-risk.test.mjs does too. No imports, so that test can load
 * this file as it stands.
 */

export const STAGE = { width: 1800, height: 1260 } as const;

type Placement =
  /** Chip above the pin's head; `x` is the chip's left edge. */
  | { kind: "above"; x: number; y: number }
  /** Leader up to `y`, then sideways to a chip ending (`left`) or starting (`right`) at `x`. */
  | { kind: "left" | "right"; x: number; y: number }
  /** Leader down to the worked-example card, whose top-left corner is (`x`, `y`). */
  | { kind: "card"; x: number; y: number };

export type HeroPin = {
  id: string;
  name: string;
  /** Shown on the worked-example card only. */
  hazard?: string;
  danno: number;
  probabilita: number;
  /** Pin head and the point where its stem meets the machine. */
  head: { x: number; y: number };
  base: { x: number; y: number };
  /**
   * Where the scan plane crosses the base, 0..1 along the sweep — when the pin
   * rises. Printed by scripts/build-hero-depth.py, like the DEPTH constants.
   */
  scan: number;
  placement: Placement;
};

export const HERO_PINS: readonly HeroPin[] = [
  {
    id: "tornio",
    name: "Tornio",
    danno: 1,
    probabilita: 2,
    head: { x: 0.2027, y: 0.3048 },
    base: { x: 0.2044, y: 0.3579 },
    scan: 0.293,
    placement: { kind: "above", x: 0.035, y: 0.13 },
  },
  {
    id: "fresatrice",
    name: "Fresatrice",
    danno: 2,
    probabilita: 2,
    head: { x: 0.4026, y: 0.1694 },
    base: { x: 0.4033, y: 0.2159 },
    scan: 0.578,
    placement: { kind: "left", x: 0.39, y: 0 },
  },
  {
    id: "trapano",
    name: "Trapano",
    danno: 2,
    probabilita: 3,
    head: { x: 0.4922, y: 0.1992 },
    base: { x: 0.4922, y: 0.2333 },
    scan: 0.691,
    placement: { kind: "right", x: 0.505, y: 0 },
  },
  {
    id: "saldatura",
    name: "Saldatura",
    hazard: "Fumi e radiazioni ottiche",
    danno: 4,
    probabilita: 2,
    head: { x: 0.6329, y: 0.3711 },
    base: { x: 0.6328, y: 0.4579 },
    scan: 0.71,
    placement: { kind: "card", x: 0.62, y: 0.8 },
  },
];

/**
 * Constants shared by the WebGL renderer (hero-depth-gl.ts). They describe the
 * depth map `officina-profondita.webp` (1 = near), not the screen.
 */
export const DEPTH = {
  /**
   * The scan plane: `s = a·u + b·v + c·depth` is constant along a vertical
   * plane that sweeps along the back wall, so the line climbs walls and
   * machines instead of sliding flat across the picture. Fitted on the floor
   * and the back wall of the depth map.
   */
  scanAxis: [2.403, -0.68, -1.0] as const,
  /** `s` over the model, so the sweep runs 0 → 1 from the lathes to the racks. */
  scanRange: [-0.8007, 1.2223] as const,
  /**
   * The navy floor the model stands on, fitted as
   * `depth ≈ c0·u + c1·v + c2·u·v + c3·v² + c4`. Anything well above it is the
   * model, which keeps the scan off the backdrop without a separate mask.
   */
  ground: [0.0012, 0.5838, 0.0349, 0.3977, -0.0005] as const,
  /** The depth that stays put while the rest parallaxes: mid-floor. */
  focus: 0.5,
} as const;

/** Scan sweep timing; the pins and the card follow it. */
export const SCAN_MS = 2600;
export const CARD_DELAY_MS = 260;

/** Ease-in-out on the sweep, so it settles onto the last machines. */
export function scanEase(t: number): number {
  const c = Math.min(1, Math.max(0, t));
  return c < 0.5 ? 4 * c * c * c : 1 - Math.pow(-2 * c + 2, 3) / 2;
}

/** The sweep starts a little before the model and ends a little past it. */
export const SCAN_FROM = -0.06;
export const SCAN_TO = 1.06;

export function scanAt(t: number): number {
  return SCAN_FROM + (SCAN_TO - SCAN_FROM) * scanEase(t);
}

/** Inverse of `scanAt`, in ms: when the sweep reaches `s`. Bisection — five calls on mount. */
export function msToReach(s: number): number {
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 40; i++) {
    const mid = (lo + hi) / 2;
    if (scanAt(mid) < s) lo = mid;
    else hi = mid;
  }
  return Math.round(hi * SCAN_MS);
}
