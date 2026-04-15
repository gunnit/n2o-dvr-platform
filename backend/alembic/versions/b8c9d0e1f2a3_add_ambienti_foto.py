"""add ambienti_foto table for work environment photo attachments (US-1.3)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-04-15 17:00:00.000000

Adds the `ambienti_foto` table that stores photo uploads attached to a
work environment (Ambiente) during the digital survey. Each row tracks
the original filename, on-disk path, MIME type, and size so the frontend
can render a thumbnail grid with metadata and a delete control.

See api/v1/ambienti.py for the POST/GET/DELETE endpoints and the
10-photos-per-ambiente enforcement.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ambienti_foto",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ambiente_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ambiente_id"], ["ambienti.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ambienti_foto_ambiente_id",
        "ambienti_foto",
        ["ambiente_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ambienti_foto_ambiente_id", table_name="ambienti_foto")
    op.drop_table("ambienti_foto")
