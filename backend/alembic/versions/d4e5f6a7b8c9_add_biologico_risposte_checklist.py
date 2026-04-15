"""add risposte_checklist column to biologico_valutazioni

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add JSONB column that persists the sector checklist responses.

    Each row is a list of {id: str, risposta: "SI"|"NO"|"NA"}. Only the
    Biologico assessment needs this field because its risk classification
    is driven by a sector-specific checklist rather than a continuous
    calculation.
    """
    op.add_column(
        "biologico_valutazioni",
        sa.Column(
            "risposte_checklist",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("biologico_valutazioni", "risposte_checklist")
