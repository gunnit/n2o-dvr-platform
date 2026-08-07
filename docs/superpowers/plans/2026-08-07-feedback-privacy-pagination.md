# Feedback Privacy and Complete Admin Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop public GitHub feedback mirrors from receiving user data and make the tenant admin queue load every feedback row.

**Architecture:** Keep the database and existing tenant-scoped API authoritative. Reduce the public mirror boundary to type-derived fixed copy, and add a small client pagination helper that consumes the existing offset/limit contract.

**Tech Stack:** Python 3.12, FastAPI service helpers, pytest/httpx MockTransport, Next.js 16, React 19, TypeScript, Node test runner.

## Global Constraints

- Work only in the isolated worktree created from fresh `origin/main`; never alter the saved checkout.
- No user-controlled feedback content or personal metadata may enter a public GitHub payload.
- Preserve organization scoping, authorization, issue close/reopen synchronization, and best-effort mirror failure behavior.
- Do not change schemas or migrations.
- Write and observe each regression test failing for the intended reason before implementation.
- Commit the privacy fix and pagination fix separately.

---

### Task 1: Minimize the public GitHub mirror payload

**Files:**
- Modify: `backend/tests/test_github_issues.py`
- Modify: `backend/app/services/github_issues.py`
- Modify: `backend/app/api/v1/feedback.py`

**Interfaces:**
- Consumes: `UserFeedback.type` and configured GitHub labels/repository.
- Produces: `create_issue_from_feedback(fb) -> tuple[int | None, str | None]`, with outbound title/body derived only from `fb.type`.

- [ ] **Step 1: Write the failing privacy regression**

Add a test that captures the real outbound JSON through the existing `httpx.MockTransport`, constructs feedback fields containing `PRIVATE_*` markers, and asserts that neither `PRIVATE_` nor the feedback UUID occurs in the serialized payload. Update the title test to require a type-derived generic title instead of description-derived text.

```python
payload = json.loads(seen["json"])
serialized = json.dumps(payload)
assert "PRIVATE_" not in serialized
assert str(fb.id) not in serialized
assert payload["title"] == "[Bug] Nuova segnalazione DVR"
assert "contenuto non viene copiato" in payload["body"]
```

- [ ] **Step 2: Run the focused test and verify RED**

Run from `backend/`:

```bash
PYTHONPATH=. /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_github_issues.py -q
```

Expected: the privacy regression fails because the current payload contains the private markers and feedback UUID.

- [ ] **Step 3: Implement the minimal structural privacy boundary**

Change the builders and call contract to this shape:

```python
def _feedback_type_label(feedback_type: str) -> str:
    return {"bug": "Bug", "idea": "Idea", "observation": "Osservazione"}.get(
        feedback_type, "Feedback"
    )


def _build_title(feedback_type: str) -> str:
    return f"[{_feedback_type_label(feedback_type)}] Nuova segnalazione DVR"


def _build_body(feedback_type: str) -> str:
    label = _feedback_type_label(feedback_type)
    return (
        f"**Tipo:** {label}\n\n"
        "È disponibile una nuova segnalazione nell'area amministrativa Feedback. "
        "Il contenuto non viene copiato su GitHub per tutelare i dati personali e aziendali."
    )
```

Make `create_issue_from_feedback` accept only `fb`, build title/body from `fb.type`, and remove the user-label argument at the API call site.

- [ ] **Step 4: Verify GREEN and the full mirror contract**

Run:

```bash
PYTHONPATH=. /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_github_issues.py -q
```

Expected: all GitHub mirror tests pass with no warnings or errors.

- [ ] **Step 5: Commit the independently reversible privacy fix**

```bash
git add backend/app/api/v1/feedback.py backend/app/services/github_issues.py backend/tests/test_github_issues.py docs/superpowers/specs/2026-08-07-feedback-privacy-pagination-design.md docs/superpowers/plans/2026-08-07-feedback-privacy-pagination.md
git commit -m "fix: minimize public feedback mirrors"
```

### Task 2: Load the complete admin feedback queue

**Files:**
- Create: `frontend/src/app/(dashboard)/admin/feedback/feedback-pagination.ts`
- Create: `frontend/tests/feedback-pagination.test.mjs`
- Modify: `frontend/src/app/(dashboard)/admin/feedback/page.tsx`

**Interfaces:**
- Consumes: `apiFetch<T>(path)` and rows with stable string `id` values.
- Produces: `fetchAllFeedback<T extends { id: string }>(apiFetch) -> Promise<T[]>` in newest-first order with duplicates removed.

- [ ] **Step 1: Write the failing pagination regression**

Create a Node test that imports the not-yet-implemented helper, returns 500 rows for offset 0 and a short page containing one older duplicate plus one new row for offset 500, and asserts the exact request paths and 501 unique output rows.

```javascript
assert.deepEqual(paths, [
  "/api/v1/feedback?limit=500&offset=0",
  "/api/v1/feedback?limit=500&offset=500",
]);
assert.equal(rows.length, 501);
assert.equal(rows[499].value, "newest-copy");
assert.equal(rows[500].id, "row-500");
```

- [ ] **Step 2: Run the focused test and verify RED**

Run from `frontend/`:

```bash
node --experimental-strip-types --test tests/feedback-pagination.test.mjs
```

Expected: the test fails because `feedback-pagination.ts` does not exist.

- [ ] **Step 3: Implement the pagination helper**

```typescript
const FEEDBACK_PAGE_SIZE = 500;

export async function fetchAllFeedback<T extends { id: string }>(
  apiFetch: (path: string) => Promise<T[]>,
): Promise<T[]> {
  const rowsById = new Map<string, T>();
  let offset = 0;
  while (true) {
    const page = await apiFetch(
      `/api/v1/feedback?limit=${FEEDBACK_PAGE_SIZE}&offset=${offset}`,
    );
    for (const row of page) {
      if (!rowsById.has(row.id)) rowsById.set(row.id, row);
    }
    if (page.length < FEEDBACK_PAGE_SIZE) break;
    offset += page.length;
  }
  return [...rowsById.values()];
}
```

Import the helper in the admin page and replace the single default request with `fetchAllFeedback<FeedbackRow>(apiFetch)`.

- [ ] **Step 4: Verify GREEN and the complete frontend unit suite**

Run:

```bash
node --experimental-strip-types --test tests/feedback-pagination.test.mjs
npm run test:unit
```

Expected: the focused regression and all frontend unit tests pass.

- [ ] **Step 5: Run static and production-build gates**

```bash
npm exec tsc -- --noEmit
npm run lint
npm run build
```

Expected: TypeScript, lint, and the Next.js production build exit 0.

- [ ] **Step 6: Commit the independently reversible pagination fix**

```bash
git add 'frontend/src/app/(dashboard)/admin/feedback/feedback-pagination.ts' 'frontend/src/app/(dashboard)/admin/feedback/page.tsx' frontend/tests/feedback-pagination.test.mjs
git commit -m "fix: load the complete feedback queue"
```

### Task 3: Broader verification and release gates

**Files:**
- Review only: all files changed by Tasks 1 and 2.

**Interfaces:**
- Consumes: the two tested commits and fresh `origin/main`/Render state.
- Produces: exact-SHA release evidence or an explicit blocker with no push/deployment claim.

- [ ] **Step 1: Run broader tests and diff checks**

```bash
cd backend && PYTHONPATH=. /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest
cd ../frontend && npm run test:unit && npm exec tsc -- --noEmit && npm run lint && npm run build
cd .. && git diff --check origin/main...HEAD && git status --short
```

- [ ] **Step 2: Review scope, secrets, privacy, compatibility, and rollback risk**

Confirm that no credentials, raw feedback, sensitive logs, schema changes, dependency changes, or unrelated saved-checkout files are present.

- [ ] **Step 3: Reconcile and push safely**

Fetch `origin/main`, require the tested commits to remain a fast-forward descendant, rerun affected focused tests if the base moved, and push with a normal non-force `git push origin HEAD:main`.

- [ ] **Step 4: Verify exact Render rollout**

Poll API, worker, and frontend until each exact tested SHA reaches terminal `live`; then run health, admin feedback count, mirror-payload contract, and post-deploy error/5xx log checks. Do not claim browser completion unless the authenticated page renders 148 rows and counters `29 nuovo` / `3 in_revisione` or fresh production data explains a different count.
