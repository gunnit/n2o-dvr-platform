"""add gdoc_file_id to documenti_generati

Track the editable Google Doc ID created when the user opens a document
for in-browser editing. Kept separate from gdrive_file_id (which points
to the archival .docx) so regeneration and editing don't collide.

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-04-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documenti_generati",
        sa.Column("gdoc_file_id", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documenti_generati", "gdoc_file_id")
