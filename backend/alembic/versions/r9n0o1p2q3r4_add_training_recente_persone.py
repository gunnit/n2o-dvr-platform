"""add training_recente_completato to persone

Revision ID: r9n0o1p2q3r4
Revises: q8m9n0o1p2q3
Create Date: 2026-05-19 12:00:00.000000

Feedback #3: explicit per-worker flag for whether the most recent mandatory
training cycle is completed (D.Lgs. 81/2008 art. 37). Non-null with a
server-side default of false so existing rows backfill cleanly without a
follow-up UPDATE.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "r9n0o1p2q3r4"
down_revision: Union[str, None] = "q8m9n0o1p2q3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "persone",
        sa.Column(
            "training_recente_completato",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("persone", "training_recente_completato")
