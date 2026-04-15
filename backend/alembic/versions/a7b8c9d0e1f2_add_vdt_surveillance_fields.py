"""add health-surveillance tracking to vdt_valutazioni (US-3.5)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-15 16:10:00.000000

Adds the three columns required to power the "Visite in scadenza" and
"Visite scadute" dashboard widgets:

  * data_ultima_visita   — DATE, nullable. Last performed eye exam. NULL
    means the worker has not yet had a first visit; in that case the next
    visit is computed from the row's created_at.
  * data_prossima_visita — DATE, nullable. Auto-computed from the above
    plus the periodicita (5 anni under 50, 2 anni for 50+). Materialised
    so the widgets are a single indexed range-scan rather than a
    per-row Python call.
  * eta_50_plus          — BOOLEAN, default False. Drives the 5y/2y
    cadence. Persona.fascia_eta currently only distinguishes minor/adult
    for MMC; VDT needs the separate >=50 threshold from art. 176, so we
    keep it on the VDT row itself.

See services/vdt_surveillance.py for the cadence helper and
api/v1/sorveglianza.py for the alert endpoint.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vdt_valutazioni",
        sa.Column("data_ultima_visita", sa.Date(), nullable=True),
    )
    op.add_column(
        "vdt_valutazioni",
        sa.Column("data_prossima_visita", sa.Date(), nullable=True),
    )
    op.add_column(
        "vdt_valutazioni",
        sa.Column(
            "eta_50_plus",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    # Range-scan index for the "Visite in scadenza / scadute" widgets.
    op.create_index(
        "ix_vdt_prossima_visita",
        "vdt_valutazioni",
        ["data_prossima_visita"],
    )


def downgrade() -> None:
    op.drop_index("ix_vdt_prossima_visita", table_name="vdt_valutazioni")
    op.drop_column("vdt_valutazioni", "eta_50_plus")
    op.drop_column("vdt_valutazioni", "data_prossima_visita")
    op.drop_column("vdt_valutazioni", "data_ultima_visita")
