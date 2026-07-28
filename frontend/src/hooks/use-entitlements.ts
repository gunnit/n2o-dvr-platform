"use client";

import { useCallback, useEffect, useState } from "react";

import { useApi } from "@/hooks/use-api";
import type { CreditPack, CreditPurchase, Entitlements, Plan } from "@/lib/billing";

/**
 * Load the current organization's entitlements and usage (MB-4.6).
 *
 * Deliberately fails **open**: on any error `entitlements` stays null and
 * callers treat that as "no information", never as "blocked". The paywall is
 * the server's 402 (INV-5); a flaky billing request must not lock an operator
 * out of a DVR they are entitled to generate.
 */
export function useEntitlements() {
  const { apiFetch, isAuthenticated } = useApi();
  const [entitlements, setEntitlements] = useState<Entitlements | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    try {
      setEntitlements(await apiFetch<Entitlements>("/api/v1/billing/entitlements"));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore nel caricamento del piano");
      setEntitlements(null);
    } finally {
      setLoading(false);
    }
  }, [apiFetch, isAuthenticated]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { entitlements, loading, error, refresh };
}

export function usePlans() {
  const { apiFetch, isAuthenticated } = useApi();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    apiFetch<Plan[]>("/api/v1/billing/plans")
      .then((p) => {
        if (!cancelled) setPlans(p);
      })
      .catch(() => {
        // An empty price list renders as "contact us" rather than an error
        // banner — the customer's own plan is unaffected either way.
        if (!cancelled) setPlans([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [apiFetch, isAuthenticated]);

  return { plans, loading };
}

/**
 * The AI credit top-up catalogue and this tenant's past purchases.
 *
 * Same fail-open posture as `useEntitlements`: an error leaves both lists empty
 * and the page renders without the top-up section rather than with an error
 * banner. Nobody is blocked by a price list they cannot see, and the plan meters
 * above it are unaffected.
 */
export function useCreditPacks() {
  const { apiFetch, isAuthenticated } = useApi();
  const [packs, setPacks] = useState<CreditPack[]>([]);
  const [purchases, setPurchases] = useState<CreditPurchase[]>([]);
  const [loading, setLoading] = useState(true);

  // Every state write happens in a `.then` rather than after an `await` in an
  // async body. Same behaviour, but it keeps the writes visibly asynchronous —
  // `react-hooks/set-state-in-effect` flags the awaited form as a cascading
  // render when the effect below calls it on mount.
  //
  // `loading` starts true and only ever falls: a refresh after a purchase
  // should update the numbers in place, not blank the panel the customer is
  // looking at.
  const refresh = useCallback(() => {
    if (!isAuthenticated) return Promise.resolve();
    // Settled, not `all`: a tenant whose purchase history fails to load should
    // still be able to buy, and vice versa.
    return Promise.allSettled([
      apiFetch<CreditPack[]>("/api/v1/billing/credits/packs"),
      apiFetch<CreditPurchase[]>("/api/v1/billing/credits/purchases"),
    ]).then(([packsResult, purchasesResult]) => {
      if (packsResult.status === "fulfilled") setPacks(packsResult.value);
      if (purchasesResult.status === "fulfilled") setPurchases(purchasesResult.value);
      setLoading(false);
    });
  }, [apiFetch, isAuthenticated]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { packs, purchases, loading, refresh };
}

/**
 * Whether the UI should visually gate `tipo` for this tenant.
 *
 * Returns false whenever we cannot be sure — no entitlements loaded, or the
 * backend is still in shadow mode — because showing a lock on something that
 * will actually succeed is worse than showing nothing.
 */
export function isDocTypeGated(ent: Entitlements | null, tipo: string): boolean {
  if (!ent || !ent.enforced) return false;
  if (ent.allowed_doc_types === null) return false;
  return !ent.allowed_doc_types.includes(tipo.toLowerCase());
}
