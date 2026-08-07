"""The SQLAlchemy models and the migration chain must describe the same schema.

When they disagree, ``alembic revision --autogenerate`` silently folds the
pre-existing drift into whatever unrelated migration you happened to be
generating — which is how a bad migration reaches production. Before this guard
existed there were 17 such diffs (tz-naive ``DateTime`` on four tables,
``String`` where the DB had ``TEXT``, nine indexes created by migration but
never declared on a model, and one index whose model-derived name did not match
the name the migration gave it).

This test fails the moment that gap reopens, so autogenerate stays trustworthy.

Skipped when no Postgres is reachable, so the default local run stays
dependency-free. CI provides one (see .github/workflows/backend-ci.yml).

The DATABASE_URL this runs against must be migrated to head first — the
comparison is meaningless otherwise, and a DB stuck at an older revision would
report every migration since as spurious drift.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db.base import Base
from app.db.session import _normalize_async_url
from app.models import *  # noqa: F401, F403 — register every model on Base.metadata

_URL = _normalize_async_url(os.environ["DATABASE_URL"]) if os.environ.get("DATABASE_URL") else None


def _diff(connection) -> list:
    return compare_metadata(MigrationContext.configure(connection), Base.metadata)


@pytest.mark.skipif(_URL is None, reason="no DATABASE_URL — needs a migrated Postgres")
def test_models_match_migrated_schema() -> None:
    """Migration head and the complete model metadata match exactly."""
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _go() -> list:
        engine = create_async_engine(_URL)
        try:
            async with engine.connect() as conn:
                return await conn.run_sync(_diff)
        finally:
            await engine.dispose()

    diffs = asyncio.run(_go())

    assert diffs == [], (
        "Models and migrations disagree in "
        f"{len(diffs)} place(s). Autogenerate is no longer trustworthy — it will "
        "fold these into the next unrelated migration.\n\n"
        + "\n".join(f"  - {d}" for d in diffs)
        + "\n\nDecide per diff which side is right: fix the model (preferred — no "
        "migration needed) or write a corrective migration. Never drop an index "
        "production queries rely on."
    )
