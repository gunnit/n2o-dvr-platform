"""add ordine to persone

Revision ID: w4x5y6z7a8b9
Revises: v3w4x5y6z7a8
Create Date: 2026-05-26 00:00:00.000000

Feedback #54 (2026-05-25): the survey page listed persone in arbitrary
order because the bulk-add flow (and "copia da altra persona") inserts
multiple rows inside the same transaction, so `created_at` ties broke
to Postgres heap order. Mirrors the o6k7l8m9n0o1 migration that fixed
ambienti — same shape, same backfill strategy.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "w4x5y6z7a8b9"
down_revision: Union[str, None] = "v3w4x5y6z7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "persone",
        sa.Column(
            "ordine",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # Per azienda, assign ordine in created_at order so the operator's
    # insertion sequence is preserved for existing rows.
    op.execute(
        """
        UPDATE persone
        SET ordine = sub.rn - 1
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY azienda_id
                       ORDER BY created_at
                   ) AS rn
            FROM persone
        ) sub
        WHERE persone.id = sub.id
        """
    )


def downgrade() -> None:
    op.drop_column("persone", "ordine")
