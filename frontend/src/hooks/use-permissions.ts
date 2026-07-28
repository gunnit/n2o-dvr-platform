"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";

import { useApi } from "@/hooks/use-api";
import {
  type Capability,
  type SessionLikeUser,
  capabilitiesOf,
  roleLabel,
} from "@/lib/permissions";
import { type AccountType } from "@/lib/ui/tenant-vocabulary";

export type Permissions = {
  /** Every capability the signed-in person holds. */
  capabilities: ReadonlySet<Capability>;
  can: (capability: Capability) => boolean;
  role: string | null;
  /** "Operatore in ufficio" — never the raw `operatore_ufficio`. */
  roleLabel: string;
  accountType: AccountType;
  /** Model B: the tenant documents itself rather than a client portfolio. */
  isDirect: boolean;
  /** Still resolving the session; render nothing rather than a wrong shell. */
  loading: boolean;
};

/**
 * Role-derived visibility for the current user.
 *
 * Pairs with `useEntitlementsContext`, which answers the *other* question — what
 * the organization bought. Both can hide the same button for entirely different
 * reasons, and the copy differs accordingly: "il tuo ruolo non lo consente"
 * versus "il tuo piano non lo include".
 */
export function usePermissions(): Permissions {
  const { data: session, status } = useSession();

  return useMemo(() => {
    const user = session?.user as SessionLikeUser & { roleLabel?: string | null };
    const capabilities = capabilitiesOf(user);
    const accountType: AccountType =
      user?.accountType === "direct" ? "direct" : "consultant";

    return {
      capabilities,
      can: (capability: Capability) => capabilities.has(capability),
      role: user?.role ?? null,
      roleLabel: user?.roleLabel || roleLabel(user?.role),
      accountType,
      isDirect: accountType === "direct",
      loading: status === "loading",
    };
  }, [session, status]);
}

/** One assignable role, as `GET /users/roles` describes it. */
export type RoleDefinition = {
  role: string;
  label: string;
  description: string;
  capabilities: string[];
};

/**
 * The assignable roles and what each one may do, straight from the server.
 *
 * Fetched rather than hardcoded so the "chi può fare cosa" table an admin reads
 * before assigning a role is generated from the matrix the API actually
 * enforces. A local copy would be a description of permissions that silently
 * stops being true the first time the matrix changes.
 *
 * Fails to an empty list, which callers render as "fall back to the plain role
 * picker" — losing the explanatory table is a much smaller problem than
 * blocking user management on it.
 */
export function useRoles() {
  const { apiFetch, isAuthenticated } = useApi();
  const [roles, setRoles] = useState<RoleDefinition[]>([]);

  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    apiFetch<RoleDefinition[]>("/api/v1/users/roles")
      .then((r) => {
        if (!cancelled) setRoles(r);
      })
      .catch(() => {
        if (!cancelled) setRoles([]);
      });
    return () => {
      cancelled = true;
    };
  }, [apiFetch, isAuthenticated]);

  return roles;
}
