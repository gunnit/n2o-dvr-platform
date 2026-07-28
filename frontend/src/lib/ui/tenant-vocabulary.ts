/**
 * The words the interface uses for the companies a tenant documents (P2-1).
 *
 * The platform serves two channels that do the same work on the same records
 * but mean different things by them:
 *
 * * a **consultant** (Model A) documents *client* companies — a portfolio;
 * * a **direct** company (Model B) documents *itself* — one employer, its own
 *   sedi.
 *
 * Shipping the consultant's nouns to a datore di lavoro ("Clienti attivi",
 * "Aggiungi cliente", "Registra una nuova azienda cliente") tells them, on the
 * first screen after signup, that the product is not for them.
 *
 * This is presentation only. There is no `if account_type == "direct"` in the
 * backend — INV-4 keeps the two channels as rows in the plan catalogue, not as
 * branching business logic — and nothing here gates anything.
 */

export type AccountType = "consultant" | "direct";

export type TenantVocabulary = {
  /** Nav / page title for the company list. */
  companiesTitle: string;
  /** Lead line on the company list page, before the " · N aziende" count. */
  listLead: string;
  /** Primary "create" action. */
  addCompany: string;
  /** Small caption under a quick-action tile. */
  addCompanyHint: string;
  /** KPI tile label. */
  activeCompanies: string;
  /** KPI empty state. */
  noCompanies: string;
  /** Heading above the company table on the dashboard. */
  companiesHeading: string;
  /** Lead paragraph on the "new company" form. */
  newCompanyLead: string;
  /** Lead paragraph on the documents page. */
  documentsLead: string;
  /** Error toast when a non-admin tries to create one. */
  adminOnlyCreate: string;
};

const CONSULTANT: TenantVocabulary = {
  companiesTitle: "Aziende",
  listLead: "Gestione clienti",
  addCompany: "Aggiungi cliente",
  addCompanyHint: "registra cliente",
  activeCompanies: "Clienti attivi",
  noCompanies: "nessun cliente",
  companiesHeading: "Aziende Clienti",
  newCompanyLead: "Registra una nuova azienda cliente.",
  documentsLead: "Genera i documenti di sicurezza per le aziende clienti",
  adminOnlyCreate: "Solo gli amministratori possono creare nuovi clienti",
};

const DIRECT: TenantVocabulary = {
  companiesTitle: "La mia azienda",
  listLead: "La tua impresa e le sue unità locali",
  addCompany: "Aggiungi sede",
  addCompanyHint: "registra sede",
  activeCompanies: "Sedi attive",
  noCompanies: "nessuna sede",
  companiesHeading: "La mia azienda",
  newCompanyLead: "Registra la tua impresa o una sua unità locale.",
  documentsLead: "Genera i documenti di sicurezza della tua azienda",
  adminOnlyCreate: "Solo gli amministratori possono aggiungere una sede",
};

export function vocabularyFor(accountType: string | null | undefined): TenantVocabulary {
  // Anything unrecognised falls back to the consultant wording: it is the
  // older channel and the one every pre-Model-B tenant is on.
  return accountType === "direct" ? DIRECT : CONSULTANT;
}
