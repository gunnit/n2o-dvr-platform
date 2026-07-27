"use client";

import { useCallback, useEffect, useState } from "react";

import { useApi } from "@/hooks/use-api";
import type { Entitlements, Plan } from "@/lib/billing";

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
