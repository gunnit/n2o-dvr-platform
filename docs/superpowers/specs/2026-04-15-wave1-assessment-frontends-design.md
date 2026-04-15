# Wave 1 — Closing PARTIAL Assessment Frontends (Parallel)

**Version**: 1.0
**Date**: 2026-04-15
**Scope**: Move 9 user stories from PARTIAL to DONE across four assessment domains (MMC, Incendio, Gestanti, Biologico) by completing the operator data-entry UI.
**Execution**: 4 parallel agents, one per assessment cluster.
**Backend**: No new calculators. New static lookup data + (Gestanti only) one cross-reference endpoint.

---

## 1. Goal & Non-Goals

### Goal

Close every "Missing" bullet listed in `docs/context/USER_STORIES.md` for these stories:

- **MMC**: US-3.1, US-3.2, US-3.3
- **Incendio**: US-3.11, US-3.12
- **Gestanti**: US-3.9, US-3.10
- **Biologico**: US-3.15

After this batch, the Progress Summary table moves from "Epic 3 — DVR Attachments: 27%" toward ~50%.

### Non-Goals (deferred)

- Generator output changes — existing `.docx` output already validated (sprint 2026-04-14, `verify_all_generators` 17/17 PASS).
- Wiring assessments into the survey wizard navigation.
- Shared component library extraction — each agent builds local components; we refactor in a follow-up if patterns emerge.
- VDT / Stress / Microclima — those are NOT STARTED stories, separate scope.
- Photo uploads (US-1.3), audit-log endpoint wiring (US-5.3), offline mode — separate batches.

---

## 2. Current State (verified 2026-04-15)

| Cluster | Page LOC | Form component | Backend calculator | Generator |
|---|---|---|---|---|
| MMC | 202 (`page.tsx`) + `mmc-form.tsx` | exists | `POST /calculate/niosh` (PLR, IR, zona) | `allegato_mmc.py` |
| Incendio | 237 + `incendio-form.tsx` | exists | `POST /calculate/fire-risk` | `allegato_incendio.py` |
| Gestanti | 123 (stub, no form component) | **missing** | none yet | `allegato_gestanti.py` |
| Biologico | 74 (stub, no form component) | **missing** | none (sector-driven static) | `allegato_biologico_*.py` × 3 |

---

## 3. Cross-Cutting Conventions (all 4 agents)

### 3.1 Stack rules

- **Next.js 16.2.3** with App Router — `frontend/AGENTS.md` warns this differs from training data. Agents MUST consult `frontend/node_modules/next/dist/docs/01-app/` before writing route handlers, params handling, or server actions. In particular: `params` in dynamic route segments is a Promise in Next 16; the existing Gestanti and Biologico stubs use it synchronously and must be migrated.
- **Forms**: react-hook-form + zod (already installed). Use shadcn `Form`, `Input`, `Slider`, `RadioGroup`, `Select`, `Textarea`.
- **State persistence**: use the existing assessment endpoints (extend if needed). No localStorage as primary store.
- **Auth pattern**: copy the `getSessionToken()` pattern from the MMC page (calls `/api/auth/session`).

### 3.2 UX rules

- **All copy in Italian**. Errors, labels, button text, badges. Domain glossary in `CLAUDE.md`.
- **Save model**: explicit "Salva valutazione" button + dirty-state badge ("Modifiche non salvate"). No auto-save in this batch.
- **Live preview**: where a calculation exists (MMC, Incendio), call `/calculate/*` on debounced input change to show real-time bands.
- **Color bands**: reuse the existing token palette already used in `incendio/page.tsx` (`emerald` / `amber` / `rose`) — don't invent new color tokens.
- **Validation feedback**: red border + inline `<FieldError>` on blur (matches survey wizard pattern in Step 1).
- **Mobile**: forms must work on tablet (≥768px primary, ≥375px functional). Field operators use tablets in the field.

### 3.3 Component layout (per agent)

```
frontend/src/
  app/(dashboard)/assessments/<name>/[aziendaId]/page.tsx   # owns auth, azienda load, finalize
  components/assessments/<name>/                            # owned by this agent
    <name>-form.tsx        # main form
    <name>-result.tsx      # band display (where applicable)
    <name>-measures.tsx    # measures section (where applicable)
```

Agents MUST NOT touch each other's directories.

### 3.4 Backend additions (per agent)

Each agent owns a single new file in `backend/app/data/` (new directory) for static lookup tables. Gestanti also adds one endpoint. No DB migrations — assessment models already cover required fields per the 2026-04-14 sprint.

### 3.5 Verification (per agent, before reporting done)

1. `cd backend && pytest tests/` — all green
2. `cd frontend && npx tsc --noEmit` — no type errors
3. `cd frontend && npm run lint` — no new lint errors
4. Manual: load page in dev, fill the happy path, hit "Salva", confirm 200 response and persistence on reload
5. Capture screenshot of the completed form into `docs/qa/<name>/<name>-01-complete.png`

---

## 4. Per-Agent Specs

### 4.1 Agent A1 — MMC (NIOSH)

**Stories closed**: US-3.1, US-3.2, US-3.3

**Files (exclusive)**:
- `frontend/src/app/(dashboard)/assessments/mmc/[aziendaId]/page.tsx` (modify)
- `frontend/src/components/assessments/mmc/*` (new dir; current `mmc-form.tsx` migrates here as `mmc-form.tsx`)
- `backend/app/data/__init__.py` (create — first agent to land creates it; if conflict, just leave existing)
- `backend/app/data/niosh_cp.py` (new)

**Backend additions**:
- `niosh_cp.py` exports `get_default_cp(sesso: Literal["M", "F"], eta: int) -> int` per the NIOSH reference table:
  - M giovane (15-18): 20 kg
  - M adulto (18-45): 25 kg
  - M anziano (>45): 20 kg
  - F giovane (15-18): 15 kg
  - F adulto (18-45): 20 kg
  - F anziano (>45): 15 kg
- Reference: `docs/context/REFERENCE_DATA.md` NIOSH section.

**Frontend additions**:
- **Multi-lift support** (US-3.1): "Aggiungi sollevamento" button appends a new parameter set to a `useFieldArray`. Each set computed independently. Per-set delete.
- **Auto-CP** (US-3.2): on form mount or when worker selected, call new `GET /api/v1/calculations/niosh-cp?sesso=M&eta=30` to retrieve default CP; field shows the value with an "Auto" badge. "Modifica CP" button unlocks the field and reveals a required `motivazione` textarea (zod: min 5 chars).
- **Range validation** (US-3.1): per-field zod schemas with Italian error text (`"Valore consentito: 0–175 cm"` etc.). Field excluded from calculation submission until valid.
- **Mandatory measures section** (US-3.3): when any computed IR > 1.0, render a non-collapsible "Misure obbligatorie" card below the result — pre-populated list from a static array of organizational/technical measures (4 items, see `REFERENCE_DATA.md`), each editable, with "Aggiungi misura" button.

**Backend endpoint**:
- Add `GET /api/v1/calculations/niosh-cp` to `backend/app/api/v1/calculations.py` (single small handler).

**Acceptance evidence**:
- Three screenshots: `mmc-01-single-lift.png`, `mmc-02-multi-lift-red.png`, `mmc-03-cp-override.png`

---

### 4.2 Agent A2 — Incendio (Fire Risk)

**Stories closed**: US-3.11, US-3.12

**Files (exclusive)**:
- `frontend/src/app/(dashboard)/assessments/incendio/[aziendaId]/page.tsx` (modify)
- `frontend/src/components/assessments/incendio/*` (new dir; migrate `incendio-form.tsx`)
- `backend/app/data/fire_measures.py` (new)

**Backend additions**:
- `fire_measures.py` exports `get_measures_for_level(livello: Literal["Basso", "Medio", "Alto"]) -> list[str]`. Source: existing `AZIONE_PER_LIVELLO` text in `incendio/page.tsx` is a single paragraph; this splits into discrete checklist items per level (3-5 measures each, derived from D.M. 03/09/2021 reference cited in `LEGISLATION_REFERENCE.md`).

**Frontend additions**:
- **Multi-area support** (US-3.11): `useFieldArray` of homogeneous areas; each with its own INF/SI/PI. "Duplica area" button copies current area's values into a new entry (keeps `nome` empty). Per-area delete with confirm.
- **Live sum + band per area**: existing pattern works for single area; extend to per-area cards.
- **Range validation tooltip** (US-3.11): on out-of-range entry, shadcn tooltip `"Valore consentito: 1–3"` (Slider with marks 1-2-3 makes this naturally constrained, but type-in fallback for keyboard users still validates).
- **Measures list per level** (US-3.12): when band changes, fetch measures from new endpoint and render checklist below the result. User can check/uncheck and add custom measures.
- **VVF banner for Alto** (US-3.12): when any area's livello is "Alto", render a sticky banner above the form: red, with text `"⚠ Richiesta valutazione approfondita VV.F. — rischio Alto rilevato in almeno un'area."` (no emoji per project rule — use Lucide `AlertTriangle` icon instead).

**Backend endpoint**:
- Add `GET /api/v1/calculations/fire-measures?livello=Alto` to `calculations.py`.

**Acceptance evidence**:
- Two screenshots: `incendio-01-medio.png`, `incendio-02-alto-vvf-banner.png`

---

### 4.3 Agent A3 — Gestanti (D.Lgs. 151/2001)

**Stories closed**: US-3.9, US-3.10

**Files (exclusive)**:
- `frontend/src/app/(dashboard)/assessments/gestanti/[aziendaId]/page.tsx` (rewrite — current is a stub)
- `frontend/src/components/assessments/gestanti/*` (new)
- `backend/app/data/dlgs_151_2001.py` (new — risk catalog from Allegati A/B/C)
- `backend/app/api/v1/gestanti.py` (new)
- `backend/app/api/v1/router.py` (modify — register new router)

**Backend additions**:
- `dlgs_151_2001.py` exports `INCOMPATIBLE_RISKS: dict[RiskKey, RiskInfo]` mapping risk identifiers (e.g., `"manual_handling_heavy"`, `"chemical_exposure_cmr"`, `"ionizing_radiation"`) to `{"allegato": "A"|"B"|"C", "descrizione": str, "incompatible_mansione_keywords": list[str]}`. Initial catalog: 12-15 entries covering the most common cross-references (manual lifting, CMR chemicals, radiation, biological hazards, night shifts, vibrations).
- `gestanti.py` exposes:
  - `POST /api/v1/aziende/{azienda_id}/gestanti/cross-reference` — body: `{worker_id: int}` — response: `{matches: [{risk_key, allegato, descrizione, suggested_alternative_mansione: str | null}], cleared: bool}`. Logic: load worker mansione, scan `INCOMPATIBLE_RISKS` for keyword overlap, propose an alternative from the same azienda's other mansioni that has zero matches.
  - `POST /api/v1/gestanti/{valutazione_id}/decision` — body: `{risk_key, action: "accept"|"reject", justification?: str, misura_alternativa?: str}` — persists into `GestantiValutazione` model (extend if needed).

**Frontend additions**:
- **Worker selector** at top: dropdown of female workers from this azienda.
- **Cross-reference panel** (US-3.9): on worker select, calls cross-reference endpoint. Renders match list with `Allegato` badge (A/B/C) and risk description. Workers with zero matches show green `"Nessun rischio identificato"` indicator.
- **Relocation flow** (US-3.10): per match row, two buttons — "Accetta riallocazione" / "Rifiuta". Accept opens a small dialog requiring `justification` (textarea, min 10 chars) before persist. Reject opens a dialog requiring `misura_alternativa` (textarea, min 10 chars).
- **"Nuovo" flag**: when re-loading after a survey update introduced new risks, matches that weren't in the prior valutazione carry a `Nuovo` badge (server tracks via comparing against last persisted decision set).
- **Existing signature block** preserved at the bottom.

**Acceptance evidence**:
- Three screenshots: `gestanti-01-no-risks.png`, `gestanti-02-matches.png`, `gestanti-03-relocation-dialog.png`

---

### 4.4 Agent A4 — Biologico (D.Lgs. 81/2008 Titolo X)

**Stories closed**: US-3.15

**Files (exclusive)**:
- `frontend/src/app/(dashboard)/assessments/biologico/[aziendaId]/page.tsx` (rewrite — current is a stub)
- `frontend/src/components/assessments/biologico/*` (new)
- `backend/app/services/document_generator/reference_data_biologico.py` (extend — already exists)

**Backend additions**:
- Extend existing `reference_data_biologico.py` to expose three constants:
  - `ALIMENTARE_CHECKLIST: list[ChecklistItem]` (~10-12 items: HACCP procedures, separazione carni/verdure, formazione, sanificazione, controllo temperature, ecc.)
  - `ASILO_CHECKLIST: list[ChecklistItem]` (~10-12: vaccinazioni, controllo stato salute, gestione rifiuti, DPI, ecc.)
  - `DENTISTI_CHECKLIST: list[ChecklistItem]` (~10-12: sterilizzazione strumenti, DPI, vaccinazioni HBV, gestione taglienti, ecc.)
- Each `ChecklistItem`: `{id: str, descrizione: str, criticita: Literal["alta", "media", "bassa"]}`.
- Expose via new endpoint `GET /api/v1/calculations/biologico-checklist?settore=alimentare`.

**Frontend additions**:
- **Sector selector** (existing) drives checklist load.
- **Per-item SI/NO/NA toggles** with criticità badge.
- **Live classification**: count of NO answers weighted by criticità → risk level (Basso/Medio/Alto) using simple formula (alta=3, media=2, bassa=1; sum > threshold = Alto).
- **Protocollo sanitario textarea** (existing) preserved.
- **Save**: persists to `BiologicoValutazione` (extend model field if needed for checklist responses — should already be JSON column per sprint notes; verify).

**Acceptance evidence**:
- Three screenshots: `biologico-01-alimentare.png`, `biologico-02-asilo.png`, `biologico-03-dentisti-alto.png`

---

## 5. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Two agents independently create `backend/app/data/__init__.py` and conflict | Orchestrator (me) creates the empty `__init__.py` and commits BEFORE dispatching agents |
| `params` Promise migration breaks gestanti/biologico stubs | Spec explicitly calls this out; agents must read Next 16 docs |
| New `BiologicoValutazione` field needed for checklist responses → migration | Verify before dispatch; if field missing, orchestrator adds Alembic migration first |
| Different agents pick different patterns for "Salva" UX | Conventions section is explicit; orchestrator code-reviews all four diffs before committing |
| Gestanti cross-reference logic depends on mansione naming consistency | Use keyword-based fuzzy matching, not exact equality; document the limitation |

---

## 6. Done Definition (whole batch)

- All 9 stories' "Missing" bullets from `USER_STORIES.md` are closed
- `docs/context/USER_STORIES.md` Progress Summary updated; affected stories flipped to `DONE`
- `pytest backend/tests/` green (16/16 + any new tests)
- `npx tsc --noEmit` and `npm run lint` clean in `frontend/`
- 11 screenshots captured in `docs/qa/{mmc,incendio,gestanti,biologico}/`
- Single commit per agent (4 commits) on `main`, then orchestrator commits the USER_STORIES.md update as the 5th
- Pushed to origin

---

*Spec authored 2026-04-15. Implementation plan produced separately by writing-plans skill.*
