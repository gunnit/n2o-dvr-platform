"""add attrezzature_speciali to persone (feedback 2026-04-28)

Revision ID: g8c9d0e1f2g3
Revises: f7b8c9d0e1f2
Create Date: 2026-04-28 11:00:00.000000

User feedback (admin/feedback #8 + #7) asked for "qualifiche" to stop
being a free-text field and become a structured set of flags for the
specific equipment / driving authorisations the worker is qualified
to use. The existing `qualifiche` column is repurposed as a free-text
"note" field (renamed in the UI), and a new JSONB array column stores
the canonical codes from the predefined set defined alongside the
frontend constant ATTREZZATURE_SPECIALI.

Codes are kept short and stable so they survive label tweaks:
  lavori_in_quota, carrello_elevatore, ple, gru, ruspa_escavatore,
  patente_cde, adr.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "g8c9d0e1f2g3"
down_revision: Union[str, Sequence[str], None] = "0a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "persone",
        sa.Column(
            "attrezzature_speciali",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("persone", "attrezzature_speciali")
