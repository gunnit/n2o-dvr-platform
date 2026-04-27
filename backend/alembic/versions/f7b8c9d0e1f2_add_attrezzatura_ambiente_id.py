"""add ambiente_id to attrezzature (Phase 2.3 / bug B5)

Revision ID: f7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-26 18:00:00.000000

Each attrezzatura must belong to a specific ambiente, not just an azienda.
The wizard already groups equipment by environment in the UI but never
persisted the link, so the DVR generator had to lump everything together
under the company. This migration:

  1. Adds attrezzature.ambiente_id (nullable) with FK to ambienti.id.
  2. Backfills existing rows to the oldest ambiente of the same azienda.
  3. Deletes orphan rows whose azienda has no ambienti at all (they
     were unusable anyway — every DVR section needs an environment).
  4. Promotes the column to NOT NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "f7b8c9d0e1f2"
# Also merges the orphan e5f6a7b8c9d1 (user_feedback) head into the main
# chain so alembic upgrade head resolves to a single revision.
down_revision: Union[str, Sequence[str], None] = ("f6a7b8c9d0e1", "e5f6a7b8c9d1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attrezzature",
        sa.Column("ambiente_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_attrezzature_ambiente_id_ambienti",
        "attrezzature",
        "ambienti",
        ["ambiente_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.execute(
        """
        UPDATE attrezzature
           SET ambiente_id = sub.first_ambiente_id
          FROM (
              SELECT DISTINCT ON (azienda_id)
                     azienda_id,
                     id AS first_ambiente_id
                FROM ambienti
            ORDER BY azienda_id, created_at NULLS LAST, id
          ) AS sub
         WHERE attrezzature.azienda_id = sub.azienda_id
           AND attrezzature.ambiente_id IS NULL
        """
    )

    op.execute("DELETE FROM attrezzature WHERE ambiente_id IS NULL")

    op.alter_column("attrezzature", "ambiente_id", nullable=False)
    op.create_index(
        "ix_attrezzature_ambiente_id",
        "attrezzature",
        ["ambiente_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_attrezzature_ambiente_id", table_name="attrezzature")
    op.drop_constraint(
        "fk_attrezzature_ambiente_id_ambienti",
        "attrezzature",
        type_="foreignkey",
    )
    op.drop_column("attrezzature", "ambiente_id")
