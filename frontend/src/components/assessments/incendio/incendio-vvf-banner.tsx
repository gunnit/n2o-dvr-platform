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
 * Sticky red banner shown when ANY area is classified Alto — per US-3.12 the
 * field operator must be made aware that a deeper VV.F. assessment and SCIA
 * obligations per DPR 151/2011 may apply. Icon via Lucide (no emoji in UI).
 */
export function IncendioVvfBanner({ visible }: IncendioVvfBannerProps) {
  if (!visible) return null;
  return (
    <div
      role="alert"
      className="sticky top-0 z-20 mb-4 flex items-start gap-3 rounded-md border border-rose-400/60 bg-rose-50 p-3 text-rose-900 shadow-sm dark:border-rose-500/40 dark:bg-rose-950/30 dark:text-rose-100"
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
