const LEGAL_SUFFIX = /^(s\.?r\.?l\.?s?|s\.?p\.?a\.?|s\.?n\.?c\.?|sas|&|di|e)$/i;

export function monogramFor(name: string): string {
  const words = name
    .trim()
    .replace(/["'`]/g, "")
    .split(/\s+/)
    .filter((w) => !LEGAL_SUFFIX.test(w));
  const source = words.length ? words : name.trim().split(/\s+/);
  const letters = source.slice(0, 2).map((w) => w[0] ?? "");
  return letters.join("").toUpperCase() || name.slice(0, 2).toUpperCase() || "?";
}
