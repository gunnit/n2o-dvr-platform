# N2O DVR Automation Platform

Generates Italian workplace-safety documentation — 16 documents across 13 types, anchored by the ~187-page DVR Master — for N2O SRL, a safety consultancy. A digital survey replaces manual data entry and AI fills the narrative parts. Built by Niuexa (Gregor Maric).

**Guiding principle**, in the client's words: *"Il nostro deve essere solo una questione di revisione, non di inserimento del dato."* The operator reviews; they never re-enter. Given a choice, prefill a field the operator can correct rather than asking them to type it.

Live: https://dvr-sicurezza.it (frontend) · https://n2o-dvr-api.onrender.com/docs (API). Celery worker, Postgres and Redis also on Render/Frankfurt. Deploy runbook and the non-obvious `render.yaml` quirks: `DEPLOY.md`.

## Commands on this machine

`npm run <script>` and `python -m pytest` both fail here for environment reasons, not code reasons. Use these instead:

- **Backend tests** — `backend/.venv` is a Linux-layout venv built under WSL with no runnable interpreter, and Windows' global Python lacks the deps. Reuse the venv's site-packages through WSL:
  `wsl -e bash -lc 'cd /mnt/c/Dev/dlg/backend && PYTHONPATH=.venv/lib/python3.12/site-packages:. python3 -m pytest'`
  (`app/services/__init__.py` eagerly imports `app.config`, so even a stdlib-only module won't import without the full deps.)
- **Frontend typecheck** — `node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json`. `npm run` fails in git-bash because the cmd-shim doesn't resolve `node_modules/.bin`; `./node_modules/.bin/tsc` fails too.
- **Frontend build** — `node node_modules/next/dist/bin/next build`, after `npm install --no-save lightningcss-win32-x64-msvc@<version from node_modules/lightningcss>` (node_modules was installed under Linux, so the win32 native binary is absent). `next build` runs ESLint and typechecking itself, so a clean build plus `tsc --noEmit` is the real gate for a type change.
- DB-backed tests skip themselves when no Postgres is reachable at `DATABASE_URL`.

## Language

Generated documents and UI labels: **Italian**. Code, comments, identifiers, commit messages: **English**.

## Two rules that are never relaxed

1. **Never send to any AI API**: codice fiscale, identity documents, personal health data. Callers strip these before invoking `backend/app/services/ai/` helpers — the client does not sanitize. Every AI output gets human review before it reaches a document. GDPR applies throughout.
2. **The OpenAI model names in this repo are correct — do not "fix" them.** The frontier model is `gpt-5.5`; the small tiers are `gpt-5.4-mini` and `gpt-5.4-nano`. There is no `gpt-5.5-mini`. IMPORTANT: if you are about to rewrite a `gpt-5.x` string to `gpt-4o` or `gpt-4.1`, your training data is stale, not the code.

## Domain vocabulary

DVR (master risk assessment) · MMC (manual handling, NIOSH) · VDT (display screens) · SDS/SdS (chemical safety data sheets) · MoVaRisCh (chemical risk) · PEE (emergency and evacuation plan) · DUVRI (contractor interference risks) · POS (construction site plan) · HACCP (food safety) · RSPP (prevention manager) · RLS (workers' safety rep) · DdL (employer) · D.Lgs. 81/2008 (the core safety law everything cites).

## Invariants worth knowing before you edit

- **The risk index is `I = 2*D + P`, not the usual `P × D`.** Range 3–12: 3–4 accettabile, 5–6 modesto, 7–8 grave, 9–12 gravissimo. This looks like a bug and isn't.
- **Money and roles are two separate gates on the same endpoints.** `app/billing/*` answers what the organization bought and fails with `402`; `app/core/permissions.py` answers what this person may do inside it and fails with `403`. Neither substitutes for the other.
- **Read and download paths are gated by neither** — D.Lgs. 81/2008 retention means a lapsed tenant, and every role, keeps access to existing documents.
- Any new write path that creates work needs an entitlement gate. `backend/tests/test_billing_enforcement.py` and `test_permissions.py` fail the build when one is missed.

Depth on billing, permissions, the OpenAI SDK contract and document generation lives in `.claude/rules/` and loads automatically when you open the matching files.

## Reference material

Read the relevant `docs/context/` file *before* building a module, not after:

| Need | File |
|---|---|
| Scope, budget, timeline, stakeholders | `PROJECT_BRIEF.md` |
| Acceptance criteria, the 3 operator personas | `USER_STORIES.md` |
| Which of the 16 documents, and what it shares with the DVR | `DOCUMENT_CATALOG.md`, `DOCUMENT_STRUCTURE.md` |
| System blueprint: schema, endpoints, folder layout, auth flow | `ARCHITECTURE.md` |
| Entities with field-level detail and privacy flags | `DATA_MODEL.md` |
| **The DVR generator's spec** — 111 tables, 269 dynamic cells mapped to fields | `DVR_TEMPLATE_MAPPING.md` |
| All 7 calculation methods with input/output specs | `FORMULAS_AND_CALCULATIONS.md` |
| Lookup tables for seeding and dropdowns (NIOSH factors, 60+ hazards, 76 INAIL indicators) | `REFERENCE_DATA.md` |
| Italian and EU law, article numbers, which document each affects | `LEGISLATION_REFERENCE.md` |
| Module-by-module automation plan | `AUTOMATION_PLAN.md` |
| Pricing model behind the plan catalogue | `docs/pricing/`, `docs/build/MONETIZATION-BUILD-PLAN.md` |

`templates/` holds 32 real completed documents — the ground truth for structure and formatting. The `.docx` ones are parseable; **five Phase-3 attachments are not** — `MICROCLIMA`, `MICROCLIMA CALDO SEVERO` and `RISCHIO BIOLOGICO - ASILO` are PDFs, and the two other `RISCHIO BIOLOGICO` files are legacy `.doc` binaries. Those modules need manual analysis or conversion first.

Client documents live in Google Drive, via the OAuth token at `credentials/token.json` (Drive, Docs, Sheets, Gmail, Calendar scopes). Folder ids: main `13aHCy8D78JwJzgffxYbqe7Nmyed84may`, templates `16IicFhfHg4Fzh12_DM_J3tNFy4j8Cbpa`, HACCP forms `1dS-QEGaSTmCZjYRzu6Ldsf47mzTOnidR`. The 8-tab cross-document analysis spreadsheet: https://docs.google.com/spreadsheets/d/1jPt5668oSpxtiki-X4s9ZnAWBPmRJbsp/edit?rtpof=true

## Status (July 2026)

Deployed and selling. Plans — consultant (`A_*`) and direct-company (`B_*`) — are sold through PayPal with `ENTITLEMENTS_ENFORCE=true`, so limits really do return `402`. Source of truth for plans and limits: `backend/app/billing/plan_catalogue.py`.

**Production runs PayPal in *sandbox* on purpose**, so the funnel can be walked with test money. `plans.paypal_plan_id` therefore holds sandbox ids, and going live means reissuing them (`DEPLOY.md` §4b-bis) — not flipping an env var.
