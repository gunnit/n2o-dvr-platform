"""add nome_area + updated_at to incendio_valutazioni and microclima_valutazioni

Revision ID: s0o1p2q3r4s5
Revises: r9n0o1p2q3r4
Create Date: 2026-05-22 10:00:00.000000

Unlocks per-area persistence for INCENDIO + MICROCLIMA: the frontend lets the
operator type a free-text area label, but the existing model only had a FK to
the ambienti table. Adding `nome_area` lets us round-trip the form label even
when the user hasn't formalised the area in the ambienti list yet.

Also adds `updated_at` for both tables so PATCH endpoints can track edits.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "s0o1p2q3r4s5"
down_revision: Union[str, None] = "r9n0o1p2q3r4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # incendio_valutazioni
    op.add_column(
        "incendio_valutazioni",
        sa.Column("nome_area", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "incendio_valutazioni",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # microclima_valutazioni
    op.add_column(
        "microclima_valutazioni",
        sa.Column("nome_area", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "microclima_valutazioni",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_column("microclima_valutazioni", "updated_at")
    op.drop_column("microclima_valutazioni", "nome_area")
    op.drop_column("incendio_valutazioni", "updated_at")
    op.drop_column("incendio_valutazioni", "nome_area")
