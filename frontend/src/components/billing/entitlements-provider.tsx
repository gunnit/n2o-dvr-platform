"use client";

/**
 * App-wide entitlements, fetched once (MB-5).
 *
 * `useEntitlements()` issues a request per mount. Once the plan badge, the
 * dashboard card, the no-plan banner and the document grid all want to read it,
 * that is four `GET /billing/entitlements` on every navigation. The provider
 * hoists the single fetch to the dashboard layout and hands the same result to
 * every consumer.
 *
 * The fail-open contract is inherited unchanged: on error `entitlements` stays
 * null and consumers must read null as "no information", never as "blocked".
 * The paywall is the server's 402 (INV-5).
 */

import { createContext, useContext, useMemo } from "react";

import { useEntitlements } from "@/hooks/use-entitlements";
import type { Entitlements } from "@/lib/billing";

export type EntitlementsContextValue = {
  entitlements: Entitlements | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

/**
 * Outside a provider the value reads as "still loading, nothing known" — which
 * every consumer renders as nothing at all. That is the safe default: a
 * component that escapes the dashboard layout must not start locking things.
 */
const EntitlementsContext = createContext<EntitlementsContextValue>({
  entitlements: null,
  loading: true,
  error: null,
  refresh: async () => {},
});

export function EntitlementsProvider({ children }: { children: React.ReactNode }) {
  const { entitlements, loading, error, refresh } = useEntitlements();
  const value = useMemo(
    () => ({ entitlements, loading, error, refresh }),
    [entitlements, loading, error, refresh]
  );
  return (
    <EntitlementsContext.Provider value={value}>{children}</EntitlementsContext.Provider>
  );
}

export function useEntitlementsContext(): EntitlementsContextValue {
  return useContext(EntitlementsContext);
}
