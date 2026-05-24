"""add misura_miglioramento column to misure_miglioramento table

Revision ID: t1u2v3w4x5y6
Revises: s0o1p2q3r4s5
Create Date: 2026-05-23 12:00:00.000000

Feedback #7: The table needs a dedicated column for the concrete improvement
measure text, separate from the risk description (misura) and the operational
procedure (procedura). AI-generated rows will populate this from the
MisuraSuggerita.titolo field.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "t1u2v3w4x5y6"
down_revision: Union[str, None] = "s0o1p2q3r4s5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "misure_miglioramento",
        sa.Column("misura_miglioramento", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("misure_miglioramento", "misura_miglioramento")
