"""add options JSONB column to documenti_generati (US-4.4)

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-04-15 21:20:00.000000

US-4.4 HACCP forms subset dialog: the operator can deselect specific forms
before generation. We persist the selection as ``options.selected_codes``
on the DocumentoGenerato row so the async worker (or the admin looking
at history later) can see exactly which subset was requested.

Column is nullable JSONB — every other generator leaves it empty.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b9c0d1e2f3a4"
# Chains after Agent-B's a9c0d1e2f3b4 (misure libreria) so the migration
# graph stays linear when both sessions land in the same commit run.
down_revision: Union[str, None] = "a9c0d1e2f3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documenti_generati",
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documenti_generati", "options")
