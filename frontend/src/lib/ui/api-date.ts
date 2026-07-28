/**
 * Parse a timestamp as the API means it (P2-2).
 *
 * The backend stores and returns naive datetimes produced by
 * `datetime.utcnow()`, so they carry no timezone designator:
 *
 *     "2026-07-28T10:12:49.776056"
 *
 * ECMAScript parses that form as **local time**, not UTC. In CEST that made
 * every freshly created record read as two hours old — a document generated a
 * minute ago was labelled "2 ore fa" — and in winter it would have been one
 * hour. The value was never wrong; the reader was.
 *
 * Anything already carrying `Z` or an explicit `±HH:MM` offset is left alone,
 * so this keeps working if the backend later starts emitting aware datetimes.
 */

/** `Z`, `+02:00`, `-0500` … at the very end of the string. */
const HAS_TIMEZONE = /(?:Z|[+-]\d{2}:?\d{2})$/i;

/** Date-only values ("2026-07-28") are calendar dates, not instants. */
const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

export function parseApiDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const raw = value.trim();
  if (!raw) return null;

  const normalized =
    DATE_ONLY.test(raw) || HAS_TIMEZONE.test(raw) ? raw : `${raw}Z`;

  const d = new Date(normalized);
  return Number.isNaN(d.getTime()) ? null : d;
}
