/**
 * Billing types and helpers (MB-4.6).
 *
 * Mirrors the FastAPI schemas in `backend/app/api/v1/billing.py`. Keep the two
 * in step — the backend is the authority, and every limit shown here is
 * re-checked server-side (INV-5). Nothing in this file gates anything: it
 * renders what the API already decided.
 */

export type Usage = {
  ai_credits_used: number;
  ai_credits_included: number | null;
  ai_credits_overage: number;
  /** null = pooled/unmetered (Enterprise) — show "illimitato", not "0". */
  ai_credits_allowance: number | null;
  ai_credits_remaining: number | null;
  active_companies: number;
  max_companies: number | null;
};

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
