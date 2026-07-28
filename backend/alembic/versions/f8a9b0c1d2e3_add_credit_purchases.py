"""Add credit_purchases — the AI credit pack ledger (closes D-14).

``usage_counters.overage_credits`` has existed since the Phase-0 monetization
migration and has been read by the spend query ever since, but nothing has ever
written it. This table is the missing half: one row per bought pack, and the
row whose ``status`` flip serializes the grant so a PayPal webhook and the
browser return cannot both credit the same order.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-07-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "credit_purchases",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # SET NULL, not CASCADE: removing an employee must not delete the
        # organization's receipt for money it actually paid.
        sa.Column(
            "created_by_user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("pack_code", sa.String(32), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("paypal_order_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_credit_purchases_organization_id", "credit_purchases", ["organization_id"]
    )
    # UNIQUE, not merely indexed: this constraint is what makes the grant
    # exactly-once when the webhook and the browser return race each other.
    op.create_index(
        "ix_credit_purchases_paypal_order_id",
        "credit_purchases",
        ["paypal_order_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_credit_purchases_paypal_order_id", table_name="credit_purchases")
    op.drop_index("ix_credit_purchases_organization_id", table_name="credit_purchases")
    op.drop_table("credit_purchases")
