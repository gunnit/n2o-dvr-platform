"""Add normalized document-image derivatives to environment photos.

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-08-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ambienti_foto",
        sa.Column("document_image_bytes", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "ambienti_foto",
        sa.Column(
            "document_image_content_type", sa.String(length=64), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column("ambienti_foto", "document_image_content_type")
    op.drop_column("ambienti_foto", "document_image_bytes")
