> **NIUEXA** | AI-Powered Business Automation
> *N2O DVR — Banca ESG-Social Add-on*
> Version 1.0 | May 2026 | Gregor Maric
> Confidential — Niuexa & N2O SRL

---

# Project Brief — Banca ESG-Social Add-on

## Executive summary

Add a **white-label "Compliance Suite ESG-Social"** to the N2O DVR platform, sold B2B2B to small Italian banks (BCC, popolari territoriali). The bank distributes a free autodichiarazione tool to all its corporate clients to comply with EBA Guidelines GL/2025/01 (effective for SNCI banks 11 Jan 2027). N2O monetizes via (a) per-client infrastructure fee from the bank and (b) revenue share on DVR Pro upsells to corporate clients converted through the bank funnel.

This is **not a new product** — it is a **second front-door** to the existing N2O DVR engine, sharing the same backend and data model, with new tenancy, theming, and user classes.

## Strategic context

Driven by three converging regulations researched 2026-05-08 (see `docs/context/BANCHE_DVR_NORMATIVA_2026.md`):

| Norm | In force | Effect |
|---|---|---|
| D.Lgs. 208/2025 (recepimento CRD VI) | 9 Jan 2026 | ESG enters Italian bank prudential supervision |
| EBA GL/2025/01 — Management of ESG Risks | 11 Jan 2026 (large) → **11 Jan 2027 (SNCI/small banks)** | Banks must collect ESG data from corporate clients |
| MEF "Dialogo PMI-Banche" v.dic 2025 | de facto standard | 40 indicators incl. 3 Priority-1 mapping directly to DVR (INAIL incidents, days lost, deaths) |

**Market window: May 2026 – Jan 2027.** Small banks must adopt a solution before SREP cycles bite. They lack internal ESG teams and the safety domain to build it themselves.

## Vision

> *"Same DVR engine, two front doors. Consultants enter through dvr-sicurezza.it to produce documents. PMI Datori di Lavoro enter through their bank's white-label portal to file the autodichiarazione once a year. The same `Azienda` record powers both. The autodichiarazione becomes the upsell trigger for DVR Pro."*

## Goals and success criteria

| # | Goal | Metric | Target |
|---|---|---|---|
| G1 | Make the offer demonstrable for sales | Working demo on staging | 4 weeks from kickoff |
| G2 | Land first pilot bank | Signed pilot agreement | 8 weeks from kickoff |
| G3 | Achieve high coverage in pilot | % corporate clients submitting autodichiarazione | ≥ 70% within 6 weeks of bank go-live |
| G4 | Activate Tier 2 upsell | % of submitting PMIs that buy DVR Pro | ≥ 5% in year 1, ≥ 15% in year 2 |
| G5 | Maintain audit-grade compliance | Banca d'Italia inspection export ready | 100% of submissions versioned, signed, immutable |
| G6 | Onboard 3 banks in 12 months | Signed contracts | 3 banks by May 2027 |

## Personas

| Persona | Description | Primary surface | Privacy class |
|---|---|---|---|
| **Banca Admin** | Compliance officer or IT of a partner bank. Manages portfolio of corporate clients, monitors coverage, exports for SREP. | `bancadashboard.niuexa.ai/{banca}` (or `esg.{banca}.it/admin`) | Sees data only for own bank's corporate clients |
| **Corporate DdL** | Datore di Lavoro of a PMI client of the bank. Compiles autodichiarazione annually. May convert to DVR Pro. | `esg.{banca}.it` (white-label) | Sees only own company data |
| **Consulente N2O** | Existing safety consultant. May co-manage the same PMIs if the bank-introduced PMI also signs as N2O client. | `dvr-sicurezza.it` (existing) | Sees data per existing org RBAC; bank-only PMIs invisible unless explicitly co-shared |
| **N2O Compliance Officer** | Internal Niuexa/N2O role for cross-bank monitoring, billing, audit. | Internal admin (`/admin/banche`) | Sees all banks for billing; cannot access individual PMI data without consent |

## Scope

### In scope (MVP)
- New entities: `Banca`, `BancaBranding`, `BancaCorporateClient`, `InvitoBanca`, `AutodichiarazioneSnapshot`, `RegistroInfortuni`, `CCNL` lookup, `CertificazioneSicurezza`.
- Two-level tenancy (`organization_id` × `banca_id`) ortogonale al modello attuale.
- Bank onboarding flow (internal admin): branding, domain, AD endorsement template.
- White-label PMI portal `esg.{banca}.it` with theming driven by `BancaBranding` config.
- Magic-link authentication for Corporate DdL (no password).
- Autodichiarazione wizard (12 MEF indicators in 4 steps, ≤10 minutes for the user).
- Auto-prefill from existing Camera di Commercio (visura) import already implemented.
- PDF generation with PADES digital signature by DdL.
- Bank admin dashboard: coverage matrix, risk semaphore, export CSV.
- Audit trail (append-only) with immutable submission snapshots.
- "Ispezione Banca d'Italia" export package.
- Upsell prompts to DVR Pro inside the portal post-submission.
- Stripe-based payment for Tier 2 with banca-attributed revenue tracking.

### Out of scope (MVP — backlog)
- Native integration with bank core banking (Cedacri, CSE, SIA) — Phase 9+.
- SSO with bank IdP (SAML/OIDC) — Phase 9+.
- Localizations beyond Italian — never.
- E and G pillars of the ESG questionnaire — partner with Cerved/Cribis or backlog.
- Mobile app — backlog; portal is mobile-responsive web.
- Multi-bank single-PMI portal (one PMI seeing all its banks) — backlog.

## Non-functional requirements

| Category | Requirement |
|---|---|
| **Privacy** | GDPR. Banca is titolare for invitations; N2O/Niuexa is titolare for the service. DPA template shipped per bank. Hosting EU (Render Frankfurt). No personal health data, no codice fiscale to OpenAI. |
| **Tenancy** | Strict isolation: a Banca Admin must never see a PMI not in its `BancaCorporateClient` list. Negative test mandatory in CI. |
| **Audit** | All submissions immutable. `AutodichiarazioneSnapshot` is append-only, never updated. New submission creates new snapshot. |
| **White-label** | Per-bank: logo, primary color, secondary color, accent color, font (one of N2O-approved), custom CTA copy, custom email-from name. All in `BancaBranding.config` JSONB. |
| **Availability** | 99.5% uptime SLA. RPO 24h, RTO 4h. |
| **Security** | OWASP top 10. Rate limiting on magic-link endpoints. Audit log for admin actions. Quarterly external security review. |
| **Performance** | Wizard load &lt; 1.5s p95. PDF generation &lt; 30s. Dashboard refresh &lt; 2s for ≤ 5000 corporate clients. |
| **Accessibility** | WCAG 2.1 AA on the PMI-facing wizard (statutory accessibility law for B2C-like portals). |

## Commercial model (B2B2B freemium)

| Tier | Description | Who pays | Price |
|---|---|---|---|
| 1 — Autodichiarazione | 12 MEF indicators, PDF firmato | Free for PMI. Banca pays infrastructure fee | €3–5 / cliente attivato / anno |
| 2 — DVR Pro | Full DVR + 16 docs, upsell from Tier 1 | PMI pays | €500–2000 per package (existing pricing). Banca gets 20% rev share. |
| Setup | White-label, DPA, training | Banca | €5–10k una tantum |

Per a 3,000-client bank, projected annual ARR €36k → €216k over 3 years (see `02 — PROPOSTA B2B2B` in Drive).

## High-level timeline (8 phases)

| Phase | Scope | Effort |
|---|---|---|
| B1 | Foundation: data model + two-level tenancy + RBAC | 1.5 wk |
| B2 | Bank onboarding & white-label theming | 1 wk |
| B3 | Corporate client onboarding (invitation + magic-link auth) | 1 wk |
| B4 | Autodichiarazione wizard (Tier 1) + PDF + signature | 2 wk |
| B5 | Bank admin dashboard (coverage, risk, export) | 1.5 wk |
| B6 | Audit & compliance (ispezione package, GDPR exports) | 0.5 wk |
| B7 | Upsell loop to DVR Pro + Stripe + rev share tracking | 1 wk |
| B8 | Pilot rollout: monitoring, feedback, polish | 1 wk |
| **Total** | **9.5 weeks** for solo dev | |

Could compress to 7 weeks with parallel agent execution.

## Stakeholders

- **Luca Marchetti (N2O)** — domain authority, sales lead with banks, validates UX from the safety consultant side
- **Gregor Maric (Niuexa)** — tech ownership, architecture, build, deploy
- **Banca pilot partner** (TBD, small BCC/popolare) — first paying customer, defines compliance officer requirements
- **Banca d'Italia** (indirect) — actual regulator; pilot bank's compliance must withstand SREP review

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Pilot bank backs out before signing | Med | High | Run pilot at-cost (€0 setup) in exchange for 12-month commitment after pilot |
| Multi-tenancy bug leaks PMI data across banks | Low | Critical | Negative tests in CI from day 1; staging fuzz with multi-bank fixture |
| Coverage low → bank disappointed | Med | High | Mandatory AD endorsement email + 3 automated reminders + escalation to gestore; track in pilot KPIs |
| Cerved/Cribis bundles a competing offering | Med | Med | Differentiation = safety domain. Lock in pilot bank with 3-year contract |
| GDPR challenge by a PMI ("perché la banca ha i miei dati di sicurezza?") | Low | Med | Clear DPA + consent flow in invitation acceptance + opt-out path |
| Stripe / payment integration delays Tier 2 | Med | Low | Tier 2 can launch 2 weeks after Tier 1; not a launch blocker |

## Open decisions to resolve before kickoff

1. **Domain strategy**: subdomain per banca (`esg.bancaxyz.it`, requires DNS per bank) vs path-based (`bancadashboard.niuexa.ai/bancaxyz`, simpler but less brand). **Recommendation**: path-based for MVP, subdomain for committed banks.
2. **Magic-link or password for PMI?** **Recommendation**: magic-link (no password headache for non-tech DdL). Backup: short numeric code on email if no link click in 5 min.
3. **N2O staff visibility on bank-only PMIs?** **Recommendation**: invisible by default. PMI explicitly opts in to "anche consulenza N2O" during invitation acceptance, which co-shares with N2O org.
4. **Pricing of pilot setup**: €0 or €2k? **Recommendation**: €0 for first pilot bank in exchange for case study + reference call rights.
5. **Stripe vs banca-collected payment?** **Recommendation**: Stripe direct from N2O. Banca rev share paid monthly via SEPA.

## Definition of "ready to sell"

- Phase B1–B5 complete (foundation through dashboard)
- Working demo on staging with a fake "Banca Demo" tenant
- Pricing sheet + termsheet template (already in `02 — PROPOSTA B2B2B`)
- Privacy DPA template signed-off by legal
- Pilot bank verbal commitment

## Definition of "production-ready"

- All 8 phases complete
- E2E test suite green: bank onboarding → invitation → submission → dashboard → upsell → payment
- Multi-tenant isolation negative tests green
- DPA signed with at least 1 bank
- Stripe live, first €1 paid (smoke test)
- Disaster recovery drill executed once
