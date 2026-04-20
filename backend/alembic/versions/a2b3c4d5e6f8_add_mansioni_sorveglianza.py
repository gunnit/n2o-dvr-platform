"""add mansioni_sorveglianza table

Revision ID: a2b3c4d5e6f8
Revises: a1b2c3d4e5f7
Create Date: 2026-04-20 00:00:00.000000

Per-mansione DPI + rischi specifici (D.Lgs. 81/08) flagging, used by the
Medico del Lavoro to define the visite-mediche protocol. Keyed by
(azienda_id, mansione_nome) unique pair.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f8"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mansioni_sorveglianza",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "azienda_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("aziende.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mansione_nome", sa.String(), nullable=False),
        sa.Column(
            "dpi_codes",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "rischi_specifici_codes",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "azienda_id",
            "mansione_nome",
            name="uq_mansioni_sorveglianza_azienda_mansione",
        ),
    )
    op.create_index(
        "ix_mansioni_sorveglianza_azienda_id",
        "mansioni_sorveglianza",
        ["azienda_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mansioni_sorveglianza_azienda_id",
        table_name="mansioni_sorveglianza",
    )
    op.drop_table("mansioni_sorveglianza")
