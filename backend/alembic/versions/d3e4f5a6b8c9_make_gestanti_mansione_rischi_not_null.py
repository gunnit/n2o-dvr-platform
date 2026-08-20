"""make gestanti mansione rischi not null

Revision ID: d3e4f5a6b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-08-20 00:00:00.000000

``NULL`` is accepted by the API request only as a signal to prefill catalog
risks. The endpoint always persists a JSON array and the response contract
requires one, so existing nulls are safely normalized before enforcing that
invariant in the database.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "d3e4f5a6b8c9"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE gestanti_mansioni_valutazioni "
        "SET rischi = '[]'::jsonb WHERE rischi IS NULL"
    )
    op.alter_column(
        "gestanti_mansioni_valutazioni",
        "rischi",
        existing_type=postgresql.JSONB(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "gestanti_mansioni_valutazioni",
        "rischi",
        existing_type=postgresql.JSONB(),
        nullable=True,
    )
