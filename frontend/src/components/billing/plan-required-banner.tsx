"use client";

/**
 * The one place the app says "your subscription needs attention" (MB-5).
 *
 * Deliberately narrow: it speaks only about the *subscription*, never about
 * what is blocked. While `enforced` is false the backend still allows every
 * operation, so a banner claiming otherwise would be a lie — hence the wording
 * below is about activating a plan, not about losing access.
 *
 * Dismissal lasts for the browser session (`sessionStorage`). A tenant who has
 * read the message should not have to read it on every route change; a new tab
 * tomorrow is a new chance to notice.
 */

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { X } from "lucide-react";

import { Notice } from "@/components/billing/billing-ui";
import { useEntitlementsContext } from "@/components/billing/entitlements-provider";

const DISMISS_KEY = "n2o.plan-banner.dismissed";

// `sessionStorage` is an external store, so it is read through
// `useSyncExternalStore` rather than copied into state inside an effect: the
// `storage` event never fires in the tab that wrote the value, so the dismissal
// has to notify its own subscribers.
const listeners = new Set<() => void>();

function subscribe(onStoreChange: () => void): () => void {
  listeners.add(onStoreChange);
  return () => {
    listeners.delete(onStoreChange);
  };
}

function isDismissed(): boolean {
  try {
    return window.sessionStorage.getItem(DISMISS_KEY) === "1";
  } catch {
    // Private mode / storage disabled: the banner simply never sticks.
    return false;
  }
}

/** On the server we assume "dismissed" so the banner never flashes in and out. */
function isDismissedOnServer(): boolean {
  return true;
}

function dismiss(): void {
  try {
    window.sessionStorage.setItem(DISMISS_KEY, "1");
  } catch {
    /* nothing to persist to — the click still hides it for this render pass */
  }
  for (const listener of listeners) listener();
}

export function PlanRequiredBanner() {
  const { entitlements, loading } = useEntitlementsContext();
  const pathname = usePathname();
  const dismissed = useSyncExternalStore(subscribe, isDismissed, isDismissedOnServer);

  // `/billing` already states all of this, in more detail and with the plan
  // picker right underneath. Repeating it above the page is noise.
  if (pathname?.startsWith("/billing")) return null;
  if (loading || !entitlements || dismissed) return null;

  const { subscribed, status, enforced } = entitlements;
  if (subscribed && (status === "active" || status === "trialing")) return null;

  const variant =
    status === "canceled"
      ? ({
          tone: "bad",
          title: "Abbonamento non attivo",
          body: "Puoi consultare e scaricare i documenti esistenti.",
          cta: "Rinnova",
        } as const)
      : status === "past_due"
        ? ({
            tone: "warn",
            title: "Pagamento in sospeso",
            body:
              "Un pagamento non è andato a buon fine. PayPal riproverà nei prossimi giorni: nel frattempo mantieni l'accesso completo.",
            cta: "Vedi i dettagli",
          } as const)
        : ({
            tone: "warn",
            title: "Non hai ancora un piano attivo",
            // While the backend runs in shadow mode nothing is actually
            // refused, and telling the customer they cannot generate would be
            // a lie they can disprove with one click.
            body: enforced
              ? "Attiva un abbonamento per generare documenti."
              : "Puoi già usare la piattaforma: attiva un abbonamento per mettere in regola la tua posizione.",
            cta: "Vedi i piani",
          } as const);

  return (
    <Notice tone={variant.tone} className="mb-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p>
          <strong>{variant.title}.</strong> {variant.body}
        </p>
        <div className="flex shrink-0 items-center gap-2">
          <Link
            href="/billing"
            className="inline-flex h-8 items-center rounded-md bg-primary px-3 text-[12.5px] font-semibold text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
          >
            {variant.cta}
          </Link>
          <button
            type="button"
            onClick={dismiss}
            aria-label="Nascondi avviso"
            className="rounded-sm p-1 opacity-60 transition-opacity hover:opacity-100"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </Notice>
  );
}
