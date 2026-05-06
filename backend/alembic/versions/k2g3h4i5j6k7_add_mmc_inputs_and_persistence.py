"""extend mmc_valutazioni with NIOSH inputs and persistence fields

Revision ID: k2g3h4i5j6k7
Revises: m4i5j6k7l8m9
Create Date: 2026-04-29 14:50:00.000000

NOTE 2026-05-06: rebased onto m4i5j6k7l8m9 to linearize a two-heads alembic
state that was failing pre_deploy on Render. Original chain pointed to
j1f2g3h4i5j6 same as l3h4i5j6k7l8 — both branched from j1.

The MMC audit (2026-04-29) flagged that the model only stored derived NIOSH
multipliers (fattore_a..fattore_f) but not the *inputs* that produced them
(altezza_cm, dislocazione_cm, distanza_cm, angolo_gradi, giudizio_presa,
frequenza_atti_min, durata_min). Without those, the per-worker assessment
grid in the generated MMC docx (template T14 layout) is unreproducible.

Also adds:
  - area_classificazione (Verde/Gialla/Rossa) for the quadro sinottico
  - misure_proposte (Text) for the Programma di Attuazione section
  - updated_at timestamp for staleness tracking
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k2g3h4i5j6k7"
down_revision: Union[str, Sequence[str], None] = "m4i5j6k7l8m9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mmc_valutazioni", sa.Column("altezza_cm", sa.Integer(), nullable=True))
    op.add_column("mmc_valutazioni", sa.Column("dislocazione_cm", sa.Integer(), nullable=True))
    op.add_column("mmc_valutazioni", sa.Column("distanza_cm", sa.Integer(), nullable=True))
    op.add_column("mmc_valutazioni", sa.Column("angolo_gradi", sa.Integer(), nullable=True))
    op.add_column("mmc_valutazioni", sa.Column("giudizio_presa", sa.String(), nullable=True))
    op.add_column("mmc_valutazioni", sa.Column("frequenza_atti_min", sa.Numeric(), nullable=True))
    op.add_column("mmc_valutazioni", sa.Column("durata_min", sa.Integer(), nullable=True))
    op.add_column("mmc_valutazioni", sa.Column("area_classificazione", sa.String(), nullable=True))
    op.add_column("mmc_valutazioni", sa.Column("misure_proposte", sa.Text(), nullable=True))
    op.add_column(
        "mmc_valutazioni",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("mmc_valutazioni", "updated_at")
    op.drop_column("mmc_valutazioni", "misure_proposte")
    op.drop_column("mmc_valutazioni", "area_classificazione")
    op.drop_column("mmc_valutazioni", "durata_min")
    op.drop_column("mmc_valutazioni", "frequenza_atti_min")
    op.drop_column("mmc_valutazioni", "giudizio_presa")
    op.drop_column("mmc_valutazioni", "angolo_gradi")
    op.drop_column("mmc_valutazioni", "distanza_cm")
    op.drop_column("mmc_valutazioni", "dislocazione_cm")
    op.drop_column("mmc_valutazioni", "altezza_cm")
