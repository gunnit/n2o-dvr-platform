export type ScadenzaTone = "ok" | "warn" | "danger" | "muted";

export type ScadenzaInfo = {
  label: string;
  tone: ScadenzaTone;
  diffDays: number;
};

export function formatScadenza(iso: string | null | undefined): ScadenzaInfo | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(d);
  target.setHours(0, 0, 0, 0);
  const diffDays = Math.round((target.getTime() - today.getTime()) / 86_400_000);

  const label = target.toLocaleDateString("it-IT", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  if (diffDays < 0) return { label: "Scaduto", tone: "danger", diffDays };
  if (diffDays <= 30) return { label, tone: "warn", diffDays };
  if (diffDays <= 180) return { label, tone: "ok", diffDays };
  return { label, tone: "muted", diffDays };
}

export const SCADENZA_TONE_CLASS: Record<ScadenzaTone, string> = {
  danger: "text-[#ba1a1a]",
  warn: "text-[#9b6829]",
  ok: "text-[#108c3d]",
  muted: "text-[#64748d]",
};
