"""add sedi_operative_extra to aziende

Revision ID: p7l8m9n0o1p2
Revises: o6k7l8m9n0o1
Create Date: 2026-05-18 01:00:00.000000

Feedback #11 (GitHub 3088e45a-7772-48e3-b5e5-2846eb452635): clients with
more than one operating address need a way to declare them all. We add a
JSONB column on `aziende` that carries the extras as
`[{via, citta, comune, provincia, cap}]`. The primary `sede_operativa_*`
columns stay as the headquarters address; this column holds everything
else.

JSONB beat a separate `sedi_operative` table because (a) every consumer
needs the list together with the azienda row, (b) the extras are never
joined or filtered on, and (c) it keeps the migration trivial and
fully online.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "p7l8m9n0o1p2"
down_revision: Union[str, None] = "o6k7l8m9n0o1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOT NULL with a server default of '[]' so existing rows immediately
    # satisfy the constraint and the column is safe to read everywhere.
    op.add_column(
        "aziende",
        sa.Column(
            "sedi_operative_extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("aziende", "sedi_operative_extra")
