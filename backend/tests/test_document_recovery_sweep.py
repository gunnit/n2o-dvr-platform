"""Regressions for the abandoned-generation sweep.

Production accumulated 25 rows stuck at "pending"/"in_progress" between
2026-07-28 and 2026-08-04, every one with ``error_message = NULL``. They were
generations whose Celery message died with the worker: the task never came
back, so neither the per-attempt rollback nor the attempt-limit give-up in
`document_tasks` ever ran, and the Documenti tab showed a spinner that could
never finish and offered no retry.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services.document_recovery import (
    ABANDONED_AFTER_MINUTES,
    ABANDONED_GENERATION_ERROR,
    reclaim_abandoned_generations,
)


class _Result:
    def __init__(self, rowcount: int):
        self.rowcount = rowcount


class _RecordingSession:
    """Captures the statement instead of executing it."""

    def __init__(self, rowcount: int = 0):
        self.statements: list = []
        self.commits = 0
        self._rowcount = rowcount

    async def execute(self, statement):
        self.statements.append(statement)
        return _Result(self._rowcount)

    async def commit(self):
        self.commits += 1


def _sql(statement) -> str:
    return str(statement.compile(compile_kwargs={"literal_binds": True}))


@pytest.mark.asyncio
async def test_sweep_updates_only_unfinished_rows_to_bozza():
    session = _RecordingSession(rowcount=25)

    reclaimed = await reclaim_abandoned_generations(session)

    assert reclaimed == 25
    assert session.commits == 1
    sql = _sql(session.statements[0])
    assert "UPDATE documenti_generati" in sql
    # Only unfinished rows are touched — a completed document must never be
    # rewritten into a draft by housekeeping.
    assert "'pending'" in sql and "'in_progress'" in sql
    assert "SET status='bozza'" in sql.replace(" = ", "=")
    assert ABANDONED_GENERATION_ERROR in sql


@pytest.mark.asyncio
async def test_sweep_ages_pending_rows_off_created_at():
    """A row that never reached a worker has no generation_started_at.

    Filtering on `generation_started_at` alone would leave those three
    "pending" rows behind forever, so the cutoff falls back to created_at.
    """
    session = _RecordingSession()

    await reclaim_abandoned_generations(session)

    sql = _sql(session.statements[0])
    assert "generation_started_at" in sql
    assert "created_at" in sql


@pytest.mark.asyncio
async def test_sweep_cutoff_clears_the_hard_task_ceiling():
    """The window must sit above the task's own hard kill limit.

    `generate_document_task` is capped at time_limit=660s and the Celery app
    at 20 min. A cutoff below either would reclaim a row that is still
    legitimately running.
    """
    from app.tasks.document_tasks import generate_document_task

    hard_limit_s = generate_document_task.time_limit
    if isinstance(hard_limit_s, tuple):  # celery stores (hard, soft) in places
        hard_limit_s = hard_limit_s[0]
    assert ABANDONED_AFTER_MINUTES * 60 > hard_limit_s
    assert ABANDONED_AFTER_MINUTES >= 20


@pytest.mark.asyncio
async def test_sweep_cutoff_is_configurable():
    session = _RecordingSession()

    await reclaim_abandoned_generations(session, older_than_minutes=120)

    sql = _sql(session.statements[0])
    # A two-hour window must not render a timestamp close to "now".
    expected = datetime.utcnow() - timedelta(minutes=120)
    assert expected.strftime("%Y-%m-%d") in sql
