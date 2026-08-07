# Worker Restart Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent abrupt worker exits from permanently stranding document rows and safely recover the two verified production rows.

**Architecture:** First deploy a backward-compatible attempt-counter migration. Then map the counter, acknowledge only after completion, reject lost child work, leave hard timeouts unacknowledged, allow one automatic recovery, and replay only the idempotent company meter for terminal rows. No queue-topology change.

**Tech Stack:** Python 3.12, Celery 5.6, Redis, SQLAlchemy async sessions, pytest.

## Global Constraints

- Work only in the isolated fresh-origin worktree.
- Preserve billing, authorization, generator dispatch, timeout, and failure-to-`bozza` semantics.
- Deploy the additive migration before any API or worker code references `generation_attempts`; Render can deploy those services in parallel.
- Commit the counter in the existing short pre-generator transaction; never hold a database lock while generating or uploading a document.
- Never create a replacement production version merely to recover the two stranded rows.
- Observe RED before implementation and independently verify GREEN.
- Commit this root-cause group separately from feedback fixes.

---

### Task 1: Deploy the attempt-counter schema first

**Files:**
- Create: `backend/alembic/versions/b0c1d2e3f4a5_add_document_generation_attempts.py`
- Create: `backend/tests/test_document_generation_attempts_migration.py`
- Temporarily modify: `backend/tests/test_schema_drift_db.py`

**Interfaces:**
- Consumes: migration head `a9b0c1d2e3f4`.
- Produces: `generation_attempts INTEGER NOT NULL DEFAULT 0` at head `b0c1d2e3f4a5`.

- [ ] **Step 1: Observe the migration regression RED, then implement the additive migration**

Verify existing rows and inserts that omit the column receive `0`, downgrade removes it, and PostgreSQL DDL sets a five-second local lock timeout before add/drop.

- [ ] **Step 2: Release and verify the migration-only SHA**

Run migration, graph, and schema tests. Deploy the migration-only commit and require successful pre-deploy migration logs before the worker/model release. Remove the narrow schema-drift allowance in Task 2.

### Task 2: Make document tasks durable and bounded

**Files:**
- Create: `backend/tests/test_document_task_recovery.py`
- Modify: `backend/app/models/documento_generato.py`
- Modify: `backend/app/tasks/document_tasks.py`
- Modify: `backend/tests/test_document_generation_attempts_migration.py`
- Modify: `backend/tests/test_schema_drift_db.py`
- Create: `docs/superpowers/specs/2026-08-07-worker-restart-recovery-design.md`
- Create: `docs/superpowers/plans/2026-08-07-worker-restart-recovery.md`

**Interfaces:**
- Consumes: a `DocumentoGenerato.id` delivered through the existing Celery task.
- Produces: late-acknowledged delivery with one bounded recovery, terminal metering repair, and no terminal-row regeneration.

- [ ] **Step 1: Write the failing task-delivery regression**

Assert the actual registered task properties rather than source text:

```python
def test_generation_task_requeues_if_worker_is_lost():
    assert generate_document_task.acks_late is True
    assert generate_document_task.reject_on_worker_lost is True
    assert generate_document_task.acks_on_failure_or_timeout is False
```

- [ ] **Step 2: Write failing attempt-bound and terminal-row regressions**

Prove attempts `0` and `1` commit values `1` and `2` before generator dispatch. Prove a delivery that reads `2` returns the row to `bozza` with cleared partial fields and a safe interruption message without generator, snapshot, Drive, or meter calls. For `completed` and `ready`, prove the row is unchanged, generation/Drive are skipped, and `record_activation_for_azienda` is called once.

- [ ] **Step 3: Run focused RED**

From `backend/`:

```bash
PYTHONPATH=. /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_document_task_recovery.py -q
```

Expected: missing hard-timeout acknowledgement policy, counter mapping/transition, bounded branch, and terminal metering replay all fail for their stated behavior.

- [ ] **Step 4: Implement the smallest coherent recovery state machine**

Map the deployed counter with matching defaults and nullability, remove the temporary drift allowance, replay the idempotent meter for terminal rows, cap generator entry at two committed attempts, and set all three Celery delivery flags.

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

### Task 3: Release and recover the two production rows

**Files:**
- Review: migration files from Task 1 and worker/model files from Task 2.

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
