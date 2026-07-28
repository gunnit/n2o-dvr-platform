/**
 * Billing types and helpers (MB-4.6).
 *
 * Mirrors the FastAPI schemas in `backend/app/api/v1/billing.py`. Keep the two
 * in step — the backend is the authority, and every limit shown here is
 * re-checked server-side (INV-5). Nothing in this file gates anything: it
 * renders what the API already decided.
 */

/** One row of "where did this period's credits go". */
export type UsageKind = {
  /** 'reasoning' | 'vision' | 'sds' | 'visura' — see CREDIT_KIND_LABELS. */
  kind: string;
  actions: number;
  credits: number;
};

export type Usage = {
  ai_credits_used: number;
  ai_credits_included: number | null;
  ai_credits_overage: number;
  /** null = pooled/unmetered (Enterprise) — show "illimitato", not "0". */
  ai_credits_allowance: number | null;
  ai_credits_remaining: number | null;
  active_companies: number;
  max_companies: number | null;
  /** Ordered by credits descending. Empty until the tenant spends something. */
  by_kind?: UsageKind[];
};

/**
 * What each metered AI action is, in the operator's words.
 *
 * The wire values are the backend's `CREDIT_WEIGHTS` keys. An unknown kind
 * falls through to the raw string rather than being dropped: a new action type
 * showing up unlabelled is a cosmetic bug, whereas silently omitting it from
 * the breakdown makes the numbers not add up.
 */
export const CREDIT_KIND_LABELS: Record<string, string> = {
  reasoning: "Suggerimenti AI (rischi, misure, DPI)",
  vision: "Riconoscimento attrezzature da foto",
  sds: "Estrazione schede di sicurezza",
  visura: "Visura camerale / Registro Imprese",
};

export function creditKindLabel(kind: string): string {
  return CREDIT_KIND_LABELS[kind] ?? kind;
}

export type Entitlements = {
  account_type: string;
  /** null = never purchased a plan. Render a call to action, not a code. */
  plan_code: string | null;
  /** `none` = no subscription row at all; the other four mirror the DB. */
  status: "none" | "trialing" | "active" | "past_due" | "canceled";
  is_active: boolean;
  /**
   * False = never bought anything. Distinct from `is_active`, which is also
   * false once a subscription lapses — "attiva un piano" vs "rinnova".
   */
  subscribed: boolean;
  /** null = all 17 document types. */
  allowed_doc_types: string[] | null;
  seats: number;
  max_companies: number | null;
  max_sites: number | null;
  ai_credits_year: number | null;
  features: Record<string, unknown>;
  period_start: string | null;
  period_end: string | null;
  /**
   * Whether the paywall actually bites yet. While false the backend runs in
   * shadow mode and allows everything, so the UI must not tell anyone an
   * action is blocked — it would be lying.
   */
  enforced: boolean;
  usage: Usage;
};

export type Plan = {
  plan_code: string;
  model: string;
  display_name: string;
  price_year_cents: number;
  seats: number;
  max_companies: number | null;
  max_sites: number | null;
  ai_credits_year: number | null;
  features: Record<string, unknown>;
};

/** An AI credit top-up on offer. Mirrors `backend/app/billing/credit_packs.py`. */
export type CreditPack = {
  pack_code: string;
  display_name: string;
  credits: number;
  price_cents: number;
  description: string;
  /** Cents per credit — the bulk discount, already computed server-side. */
  price_per_credit_cents: number;
  recommended: boolean;
};

/** A top-up receipt. `pending` means checkout was started but never paid. */
export type CreditPurchase = {
  id: string;
  pack_code: string;
  display_name: string;
  credits: number;
  amount_cents: number;
  currency: string;
  status: "pending" | "completed" | "failed";
  period_start: string;
  created_at: string;
  completed_at: string | null;
};

export const PURCHASE_STATUS_LABELS: Record<CreditPurchase["status"], string> = {
  pending: "In attesa di pagamento",
  completed: "Completato",
  failed: "Non completato",
};

/** 149000 → "€ 1.490" — annual list price, IVA esclusa. */
export function formatEuro(cents: number): string {
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 0,
    maximumFractionDigits: cents % 100 === 0 ? 0 : 2,
  }).format(cents / 100);
}

/** null means unlimited everywhere in the plan catalogue. */
export function formatLimit(value: number | null): string {
  return value === null ? "illimitato" : String(value);
}

export const STATUS_LABELS: Record<Entitlements["status"], string> = {
  none: "Nessun piano attivo",
  trialing: "In attivazione",
  active: "Attivo",
  past_due: "Pagamento in sospeso",
  canceled: "Non attivo",
};

/**
 * Tone for the status badge. `past_due` is deliberately a warning and not an
 * error: the customer still has full access while PayPal retries, and telling
 * them they are cut off when they are not causes support calls.
 */
export const STATUS_TONE: Record<Entitlements["status"], "ok" | "warn" | "bad"> = {
  // Neutral-warning, not error: a tenant who has just signed up has done
  // nothing wrong, and while ENTITLEMENTS_ENFORCE is off nothing is blocked.
  none: "warn",
  trialing: "warn",
  active: "ok",
  past_due: "warn",
  canceled: "bad",
};

/**
 * Seat counts come from the plan catalogue, except in the INV-1 data-gap
 * fallback which reports `2**31-1` to mean "do not block anybody". That
 * sentinel must never reach the customer as a literal.
 */
const UNLIMITED_SEATS_SENTINEL = 2 ** 31 - 1;

export function formatSeats(seats: number): string {
  return seats >= UNLIMITED_SEATS_SENTINEL ? "illimitati" : String(seats);
}

export function creditsPercent(usage: Usage): number | null {
  if (usage.ai_credits_allowance === null || usage.ai_credits_allowance === 0) return null;
  return Math.min(100, Math.round((usage.ai_credits_used / usage.ai_credits_allowance) * 100));
}

export function companiesPercent(usage: Usage): number | null {
  if (usage.max_companies === null || usage.max_companies === 0) return null;
  return Math.min(100, Math.round((usage.active_companies / usage.max_companies) * 100));
}

export function formatPeriodEnd(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" });
}

/** "28 lug 2026, 14:32" — for receipts, where the time distinguishes retries. */
export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("it-IT", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Options for `NUMBER_FORMAT`, widened by hand.
 *
 * `minimumGroupingDigits` is ES2023 Intl and this project's TypeScript lib
 * still types `NumberFormatOptions` without it, so the literal is declared
 * against an extended type rather than cast — a cast would also silence a
 * genuine typo in one of the neighbouring keys.
 */
const GROUPED_IT: Intl.NumberFormatOptions & { minimumGroupingDigits?: number } = {
  useGrouping: true,
  // Italian CLDR sets this to 2, so a bare it-IT formatter renders 2000 as
  // "2000" but 10000 as "10.000". Every credit figure written down elsewhere —
  // the pack names from the catalogue ("2.000 crediti"), `docs/pricing`, the
  // public price list — groups from four digits, and the mismatch surfaced as a
  // card titled "2.000 crediti" above a button reading "Acquista 2000 crediti".
  minimumGroupingDigits: 1,
};

// Constructing an Intl formatter is not free and this runs once per figure on
// a screen full of them.
const NUMBER_FORMAT = new Intl.NumberFormat("it-IT", GROUPED_IT);

/** 1240 → "1.240". Thousands separators make four-digit balances readable. */
export function formatNumber(value: number): string {
  return NUMBER_FORMAT.format(value);
}

/**
 * How worried the credit tracker should look.
 *
 * Thresholds match the meters everywhere else — amber at 75%, red at 90% — and
 * exist so an operator learns about the ceiling before they hit it rather than
 * as a 402 halfway through a batch.
 */
export type MeterTone = "ok" | "warn" | "bad";

export function meterTone(percent: number | null): MeterTone {
  if (percent === null) return "ok";
  if (percent >= 90) return "bad";
  if (percent >= 75) return "warn";
  return "ok";
}

/**
 * Whether the tenant should be nudged to top up.
 *
 * Only ever true for a metered plan that is actually running out — pooled
 * (Enterprise) plans have no ceiling, and a tenant at 10% does not need to be
 * sold anything.
 */
export function shouldSuggestTopUp(usage: Usage): boolean {
  const percent = creditsPercent(usage);
  return percent !== null && percent >= 75;
}
