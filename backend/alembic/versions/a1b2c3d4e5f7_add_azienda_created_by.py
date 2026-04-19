"""add created_by_user_id to aziende

Revision ID: a1b2c3d4e5f7
Revises: f5a6b7c8d9e0
Create Date: 2026-04-19 10:00:00.000000

Stamps authorship on azienda rows so the admin user-management page
can show a per-user "aziende created" counter. Nullable because
existing rows predate the column and we don't backfill.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "aziende",
        sa.Column("created_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_aziende_created_by_user",
        "aziende",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_aziende_created_by_user", "aziende", type_="foreignkey")
    op.drop_column("aziende", "created_by_user_id")
