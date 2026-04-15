"""add data_scadenza_dvr to aziende (US-5.1)

Revision ID: e1f2a3b4c5d6
Revises: c9d0e1f2a3b4
Create Date: 2026-04-15 18:00:00.000000

US-5.1 admin dashboard: track DVR expiry per azienda so the dashboard
can render a "Scadenze imminenti" KPI (DVRs expiring within 30 days)
and sort/chip the azienda table by that date.

Single nullable Date column — historical aziende without a scadenza
simply won't appear in the imminent-expiry counter.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "aziende",
        sa.Column("data_scadenza_dvr", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("aziende", "data_scadenza_dvr")
