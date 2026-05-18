"""add destinazione_uso to sostanze_chimiche

Revision ID: q8m9n0o1p2q3
Revises: p7l8m9n0o1p2
Create Date: 2026-05-18 19:00:00.000000

Feedback #35 (GitHub issue 35): the DVR inventory table needs a separate
"Destinazione d'uso" column distinct from the existing "Attività / Uso".
"Attività / Uso" is what the operator manually declares (where in the
workplace the chemical is used); "destinazione_uso" is the manufacturer-
declared identified use from SDS Section 1.2, populated automatically by
the AI extractor.

Nullable Text — manual rows leave it None, AI fills it on extraction.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q8m9n0o1p2q3"
down_revision: Union[str, None] = "p7l8m9n0o1p2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sostanze_chimiche",
        sa.Column("destinazione_uso", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sostanze_chimiche", "destinazione_uso")
