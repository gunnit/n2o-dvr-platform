"""add interference columns to duvri (US-4.6)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-15 09:30:00.000000

Adds two JSONB columns to the duvri table to power the interference rules
engine:

  * attrezzature_appaltatore — list[{tipo, descrizione}] of contractor
    activities/equipment used to feed evaluate_rules().
  * interferenze_decisioni    — list[{rule_id, decision, custom_text}]
    capturing accept/reject choices the operator made on suggested rules.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "duvri",
        sa.Column(
            "attrezzature_appaltatore",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "duvri",
        sa.Column(
            "interferenze_decisioni",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("duvri", "interferenze_decisioni")
    op.drop_column("duvri", "attrezzature_appaltatore")
