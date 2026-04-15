"""add qualifiche to persone (US-1.4)

Revision ID: a8b9c0d1e2f3
Revises: e1f2a3b4c5d6
Create Date: 2026-04-15 20:55:00.000000

US-1.4 persone modal: free-text qualifiche field (attestati, patenti,
corsi di formazione) on every persona. Nullable — existing rows stay
empty and new rows opt in via the modal.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "persone",
        sa.Column("qualifiche", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("persone", "qualifiche")
