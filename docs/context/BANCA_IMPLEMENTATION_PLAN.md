> **NIUEXA** | AI-Powered Business Automation
> *N2O DVR — Banca ESG-Social Add-on*
> Version 1.0 | May 2026 | Gregor Maric
> Confidential — Niuexa & N2O SRL

---

# Implementation Plan — Banca ESG-Social Add-on

This document is designed to be **agent-executable**. An AI coding agent should be able to read this file plus `BANCA_USER_STORIES.md`, `BANCA_DATA_MODEL.md`, `BANCA_PROJECT_BRIEF.md` and produce production-ready code without further direction.

## How to use this document (for the agent)

1. Work phases in order **B1 → B8**. Do not skip ahead.
2. Each phase ends with a **Verification Gate** that must pass before moving on.
3. Each task must end with: (a) green tests, (b) updated migration if schema changed, (c) commit on a feature branch.
4. When a story marks "DoD includes E2E test", you MUST write the Playwright test in `frontend/tests/e2e/banca/` BEFORE marking complete.
5. When uncertain on UX (copy, color), use the **defaults** in `BANCA_PROJECT_BRIEF.md`. Do NOT pause for human input on style.
6. When uncertain on **legal/commercial** wording (DPA, pricing, contract terms), STOP and ask Gregor.
7. After each Verification Gate, run the full E2E suite and `pytest` and report the result before opening the next phase.

## Repo placement (no new repo — see brief)

```
backend/app/
├── api/v1/
│   ├── banca/                       ← NEW
│   │   ├── admin.py                 ← Niuexa admin endpoints
│   │   ├── staff.py                 ← banca_admin / banca_viewer
│   │   ├── corporate_ddl.py         ← PMI endpoints
│   │   └── webhooks_stripe.py       ← Stripe webhook
│   └── … (existing N2O DVR routers)
├── services/banca/                  ← NEW
│   ├── invitations.py
│   ├── autodichiarazione.py
│   ├── pdf_generator.py
│   ├── audit.py
│   ├── rev_share.py
│   └── tenancy.py                   ← repo helpers with_banca_scope
├── models/                          ← extend, do not split
│   ├── banca.py                     ← NEW
│   ├── banca_branding.py            ← NEW
│   ├── banca_user.py                ← NEW
│   ├── banca_corporate_client.py    ← NEW
│   ├── invito_banca.py              ← NEW
│   ├── autodichiarazione_draft.py   ← NEW
│   ├── autodichiarazione_snapshot.py← NEW
│   ├── registro_infortuni.py        ← NEW
│   ├── certificazione_sicurezza.py  ← NEW
│   ├── ccnl.py                      ← NEW
│   ├── revshare_ledger.py           ← NEW
│   └── audit_log_banca.py           ← NEW
├── alembic/versions/
│   └── bxxx_banca_addon_schema.py   ← single migration

frontend/                            ← existing N2O DVR consultant app
   ├── app/
   │   ├── admin/banche/             ← NEW — niuexa admin
   │   └── … (existing)

frontend-banca/                      ← NEW — white-label PMI + banca admin
   ├── app/
   │   ├── esg/[banca]/              ← PMI portal (Corporate DdL)
   │   │   ├── benvenuto/
   │   │   ├── wizard/
   │   │   ├── storico/
   │   │   ├── upsell/
   │   │   └── verifica/
   │   ├── banca/[banca]/admin/      ← banca staff dashboard
   │   │   ├── dashboard/
   │   │   ├── clienti/
   │   │   ├── inviti/
   │   │   ├── export/
   │   │   └── users/
   │   └── api/                      ← Next.js BFF
   ├── tests/e2e/                    ← Playwright tests
   └── lib/theming/                  ← BancaBranding consumer

shared/
   └── types/banca.ts                ← TypeScript types shared between FE and BFF
```

**Frontend split rationale**: existing N2O consultant frontend stays untouched. New `frontend-banca/` Next.js app uses the same `api/v1` backend, shares types via `shared/types/banca.ts`. Two frontends = two independent deploys, less blast radius. Same monorepo.

---

## Phase B1 — Foundation (data model + tenancy + RBAC)

**Goal**: Database schema, repository helpers, RBAC enforced. No UI yet. The platform is "ready to receive" banca data.

**Stories included**: US-B7.1 (tenancy isolation)

**Tasks**
1. Write Alembic migration `bxxx_banca_addon_schema.py` covering all new tables and additive columns per `BANCA_DATA_MODEL.md`.
2. Add SQLAlchemy models for each new entity. Define relationships explicitly.
3. Implement append-only triggers on `autodichiarazione_snapshot` and `audit_log_banca`.
4. Implement `services/banca/tenancy.py` with `AziendaRepo.for_banca(banca_id)`, `AziendaRepo.for_corporate_ddl(...)`, etc.
5. Extend RBAC enum: `banca_admin`, `banca_viewer`, `corporate_ddl`, `niuexa_admin`, `niuexa_compliance`.
6. Write unit tests in `tests/test_banca_tenancy.py` proving cross-tenant isolation (10+ negative tests).
7. Seed `ccnl` lookup with top 30 from `references/ccnl_top30.csv` (research and prepare this CSV in `scripts/seed_ccnl.py`).

**Verification Gate B1**
- [ ] `alembic upgrade head` clean from empty DB
- [ ] `alembic downgrade -1` reverses cleanly
- [ ] All new tables visible in `\dt` against staging DB
- [ ] `pytest tests/test_banca_tenancy.py` green (≥ 10 tests)
- [ ] Attempting UPDATE on `autodichiarazione_snapshot` raises exception (test exists)
- [ ] CCNL table has 30 rows
- [ ] `grep -r "session.query(Azienda)" backend/app/api/v1/banca/` returns 0 results

**Effort**: 1.5 weeks

---

## Phase B2 — Bank onboarding & white-label theming

**Goal**: Niuexa admin can create a Banca tenant and the white-label portal renders with custom branding.

**Stories included**: US-B1.1, US-B1.2, US-B1.4 (banca admin provisioning)

**Tasks**
1. Backend endpoints: `POST /admin/banche`, `PATCH /admin/banche/{slug}`, `POST /admin/banche/{slug}/branding`.
2. Logo upload: accept PNG/SVG ≤ 500 KB, store on Render Disk under `/data/banca-logos/{slug}.{ext}`, return signed URL.
3. Niuexa admin UI in existing `frontend/app/admin/banche/` (table list, create form, branding form).
4. New `frontend-banca/` Next.js app scaffolded with Tailwind + theming via CSS variables.
5. `lib/theming/banca-theme-provider.tsx` reads `/api/v1/banca/{slug}/public-branding` at SSR and injects CSS vars (`--bg-primary`, `--color-accent`, etc.).
6. Public landing at `frontend-banca/app/esg/[banca]/page.tsx` showing branded "benvenuto" placeholder.
7. Magic-link invitation for first `banca_admin` user (US-B1.4).
8. E2E tests: create Banca → upload logo → visit `/esg/{slug}` → verify branded header.

**Verification Gate B2**
- [ ] Create 2 banche (`bancademo1`, `bancademo2`) with different colors
- [ ] Visit each `/esg/{slug}` — distinct theming, both isolated
- [ ] `frontend-banca` deploys independently to Render (staging)
- [ ] E2E `test_b2_create_tenant_and_brand.spec.ts` green
- [ ] Banca Admin invite → accept → dashboard placeholder renders, scoped to own bank

**Effort**: 1 week

---

## Phase B3 — Corporate client onboarding (invitation + magic-link auth)

**Goal**: Bank admin imports CSV, invitations go out, Corporate DdL clicks link and lands authenticated.

**Stories included**: US-B1.3, US-B2.1, US-B2.2, US-B2.3, US-B2.4

**Tasks**
1. CSV import endpoint with header validation, P.IVA dedup, error reporting.
2. Celery task `send_banca_invites` with idempotency key.
3. Email template `templates/emails/banca_invito.html` — bank logo from `BancaBranding`, N2O footer, magic link + backup 6-digit code.
4. Magic-link endpoint with one-shot semantics + session cookie issuance.
5. Backup code endpoint with rate limiting (Redis-backed).
6. PMI portal `frontend-banca/app/esg/[banca]/benvenuto/page.tsx` with company name pre-loaded.
7. Reminder Celery beat task running daily at 09:00 UTC.
8. Optional "anche consulenza N2O" toggle on welcome page.

**Verification Gate B3**
- [ ] Import a 100-row CSV → 100 `BancaCorporateClient` rows in `da_invitare`
- [ ] Send invites → 100 mails in Gmail (use sandboxed test inbox), all unique tokens
- [ ] Click a token → authenticated session, lands on `/benvenuto`
- [ ] Expired token → graceful error + "richiedi nuovo link" CTA
- [ ] Backup code: 5 wrong attempts → 15-min lockout
- [ ] Reminder at +7 days fires (use frozen-time test fixture)
- [ ] E2E `test_b3_invitation_flow.spec.ts` green end-to-end

**Effort**: 1 week

---

## Phase B4 — Autodichiarazione wizard (Tier 1) + PDF + signature

**Goal**: Corporate DdL compiles 12 MEF indicators, signs, gets a signed PDF emailed.

**Stories included**: US-B3.1 through US-B3.7

**Tasks**
1. Wizard state machine in `frontend-banca/app/esg/[banca]/wizard/`. 5 steps:
   - Step 1: Anagrafica (with visura prefill)
   - Step 2: Composizione lavoratori (CCNL, contract mix)
   - Step 3: Salute & Sicurezza P1 (RegistroInfortuni)
   - Step 4: Politiche & formazione
   - Step 5: Revisione + firma
2. Auto-save endpoint `PATCH /esg/{slug}/wizard` debounced 30s.
3. CCNL autocomplete component.
4. Semaphore preview component fed by `services/banca/autodichiarazione.py::compute_semaphore`.
5. Signature canvas (react-signature-canvas or similar; reuse existing pattern if present in N2O frontend).
6. PDF generator `services/banca/pdf_generator.py`:
   - Uses python-docx → LibreOffice headless → PDF, OR
   - Direct PDF with reportlab if simpler
   - PADES signature using `endesive` or `pyhanko`
   - Includes bank logo (from BancaBranding), N2O footer, all 12 indicators, signature image, doc hash, QR code with verification URL.
7. Submission endpoint: validates, persists `AutodichiarazioneSnapshot`, deletes draft, triggers email to DdL + Banca Admin.
8. Storico page at `/esg/[banca]/storico/page.tsx` — list past submissions with PDF download.

**Verification Gate B4**
- [ ] Complete wizard end-to-end on staging in < 10 min for an N2O test fixture
- [ ] Submit → PDF arrives in DdL inbox (test mailbox)
- [ ] PDF has correct branding, indicators, signature, hash
- [ ] Snapshot row exists, marked immutable (UPDATE attempt fails)
- [ ] Auto-save: kill tab mid-step → reopen → resume at same step with same data
- [ ] Semaphore changes color correctly per input (test all 3 transitions)
- [ ] E2E `test_b4_autodichiarazione_happy_path.spec.ts` green
- [ ] E2E `test_b4_autodichiarazione_immutable.spec.ts` green

**Effort**: 2 weeks

---

## Phase B5 — Bank admin dashboard

**Goal**: Bank admin has a working dashboard with coverage, drill-down, exports.

**Stories included**: US-B4.1, US-B4.2, US-B4.3, US-B4.4, US-B4.5

**Tasks**
1. Dashboard at `frontend-banca/app/banca/[banca]/admin/dashboard/page.tsx`:
   - 5 KPI tiles
   - Donut chart status distribution (Recharts or visx)
   - Heatmap ATECO × semaphore (visx or custom Tailwind grid)
   - Coverage trend over last 12 weeks (line chart)
2. Clients list with filter sidebar (ATECO, status, semaphore, region, gestore).
3. Client drill-down page: latest submission, indicator table, PDF download, history list.
4. CSV/XLSX export endpoint. For >1000 rows → Celery task → email signed S3-like URL.
5. ATECO median seed for semaphore thresholds (research INAIL public stats).
6. Banca user management UI: list, invite, role pick, revoke.
7. Permission tests in CI: banca_viewer cannot invite users; banca_admin of A cannot read B's clients.

**Verification Gate B5**
- [ ] Dashboard renders < 2s with 1000-client fixture
- [ ] Filters reflow client list in < 500ms
- [ ] Export 1000 rows → email arrives with link; link returns valid CSV
- [ ] Banca A admin gets 404 trying to read Banca B URLs (auto-tested)
- [ ] banca_viewer can read but not invite users (auto-tested)
- [ ] E2E `test_b5_dashboard_isolation.spec.ts` green

**Effort**: 1.5 weeks

---

## Phase B6 — Audit & compliance package

**Goal**: A bank can hand over a Banca d'Italia inspection package on click.

**Stories included**: US-B5.1, US-B5.2, US-B5.3, US-B7.2, US-B7.4

**Tasks**
1. Audit log endpoint with pagination + date filters.
2. "Pacchetto ispezione" Celery task:
   - Bundles all PDFs into ZIP
   - Generates CSV manifest with hashes
   - Audit log CSV
   - Coverage summary PDF
   - Sends signed-URL email when ready (7-day TTL)
3. DSAR endpoints: `/esg/{slug}/gdpr/export` and `/esg/{slug}/gdpr/delete` for Corporate DdL.
4. DPA generator: `templates/legal/dpa_template.docx` with Jinja variables → endpoint `POST /admin/banche/{slug}/dpa/genera`.
5. PDF tamper verifier at `frontend-banca/app/esg/[banca]/verifica/page.tsx`: upload PDF → SHA-256 → match against any stored snapshot.

**Verification Gate B6**
- [ ] Generate ispezione ZIP with 50-client fixture, open ZIP, all PDFs present and re-hash matches
- [ ] DSAR export for one Azienda returns all its data in ZIP
- [ ] DSAR delete request anonymizes fields (manual inspection of DB row)
- [ ] Verifier correctly flags a modified PDF as TAMPER
- [ ] E2E `test_b6_ispezione_export.spec.ts` green

**Effort**: 0.5 weeks

---

## Phase B7 — Upsell to DVR Pro + Stripe + revenue share

**Goal**: Post-submission upsell converts to paid DVR Pro and bank gets attribution.

**Stories included**: US-B6.1, US-B6.2, US-B6.3

**Tasks**
1. Post-submission upsell page with 3 dynamic cards.
2. Stripe Checkout session for "Pacchetto DVR Pro" SKU(s). 3 SKUs: DVR aggiornamento, MMC allegato, pacchetto completo.
3. Stripe webhook handler (signature-verified) → creates `DvrProSubscription` + `RevShareLedger` row.
4. Existing DVR wizard becomes accessible inside the banca portal for users with `dvr_pro_active=true`.
5. Niuexa admin revshare report at `/admin/banche/{slug}/revenue` with monthly aggregate + CSV export.
6. SEPA payout flow — manual MVP (Banca Admin sees IBAN, Gregor wires monthly). Stripe Connect for v2.

**Verification Gate B7**
- [ ] Complete wizard → upsell page renders → click → Stripe Checkout → pay with test card → return to portal → DVR wizard accessible
- [ ] `RevShareLedger` row created with correct % and banca attribution
- [ ] Negative test: non-banca PMI buys DVR Pro → NO ledger entry
- [ ] Monthly report aggregates correctly for fixture of 10 purchases
- [ ] E2E `test_b7_upsell_to_dvr_pro.spec.ts` green (Stripe test mode)

**Effort**: 1 week

---

## Phase B8 — Pilot rollout

**Goal**: Working end-to-end on real pilot bank with 50 PMIs. Monitoring in place.

**Stories included**: ops-focused; closing any P1 bugs found in pilot.

**Tasks**
1. Add Sentry to both frontends + backend.
2. Add structured logging with banca_slug + corporate_client_id correlation.
3. Build a `/admin/banche/{slug}/health` dashboard for Gregor (Niuexa admin): queue depth, error rate, invitation latency, coverage by week.
4. Run **pilot rehearsal**: full flow on `bancademo` with 5 real-looking test companies. Time each user journey, identify friction.
5. Onboard the real pilot bank: create tenant, import their 50 selected clients, run invitation campaign, monitor daily.
6. Triage and fix P1 issues from pilot bank feedback within 24h SLA.
7. Write a **playbook for going-live** for future banche (checklist, runbook).

**Verification Gate B8**
- [ ] Pilot bank tenant created and configured in production
- [ ] 50 invitations sent successfully
- [ ] At least 35 PMIs submit (70% coverage target)
- [ ] No P1 incidents in first 4 weeks
- [ ] Pilot bank signs continuation contract (or feedback explains why not)

**Effort**: 1 week

---

## Definition of Done (per task/PR)

A task is DONE only if:
1. Code merged to `main` via PR.
2. Migration (if any) applied to staging and clean.
3. All new unit tests passing in CI.
4. All new E2E tests passing on staging.
5. No regressions in existing N2O DVR test suite (`pytest backend/tests` + Playwright `frontend/tests/e2e`).
6. Type-checks pass (`mypy backend`, `tsc --noEmit` for frontend).
7. Lint passes (`ruff backend`, `eslint frontend`).
8. PR description references the story IDs and verification gate items closed.

## Definition of Done (per phase)

A phase is DONE only if:
1. All stories in the phase have all AC met.
2. All Verification Gate items checked.
3. Demo recorded (Loom or equivalent) showing the new flows end-to-end.
4. PROJECT_BRIEF success criteria for that phase are met.

## Testing strategy

### Unit tests (pytest)
- `backend/tests/banca/test_*.py` mirroring the service file structure
- Coverage target: ≥ 80% on `services/banca/`
- Specific suites:
  - `test_tenancy.py` — repo helpers, scope enforcement
  - `test_invitations.py` — token generation, expiry, dedup
  - `test_autodichiarazione.py` — semaphore logic, submission immutability
  - `test_pdf_generator.py` — PDF hash stability, signature presence
  - `test_rev_share.py` — ledger math, idempotency
  - `test_audit.py` — append-only invariants

### Integration tests (pytest + real Postgres)
- Migration up/down round-trip
- Cross-bank isolation: seed 3 banche × 100 clients each, confirm 0 cross-bank leakage in 30+ scenarios
- Stripe webhook → ledger flow with mocked Stripe API
- Email sending end-to-end with Mailpit or smtp mock

### E2E tests (Playwright, in `frontend-banca/tests/e2e/`)
- `b1_create_tenant.spec.ts`
- `b2_branding_isolation.spec.ts`
- `b3_invitation_flow.spec.ts`
- `b4_wizard_happy_path.spec.ts`
- `b4_wizard_resume_draft.spec.ts`
- `b4_wizard_immutability.spec.ts`
- `b5_dashboard_coverage.spec.ts`
- `b5_dashboard_isolation.spec.ts`
- `b6_ispezione_export.spec.ts`
- `b6_pdf_tamper_verifier.spec.ts`
- `b7_upsell_stripe.spec.ts`
- `b7_revshare_attribution.spec.ts`

### Cross-tenant negative-test fixture (mandatory in CI)
Seeds: 2 banche, 2 azienda per banca, 1 N2O org with 1 own client, 1 azienda shared between N2O and bancademo1.
Asserts (≥ 12 scenarios):
- banca_admin@A reading banca B → 404
- corporate_ddl(azienda X under banca A) reading azienda Y under banca A → 404
- n2o_consultant reading banca-only azienda where `consente_consulenza_n2o=false` → 404
- niuexa_admin can read anything, but every read is in audit log

### Load tests (light, before pilot)
- 100 concurrent magic-link clicks → no token reuse
- Dashboard with 5000 corporate clients renders < 2s
- Bulk export of 5000 rows completes < 60s

---

## Feature flags

- `BANCA_MODULE_ENABLED` — kill switch for the whole module; default off in production until B2 ships.
- `BANCA_STRIPE_ENABLED` — gates Phase B7. Default off until live mode tested.
- `BANCA_AUTO_REMINDERS_ENABLED` — per-Banca toggle for reminder cadence (default on).

---

## Release plan

| Milestone | Trigger | Environment |
|---|---|---|
| Internal alpha | End of B5 | Staging, internal users only |
| Pilot bank live | End of B8 | Production, behind feature flag for that bank's slug |
| GA | After 2 pilot banks complete a full cycle | Production, marketing site updated |

---

## Risk register (delta from PROJECT_BRIEF)

| Risk | Phase | Mitigation |
|---|---|---|
| Alembic migration conflict with concurrent DVR feature work | B1 | Coordinate with N2O DVR backlog; merge migrations atomically |
| Email deliverability low (corporate spam filters) | B3 | Use SPF/DKIM/DMARC; pre-warm `from` address; allow custom from per bank in B8 |
| PDF signing library issues on Render | B4 | Test on Render staging early; fallback to Linux container with libreoffice headless |
| Stripe Italian VAT/IVA handling | B7 | Stripe Tax enabled; legal review of invoice template |
| Pilot bank's IT pushes back on "data hosted by Niuexa" | B8 | Offer on-prem deploy in B9+ as paid option; for now, DPA + Frankfurt hosting + ISO27001 plan |

---

## Open follow-ups (beyond MVP)

- Phase B9: SSO with bank IdP (SAML 2.0 + OIDC) — required for some banks
- Phase B10: Cedacri / CSE core banking webhook (real-time credit score updates)
- Phase B11: Aggregate benchmarks (anonymized per-ATECO median, served to PMIs)
- Phase B12: Mobile-native app
- Phase B13: E and G ESG pillars (partner integrations with Cerved/Cribis)

---

## Agent execution recipe

To run this plan with an AI coding agent:

```bash
# Suggested invocation with /gsd:autonomous or manual phase-by-phase
/gsd:new-milestone "Banca ESG-Social Add-on"
# Then for each phase:
/gsd:add-phase B1 "Foundation — data model, tenancy, RBAC"
/gsd:plan-phase B1
/gsd:execute-phase B1
# After Verification Gate B1 passes:
/gsd:add-phase B2 "Bank onboarding & white-label"
# … and so on through B8
```

Alternative: a single `gsd-executor` agent reads this file + `BANCA_USER_STORIES.md` + `BANCA_DATA_MODEL.md` and works in order. Each commit message must reference the story IDs being closed (`feat(banca): close US-B1.1, US-B1.2 — banca tenant create + branding`).

If GSD is not used, the agent must:
1. Create a working branch `feat/banca-Bx-<short-name>` per phase.
2. Open a draft PR at phase start with checklist mirroring the Verification Gate.
3. Convert the draft to ready-for-review when the gate is fully checked.
4. Wait for human approval before starting the next phase.
