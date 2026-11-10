"""add azienda_foto_presentazione (company photo for the DVR) (2026-11-10)

Revision ID: f2a3b4c5d6e8
Revises: e1f2a3b4c5d7
Create Date: 2026-11-10

One normalised JPEG per azienda, printed under "Presentazione dell'azienda" in
the DVR. Kept in its own table (1:1, unique azienda_id, cascade delete) so
azienda list queries never load the bytes; bytes live in the database because
the Celery worker does not share the API's disk.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a3b4c5d6e8"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "azienda_foto_presentazione",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("document_image_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("azienda_id"),
    )


def downgrade() -> None:
    op.drop_table("azienda_foto_presentazione")
