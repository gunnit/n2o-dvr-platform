"""scheda ambiente for the incendio and PEE allegati

Revision ID: c6d7e8f9a0b1
Revises: d3e4f5a6b8c9
Create Date: 2026-09-04

Segnalazioni 2026-08-25 (incendio + PEE): each ambiente needs a description
with the materials present, the maximum number of people and the possible
ignition sources. Both allegati read the same facts, so they live on the
ambiente row rather than on either assessment.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c6d7e8f9a0b1"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ambienti", sa.Column("descrizione_locale", sa.Text(), nullable=True))
    op.add_column("ambienti", sa.Column("materiali_presenti", sa.Text(), nullable=True))
    op.add_column("ambienti", sa.Column("max_persone", sa.Integer(), nullable=True))
    op.add_column("ambienti", sa.Column("sorgenti_innesco", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ambienti", "sorgenti_innesco")
    op.drop_column("ambienti", "max_persone")
    op.drop_column("ambienti", "materiali_presenti")
    op.drop_column("ambienti", "descrizione_locale")
