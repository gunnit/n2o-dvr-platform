/**
 * The datore-di-lavoro acknowledgement shown on the direct (Model B) signup.
 *
 * `backend/app/data/ddl_consent.py` is the authority for both the wording and
 * the version id. This file exists because the text has to be *rendered*, and
 * the signup form echoes `DDL_CONSENT_VERSION` back to the API — which rejects
 * a version it does not recognise. So if these two ever drift, registration
 * fails loudly instead of recording consent to text nobody was shown.
 *
 * Changing the wording means adding a new version on both sides, never editing
 * an existing one: the stored version is evidence of what a given customer
 * agreed to on a given day.
 */

export const DDL_CONSENT_VERSION = "2026-07";

export const DDL_CONSENT_TEXT =
  "Dichiaro di essere il datore di lavoro o il soggetto responsabile della " +
  "sicurezza per l'impresa che sto registrando. La piattaforma è uno strumento " +
  "di redazione assistita: predispone struttura, calcoli e testi del documento, " +
  "ma non sostituisce la valutazione dei rischi né la firma del datore di " +
  "lavoro, che restano di mia competenza e responsabilità ai sensi del " +
  "D.Lgs. 81/2008.";
