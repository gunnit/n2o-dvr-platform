/**
 * The app's semantic colour vocabulary — one definition, two densities.
 *
 * Before this file, "warning" was spelled `amber-50/amber-300/amber-900` in the
 * callouts, `amber-100/amber-800` in the badges, `yellow-100/yellow-800` in the
 * risk chips and `#9b6829` in `status-map.ts` — four different yellows for one
 * meaning, none of them the theme's `--color-warning`. Tailwind's default
 * palette is not this project's palette (DESIGN.md §0), so the hues live here
 * and nowhere else.
 *
 * Two tiers, because tint density drives text contrast:
 *
 * - `TONE_SURFACE` — large boxes (Callout, panels). ~5% tint, so the mid-weight
 *   text colour still clears AA.
 * - `TONE_CHIP` — badges and pills. ~10-14% tint so a 22px pill reads as a
 *   filled object at a glance, which forces a darker text colour.
 *
 * Every pairing below is measured against white at ≥4.9:1, so an 11px badge
 * label passes WCAG AA — worth re-checking if you change a value, since the
 * chip tier has very little headroom.
 *
 * Tailwind needs literal class strings, so these are spelled out rather than
 * composed from `TONE_SOLID`.
 */

export type Tone = "neutral" | "info" | "success" | "warning" | "danger" | "ai";

/** The pure hue for bars, dots and progress fills — no tint, no text duty. */
export const TONE_SOLID: Record<Tone, string> = {
  neutral: "#64748d",
  info: "#1b5594",
  success: "#15be53",
  warning: "#f59e0b",
  danger: "#ef4444",
  ai: "#7c3aed",
};

/** Callout / panel tier: ~5% wash under a hairline. */
export const TONE_SURFACE: Record<Tone, string> = {
  neutral: "border-[#e5edf5] bg-[#f6f9fc] text-[#273951]",
  info: "border-[rgba(27,85,148,0.24)] bg-[rgba(27,85,148,0.045)] text-[#1b5594]",
  success: "border-[rgba(16,140,61,0.26)] bg-[rgba(16,140,61,0.05)] text-[#0f7a37]",
  warning: "border-[rgba(155,104,41,0.26)] bg-[rgba(155,104,41,0.05)] text-[#8a5c23]",
  danger: "border-[rgba(199,42,58,0.28)] bg-[rgba(199,42,58,0.05)] text-[#c72a3a]",
  ai: "border-[rgba(124,58,237,0.24)] bg-[rgba(124,58,237,0.05)] text-[#5b21b6]",
};

/**
 * Four-step severity ramp, low → critical.
 *
 * Distinct from `TONE_CHIP` because a ramp needs four *ordered* steps, not four
 * unrelated meanings — and green→amber→orange→red is the ordering a reader
 * already knows. Two domains ride on it: the risk index (`lib/ui/risk`) and
 * improvement-measure priority. Text darkens as tint deepens so every step
 * clears AA at badge size.
 */
export const SCALE_CHIP = [
  "border-[rgba(21,190,83,0.32)] bg-[rgba(21,190,83,0.16)] text-[#0c6b2f]",
  "border-[rgba(245,158,11,0.34)] bg-[rgba(245,158,11,0.18)] text-[#8a5c23]",
  "border-[rgba(249,115,22,0.32)] bg-[rgba(249,115,22,0.16)] text-[#9a3d0a]",
  "border-[rgba(239,68,68,0.32)] bg-[rgba(239,68,68,0.16)] text-[#b01e2e]",
] as const;

/** Solid fills for the same ramp — meter bars, legend dots, no text on top. */
export const SCALE_BAR = [
  "bg-[#15be53]",
  "bg-[#f59e0b]",
  "bg-[#f97316]",
  "bg-[#ef4444]",
] as const;

/**
 * The assessment forms' band pill (basso / medio / alto, allegato A / B / C).
 *
 * Ring-based rather than bordered because that is how those forms already build
 * the pill — the caller supplies `ring-1` and this supplies the colour, so the
 * swap is hue-only. Same three hues as `SCALE_CHIP` steps 0/1/3, so a MEDIO
 * band and a MODESTO risk are the same yellow rather than two near-misses.
 */
export const BAND_RING = {
  low: "bg-[rgba(21,190,83,0.16)] text-[#0c6b2f] ring-[rgba(21,190,83,0.34)]",
  mid: "bg-[rgba(245,158,11,0.18)] text-[#8a5c23] ring-[rgba(245,158,11,0.36)]",
  high: "bg-[rgba(239,68,68,0.16)] text-[#b01e2e] ring-[rgba(239,68,68,0.34)]",
} as const;

/** Badge / pill tier: denser fill, darker label. */
export const TONE_CHIP: Record<Tone, string> = {
  neutral: "border-[#e5edf5] bg-[#f6f9fc] text-[#273951]",
  info: "border-[rgba(27,85,148,0.28)] bg-[rgba(27,85,148,0.1)] text-[#1b5594]",
  success: "border-[rgba(16,140,61,0.3)] bg-[rgba(16,140,61,0.14)] text-[#0c6b2f]",
  warning: "border-[rgba(155,104,41,0.3)] bg-[rgba(155,104,41,0.12)] text-[#8a5c23]",
  danger: "border-[rgba(199,42,58,0.3)] bg-[rgba(199,42,58,0.1)] text-[#b01e2e]",
  ai: "border-[rgba(124,58,237,0.26)] bg-[rgba(124,58,237,0.1)] text-[#5b21b6]",
};
