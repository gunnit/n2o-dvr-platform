"""add misure_miglioramento (DVR §4.1 Programma di Miglioramento)

Revision ID: j1f2g3h4i5j6
Revises: i0e1f2g3h4i5
Create Date: 2026-04-28 19:00:00.000000

The audit (2026-04-28) flagged the DVR §4.1 Programma di Miglioramento as
placeholder-only — 118 pericoli with I>=5 produced zero real misura rows
in the generated docx. This migration creates the table that backs the
T109 grid, with optional FK to the originating pericolo so the auto-seed
pass can run on first generation and operators can edit thereafter.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j1f2g3h4i5j6"
down_revision: Union[str, Sequence[str], None] = "i0e1f2g3h4i5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "misure_miglioramento",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "azienda_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("aziende.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pericolo_valutazione_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pericoli_valutazione.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("misura", sa.Text, nullable=False),
        sa.Column("procedura", sa.Text, nullable=True),
        sa.Column("risorse", sa.Text, nullable=True),
        sa.Column("responsabile", sa.String, nullable=True),
        sa.Column("scadenza", sa.String, nullable=True),
        sa.Column("priorita", sa.String, nullable=True),
        sa.Column(
            "ordine", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_misure_miglioramento_azienda_id",
        "misure_miglioramento",
        ["azienda_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_misure_miglioramento_azienda_id",
        table_name="misure_miglioramento",
    )
    op.drop_table("misure_miglioramento")
