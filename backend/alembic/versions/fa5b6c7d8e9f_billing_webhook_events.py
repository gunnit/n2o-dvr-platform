"""monetization phase 4: billing_webhook_events (webhook idempotency ledger)

Revision ID: fa5b6c7d8e9f
Revises: ef4a5b6c7d8e
Create Date: 2026-07-27

The webhook is the sole writer of subscriptions.status (INV-2). PayPal retries
an event until it receives a 2xx and retries can overlap, so exactly-once
handling is enforced here by the primary key rather than in application logic.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "fa5b6c7d8e9f"
down_revision: Union[str, Sequence[str], None] = "ef4a5b6c7d8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_webhook_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("event_id"),
    )
    # "Show me everything that happened to this subscription" is the support
    # query; without this it is a sequential scan over every event we ever got.
    op.create_index(
        "ix_billing_webhook_events_resource_id",
        "billing_webhook_events",
        ["resource_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_billing_webhook_events_resource_id", table_name="billing_webhook_events"
    )
    op.drop_table("billing_webhook_events")
