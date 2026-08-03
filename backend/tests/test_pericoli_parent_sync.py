"""Regression coverage for child-hazard writes keeping their parent in sync."""

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import pericoli


@pytest.mark.asyncio
@pytest.mark.parametrize("count, expected", [(1, True), (0, False)])
async def test_sync_parent_uses_persisted_applicable_child_count(count, expected):
    class CountResult:
        def scalar_one(self):
            return count

    parent = SimpleNamespace(id=uuid.uuid4(), applicabile=not expected)
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()

    await pericoli._sync_parent_applicabile(parent, db)

    db.flush.assert_awaited_once()
    assert parent.applicabile is expected


@pytest.mark.asyncio
async def test_lock_parent_selects_matching_parent_for_update():
    parent = SimpleNamespace(id=uuid.uuid4())

    class ParentResult:
        def scalar_one_or_none(self):
            return parent

    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = ParentResult()
    rischio_id = uuid.uuid4()
    ambiente_id = uuid.uuid4()

    assert await pericoli._lock_parent(rischio_id, ambiente_id, db) is parent

    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "valutazioni_rischio.id =" in sql
    assert rischio_id.hex in sql
    assert "valutazioni_rischio.ambiente_id =" in sql
    assert ambiente_id.hex in sql
    assert "FOR UPDATE" in sql


def test_every_child_write_endpoint_locks_parent_then_syncs_before_commit():
    endpoints = (
        pericoli.create_pericolo_valutazione,
        pericoli.update_pericolo_valutazione,
        pericoli.delete_pericolo_valutazione,
        pericoli.batch_upsert_pericoli,
    )
    for endpoint in endpoints:
        source = inspect.getsource(endpoint)
        assert source.index("parent = await _lock_parent") < source.index(
            "await _sync_parent_applicabile"
        )
        assert source.index("await _sync_parent_applicabile") < source.index(
            "await db.commit()"
        )
