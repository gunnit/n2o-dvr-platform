"""add stress_misure_libreria (US-3.8)

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-04-15 18:00:00.000000

US-3.8 introduces a per-azienda library of corrective measures for the
stress lavoro-correlato assessment. When the operator edits one of the
default suggested measures (or adds a brand-new one via "Aggiungi
misura"), the resulting text is persisted here so it can be surfaced on
future valutazioni and tagged "Personalizzato" in the UI.

Columns:
  * id               — UUID PK (uuid4 generated app-side)
  * azienda_id       — UUID FK aziende.id ON DELETE CASCADE
  * livello_rischio  — text; one of Basso / Medio / Alto
  * testo            — the measure text
  * personalizzato   — bool, default true (library only stores custom rows)
  * created_at       — timestamp, server default now()
  * updated_at       — timestamp, server default now(), onupdate now()
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stress_misure_libreria",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "azienda_id",
            UUID(as_uuid=True),
            sa.ForeignKey("aziende.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("livello_rischio", sa.String(), nullable=False),
        sa.Column("testo", sa.Text(), nullable=False),
        sa.Column(
            "personalizzato",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
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
    )
    op.create_index(
        "ix_stress_misure_libreria_azienda_livello",
        "stress_misure_libreria",
        ["azienda_id", "livello_rischio"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stress_misure_libreria_azienda_livello",
        table_name="stress_misure_libreria",
    )
    op.drop_table("stress_misure_libreria")
