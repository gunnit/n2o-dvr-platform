/**
 * Italian Codice Fiscale parser (frontend mirror).
 *
 * Mirrors `backend/app/services/codice_fiscale.py` so the MMC form can
 * auto-derive a worker's age band from their CF without a server round-trip.
 * Keep the two implementations in sync — there's a unit test for the
 * backend; the frontend logic is intentionally simple.
 *
 * CF format: SSS NNN YY M DD CCCC X (16 chars).
 * Returns `null` on any malformed input — callers decide how to handle.
 */

const MONTH_LETTERS: Record<string, number> = {
  A: 1, // gennaio
  B: 2, // febbraio
  C: 3, // marzo
  D: 4, // aprile
  E: 5, // maggio
  H: 6, // giugno
  L: 7, // luglio
  M: 8, // agosto
  P: 9, // settembre
  R: 10, // ottobre
  S: 11, // novembre
  T: 12, // dicembre
};

const FEMALE_DAY_OFFSET = 40;

function normalize(cf: string | null | undefined): string | null {
  if (typeof cf !== "string") return null;
  const s = cf.trim().toUpperCase();
  if (s.length !== 16) return null;
  return s;
}

export function extractBirthDate(
  cf: string | null | undefined,
  today: Date = new Date(),
): Date | null {
  const s = normalize(cf);
  if (!s) return null;

  const yearStr = s.slice(6, 8);
  const monthLetter = s.slice(8, 9);
  const dayStr = s.slice(9, 11);

  if (!/^\d{2}$/.test(yearStr) || !/^\d{2}$/.test(dayStr)) return null;
  const month = MONTH_LETTERS[monthLetter];
  if (!month) return null;

  const yy = parseInt(yearStr, 10);
  let day = parseInt(dayStr, 10);
  if (day > FEMALE_DAY_OFFSET) day -= FEMALE_DAY_OFFSET;
  if (day < 1 || day > 31) return null;

  // Century disambiguation: prefer 2000+ when within 5y of today; else 1900+.
  const candidate2000 = 2000 + yy;
  const year = candidate2000 <= today.getFullYear() + 5 ? candidate2000 : 1900 + yy;

  const d = new Date(year, month - 1, day);
  // JS Date silently rolls over invalid days (Feb 30 → Mar 2). Reject those.
  if (
    d.getFullYear() !== year ||
    d.getMonth() !== month - 1 ||
    d.getDate() !== day
  ) {
    return null;
  }
  return d;
}

export function extractAge(
  cf: string | null | undefined,
  today: Date = new Date(),
): number | null {
  const bd = extractBirthDate(cf, today);
  if (!bd) return null;
  let years = today.getFullYear() - bd.getFullYear();
  const monthsDelta = today.getMonth() - bd.getMonth();
  const daysDelta = today.getDate() - bd.getDate();
  if (monthsDelta < 0 || (monthsDelta === 0 && daysDelta < 0)) years -= 1;
  return years < 0 ? null : years;
}

export function extractSex(cf: string | null | undefined): "M" | "F" | null {
  const s = normalize(cf);
  if (!s) return null;
  const dayStr = s.slice(9, 11);
  if (!/^\d{2}$/.test(dayStr)) return null;
  const raw = parseInt(dayStr, 10);
  if (raw > FEMALE_DAY_OFFSET) {
    return raw >= 41 && raw <= 71 ? "F" : null;
  }
  return raw >= 1 && raw <= 31 ? "M" : null;
}

/**
 * Map an age in years to the MMC fascia_eta band.
 * - <=18 → "15-18" (giovane lavoratore, lower CP)
 * - >18  → ">18"  (adulto)
 */
export function fasciaEtaFromAge(age: number): "15-18" | ">18" {
  return age <= 18 ? "15-18" : ">18";
}
