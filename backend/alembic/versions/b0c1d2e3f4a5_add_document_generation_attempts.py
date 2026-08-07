"""Add a durable document-generation attempt counter.

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-08-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b0c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _bound_postgres_lock_wait() -> None:
    """Fail the deploy instead of queueing production traffic behind this DDL."""
    if op.get_bind().dialect.name == "postgresql":
        op.execute(sa.text("SET LOCAL lock_timeout = '5s'"))


def upgrade() -> None:
    _bound_postgres_lock_wait()
    op.add_column(
        "documenti_generati",
        sa.Column(
            "generation_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    _bound_postgres_lock_wait()
    op.drop_column("documenti_generati", "generation_attempts")
