"""add survey_snapshot_hash + stale_snapshot to documenti_generati (US-5.2)

Revision ID: d3e4f5a6b7c8
Revises: d1e2f3a4b5c6
Create Date: 2026-04-15 23:30:00.000000

US-5.2 AC2: "Given survey data is changed while a generation job is in
flight, When the job completes, Then I receive a warning that the
snapshot may be stale and I can choose to regenerate."

Implementation: at the start of every generation we hash the survey
payload (azienda + persone + ambienti + attrezzature + rischi +
sostanze) into a stable digest, persist it on the document row, and on
completion compare against a fresh hash. If they differ, set
``stale_snapshot=true`` so the documents page can render the
"Rigenera" banner and the AC2 warning.

The hash also lets the frontend short-circuit AC1 — when the freshly
computed hash matches the latest completed document for the same type,
we know the survey hasn't drifted since that generation, so the
"Rigenera" CTA on the dashboard can be hidden / muted.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documenti_generati",
        sa.Column("survey_snapshot_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "documenti_generati",
        sa.Column(
            "stale_snapshot",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("documenti_generati", "stale_snapshot")
    op.drop_column("documenti_generati", "survey_snapshot_hash")
