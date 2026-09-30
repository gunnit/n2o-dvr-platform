/**
 * The context the Segnala dialog attaches to a report on the operator's behalf.
 *
 * The operator types the description; the browser supplies everything else.
 * That asymmetry is the point of this module. An over-long user agent or a
 * URL carrying a long query string used to come back as a 422 — the report
 * the operator had just written was refused, and the message they saw blamed
 * the send rather than the metadata they never chose. So each auto-captured
 * field is clamped here, to the same limits the API stores
 * (`PAGE_URL_MAX` / `ROUTE_MAX` / `USER_AGENT_MAX` in
 * `backend/app/api/v1/feedback.py`). Truncated context still triages fine; a
 * lost report does not.
 */

export const PAGE_URL_MAX = 2048;
export const ROUTE_MAX = 512;
export const USER_AGENT_MAX = 512;

export interface FeedbackContext {
  page_url: string | null;
  route: string | null;
  user_agent: string | null;
}

function clamp(value: string | null | undefined, max: number): string | null {
  if (!value) return null;
  return value.length > max ? value.slice(0, max) : value;
}

export function buildFeedbackContext(source: {
  pageUrl?: string | null;
  route?: string | null;
  userAgent?: string | null;
}): FeedbackContext {
  return {
    page_url: clamp(source.pageUrl, PAGE_URL_MAX),
    route: clamp(source.route, ROUTE_MAX),
    user_agent: clamp(source.userAgent, USER_AGENT_MAX),
  };
}

/** Reads the live browser context. Safe to call where `window` is absent. */
export function currentFeedbackContext(route: string | null): FeedbackContext {
  return buildFeedbackContext({
    pageUrl: typeof window !== "undefined" ? window.location.href : null,
    route,
    userAgent: typeof navigator !== "undefined" ? navigator.userAgent : null,
  });
}
