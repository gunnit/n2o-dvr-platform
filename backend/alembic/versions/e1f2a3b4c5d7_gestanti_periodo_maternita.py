"""gestanti: periodo di maternità instead of data presunto parto (2026-10-02)

Revision ID: e1f2a3b4c5d7
Revises: d8e9f0a1b2c3
Create Date: 2026-10-03

N2O asked for the start and end of the maternity period on the scheda, not
the expected delivery date. Two nullable dates are added and prefilled for
existing rows with the default art. 16 D.Lgs. 151/2001 window the allegato
used to compute (two months before the expected delivery, three after), so
nothing already entered is lost and the operator only reviews.
``data_presunto_parto`` is kept, unused by the UI, so a rollback loses
nothing either.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d7"
down_revision: Union[str, Sequence[str], None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "gestanti_valutazioni",
        sa.Column("data_inizio_maternita", sa.Date(), nullable=True),
    )
    op.add_column(
        "gestanti_valutazioni",
        sa.Column("data_fine_maternita", sa.Date(), nullable=True),
    )
    op.execute(
        """
        UPDATE gestanti_valutazioni
        SET data_inizio_maternita = data_presunto_parto - 60,
            data_fine_maternita = data_presunto_parto + 90
        WHERE data_presunto_parto IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("gestanti_valutazioni", "data_fine_maternita")
    op.drop_column("gestanti_valutazioni", "data_inizio_maternita")
