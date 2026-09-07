"use client";

import { AlertTriangle } from "lucide-react";

export interface IncendioVvfBannerProps {
  /**
   * Whether to render the banner. The parent decides based on the max band
   * across all areas (visible iff at least one area is "Alto").
   */
  visible: boolean;
}

/**
 * Red alert shown at the top of the page when ANY area is classified Alto —
 * per US-3.12 the field operator must be made aware that a deeper VV.F.
 * assessment and SCIA obligations per DPR 151/2011 may apply. Icon via
 * Lucide (no emoji in UI).
 *
 * In flow, not sticky: pinned at `top-0` it slid under the app header and
 * over the summary card, and on a phone the two pinned blocks took more than
 * half the viewport (UI/UX audit 2026-09-07, F1). While scrolling, the red
 * "livello massimo: Alto" chip in the summary card carries the signal.
 */
export function IncendioVvfBanner({ visible }: IncendioVvfBannerProps) {
  if (!visible) return null;
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-md border border-[rgba(199,42,58,0.28)] bg-[rgba(199,42,58,0.05)] p-3 text-[#c72a3a] shadow-stripe-ambient"
    >
      <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0" aria-hidden="true" />
      <div>
        <p className="font-medium">Richiesta valutazione approfondita VV.F.</p>
        <p className="text-sm">
          Rischio Alto rilevato in almeno un&apos;area. Attivare un professionista
          antincendio (ex L. 818/1984) e verificare gli obblighi SCIA ai sensi
          del DPR 151/2011.
        </p>
      </div>
    </div>
  );
}
