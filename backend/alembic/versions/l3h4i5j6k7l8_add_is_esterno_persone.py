"""add is_esterno to persone

Revision ID: l3h4i5j6k7l8
Revises: j1f2g3h4i5j6
Create Date: 2026-04-30 09:00:00.000000

Feedback #10 (Luca Marchetti, 2026-04-29): the Medico Competente and the
RSPP are frequently external consultants rather than employees of the
client. The DVR organigramma must label them as such, and the survey UI
needs a checkbox so the operator can flag them.

This migration intentionally chains off j1f2g3h4i5j6 (the last
production-applied head), NOT off the uncommitted MMC migration
k2g3h4i5j6k7 which is local WIP and not yet on Render.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "l3h4i5j6k7l8"
down_revision: Union[str, Sequence[str], None] = "j1f2g3h4i5j6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "persone",
        sa.Column(
            "is_esterno",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("persone", "is_esterno")
