"""monetization phase 0: account_type, plans, subscriptions, usage, active companies

Additive only — no existing column is altered or dropped and no gate is wired,
so this migration changes zero runtime behavior. It creates the tables the
entitlement resolver reads.

`organizations.account_type` carries a server_default of 'consultant' so every
row that already exists is grandfathered into Model A without a backfill pass
(INV-1: never lock out the live N2O tenant).

Revision ID: cd2e3f4a5b6c
Revises: bc1d2e3f4a5b
Create Date: 2026-07-27 10:00:00.000000

NULL semantics are uniform across every limit column: NULL means
"unlimited / not metered", never "zero".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cd2e3f4a5b6c"
down_revision: Union[str, None] = "bc1d2e3f4a5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Organization.account_type ----------------------------------------
    op.add_column(
        "organizations",
        sa.Column(
            "account_type",
            sa.String(length=16),
            nullable=False,
            server_default="consultant",
        ),
    )

    # --- plans: the catalogue (Model A vs B differ only as rows here) ------
    op.create_table(
        "plans",
        sa.Column("plan_code", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=1), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("price_year_cents", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("seats", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("max_companies", sa.Integer(), nullable=True),
        sa.Column("max_sites", sa.Integer(), nullable=True),
        sa.Column("ai_credits_year", sa.Integer(), nullable=True),
        sa.Column(
            "allowed_doc_types", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "features",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("stripe_price_id", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("plan_code"),
    )

    # --- subscriptions: one live subscription per organization ------------
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_code", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("stripe_customer_id", sa.String(length=64), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=64), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_code"], ["plans.plan_code"]),
        sa.PrimaryKeyConstraint("id"),
        # One live subscription per org — the resolver's join assumes it.
        sa.UniqueConstraint("organization_id"),
    )

    # --- usage_counters: the per-period AI credit meter --------------------
    op.create_table(
        "usage_counters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("ai_credits_used", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("overage_credits", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Addresses the meter and lets the spend path create it lazily with
        # INSERT … ON CONFLICT DO NOTHING.
        sa.UniqueConstraint(
            "organization_id", "period_start", name="uq_usage_counters_org_period"
        ),
    )

    # --- ai_usage_events: append-only ledger + idempotency guard -----------
    op.create_table(
        "ai_usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # The UNIQUE is the whole point: a retried spend collides instead of
        # double-charging (INV-6).
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        op.f("ix_ai_usage_events_organization_id"),
        "ai_usage_events",
        ["organization_id"],
        unique=False,
    )

    # --- active_company_periods: the Model A meter ------------------------
    op.create_table(
        "active_company_periods",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("azienda_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column(
            "first_activated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        # Composite PK makes every completion path's insert retry-safe.
        sa.PrimaryKeyConstraint("organization_id", "azienda_id", "period_start"),
    )


def downgrade() -> None:
    op.drop_table("active_company_periods")
    op.drop_index(op.f("ix_ai_usage_events_organization_id"), table_name="ai_usage_events")
    op.drop_table("ai_usage_events")
    op.drop_table("usage_counters")
    op.drop_table("subscriptions")
    op.drop_table("plans")
    op.drop_column("organizations", "account_type")
