"use client";

import { useMemo } from "react";
import { useSession } from "next-auth/react";

import { vocabularyFor, type TenantVocabulary } from "@/lib/ui/tenant-vocabulary";

/**
 * The right nouns for this tenant's channel (P2-1).
 *
 * Reads `accountType` off the session rather than calling
 * `GET /billing/entitlements`: the claim is already in the JWT, and page
 * headings should not wait on — or disappear because of — a billing request.
 * It only decides wording, so a stale claim costs nothing (INV-3 keeps every
 * actual limit resolving from the database server-side).
 */
export function useTenantVocabulary(): TenantVocabulary {
  const { data: session } = useSession();
  const accountType = (session?.user as { accountType?: string } | undefined)?.accountType;
  return useMemo(() => vocabularyFor(accountType), [accountType]);
}
