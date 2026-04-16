# E2E QA Test Report — 2026-04-16

**Platform**: N2O DVR Automation Platform
**Harness**: 5 parallel Playwright MCP agents (sequential browser access), one per epic
**Stack tested**: Next.js 16 + Turbopack (frontend :3000) · FastAPI + Celery (backend :8000) · Postgres + Redis (Docker) · fully seeded Acme Meccanica Composita SRL fixture
**Scope**: all 46 user stories across 5 epics in `docs/context/USER_STORIES.md` (status matrix dated 2026-04-15 claimed 42 DONE / 4 PARTIAL / 0 NOT STARTED = 96%)

---

## Headline

| | PASS | PARTIAL | FAIL | BLOCKED |
|---|---:|---:|---:|---:|
| Epic 1 — Digital Survey (10) | 2 | 4 | 2 | 2 |
| Epic 2 — DVR Master (9) | 5 | 3 | 0 | 1 |
| Epic 3 — DVR Attachments (15) | 10 | 5 | 0 | 0 |
| Epic 4 — Complementary Docs (8) | 3 | 1 | 3 | 1 |
| Epic 5 — Cross-cutting (4) | 4 | 0 | 0 | 0 |
| **Total (46)** | **24 (52 %)** | **13 (28 %)** | **5 (11 %)** | **4 (9 %)** |

**Empirical DONE rate: 52 %** vs. docs claim of **96 %**. Reconciliation note in USER_STORIES.md overstates completion — primarily in Epic 1 (basic wizard validation missing) and Epic 4 (three independent bugs block doc features end-to-end).

---

## Critical Bugs (ship-blockers)

### B-01 · US-1.1 — Step 1 Azienda has no validation
**Severity**: blocker · **File**: `frontend/src/components/survey/steps/step-azienda.tsx`
No red border, no "Campo obbligatorio" inline error, no format check on partita IVA (3-digit accepted) or ATECO (garbage accepted). Avanti navigates regardless. Docs claim AC1/AC2/AC3 all met.
**Repro**: open survey wizard fresh, leave ragione sociale empty + enter PIV "123" + ATECO "BADCODE" → tab through fields → click Avanti → arrives at Step 2.

### B-02 · US-1.9 — SDS upload crashes on first PDF
**Severity**: blocker · **File**: `frontend/src/components/survey/steps/step-sostanze.tsx:772`
`sost.pittogrammi.includes(p.code)` throws `TypeError: Cannot read properties of null (reading 'includes')` because new-upload response has `pittogrammi: null` before extraction completes. Whole step becomes unusable; requires "Reload to try again". Blocks US-1.10 end-to-end.
**Fix**: `(sost.pittogrammi ?? []).includes(p.code)` or default in upload response handler.

### B-03 · US-1.6 — Signature gating broken
**Severity**: blocker · **File**: `frontend/src/components/survey/steps/step-riepilogo.tsx`
"Completa Sopralluogo" button is enabled with empty signature canvas; clicking it is a no-op (no toast, no nav, no missing-items list). Also summary panels show "Valutazione Rischi 0" / "Sostanze Chimiche 0" despite Acme having both fully seeded. AC2 + AC3 fail.

### B-04 · US-4.3 — HACCP router never mounted
**Severity**: blocker · **File**: `backend/app/api/v1/router.py`
Router for HACCP endpoints is imported but not included. `/api/v1/haccp/_meta/activity-types` and `/api/v1/aziende/{id}/haccp/config` return 404. Frontend HACCP assessment page renders "Not Found" banner with empty "-- Seleziona --".
**Fix**: `from app.api.v1.haccp import router as haccp_router` + `api_router.include_router(haccp_router)`.

### B-05 · US-4.5 — DUVRI schema mismatch
**Severity**: blocker · **File**: `backend/app/schemas/duvri.py:20,76`
`DuvriResponse.interferenze[].dpi: str | None` but DB stores `list[str]`. `GET /aziende/{id}/duvri` 500s with Pydantic ResponseValidationError. List page shows "Failed to fetch". Blocks US-4.5 and downgrades US-4.6 to PARTIAL.
**Fix**: change schema to `list[str] | None` (or join in serializer).

### B-06 · US-4.7 / 4.8 — POS PhaseBuilder crashes on legacy data
**Severity**: blocker · **File**: `frontend/src/components/assessments/pos/phase-builder.tsx:166`
`p.dipende_da.map(...)` with no null guard. Acme's seeded `fasi_lavorative` uses legacy `{fase, dpi, mezzi, rischi, descrizione}` shape without `dipende_da`. Backend generator handles this via `PosPhase` promotion; frontend read-path does not. Whole `/assessments/pos/:id` page crashes, which blocks US-4.8 DPI matrix (rendered on the same page).
**Fix**: `(p.dipende_da ?? []).map(...)` + read-path promotion to mirror backend.

### B-07 · Environmental — Pydantic EmailStr rejects `.test` TLD
**Severity**: high (affects demo path) · **File**: `backend/app/schemas/auth.py`
Seeded Acme admin `admin@acme-meccanica.test` cannot log in via `/auth/login` because Pydantic `EmailStr` rejects reserved `.test` TLD. Blocks the "documented fixture login" path. Agent 1 worked around by using `qa@niuexa.ai` mapped into the Acme org.
**Fix**: change fixture email to `.local` / `.example` / `.it`, or loosen validator.

---

## High-Severity Bugs (not ship-blockers)

### H-01 · US-1.4 — Codice fiscale validation missing
`persona-dialog.tsx` accepts "INVALID123" (10 chars) and keeps Save enabled. AC says 16-char alphanumeric pattern required + "Codice fiscale non valido" + Save disabled.

### H-02 · US-3.12 — Incendio form has React infinite render loop
`Maximum update depth exceeded` fires 48+ times on every interaction. Likely missing useEffect dep or setState-in-effect guard in `incendio-form.tsx`. Functional but perf/telemetry noise.

### H-03 · US-1.3 — Oversize file silently rejected
Ambienti photo upload rejects 11 MB .jpg with no toast. (Bad-format .txt correctly triggers the Italian toast.)

### H-04 · US-3.2 — MMC CP stale until next interaction
Changing sesso/eta doesn't re-fetch CP immediately; user sees wrong value for one cycle.

---

## Medium / UX gaps

| ID | US | Gap |
|----|----|-----|
| M-01 | US-1.2 | "Altro" env type not in dropdown; AC-3 empty-list behavior untestable. |
| M-02 | US-2.4 | Non-CE equipment red highlight unverifiable — all fixture rows are CE-marked. |
| M-03 | US-2.6 | AI error surface lacks explicit "Riprova" button (AC wants it). |
| M-04 | US-3.4 | No CSV bulk-import for VDT hours (AC3). |
| M-05 | US-3.6 | Stress toggles are 3-state (Diminuito/Inalterato/Aumentato) not SI/NO — arguably more faithful to INAIL but contradicts AC. |
| M-06 | US-3.7 | No hover tooltip with per-area subtotals + formula — subtotals inline instead. |
| M-07 | US-3.12 | VVF reference appears in bottom action panel, not a sticky top banner as AC specifies. |
| M-08 | US-3.15 | Sector label "Studio odontoiatrico" vs AC "Dentisti" (semantically equivalent). |
| M-09 | US-1.1 | AC1 auto-save within 2s — currently saves on step navigation only. |

---

## Environmental Findings

1. **Celery worker was not running at test start** — all DVR / attachment / PEE / HACCP / DUVRI / POS generations sat in `pending` forever. Fixed mid-run by launching `celery -A app.celery_app worker`. Generation now completes in ~15-60 s per doc. docker-compose has a `worker` service under the `full` profile, but dev runbook doesn't mention it — suggest adding to CONTINUE.md or a `npm run dev:all` script.
2. **OpenAI API key not set** — all AI flows surface "OPENAI_API_KEY is not configured" inline. This prevented end-to-end testing of: US-2.1 Retry UI, US-2.6 AI suggestion accept/modify, US-3.6-3.8 (no AI in attachments so unaffected), US-5.3 admin feedback with real signals (empty lists are still valid).
3. **Docker Desktop WSL integration** was off initially — user enabled it. Postgres 16-alpine + Redis 7-alpine came up on first `docker compose up -d`.
4. **Pre-existing DB had schema drift** — had to `DROP DATABASE n2o; CREATE DATABASE n2o; alembic upgrade heads` to reach a clean state. Multiple alembic heads (`c1d2e3f4a5b6` + `d3e4f5a6b7c8`) merged cleanly with `upgrade heads`.
5. **Next.js Turbopack `.next` cache was corrupt** on first boot (ChunkLoadError on `/_next/static/chunks/...`). Fixed via `rm -rf .next && npm run dev`.
6. **Playwright MCP Chrome singleton locked twice** (Epic 5) — recovered with `pkill` + session restart. Worth noting for future multi-agent runs.

---

## Per-Epic Detail

### Epic 1 — Digital Survey (2 P / 4 PART / 2 FAIL / 2 BLOCK)
- **PASS**: US-1.3 (photo rejection toast), US-1.5 (contextual rischi + attrezzature-driven suggestions)
- **PARTIAL**: US-1.2 (no "Altro"), US-1.4 (CF val missing), US-1.7 (RSPP gate not enforced), US-1.8 (no per-file progress bars)
- **FAIL**: US-1.1 (no validation), US-1.9 (crash on upload)
- **BLOCKED**: US-1.6 (signature gate broken → can't test locked-edit state), US-1.10 (blocked by US-1.9 crash)

### Epic 2 — DVR Master (5 P / 3 PART / 0 FAIL / 1 BLOCK→resolved)
- **PASS**: US-2.1 (AI description + revisions + visura + history panel), US-2.2 (seismic + regional regs), US-2.3 (matrix pre-fill + reset), US-2.7 (sliders + I=2D+P bands), US-2.9 (version history drawer)
- **PARTIAL**: US-2.4 (non-CE red highlight unverifiable), US-2.5 (dependent on DVR gen), US-2.6 (AI library UI unreached — no key)
- **BLOCKED → now working**: US-2.8 (Celery fix resolved; previously generation never completed)

### Epic 3 — DVR Attachments (10 P / 5 PART / 0 FAIL / 0 BLOCK)
- **PASS**: US-3.1, 3.3, 3.5, 3.8, 3.9, 3.10, 3.11, 3.13, 3.14, 3.15
- **PARTIAL**: US-3.2 (stale CP), US-3.4 (no CSV), US-3.6 (3-state toggles), US-3.7 (no tooltip), US-3.12 (render loop + non-sticky VVF)
- **Strongest epic** — computation layers are solid across MMC, VDT, Stress, Gestanti, Incendio, Microclima, Biologico.

### Epic 4 — Complementary Docs (3 P / 1 PART / 3 FAIL / 1 BLOCK)
- **PASS**: US-4.1 (PEE with DVR guard + planimetria), US-4.2 (A-E procedures), US-4.4 (HACCP forms bundle .zip)
- **PARTIAL**: US-4.6 (rules engine works, UI unreachable due to B-05)
- **FAIL**: US-4.3 (B-04 router miss), US-4.5 (B-05 schema drift), US-4.7 (B-06 phase-builder crash)
- **BLOCKED**: US-4.8 (dependent on B-06)
- **Weakest epic** — 3 independent bugs each block a different feature end-to-end even though generators produce valid output on disk.

### Epic 5 — Cross-cutting (4 P / 0 PART / 0 FAIL / 0 BLOCK)
- **PASS**: US-5.1 (5 KPIs + search + sort + surveillance widgets), US-5.2 (stale_snapshot flag + amber UI), US-5.3 (admin panel + AI badge diff + endpoints), US-5.4 (backups panel + audit events + Render handoff)
- **All four stories ship-ready.** The reconciliation note dated 2026-04-15 (Agent-D + Agent-E work) holds up empirically.

---

## Evidence

All screenshots under `/mnt/c/Dev/dlg/docs/qa/e2e-2026-04-16/`, named `epic<N>-us<M.K>-<slug>.png`. ~50 screenshots captured across five agents. Generator output `.docx` / `.zip` files on disk at `backend/var/storage/documents/4025a1c5-2966-4d14-9993-f41eb01d3042/`.

---

## Recommendation

**Do not declare MVP shipped until B-01 through B-06 are fixed.** These are not polish — they each break a documented acceptance criterion in a way a client demo would hit within 60 seconds. Fix order:

1. **B-07** (auth email validator) — 5 min. Unblocks the documented Acme login path.
2. **B-04** (HACCP router mount) — 5 min. One-line fix in `router.py`.
3. **B-05** (DUVRI schema) — 10 min. Change `dpi` type.
4. **B-02** (SDS null guard) — 10 min. One-line frontend fix.
5. **B-06** (POS phase-builder guard + promotion) — 30 min. Needs read-path mirror of backend promotion logic.
6. **B-01** (Step 1 validation) — 1-2 h. Build out `react-hook-form` + zod schema, or wire the existing validation helpers that Agent 1 saw present in `lib/validation/` but not connected.
7. **B-03** (signature gating + summary aggregation) — 2-3 h. Two related bugs in `step-riepilogo.tsx`.

After B-01 through B-06 land, re-run Agents 1 + 4 (the two failing epics) to confirm resolution. Epics 2, 3, 5 passed the smoke bar and are re-test-light.
