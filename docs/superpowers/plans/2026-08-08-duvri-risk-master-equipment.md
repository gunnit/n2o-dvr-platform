# DUVRI Risk Master Equipment Production Fix

**Goal:** Make every company equipment row from Risk Master visible in the DUVRI workflow and generated DUVRI, while preserving contractor-equipment rule semantics and removing legacy donor equipment from generated files.

**Architecture:** Keep principal-company equipment derived read-only from the existing tenant-scoped `GET /aziende/{id}/attrezzature` API. Continue persisting only canonical contractor activities in `attrezzature_appaltatore`. In the document generator, render principal equipment from `BaseDocumentGenerator.load_data()` and scrub only the legacy template blocks that encode donor equipment, schedules, and equipment-specific measures.

**Tech Stack:** Next.js 16 / React 19 / TypeScript, Node test runner, FastAPI/Python, python-docx, pytest.

## Global Constraints

- The current directory is the scheduler-managed isolated worktree. Do not create a nested worktree or alter `/Users/macbookair/Documents/DVR`.
- Test-first: add each regression, run it, and record the expected red failure before implementation; then run focused green and relevant broader suites.
- Treat Risk Master equipment as principal-company data. Do not insert it into `attrezzature_appaltatore` or feed free-text descriptions into the canonical contractor rules engine.
- Display every equipment row, including equal descriptions belonging to different environments; do not silently deduplicate real records.
- A failed equipment load must be visible in the DUVRI form; it must not be presented as an empty Risk Master.
- Keep UI styling within `frontend/DESIGN.md`; use existing components and responsive patterns.
- Preserve legitimate DUVRI template/legal structure. Remove only anchored donor equipment blocks and tables, then render current principal and contractor data distinctly.
- No migration is required. Legacy DUVRI payloads must continue to validate and generate.
- Never expose production credentials or sensitive feedback/log content in code, tests, commits, or reports.
- Commit Task 1 and Task 2 independently. Do not push or deploy from an implementer task.

---

### Task 1: Surface Risk Master equipment in the DUVRI form

**Files:**
- Create: `frontend/src/app/(dashboard)/assessments/duvri/[aziendaId]/risk-master-equipment.ts`
- Modify: `frontend/src/app/(dashboard)/assessments/duvri/[aziendaId]/page.tsx`
- Create: `frontend/tests/duvri-risk-master-equipment.test.mjs`

**Step 1: Write the failing regression**

Create a pure loader/normalizer test that supplies equipment and environment API fixtures and asserts:

- the loader calls `/api/v1/aziende/{id}/attrezzature` and `/api/v1/aziende/{id}/ambienti`;
- whitespace-only descriptions are omitted;
- descriptions are trimmed;
- two records with the same description but different IDs/environments are both retained;
- environment names are attached when known and a deterministic Italian fallback is used when unknown;
- output order is deterministic by environment, description, then ID.

Run:

```bash
cd frontend && node --experimental-strip-types --test tests/duvri-risk-master-equipment.test.mjs
```

Expected red: the new module/export is missing or the behavioral assertions fail before implementation.

**Step 2: Implement the pure data bridge**

In `risk-master-equipment.ts`, define minimal structural input/output types and export a loader that uses the supplied `apiFetch`, fetches both existing endpoints, and returns display rows without mutating or persisting anything. Reject load failures to the caller.

**Step 3: Wire the DUVRI page**

Load the bridge for the current company, with cancellation protection. In both create and edit dialogs render a distinct read-only section before contractor activities:

- heading `Attrezzature del committente (Rischio Master)` plus the count;
- one compact responsive row per equipment record, with description and environment;
- loading text while pending;
- `Nessuna attrezzatura registrata nel Rischio Master.` only after a successful empty response;
- a visible destructive/error callout on failure.

Leave the existing `Attrezzature / attività appaltatore` selector, payload, and interference analysis unchanged.

**Step 4: Verify focused and broader frontend gates**

Run:

```bash
cd frontend && node --experimental-strip-types --test tests/duvri-risk-master-equipment.test.mjs
cd frontend && node --experimental-strip-types --test tests/*.test.mjs
cd frontend && node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json
cd frontend && node node_modules/next/dist/bin/next build
```

Commit with a focused `fix(duvri): ...` subject and write TDD evidence to the task report.

---

### Task 2: Render current equipment and remove donor equipment from DUVRI DOCX

**Files:**
- Modify: `backend/tests/test_generators.py`
- Modify: `backend/scripts/verify_all_generators.py`
- Modify: `backend/app/services/document_generator/duvri.py`

**Step 1: Write the failing generator regression**

Extend the in-memory fixture with environment-linked Risk Master equipment and one contractor activity. Add a focused generated-DUVRI assertion that proves:

- a table headed `Attrezzatura del committente` / `Ambiente` contains every fixture equipment row exactly once with the correct environment;
- a separate `Tipo` / `Descrizione` table still contains the contractor activity;
- known donor-only content is absent, including `RECOM`, `Carrello elevatore (muletto)`, `Transpallet elettrico`, `Lavatrice ad uso operativo`, `Sabbiatrice`, and `Forno per lavorazioni`;
- the legitimate fixture `Carrello elevatore` appears exactly once, proving donor removal does not erase current data.

Run:

```bash
cd backend && pytest -q tests/test_generators.py -k duvri
```

Expected red: current generated output has no principal-equipment table and still contains donor content.

**Step 2: Implement anchored donor cleanup**

In `duvri.py`, add a narrowly scoped helper that removes these known donor blocks from the legacy template by stable text anchors:

- the donor principal/contractor equipment list;
- donor cronoprogram and equipment-interference tables identified by their donor text;
- the sample equipment-specific measures block;
- the sample welding block tied to the donor company.

Do not remove headers, footers, generic legal text, or unrelated tables. Avoid hard-coded paragraph/table indices.

**Step 3: Render current principal equipment distinctly**

Using `data["attrezzature"]` plus `data["ambienti"]`, add one company-equipment table before per-appalto contractor sections. Preserve every nonblank row and map `ambiente_id` to the current environment name; use `Ambiente non disponibile` when missing. For a successful empty inventory, render `Nessuna attrezzatura registrata nel Rischio Master.`. Keep the existing contractor table unchanged.

**Step 4: Verify focused and broader backend gates**

Run:

```bash
cd backend && pytest -q tests/test_generators.py -k duvri
cd backend && pytest -q tests/test_generators.py::test_all_17_generators_pass
cd backend && python -m scripts.verify_all_generators /private/tmp/dvr-duvri-generator-verify
cd backend && pytest -q
```

Generate a production-like synthetic DUVRI and retain its path for final structural and visual inspection. Commit with a focused `fix(docs): ...` subject and write TDD evidence to the task report.

---

### Task 3: Integration review and release gates

**Files:**
- Review only unless a reviewer identifies a required correction.

**Step 1: Review both commits**

Verify separate root causes, no secrets or sensitive data, no migration, backward compatibility, rollback safety, no contractor-rule semantic change, and a clean worktree.

**Step 2: Browser and document evidence**

Run authenticated DUVRI browser checks at desktop and mobile widths without saving production data. Render the synthetic DOCX through the bundled `render_docx.py` and inspect every page for clipping, overlap, broken tables, donor content, and correct principal/contractor separation.

**Step 3: Reconcile and release**

Fetch fresh `origin/main`, reconcile only in this isolated worktree, rerun affected verification, push a normal fast-forward to `main`, and verify GitHub `main` equals the tested SHA. Poll every affected Render service to a terminal live deployment of that exact SHA.

**Step 4: Production verification**

Repeat the original DUVRI UI probe, use only a safe non-billable document flow if production generation is needed, inspect post-deploy logs for the original signatures and new failures, then mark the target feedback `risolto` only if all required evidence is green. Otherwise keep it `in_revisione` and report the exact blocker.
