"""add file_content and file_name to documenti_generati

Store generated document bytes in Postgres so the API service can serve
downloads without sharing a filesystem with the Celery worker.

Revision ID: e4f5a6b7c8d9
Revises: cc08e747b268
Create Date: 2026-04-17 01:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "cc08e747b268"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documenti_generati",
        sa.Column("file_content", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "documenti_generati",
        sa.Column("file_name", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documenti_generati", "file_name")
    op.drop_column("documenti_generati", "file_content")
