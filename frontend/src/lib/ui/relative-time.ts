import { parseApiDate } from "@/lib/ui/api-date";

export function formatRelative(iso: string | null | undefined): string {
  // Parsed as UTC when the API omits the offset, which it does everywhere —
  // otherwise "adesso" renders as "2 ore fa" in CEST (P2-2).
  const d = parseApiDate(iso);
  if (!d) return "";
  const diffMs = Date.now() - d.getTime();
  const mins = Math.round(diffMs / 60_000);
  // Clock skew between the server and the browser can put a just-created
  // record a few seconds in the future; "fra 1 minuto" would be nonsense.
  if (mins < 1) return "adesso";
  if (mins < 60) return `${mins} min fa`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} ${hrs === 1 ? "ora" : "ore"} fa`;
  const days = Math.round(hrs / 24);
  if (days === 0) return "oggi";
  if (days === 1) return "ieri";
  if (days < 30) return `${days} giorni fa`;
  return d.toLocaleDateString("it-IT", { day: "2-digit", month: "short" });
}
