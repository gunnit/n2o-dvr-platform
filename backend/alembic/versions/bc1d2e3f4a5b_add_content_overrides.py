"""add content_overrides JSONB to documenti_generati

Inline preview editing: per-paragraph plain-text overrides keyed by block
address ("12" for a top-level paragraph, "table:row:cell:para" for a cell
paragraph). Applied to the stored .docx bytes at download time and folded
into a new version row by POST /documenti/{id}/save-edited-version, which
then clears the column on the source row.

Revision ID: bc1d2e3f4a5b
Revises: aa9f8e7d6c5b
Create Date: 2026-07-17 09:00:00.000000

Column is nullable JSONB — rows without pending inline edits stay NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "bc1d2e3f4a5b"
down_revision: Union[str, None] = "aa9f8e7d6c5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documenti_generati",
        sa.Column("content_overrides", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documenti_generati", "content_overrides")
