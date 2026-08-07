"""Regression coverage for the durable document-generation attempt counter."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _load_migration():
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "b0c1d2e3f4a5_add_document_generation_attempts.py"
    )
    spec = importlib.util.spec_from_file_location(
        "document_generation_attempts_migration", migration_path
    )
    migration = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migration)
    return migration


def test_document_attempt_counter_migration_upgrades_and_downgrades_sqlite(monkeypatch):
    """The counter is defaulted for existing and newly inserted document rows."""
    migration = _load_migration()

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE documenti_generati (id INTEGER PRIMARY KEY)"
        )
        connection.execute(text("INSERT INTO documenti_generati (id) VALUES (1)"))
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(migration, "op", operations)

        migration.upgrade()

        column = next(
            item
            for item in inspect(connection).get_columns("documenti_generati")
            if item["name"] == "generation_attempts"
        )
        assert column["nullable"] is False
        assert column["type"].python_type is int
        assert str(column["default"]) == "0"

        connection.execute(text("INSERT INTO documenti_generati (id) VALUES (2)"))
        assert connection.execute(
            text("SELECT id, generation_attempts FROM documenti_generati ORDER BY id")
        ).all() == [(1, 0), (2, 0)]

        migration.downgrade()
        assert {
            item["name"] for item in inspect(connection).get_columns("documenti_generati")
        } == {"id"}


class _PostgresOperationsSpy:
    def __init__(self):
        self.calls: list[tuple[str, Any]] = []

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    def execute(self, statement):
        self.calls.append(("execute", str(statement)))

    def add_column(self, table_name, column):
        self.calls.append(("add_column", (table_name, column.name)))

    def drop_column(self, table_name, column_name):
        self.calls.append(("drop_column", (table_name, column_name)))


def test_document_attempt_counter_migration_bounds_postgres_lock_wait(monkeypatch):
    migration = _load_migration()
    operations = _PostgresOperationsSpy()
    monkeypatch.setattr(migration, "op", operations)

    migration.upgrade()
    assert operations.calls == [
        ("execute", "SET LOCAL lock_timeout = '5s'"),
        ("add_column", ("documenti_generati", "generation_attempts")),
    ]

    operations.calls.clear()
    migration.downgrade()
    assert operations.calls == [
        ("execute", "SET LOCAL lock_timeout = '5s'"),
        ("drop_column", ("documenti_generati", "generation_attempts")),
    ]
