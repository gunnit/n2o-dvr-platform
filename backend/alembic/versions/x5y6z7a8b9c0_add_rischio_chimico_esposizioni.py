"""add rischio_chimico_esposizioni table

Revision ID: x5y6z7a8b9c0
Revises: w4x5y6z7a8b9
Create Date: 2026-05-31 09:00:00.000000

Chemical-risk (MoVaRisCh) exposures, one row per (worker x substance). Stores
the AI-suggested / operator-reviewed exposure inputs plus the denormalized
derived results (P, Einal, Rinal, Ecute, Rcute, Rcum, livelli). See
docs/context/RISCHIO_CHIMICO_MAPPING.md and app/services/movarisch_calculator.py.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x5y6z7a8b9c0"
down_revision: Union[str, None] = "w4x5y6z7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rischio_chimico_esposizioni",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("persona_id", sa.UUID(), nullable=True),
        sa.Column("sostanza_id", sa.UUID(), nullable=True),
        sa.Column("ambiente_id", sa.UUID(), nullable=True),
        # Exposure inputs
        sa.Column("proprieta_fisiche", sa.String(), nullable=True),
        sa.Column("quantita_classe", sa.String(), nullable=True),
        sa.Column("tipologia_uso", sa.String(), nullable=True),
        sa.Column("tipologia_controllo", sa.String(), nullable=True),
        sa.Column("tempo_esposizione", sa.String(), nullable=True),
        sa.Column("distanza_classe", sa.String(), nullable=True),
        sa.Column("via_cutanea_applicabile", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("contatto_cutaneo", sa.String(), nullable=True),
        # Derived results
        sa.Column("p_score", sa.Numeric(), nullable=True),
        sa.Column("governing_code", sa.String(), nullable=True),
        sa.Column("is_cancerogeno", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("d_ind", sa.Integer(), nullable=True),
        sa.Column("u_ind", sa.Integer(), nullable=True),
        sa.Column("c_ind", sa.Integer(), nullable=True),
        sa.Column("i_ind", sa.Integer(), nullable=True),
        sa.Column("einal", sa.Numeric(), nullable=True),
        sa.Column("rinal", sa.Numeric(), nullable=True),
        sa.Column("ecute", sa.Integer(), nullable=True),
        sa.Column("rcute", sa.Numeric(), nullable=True),
        sa.Column("rcum", sa.Numeric(), nullable=True),
        sa.Column("r_governing", sa.Numeric(), nullable=True),
        sa.Column("zona", sa.String(), nullable=True),
        sa.Column("livello_salute", sa.String(), nullable=True),
        sa.Column("livello_sicurezza", sa.String(), nullable=True),
        # Lifecycle
        sa.Column("ai_suggested", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("human_reviewed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["persone.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sostanza_id"], ["sostanze_chimiche.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ambiente_id"], ["ambienti.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rischio_chimico_esposizioni_azienda_id",
        "rischio_chimico_esposizioni",
        ["azienda_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rischio_chimico_esposizioni_azienda_id",
        table_name="rischio_chimico_esposizioni",
    )
    op.drop_table("rischio_chimico_esposizioni")
