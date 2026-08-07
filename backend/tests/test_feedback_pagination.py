"""Regression coverage for stable offset pagination in admin feedback."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.api.v1.feedback import list_feedback


class _EmptyRows:
    def all(self) -> list[tuple[Any, ...]]:
        return []


class _CapturingSession:
    """Minimal async session that preserves the endpoint's emitted query."""

    statement: Any | None = None

    async def execute(self, statement: Any) -> _EmptyRows:
        self.statement = statement
        return _EmptyRows()


@pytest.mark.asyncio
async def test_list_feedback_uses_unique_tiebreaker_for_offset_pages():
    """Timestamp ties must have a stable order or pages can lose a row."""
    session = _CapturingSession()

    rows = await list_feedback(
        status=None,
        type=None,
        limit=500,
        offset=500,
        admin=SimpleNamespace(organization_id=uuid.uuid4()),
        db=session,
    )

    assert rows == []
    assert session.statement is not None
    assert tuple(str(clause) for clause in session.statement._order_by_clauses) == (
        "user_feedback.created_at DESC",
        "user_feedback.id DESC",
    )
