/**
 * The DVR risk index as the landing page shows it: `I = 2·D + P`.
 *
 * Mirrors `calculate_risk_index` in backend/app/services/risk_calculator.py —
 * the same scales and bands — and the DVR Master's level table
 * (`_RISK_LEVEL_TABLE_ROWS` in document_generator/dvr_master.py) word for
 * word, so a number a visitor plays with on the public page is the number,
 * the action and the deadline the product would print. Not the textbook
 * `P × D`: damage weighs double (see CLAUDE.md).
 */

export const SCALE = [1, 2, 3, 4] as const;
export type ScaleValue = (typeof SCALE)[number];

/** Probabilità, 1–4, labelled as in the risk editor and the DVR Master. */
export const PROBABILITA_LABELS: Record<ScaleValue, string> = {
  1: "Bassa",
  2: "Medio-Bassa",
  3: "Medio-Alta",
  4: "Elevata",
};

/** Danno, 1–4, labelled as the DVR Master prints them (the noun is "danno"). */
export const DANNO_LABELS: Record<ScaleValue, string> = {
  1: "Trascurabile",
  2: "Modesto",
  3: "Notevole",
  4: "Ingente",
};

export type RiskBand = {
  key: "accettabile" | "modesto" | "grave" | "gravissimo";
  label: string;
  min: number;
  max: number;
  /** A theme token from globals.css, so the landing and the app agree. */
  color: string;
  /** "Azione" and "Tempistica", as the DVR's level table prints them. */
  action: string;
  timeframe: string;
};

export const RISK_BANDS: readonly RiskBand[] = [
  {
    key: "accettabile",
    label: "Accettabile",
    min: 3,
    max: 4,
    color: "var(--color-risk-green)",
    action: "Monitoraggio",
    timeframe: "Continuo",
  },
  {
    key: "modesto",
    label: "Modesto",
    min: 5,
    max: 6,
    color: "var(--color-risk-yellow)",
    action: "Strumenti di minimizzazione",
    timeframe: "1 anno",
  },
  {
    key: "grave",
    label: "Grave",
    min: 7,
    max: 8,
    color: "var(--color-risk-orange)",
    action: "Sensibilizzazione + controllo",
    timeframe: "6 mesi",
  },
  {
    key: "gravissimo",
    label: "Gravissimo",
    min: 9,
    max: 12,
    color: "var(--color-risk-red)",
    action: "Ricerca urgente misure",
    timeframe: "Immediatamente",
  },
];

export function isScaleValue(value: number): value is ScaleValue {
  return Number.isInteger(value) && value >= 1 && value <= 4;
}

/**
 * `I = 2·D + P`. Named arguments on purpose: the backend's
 * `calculate_risk_index(p, d)` takes them the other way round.
 * Throws outside the 1–4 scales, as the backend does.
 */
export function riskIndex({ danno, probabilita }: { danno: number; probabilita: number }): number {
  if (!isScaleValue(danno)) throw new RangeError(`Danno (D) must be 1-4, got ${danno}`);
  if (!isScaleValue(probabilita)) {
    throw new RangeError(`Probabilità (P) must be 1-4, got ${probabilita}`);
  }
  return 2 * danno + probabilita;
}

export function riskBand(index: number): RiskBand {
  const band = RISK_BANDS.find((b) => index >= b.min && index <= b.max);
  if (!band) throw new RangeError(`Risk index must be 3-12, got ${index}`);
  return band;
}
