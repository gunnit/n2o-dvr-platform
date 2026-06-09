"""add attrezzature to haccp_config

Revision ID: y6z7a8b9c0d1
Revises: x5y6z7a8b9c0
Create Date: 2026-06-08 12:00:00.000000

Feedback #65: HACCP needs an equipment list with a flag marking which items
are subject to HACCP control. Stored as a JSONB column on `haccp_config`
shaped as `[{nome: str, sotto_controllo_haccp: bool}]`. JSONB (rather than a
side table) because the list is always read with the config row and never
joined or filtered on — same rationale as `ccps` / `tipi_alimenti_trattati`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "y6z7a8b9c0d1"
down_revision: Union[str, None] = "x5y6z7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOT NULL with a server default of '[]' so existing rows immediately
    # satisfy the constraint and the column is safe to read everywhere.
    op.add_column(
        "haccp_config",
        sa.Column(
            "attrezzature",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("haccp_config", "attrezzature")
