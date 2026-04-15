"""add dpi matrix columns to pos (US-4.8)

Revision ID: c9d0e1f2a3b4
Revises: a7b8c9d0e1f2
Create Date: 2026-04-15 17:00:00.000000

US-4.8 adds three JSONB columns to the ``pos`` table so each POS owns its
own role x phase DPI matrix:

  * dpi_matrix         — {phase_key: {role_key: [dpi_codes]}}. Operator
    edits live here; starts empty and is populated on the first "Rigenera
    dai default" call.
  * dpi_matrix_roles   — selected roles for this POS (subset of
    ROLES_CONSTRUCTION or custom-added strings).
  * dpi_matrix_phases  — selected phases (subset of PHASES_CONSTRUCTION
    or custom strings).

See services/dpi_rules.py for the rules engine that seeds defaults and
app/api/v1/pos.py for the /dpi-matrix endpoint.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pos",
        sa.Column(
            "dpi_matrix",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "pos",
        sa.Column(
            "dpi_matrix_roles",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "pos",
        sa.Column(
            "dpi_matrix_phases",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("pos", "dpi_matrix_phases")
    op.drop_column("pos", "dpi_matrix_roles")
    op.drop_column("pos", "dpi_matrix")
