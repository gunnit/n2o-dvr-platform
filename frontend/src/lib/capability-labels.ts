/**
 * Human names for the capability strings the API hands back.
 *
 * The strings themselves (`documents:generate`) are an internal vocabulary and
 * must never reach an administrator choosing a role for a colleague. Anything
 * unlabelled falls through to the raw value rather than being dropped: an
 * unfamiliar capability appearing in the table is a cosmetic gap, whereas
 * silently omitting it would misdescribe what a role can do.
 */
export const CAPABILITY_LABELS: Record<string, string> = {
  "aziende:read": "Consultare l'anagrafica clienti",
  "aziende:create": "Registrare nuovi clienti",
  "aziende:delete": "Eliminare clienti",
  "survey:write": "Compilare i sopralluoghi",
  "assessments:write": "Compilare le valutazioni",
  "documents:read": "Consultare e scaricare i documenti",
  "documents:generate": "Generare e modificare i documenti",
  "documents:delete": "Eliminare versioni di documenti",
  "ai:use": "Usare le funzioni AI",
  "billing:read": "Vedere piano e crediti",
  "billing:manage": "Gestire abbonamento e acquisti",
  "users:manage": "Gestire gli utenti",
  "org:manage": "Personalizzare carta intestata e logo",
  "admin:tools": "Accedere a feedback, backup e strumenti admin",
};

export function capabilityLabel(capability: string): string {
  return CAPABILITY_LABELS[capability] ?? capability;
}
