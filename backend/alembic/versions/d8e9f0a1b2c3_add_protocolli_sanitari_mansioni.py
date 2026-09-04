"""protocollo sanitario per mansione (segnalazione 2026-08-25)

Revision ID: d8e9f0a1b2c3
Revises: c6d7e8f9a0b1
Create Date: 2026-09-04

One row per (azienda, mansione) carrying the accertamenti, their cadence
and the correlated occupational diseases the Medico Competente prescribes
for a role. Per mansione, never per person: nothing in this table is an
individual's health record.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, Sequence[str], None] = "c6d7e8f9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "protocolli_sanitari_mansioni",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "azienda_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("aziende.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mansione", sa.String(), nullable=False),
        sa.Column(
            "rischi_specifici",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "accertamenti",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("periodicita", sa.String(), nullable=True),
        sa.Column(
            "malattie_correlate",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "fonte", sa.String(), nullable=False, server_default="manuale"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_protocolli_sanitari_mansioni_azienda_id",
        "protocolli_sanitari_mansioni",
        ["azienda_id"],
    )
    # Case-insensitive uniqueness: "Saldatore" and "saldatore" are one role.
    op.create_index(
        "uq_protocolli_sanitari_mansioni_azienda_mansione_lower",
        "protocolli_sanitari_mansioni",
        ["azienda_id", sa.text("lower(mansione)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_protocolli_sanitari_mansioni_azienda_mansione_lower",
        table_name="protocolli_sanitari_mansioni",
    )
    op.drop_index(
        "ix_protocolli_sanitari_mansioni_azienda_id",
        table_name="protocolli_sanitari_mansioni",
    )
    op.drop_table("protocolli_sanitari_mansioni")
