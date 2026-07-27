"""pericoli_valutazione: make created_at / updated_at NOT NULL

Schema-only, no behavior change. Closes the last of the 17 model-vs-migration
drifts that made `alembic revision --autogenerate` unusable (it emitted this
diff on every unrelated run, so any new migration silently carried it along).

Migration 0a1b2c3d4e5f created ``pericoli_valutazione`` with

    sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now())

— omitting ``nullable=False``, which every other table in the schema carries on
these two columns (rischi_misure_libreria, stress_misure_libreria, user_feedback,
ai_feedback, ambienti_foto, description_revisions, …). The model has always
declared them non-optional (``Mapped[datetime]``), so here the *migration* is the
side that is wrong, not the model — hence a corrective migration rather than a
model edit.

Safe by construction: both columns carry ``server_default=now()`` and the ORM
never sends an explicit NULL (SQLAlchemy omits unset server-default columns from
the INSERT), so no live row can be null. The backfill below is belt-and-braces
for any row written outside the ORM. SET NOT NULL takes a brief ACCESS EXCLUSIVE
lock and scans the table without rewriting it.

Revision ID: ef4a5b6c7d8e
Revises: de3f4a5b6c7d
Create Date: 2026-07-27 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ef4a5b6c7d8e"
down_revision: Union[str, Sequence[str], None] = "de3f4a5b6c7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE pericoli_valutazione
        SET created_at = COALESCE(created_at, now()),
            updated_at = COALESCE(updated_at, created_at, now())
        WHERE created_at IS NULL OR updated_at IS NULL
        """
    )
    op.alter_column(
        "pericoli_valutazione",
        "created_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_server_default=sa.text("now()"),
        nullable=False,
    )
    op.alter_column(
        "pericoli_valutazione",
        "updated_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_server_default=sa.text("now()"),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "pericoli_valutazione",
        "updated_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_server_default=sa.text("now()"),
        nullable=True,
    )
    op.alter_column(
        "pericoli_valutazione",
        "created_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_server_default=sa.text("now()"),
        nullable=True,
    )
