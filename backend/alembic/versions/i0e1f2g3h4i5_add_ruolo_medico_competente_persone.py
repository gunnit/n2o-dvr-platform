"""add ruolo_medico_competente to persone

Revision ID: i0e1f2g3h4i5
Revises: h9d0e1f2g3h4
Create Date: 2026-04-28 18:00:00.000000

The DVR Master generator queries this flag to populate the Medico Competente
slot in the organigramma table (T009) and the §4 signature block. Without
the column the slot rendered as "—" even when a Persona with mansione
"Medico Competente" was present in the survey.

Backfill on upgrade: any Persona whose `mansione` already mentions "medico"
gets the flag set, so existing seed data immediately surfaces in the docx.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i0e1f2g3h4i5"
down_revision: Union[str, Sequence[str], None] = "h9d0e1f2g3h4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "persone",
        sa.Column(
            "ruolo_medico_competente",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        "UPDATE persone SET ruolo_medico_competente = true "
        "WHERE LOWER(COALESCE(mansione, '')) LIKE '%medico%'"
    )


def downgrade() -> None:
    op.drop_column("persone", "ruolo_medico_competente")
