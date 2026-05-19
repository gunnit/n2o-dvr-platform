> **NIUEXA** | AI-Powered Business Automation
> *N2O DVR — Banca ESG-Social Add-on*
> Version 1.0 | May 2026 | Gregor Maric
> Confidential — Niuexa & N2O SRL

---

# User Stories — Banca ESG-Social Add-on

Each story follows the format `As a <persona>, I want <capability>, so that <benefit>` paired with **Acceptance Criteria** as Given/When/Then. Stories are testable. Every story has a **Definition of Done** that includes an executable test reference (Playwright E2E, pytest unit, or both).

Story IDs use the prefix `US-B<epic>.<n>` to distinguish from existing N2O DVR stories.

---

## Personas (recap)

- **Banca Admin** — compliance/IT of a partner bank
- **Corporate DdL** — Datore di Lavoro of a PMI client of the bank
- **Consulente N2O** — existing safety consultant
- **N2O Compliance Officer** — internal cross-bank admin

---

## Epic B1 — Bank onboarding & white-label setup

### US-B1.1 — Niuexa admin creates a new Banca tenant

**As a** N2O Compliance Officer
**I want** to create a new bank tenant from an internal admin page
**So that** we can spin up a white-label environment for a new partner bank without engineering work

**Acceptance Criteria**
- AC1 — **Given** I am logged in as `niuexa_admin`, **when** I visit `/admin/banche/nuova` and submit name + slug + AD name + AD email + setup notes, **then** a new `Banca` record is created with status `setup_in_corso` and a `BancaBranding` row is auto-created with default theme.
- AC2 — **Given** a `Banca` with slug `democredit`, **when** I visit `https://esg.dvr-sicurezza.it/democredit`, **then** the white-label PMI portal loads with the default theme and bank name in the header.
- AC3 — **Given** I create a Banca, **when** I submit, **then** an audit log entry is written with my user id, timestamp, and the diff.

**DoD**
- Migration adds `banca` + `banca_branding` tables
- Endpoint `POST /admin/banche` + UI at `/admin/banche/nuova`
- Audit log emits banca.created event
- E2E test `tests/e2e/banca/test_b1_create_tenant.spec.ts`
- Unit test `tests/test_banca_repository.py::test_create_and_uniqueness`

---

### US-B1.2 — Niuexa admin configures branding for a Banca

**As a** N2O Compliance Officer
**I want** to upload the bank's logo and pick primary/secondary colors
**So that** the white-label portal feels like the bank's own product

**AC**
- AC1 — **Given** an existing Banca, **when** I upload a PNG/SVG logo (≤ 500 KB) and save 3 hex colors and a CTA copy variant, **then** `BancaBranding.config` is updated.
- AC2 — **Given** I save a malformed hex color, **then** the form rejects with a clear error and nothing is persisted.
- AC3 — **When** I save valid branding, **then** the PMI portal at `/esg/{slug}` reflects the new theme within 60 seconds (no rebuild required).

**DoD**
- Theming is data-driven via CSS variables injected from `BancaBranding.config`
- Logo stored on Render Disk (or S3-compatible) with signed URL
- E2E test verifies portal renders with custom colors
- Snapshot test `tests/e2e/banca/test_b1_branding.spec.ts`

---

### US-B1.3 — Niuexa admin imports a corporate client list for a Banca

**As a** N2O Compliance Officer
**I want** to bulk import a CSV of corporate clients (ragione sociale, P.IVA, email DdL, sede)
**So that** the bank doesn't have to send PEC by PEC

**AC**
- AC1 — **Given** a Banca, **when** I upload a CSV with valid headers (`ragione_sociale, partita_iva, email_ddl, sede_legale_via, sede_legale_citta, cap`), **then** for each row a `BancaCorporateClient` is created in status `da_invitare`, linked to an `Azienda` (created if not exists, matched by P.IVA if exists).
- AC2 — **Given** an Azienda already exists in another Banca's portfolio, **when** I import it, **then** a NEW `BancaCorporateClient` is created (the company can be cliente of multiple banks). No data leak between banks.
- AC3 — **Given** a CSV with 100 rows and 3 invalid (missing P.IVA), **then** 97 are imported, 3 are reported with row number and error message.

**DoD**
- Endpoint `POST /admin/banche/{slug}/clienti/import` accepting `multipart/form-data`
- P.IVA matching uses the existing `azienda.partita_iva` index
- Integration test importing CSV with deduplication scenarios
- **Negative test**: import the same P.IVA in two banks, verify isolation

---

### US-B1.4 — Banca Admin user is provisioned

**As a** N2O Compliance Officer
**I want** to invite a bank employee as Banca Admin
**So that** the bank can self-serve the dashboard

**AC**
- AC1 — Invitation email sent with magic link (24h validity).
- AC2 — On accepting, the user gets role `banca_admin` scoped to the Banca, and lands on the bank dashboard.
- AC3 — Audit log records the role grant.

**DoD**
- New role in RBAC enum
- E2E test: invite → accept → dashboard renders → user cannot access another banca's data (negative test)

---

## Epic B2 — Corporate client onboarding (invitation flow)

### US-B2.1 — Banca Admin sends invitation campaign to corporate clients

**As a** Banca Admin
**I want** to launch a one-click invitation campaign to all my `da_invitare` clients
**So that** all my corporate clients receive a branded email at once

**AC**
- AC1 — **Given** N corporate clients in `da_invitare`, **when** I click "Invia inviti", **then** N emails are queued via Celery, each with a unique `InvitoBanca` token and 14-day expiry.
- AC2 — Email is co-branded (bank logo + N2O footer), uses bank's `from` name + reply-to.
- AC3 — Each client's status transitions to `invitato` with `invitato_at` timestamp.
- AC4 — If I click again, only clients still in `da_invitare` get the email (no double-send).

**DoD**
- Celery task `send_banca_invites`
- Email template `templates/emails/banca_invito.html` with theming variables
- Idempotency guarantee tested with concurrent clicks
- E2E test with 5 clients, verify 5 mails sent (mock SMTP)

---

### US-B2.2 — Banca Admin schedules automatic reminders

**As a** Banca Admin
**I want** invitations to auto-remind at +7, +14, +30 days
**So that** I don't have to chase clients manually

**AC**
- AC1 — Reminders skip clients that already submitted.
- AC2 — Reminder copy differs per round ("primo sollecito", "secondo sollecito", "ultimo sollecito" with gestore CC).
- AC3 — Banca Admin can disable reminders per client (e.g. cliente in fase di chiusura conto).

**DoD**
- Celery beat schedule for daily reminder pass
- Test with frozen-time fixture verifying reminder triggers

---

### US-B2.3 — Corporate DdL accepts invitation via magic link

**As a** Corporate DdL
**I want** to click the link in the email and access the portal without registering a password
**So that** the friction to start is zero

**AC**
- AC1 — **Given** a valid `InvitoBanca` token, **when** I click, **then** I land on `/esg/{banca_slug}/benvenuto` with my company name pre-loaded and a CTA "Inizia autodichiarazione".
- AC2 — **Given** an expired token, **then** I see a "richiedi nuovo link" page that emails me a fresh one.
- AC3 — **Given** I accept, **then** my session is authenticated for 14 days (refreshed on use), my `BancaCorporateClient` status becomes `accesso_effettuato`, and an audit log captures my IP and user agent.
- AC4 — **Given** I am offered the optional "vuoi anche la consulenza completa N2O?" toggle and I accept, **then** my Azienda is also linked to N2O's `organization_id` for shared visibility.

**DoD**
- Magic-link endpoint `POST /auth/magic-link/{token}` with one-time-use semantics
- Session cookie with `HttpOnly`, `Secure`, `SameSite=Lax`
- E2E test happy path + expired + already-used token

---

### US-B2.4 — Corporate DdL receives a numeric backup code if the link fails

**As a** Corporate DdL
**I want** a 6-digit code in the same email
**So that** I can sign in even if the link is mangled by my mail client

**AC**
- AC1 — Email contains both magic link and a 6-digit code valid 15 minutes.
- AC2 — Entering the code on `/esg/{banca}/codice` authenticates same as the link.
- AC3 — Code is rate-limited: 5 wrong attempts trigger 15-minute lockout.

**DoD**
- E2E test with code-based flow
- Brute-force resilience test

---

## Epic B3 — Autodichiarazione compilation (Tier 1, free)

### US-B3.1 — DdL completes anagrafica step with auto-prefill

**As a** Corporate DdL
**I want** the wizard to pre-fill my company anagrafica from visura camerale
**So that** I don't retype what's already known

**AC**
- AC1 — **Given** Azienda has a parsed visura (existing platform feature), **then** ragione sociale, P.IVA, sede, codice ATECO, dipendenti, forma giuridica are pre-filled and editable.
- AC2 — **Given** no visura present, **then** the user can upload a PDF and the existing extraction runs.
- AC3 — Fields enter validation (P.IVA format, CAP format) before allowing "Avanti".

**DoD**
- Reuses existing visura extraction pipeline
- E2E test with seeded Azienda → wizard step 1 → "Avanti" → fields visible

---

### US-B3.2 — DdL enters/confirms employee headcount, contract mix, CCNL

**As a** Corporate DdL
**I want** to enter employees by contract type (T.I., T.D., apprendisti) and pick our CCNL from a list
**So that** indicators 28, 35, 36 of MEF are captured

**AC**
- AC1 — Headcount fields validate as integers ≥ 0.
- AC2 — CCNL picker is autocomplete on a seeded lookup table (≥ 30 most common CCNLs incl. metalmeccanici, terziario, edilizia, etc.).
- AC3 — Field "% lavoratori coperti da CCNL" defaults to 100 with note "in Italia tipicamente 100%; modifica se diverso".

**DoD**
- `CCNL` lookup table seeded with N2O reference list
- E2E test selects CCNL and verifies persistence

---

### US-B3.3 — DdL submits annual safety stats (MEF Priority-1 indicators)

**As a** Corporate DdL
**I want** to enter our infortuni INAIL, giornate perse, decessi for the year
**So that** the bank gets the 3 Priority-1 indicators required by EBA

**AC**
- AC1 — Three numeric inputs with help-text quoting MEF definitions (one-click expandable).
- AC2 — Tasso di infortuni computed automatically when user enters ore lavorate totali (or estimated from FTE × 2000 if user opts in).
- AC3 — If user enters decessi > 0, an empathetic banner is shown ("ci dispiace; questi dati sono trattati con riservatezza") + a free-text "Note" field for context.
- AC4 — Banker semaphore preview: green if 0 deaths AND tasso ≤ industry median; yellow if above median; red if deaths > 0 OR tasso > 2× median.

**DoD**
- Stores in `RegistroInfortuni` (new entity) keyed (azienda_id, anno_riferimento)
- Median per ATECO seeded from INAIL public data (or fallback global median)
- E2E test verifies semaphore changes with input

---

### US-B3.4 — DdL confirms safety policies & training summary

**As a** Corporate DdL
**I want** to confirm we have a DVR aggiornato, RSPP/RLS designati, and report training hours
**So that** indicators 26, 31, 39 of MEF are captured

**AC**
- AC1 — Checkbox "DVR aggiornato negli ultimi 24 mesi" — required; if unchecked, blocks submission and surfaces upsell to DVR Pro.
- AC2 — Numeric "Ore di formazione SS erogate nell'anno (totale aziendale)" + "di cui obbligatoria".
- AC3 — Free-text "Procedure per segnalazione situazioni di pericolo (max 500 caratteri)".
- AC4 — Optional toggles: certificazione ISO 45001, codice etico presente.

**DoD**
- Persists to `AutodichiarazioneSnapshot.payload` JSONB
- E2E happy path test

---

### US-B3.5 — DdL reviews summary and signs digitally

**As a** Corporate DdL
**I want** to review all my answers on one page and sign the document
**So that** I submit a formal declaration like I do for any other compliance

**AC**
- AC1 — Summary page shows all 12 indicators with edit links per section.
- AC2 — Signature step: canvas signature pad + checkbox "dichiaro che le informazioni sono veritiere ai sensi DPR 445/2000".
- AC3 — On submit: PADES-signed PDF generated, `AutodichiarazioneSnapshot` stored (immutable), email sent to DdL (copy) and to Banca Admin (notification of new submission), `BancaCorporateClient.status = submitted`.

**DoD**
- PDF generator with PADES signature (reuse existing `firma_png` on Azienda)
- Snapshot is immutable: schema constraint prevents UPDATE
- E2E test: sign → see confirmation → re-load → cannot edit → must "nuova compilazione anno X+1"

---

### US-B3.6 — DdL can save draft mid-wizard

**As a** Corporate DdL
**I want** to leave and come back without losing progress
**So that** I can take 10 minutes here and 10 there

**AC**
- AC1 — Form auto-saves to `AutodichiarazioneDraft` every 30 seconds and on each "Avanti" click.
- AC2 — On re-entry, wizard resumes at the last completed step.
- AC3 — Draft is discarded once submitted.

**DoD**
- Auto-save tested in E2E (kill tab → reopen)

---

### US-B3.7 — DdL downloads the signed PDF post-submission

**As a** Corporate DdL
**I want** to download the signed PDF
**So that** I have my copy on file

**AC**
- AC1 — Post-submission, "Scarica PDF" CTA.
- AC2 — PDF includes bank logo, N2O footer, all 12 indicators, signature, timestamp, document hash.
- AC3 — Re-downloads allowed any time within session validity.

**DoD**
- PDF hash stored in `AutodichiarazioneSnapshot.pdf_sha256`
- E2E download + open + visual assertion on key strings

---

## Epic B4 — Banca admin dashboard

### US-B4.1 — Banca Admin sees portfolio coverage

**As a** Banca Admin
**I want** a dashboard showing % of clients submitted vs invited vs pending
**So that** I can plan reminder campaigns and report to my CdA

**AC**
- AC1 — Top tiles: Total clients / Invited / Accessed / Submitted / Overdue (> 30 days post-invite without submission).
- AC2 — Donut chart of status distribution.
- AC3 — Filter by ATECO macro-sector, by area geografica, by ramo (corporate/SMI).
- AC4 — Updated every load; no caching of stale data.

**DoD**
- SQL aggregation tested with 1000-client fixture, <500ms p95
- E2E test verifies tiles update after a submission

---

### US-B4.2 — Banca Admin drills down on individual client

**As a** Banca Admin
**I want** to click a client and see their latest submission with semaphore details
**So that** I can flag high-risk relationships to the credit committee

**AC**
- AC1 — Client detail page shows: latest submission date, semaphore, all 12 indicators in tabular form, downloadable PDF.
- AC2 — History of all years' submissions if multiple.
- AC3 — Read-only — Banca Admin cannot edit client data, only view.

**DoD**
- Permission test: Banca Admin of Banca A cannot access client of Banca B (negative test in CI)

---

### US-B4.3 — Banca Admin exports portfolio for SREP

**As a** Banca Admin
**I want** to export CSV/Excel of all submissions with all indicators
**So that** I feed it into our credit risk system or share with Banca d'Italia ispezione

**AC**
- AC1 — Export includes: P.IVA, ragione sociale, ATECO, all 12 indicators, semaphore, submission date, PDF hash, signed-by.
- AC2 — Export respects current filters.
- AC3 — Background job for >1000 rows; emails the download link when ready.

**DoD**
- CSV + XLSX formats
- Hash column allows banks to prove integrity to ispettori
- E2E test exports 100-row fixture

---

### US-B4.4 — Banca Admin sees risk distribution heatmap

**As a** Banca Admin
**I want** a heatmap of clients by ATECO × semaphore
**So that** I spot sector-level concentration of social risk

**AC**
- AC1 — Heatmap with ATECO macro on Y, R/Y/G on X, cell count + % of portfolio.
- AC2 — Click a cell drills to filtered client list.

**DoD**
- E2E test verifies heatmap renders for fixture with mixed sectors

---

### US-B4.5 — Banca Admin manages user permissions

**As a** Banca Admin
**I want** to add or remove other banca staff with role `banca_viewer` (read-only)
**So that** credit officers can browse without changing data

**AC**
- AC1 — Add user by email; magic-link invite; choose role `banca_admin` or `banca_viewer`.
- AC2 — Remove user; access revoked within 60 seconds.
- AC3 — Banca Admin cannot escalate themselves to `niuexa_admin`.

**DoD**
- RBAC enforced server-side; client-side permission check tested
- Privilege escalation negative test

---

## Epic B5 — Compliance evidence & exports

### US-B5.1 — Audit log is queryable

**As a** N2O Compliance Officer
**I want** an audit log endpoint scoped per Banca
**So that** during ispezione we can show "who did what, when"

**AC**
- AC1 — `GET /admin/banche/{slug}/audit?from=...&to=...` returns paginated events.
- AC2 — Events captured: invitation sent, draft started, draft saved, submitted, exported, deleted (if ever).
- AC3 — Audit entries are immutable (append-only).

**DoD**
- DB constraint preventing UPDATE on `audit_log_banca` table
- Test attempts to modify a row → fails

---

### US-B5.2 — "Ispezione Banca d'Italia" export package

**As a** Banca Admin
**I want** a one-click "pacchetto ispezione" ZIP containing all submissions in PDF + a CSV manifest with hashes
**So that** I hand it to the BI inspector and the inspection is fast

**AC**
- AC1 — ZIP includes: CSV with all client metadata + indicators + PDF SHA-256 + signature timestamp; PDFs of all submissions (latest per year); audit log CSV; coverage report.
- AC2 — ZIP filename: `ispezione_{banca_slug}_{YYYY-MM-DD}.zip`.
- AC3 — Background job for >500 PDFs; email link when ready, 7-day signed URL.

**DoD**
- E2E test generates package with 50-client fixture, opens ZIP, verifies hash match

---

### US-B5.3 — GDPR data subject access request (DSAR)

**As a** Corporate DdL
**I want** to request a copy or deletion of my data
**So that** I exercise my GDPR rights

**AC**
- AC1 — "I miei dati / GDPR" link in PMI portal footer.
- AC2 — Export: all `AutodichiarazioneSnapshot` for my Azienda + my access log.
- AC3 — Deletion: anonymizes personal fields (DdL name, signature, IP) but retains anonymized statistical record for bank's audit needs. Communicates to Banca Admin via email.

**DoD**
- 30-day SLA on requests
- E2E test requesting export → ZIP download

---

## Epic B6 — Upsell to DVR Pro (Tier 2)

### US-B6.1 — DdL sees DVR Pro upsell post-submission

**As a** Corporate DdL who just submitted autodichiarazione
**I want** to see what else N2O can do for me
**So that** if my DVR is expiring, I know I can upgrade now

**AC**
- AC1 — Post-submission page shows 3 upsell cards: "Aggiorna il tuo DVR", "Allegato MMC", "Pacchetto completo 16 documenti".
- AC2 — Cards are dynamic: if I marked "DVR aggiornato negli ultimi 24 mesi", de-emphasize "Aggiorna il tuo DVR".
- AC3 — Each card has price and "Inizia" CTA.

**DoD**
- E2E test verifies cards render and CTAs route to product page

---

### US-B6.2 — DdL purchases DVR Pro via Stripe

**As a** Corporate DdL who clicked a DVR Pro upsell
**I want** to pay with card and immediately access the full product
**So that** I don't wait for invoicing

**AC**
- AC1 — Stripe Checkout in Italian, EUR.
- AC2 — On success: invoice generated, `DvrProSubscription` created, Azienda flagged `dvr_pro_active`, user gains access to the full DVR wizard inside the same portal.
- AC3 — On failure: clear message, retry option.

**DoD**
- Stripe webhook signed-verified
- Test mode E2E with Stripe test card

---

### US-B6.3 — Revenue share to Banca is tracked

**As a** N2O Compliance Officer
**I want** every Tier 2 purchase by a Banca-introduced PMI to attribute 20% to the Banca
**So that** I can pay rev share at month-end without manual reconciliation

**AC**
- AC1 — `RevShareLedger` entry on every successful Stripe payment for a `BancaCorporateClient`-linked Azienda.
- AC2 — Monthly aggregate report at `/admin/banche/{slug}/revenue` with downloadable CSV.
- AC3 — SEPA payout flow (manual or via Stripe Connect — choose later) records `paid_at` on settle.

**DoD**
- Unit test: payment event → ledger entry with correct % and banca attribution
- Negative test: payment for a non-banca Azienda creates NO ledger entry

---

## Epic B7 — Cross-cutting (privacy, audit, GDPR, security)

### US-B7.1 — Multi-tenant isolation enforced everywhere

**As a** Niuexa engineer
**I want** every query touching `Azienda` or `BancaCorporateClient` to be scoped by current tenant
**So that** Banca A never sees Banca B's data even in case of code bugs

**AC**
- AC1 — A repository helper `with_banca_scope(banca_id)` is the only way to query bank-scoped entities.
- AC2 — Direct `Azienda.query.all()` in bank-context code raises a lint/static-analysis error.
- AC3 — CI runs cross-tenant negative test fixture: User of Banca A tries to read Banca B's `BancaCorporateClient` → 404 (not 403, to avoid existence leak).

**DoD**
- Custom static analysis rule (e.g. via custom lint) or runtime middleware enforcement
- Negative test in CI

---

### US-B7.2 — DPA artifact generation per Banca

**As a** N2O Compliance Officer
**I want** to generate a DPA PDF tailored to each Banca
**So that** I send it for signature without manual drafting

**AC**
- AC1 — From `/admin/banche/{slug}/dpa/genera`, downloadable PDF with bank name, addresses, technical/organizational measures appendix, signed by Niuexa legal rep.
- AC2 — Template versioned; current version recorded on the Banca record.

**DoD**
- Template file in `templates/legal/dpa_template.docx`
- Unit test of variable substitution

---

### US-B7.3 — Magic-link rate limiting and anti-abuse

**As a** Niuexa engineer
**I want** the magic-link endpoint rate-limited per IP and per email
**So that** an attacker cannot enumerate valid PMI emails

**AC**
- AC1 — 5 requests/minute per IP, 3 requests/hour per email.
- AC2 — On exceeding, returns 429 with vague "se l'indirizzo esiste, riceverai una mail" (no enumeration leak).
- AC3 — Persistent storage (Redis) for rate-limit counters.

**DoD**
- Load test with 100 concurrent requests confirms backpressure

---

### US-B7.4 — Submission integrity (PDF tamper detection)

**As a** Banca Admin
**I want** the export package to include a hash for each PDF
**So that** a tampered PDF can be detected by re-hashing

**AC**
- AC1 — Every `AutodichiarazioneSnapshot` stores `pdf_sha256`.
- AC2 — Bank can re-hash a downloaded PDF and compare.
- AC3 — A tamper-detection page at `/esg/{banca}/verifica` accepts a PDF and reports match/mismatch.

**DoD**
- E2E test: download PDF → modify 1 byte → upload to verifier → mismatch reported

---

## Story coverage matrix

| Epic | Stories | Coverage of MEF indicators |
|---|---|---|
| B1 — Bank onboarding | 4 | n/a |
| B2 — Invitation | 4 | n/a |
| B3 — Autodichiarazione | 7 | indicators 26, 28, 29 (opt), 31, 32, 33, 34, 35, 36, 39 + cert ISO + codice etico |
| B4 — Bank dashboard | 5 | reports on all above |
| B5 — Compliance | 3 | audit & evidence |
| B6 — Upsell | 3 | Tier 2 revenue |
| B7 — Cross-cutting | 4 | security & GDPR |
| **TOTAL** | **30** | **all MEF Sezione 4 + key cross-sector indicators** |

## Out-of-MVP user stories (backlog)

- US-B8.1 SSO with bank IdP (SAML/OIDC)
- US-B8.2 Core banking API integration (Cedacri, CSE)
- US-B8.3 Multi-bank PMI view ("vedi tutte le banche che ti chiedono questa autodichiarazione")
- US-B8.4 Mobile app
- US-B8.5 Mid-year delta declaration ("è cambiato qualcosa rispetto all'ultima dichiarazione?")
- US-B8.6 White-label email-from on custom bank domain (requires DKIM per bank)
- US-B8.7 AI assistant in the wizard ("aiuto, non so cosa rispondere qui")
- US-B8.8 Aggregate benchmark per ATECO (anonymized; "il tuo tasso infortuni vs media settore")
