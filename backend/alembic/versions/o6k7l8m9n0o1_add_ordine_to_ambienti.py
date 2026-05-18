"""add ordine to ambienti

Revision ID: o6k7l8m9n0o1
Revises: n5j6k7l8m9n0
Create Date: 2026-05-18 00:00:00.000000

Feedback #22 (GitHub 381a62cc-6d81-4323-8092-76e257e95512): the survey
listed ambienti in arbitrary order because `list_ambienti` had no
`order_by`. We add an `ordine` column so the API can return them in a
stable, operator-controlled sequence, and seed it for existing rows
using ROW_NUMBER() partitioned by azienda so each azienda's history is
preserved (earliest created_at = ordine 0).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "o6k7l8m9n0o1"
down_revision: Union[str, None] = "n5j6k7l8m9n0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add the column with a server default so existing rows get 0 and
    #    the NOT NULL constraint can be enforced immediately.
    op.add_column(
        "ambienti",
        sa.Column(
            "ordine",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # 2. Backfill: per azienda, assign ordine in created_at order so the
    #    insertion sequence is preserved for existing data.
    op.execute(
        """
        UPDATE ambienti
        SET ordine = sub.rn - 1
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY azienda_id
                       ORDER BY created_at
                   ) AS rn
            FROM ambienti
        ) sub
        WHERE ambienti.id = sub.id
        """
    )


def downgrade() -> None:
    op.drop_column("ambienti", "ordine")
