"""add mansione column to stress_valutazioni

Revision ID: u2v3w4x5y6z7
Revises: t1u2v3w4x5y6
Create Date: 2026-05-23 18:00:00.000000

Feedback #17: per-mansione stress assessments. Adds a nullable `mansione`
column so operators can run separate INAIL checklist evaluations for each
job role (Operaio, Impiegato, Dirigente, etc.) instead of a single
company-wide assessment. NULL = "Generale" (backward-compatible).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "u2v3w4x5y6z7"
down_revision: Union[str, None] = "t1u2v3w4x5y6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stress_valutazioni",
        sa.Column("mansione", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stress_valutazioni", "mansione")
