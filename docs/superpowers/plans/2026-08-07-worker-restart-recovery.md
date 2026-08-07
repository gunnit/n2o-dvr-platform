# Worker Restart Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent abrupt worker exits from permanently stranding document rows and safely recover the two verified production rows.

**Architecture:** Configure the existing document Celery task for acknowledgement after completion, reject abruptly lost child work, and short-circuit persisted terminal rows so post-commit redelivery is idempotent. No schema or queue-topology change.

**Tech Stack:** Python 3.12, Celery 5.6, Redis, SQLAlchemy async sessions, pytest.

## Global Constraints

- Work only in the isolated fresh-origin worktree.
- Preserve billing, authorization, generator dispatch, timeout, and failure-to-`bozza` semantics.
- Never create a replacement production version merely to recover the two stranded rows.
- Observe RED before implementation and independently verify GREEN.
- Commit this root-cause group separately from feedback fixes.

---

### Task 1: Make document tasks durable across worker loss

**Files:**
- Create: `backend/tests/test_document_task_recovery.py`
- Modify: `backend/app/tasks/document_tasks.py`
- Create: `docs/superpowers/specs/2026-08-07-worker-restart-recovery-design.md`
- Create: `docs/superpowers/plans/2026-08-07-worker-restart-recovery.md`

**Interfaces:**
- Consumes: a `DocumentoGenerato.id` delivered through the existing Celery task.
- Produces: the same task result and document lifecycle, but the broker acknowledgement occurs only after task return and terminal rows are not regenerated.

- [ ] **Step 1: Write the failing task-delivery regression**

Assert the actual registered task properties rather than source text:

```python
def test_generation_task_requeues_if_worker_is_lost():
    assert generate_document_task.acks_late is True
    assert generate_document_task.reject_on_worker_lost is True
```

- [ ] **Step 2: Write the failing completed-row idempotency regression**

Patch `async_session_factory` with a minimal async session returning a completed document. Patch generator lookup, billing metering, and upload boundaries to fail the test if reached. Await `_run_generation(document_id)` and assert the row is unchanged and the session did not commit.

- [ ] **Step 3: Run focused RED**

From `backend/`:

```bash
PYTHONPATH=. /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_document_task_recovery.py -q
```

Expected: the task configuration assertion fails on `acks_late=False` / missing worker-loss rejection, and the terminal-row test proves current code incorrectly enters generation.

- [ ] **Step 4: Implement the minimal recovery boundary**

In `_run_generation`, after loading the row and before any mutation:

```python
if doc.status in {"completed", "ready"}:
    logger.info("Document %s already completed; skipping redelivery", document_id)
    return
```

On the existing task decorator add:

```python
acks_late=True,
reject_on_worker_lost=True,
```

- [ ] **Step 5: Verify focused GREEN and worker invariants**

```bash
PYTHONPATH=. /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_document_task_recovery.py -q
PYTHONPATH=. /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_billing_enforcement.py tests/test_document_task_recovery.py -q
```

- [ ] **Step 6: Commit independently**

```bash
git add backend/app/tasks/document_tasks.py backend/tests/test_document_task_recovery.py docs/superpowers/specs/2026-08-07-worker-restart-recovery-design.md docs/superpowers/plans/2026-08-07-worker-restart-recovery.md
git commit -m "fix: recover document tasks after worker loss"
```

### Task 2: Release and recover the two production rows

**Files:**
- Review only: Task 1 files.

**Interfaces:**
- Consumes: exact tested SHA and the two authorized production row IDs.
- Produces: both original rows terminal on the exact fixed SHA, or an explicit active blocker.

- [ ] **Step 1: Run the complete backend suite and diff/security review**

```bash
PYTHONPATH=. /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest
git diff --check origin/main...HEAD
```

Confirm no migrations, credentials, raw logs, production IDs, or unrelated files are committed.

- [ ] **Step 2: Re-fetch and push safely**

Fetch `origin/main`, require fast-forward ancestry, rerun affected tests if the base moved, and push normally without force.

- [ ] **Step 3: Verify the exact worker rollout**

Poll the worker deployment until the exact tested SHA reaches terminal `live`. Verify API and frontend rollout of the same repository SHA before recovery.

- [ ] **Step 4: Requeue the two original rows once**

Resolve the full IDs through the authorized production session without emitting them in logs or reports. Dispatch each existing ID once through the production Celery task. Do not create new document rows.

- [ ] **Step 5: Verify recovery and post-deploy health**

Poll the two original records until both are `completed` with file content, or until a terminal `bozza` error supplies an actionable failure. Correlate task terminal events and inspect API, worker, PostgreSQL, Redis, frontend, migration, and deployment logs for new failures, duplicates, the original stranded signature, and 5xx responses.
