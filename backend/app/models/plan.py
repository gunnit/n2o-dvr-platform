"""Plan catalogue — the commercial product, expressed as data.

Model A (consultants) and Model B (direct companies) are the *same engine*
sold under different plans. They differ only as rows in this table (INV-4):
never as forked code, a second deployment, or scattered
``if account_type == "direct"`` branches.

Rows are seeded by MB-1.2 / MB-5.1, not written by application code.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Plan(Base):
    __tablename__ = "plans"

    # Natural PK — stable, human-readable, referenced by subscriptions and by
    # the seed scripts. See billing.constants.PLAN_CODES.
    plan_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    # 'A' = consultants/studios, 'B' = direct companies.
    model: Mapped[str] = mapped_column(String(1), nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    # Annual list price in euro cents, **excluding** IVA 22%. Zero for
    # A_FOUNDING (the N2O grandfather row). First-year setup fees are one-time
    # Checkout line items, not plan fields.
    # server_default uses text() rather than a bare string so the rendered DDL
    # is byte-identical to the migration's (`DEFAULT 0`, not `DEFAULT '0'`) and
    # autogenerate never reports phantom drift.
    price_year_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    # --- Limits. NULL consistently means "unlimited / not metered". ---------
    seats: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    # Model A meter: distinct client companies activated per period.
    max_companies: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Model B meter: sedi / unità locali.
    max_sites: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # AI credits granted per period. NULL = pooled/unmetered (A_ENTERPRISE):
    # the metering check short-circuits to "allow".
    ai_credits_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Canonical (lowercase) tipo_documento strings this plan may generate.
    # NULL = all 17, which is every Model A plan. An explicit subset is the
    # channel-conflict contract for Model B (plan §6, INV-9) — POS and HACCP
    # stay out of every B plan until OPEN-DECISION-1 is resolved.
    allowed_doc_types: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # Non-metered capability flags, e.g.
    # {"white_label_domain": bool, "sub_tenants": int, "api": "none|read|full",
    #  "data_certa": bool, "rspp_reviews_included": int}
    features: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    # Filled by the Phase 4 PayPal catalogue setup script — the `P-…` billing
    # plan id. The join key between our catalogue and PayPal's; PayPal never
    # owns entitlements (INV-2).
    paypal_plan_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Sellable today. Retiring a plan sets this false; existing subscriptions
    # on it keep resolving, so rows are never deleted.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
