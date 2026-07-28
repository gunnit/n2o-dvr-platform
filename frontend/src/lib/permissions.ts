/**
 * What the signed-in person may do — the client-side reading of
 * `backend/app/core/permissions.py`.
 *
 * Two rules keep this honest:
 *
 * 1. **The capability strings come from the server**, not from a role map
 *    copied into this file. `/auth/me` returns them, NextAuth stores them on
 *    the session, and everything here just asks "is this string in that list".
 *    A hand-mirrored matrix is the thing that eventually tells a user they can
 *    do something the API then refuses.
 * 2. **Nothing here is a security boundary.** Hiding a button is a courtesy;
 *    the 403 from `require_capability` is the actual rule. Treat a missing
 *    capability as "don't show it", never as "it is safe to skip the check".
 *
 * Sessions minted before this shipped carry no `capabilities`. Rather than
 * locking those users out of their own navigation until they sign in again,
 * `capabilitiesOf` falls back to a role-derived set — deliberately the only
 * place a role name is interpreted on the client.
 */

export const AZIENDE_READ = "aziende:read";
export const AZIENDE_CREATE = "aziende:create";
export const AZIENDE_DELETE = "aziende:delete";
export const SURVEY_WRITE = "survey:write";
export const ASSESSMENTS_WRITE = "assessments:write";
export const DOCUMENTS_READ = "documents:read";
export const DOCUMENTS_GENERATE = "documents:generate";
export const DOCUMENTS_DELETE = "documents:delete";
export const AI_USE = "ai:use";
export const BILLING_READ = "billing:read";
export const BILLING_MANAGE = "billing:manage";
export const USERS_MANAGE = "users:manage";
export const ORG_MANAGE = "org:manage";
export const ADMIN_TOOLS = "admin:tools";

export type Capability = string;

/** Everything an admin holds. Only used by the legacy-session fallback. */
const ALL: Capability[] = [
  AZIENDE_READ,
  AZIENDE_CREATE,
  AZIENDE_DELETE,
  SURVEY_WRITE,
  ASSESSMENTS_WRITE,
  DOCUMENTS_READ,
  DOCUMENTS_GENERATE,
  DOCUMENTS_DELETE,
  AI_USE,
  BILLING_READ,
  BILLING_MANAGE,
  USERS_MANAGE,
  ORG_MANAGE,
  ADMIN_TOOLS,
];

const FIELD: Capability[] = [
  AZIENDE_READ,
  SURVEY_WRITE,
  ASSESSMENTS_WRITE,
  DOCUMENTS_READ,
  AI_USE,
  BILLING_READ,
];

const OFFICE: Capability[] = [...FIELD, DOCUMENTS_GENERATE, DOCUMENTS_DELETE];

/**
 * The pre-`capabilities` fallback, kept in step with the server matrix by
 * `backend/tests/test_permissions.py`, which reads this file.
 */
const LEGACY_ROLE_CAPABILITIES: Record<string, Capability[]> = {
  admin: ALL,
  operatore_ufficio: OFFICE,
  operatore_campo: FIELD,
};

export const ROLE_LABELS: Record<string, string> = {
  admin: "Amministratore",
  operatore_ufficio: "Operatore in ufficio",
  operatore_campo: "Operatore sul campo",
};

export function roleLabel(role: string | null | undefined): string {
  return ROLE_LABELS[role ?? ""] ?? "Operatore";
}

export type SessionLikeUser = {
  role?: string | null;
  capabilities?: string[] | null;
  accountType?: string | null;
} | null | undefined;

/** The capability set for a session user, server-provided where available. */
export function capabilitiesOf(user: SessionLikeUser): ReadonlySet<Capability> {
  if (user?.capabilities?.length) return new Set(user.capabilities);
  // A session issued before `/auth/me` returned capabilities. Unknown roles get
  // the least-privileged set, matching the server's own default.
  return new Set(LEGACY_ROLE_CAPABILITIES[user?.role ?? ""] ?? FIELD);
}

export function can(user: SessionLikeUser, capability: Capability): boolean {
  return capabilitiesOf(user).has(capability);
}

/** True when the user holds every one of `capabilities`. */
export function canAll(user: SessionLikeUser, ...capabilities: Capability[]): boolean {
  const held = capabilitiesOf(user);
  return capabilities.every((c) => held.has(c));
}
