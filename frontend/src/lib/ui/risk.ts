import type { LivelloRischio } from "@/types";
import { SCALE_BAR, SCALE_CHIP } from "@/lib/ui/tones";

/**
 * The N2O risk ramp — the one place `I = 2*D + P` turns into a colour.
 *
 * Three copies of this existed: `rischi-editor` and `pericoli-panel` each held
 * an identical green/yellow/orange/red map in Tailwind defaults, while
 * `miglioramento-tab` had already been moved to theme colours but routed GRAVE
 * through the brand navy — which reads as a call-to-action, not a severity, and
 * broke the ramp in the middle. The landing page legend (`app/page.tsx`) is the
 * one that had it right, and its `--color-risk-*` hues are what this encodes.
 *
 * The ramp must stay four visually distinct steps: the colour *is* the reading
 * here, not decoration. Text darkens as the tint deepens so every step clears
 * WCAG AA at badge size (measured ≥5:1); the labels are words as well, so
 * colour is never the only channel.
 */

export const RISK_ORDER: readonly LivelloRischio[] = [
  "ACCETTABILE",
  "MODESTO",
  "GRAVE",
  "GRAVISSIMO",
] as const;

export const RISK_LABEL: Record<LivelloRischio, string> = {
  ACCETTABILE: "Accettabile",
  MODESTO: "Modesto",
  GRAVE: "Grave",
  GRAVISSIMO: "Gravissimo",
};

/** Index band each level covers, for legends. Must match `livelloFor`. */
export const RISK_RANGE: Record<LivelloRischio, string> = {
  ACCETTABILE: "3-4",
  MODESTO: "5-6",
  GRAVE: "7-8",
  GRAVISSIMO: "9-12",
};

/** Tinted pill: fill + hairline + label, sized by the caller. */
export const RISK_CHIP: Record<LivelloRischio, string> = {
  ACCETTABILE: SCALE_CHIP[0],
  MODESTO: SCALE_CHIP[1],
  GRAVE: SCALE_CHIP[2],
  GRAVISSIMO: SCALE_CHIP[3],
};

/** Solid fill for meter bars and legend dots — no text sits on these. */
export const RISK_BAR: Record<LivelloRischio, string> = {
  ACCETTABILE: SCALE_BAR[0],
  MODESTO: SCALE_BAR[1],
  GRAVE: SCALE_BAR[2],
  GRAVISSIMO: SCALE_BAR[3],
};

/**
 * Band thresholds from FORMULAS_AND_CALCULATIONS.md: 3-4 accettabile,
 * 5-6 modesto, 7-8 grave, 9-12 gravissimo.
 */
export function livelloFor(indice: number): LivelloRischio {
  if (indice <= 4) return "ACCETTABILE";
  if (indice <= 6) return "MODESTO";
  if (indice <= 8) return "GRAVE";
  return "GRAVISSIMO";
}
