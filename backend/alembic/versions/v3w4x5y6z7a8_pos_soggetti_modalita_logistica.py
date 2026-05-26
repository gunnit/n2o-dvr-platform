"""add soggetti di riferimento, modalita organizzative, organizzazione logistica to pos

Revision ID: v3w4x5y6z7a8
Revises: u2v3w4x5y6z7
Create Date: 2026-05-26 12:00:00.000000

POS feedback from Luca Marchetti (2026-05-25 email "Elementi fondamentali
dei POS", attachment with yellow-highlighted required inputs). Adds the
fields the annotated template flagged as missing:

* Soggetti di riferimento (All. XV punto 3.2.1 b) — progettista responsabile,
  direttore operativo edilizia/strutture, direttore operativo impianti,
  responsabile dei lavori, coordinatore per la sicurezza in fase di
  progettazione (CSP). The existing ``coordinatore_sicurezza`` column keeps
  its name and now explicitly means the CSE — kept for backwards
  compatibility with existing POS rows.
* Modalità organizzative (All. XV punto 3.2.1 c) — orario lavoro cantiere,
  turni, riunioni di coordinamento.
* Organizzazione logistica — monoblocchi installati (bool + dettagli),
  modalità consumazione pasti.

All new columns are nullable / default false so existing rows continue to
satisfy the constraints without a backfill.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v3w4x5y6z7a8"
down_revision: Union[str, None] = "u2v3w4x5y6z7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_STRING_COLUMNS = [
    # Soggetti di riferimento
    "progettista_responsabile",
    "direttore_operativo_edilizia",
    "direttore_operativo_impianti",
    "responsabile_lavori",
    "coordinatore_progettazione",
]

_NEW_TEXT_COLUMNS = [
    # Modalità organizzative
    "orario_lavoro_cantiere",
    "turni_descrizione",
    "riunioni_coordinamento",
    # Organizzazione logistica
    "monoblocchi_dettagli",
    "modalita_pasti",
]


def upgrade() -> None:
    for name in _NEW_STRING_COLUMNS:
        op.add_column("pos", sa.Column(name, sa.String(), nullable=True))
    for name in _NEW_TEXT_COLUMNS:
        op.add_column("pos", sa.Column(name, sa.Text(), nullable=True))
    op.add_column(
        "pos",
        sa.Column(
            "monoblocchi_installati",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("pos", "monoblocchi_installati")
    for name in reversed(_NEW_TEXT_COLUMNS):
        op.drop_column("pos", name)
    for name in reversed(_NEW_STRING_COLUMNS):
        op.drop_column("pos", name)
