"""add rischi_misure_libreria (US-2.6)

Revision ID: a9c0d1e2f3b4
Revises: a8b9c0d1e2f3
Create Date: 2026-04-15 22:00:00.000000

US-2.6 AC2 introduces a per-azienda library of accepted / edited /
manually-authored improvement measures for the Risk Scoring Interface.
When the operator tags a measure from the AI suggestion panel or types
one from scratch, the full payload is persisted here so it can be
surfaced on future risks of the same categoria for the same client.

Columns:
  * id                    UUID PK (uuid4 generated app-side)
  * azienda_id            UUID FK aziende.id ON DELETE CASCADE
  * categoria_rischio     text (matches ValutazioneRischio.categoria_rischio)
  * titolo                text
  * descrizione           text
  * tipo                  text (tecnica | organizzativa | dpi | formazione | sorveglianza_sanitaria)
  * priorita              text (bassa | media | alta | urgente)
  * tempistica            text
  * riferimento_normativo text, nullable
  * provenance            text (ai-accepted | ai-modified | manual)
  * created_at, updated_at

Index on (azienda_id, categoria_rischio) — always the primary access path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "a9c0d1e2f3b4"
down_revision: Union[str, None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rischi_misure_libreria",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "azienda_id",
            UUID(as_uuid=True),
            sa.ForeignKey("aziende.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("categoria_rischio", sa.String(), nullable=False),
        sa.Column("titolo", sa.String(), nullable=False),
        sa.Column("descrizione", sa.Text(), nullable=False),
        sa.Column(
            "tipo", sa.String(), nullable=False, server_default="tecnica"
        ),
        sa.Column(
            "priorita", sa.String(), nullable=False, server_default="media"
        ),
        sa.Column(
            "tempistica", sa.String(), nullable=False, server_default=""
        ),
        sa.Column("riferimento_normativo", sa.Text(), nullable=True),
        sa.Column(
            "provenance",
            sa.String(),
            nullable=False,
            server_default="manual",
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
        "ix_rischi_misure_libreria_azienda_categoria",
        "rischi_misure_libreria",
        ["azienda_id", "categoria_rischio"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rischi_misure_libreria_azienda_categoria",
        table_name="rischi_misure_libreria",
    )
    op.drop_table("rischi_misure_libreria")
