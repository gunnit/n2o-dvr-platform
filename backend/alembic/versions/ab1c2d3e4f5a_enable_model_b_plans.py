"""monetization phase 5 (MB-5.1 / MB-5.7): sell the Model B plans

Revision ID: ab1c2d3e4f5a
Revises: fa5b6c7d8e9f
Create Date: 2026-07-28

Two changes, both needed before a direct company can pay:

1. **Activate the three Model B plans.** `de3f4a5b6c7d` seeded them with
   `active = false` because Phase 5 had not happened; `list_purchasable()`
   filters on that column, so `GET /billing/plans` returned nothing for a direct
   tenant and `/subscribe` 409'd. This flips them on. The frozen literals in
   `de3f4a5b6c7d` are deliberately left alone — a migration is history, not a
   copy of the current catalogue — so a database migrated from empty passes
   through inactive and arrives active, which is what
   `app/billing/plan_catalogue.py` now declares.

   What the flag does *not* do is relax the channel guardrail: no Model B plan
   grants `pos`, `haccp` or `haccp_forms` (`allowed_doc_types` is untouched
   here), so construction and food-chain work still routes to a consultant.

2. **Record the datore-di-lavoro consent (MB-5.7).** A direct signup must
   acknowledge that the employer signs the DVR and carries the responsibility,
   and that the platform is assisted drafting, not a substitute for the
   employer's own assessment. Both columns stay NULL for every consultant org —
   they are the evidentiary record of a direct signup, so they are written once
   at registration and never updated.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ab1c2d3e4f5a"
down_revision: Union[str, Sequence[str], None] = "fa5b6c7d8e9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_B_PLANS = ("B_BASE", "B_PLUS", "B_MULTISEDE")


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("ddl_consent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("ddl_consent_version", sa.String(length=16), nullable=True),
    )

    op.execute(
        sa.text(
            "UPDATE plans SET active = true WHERE plan_code IN "
            "('B_BASE', 'B_PLUS', 'B_MULTISEDE')"
        )
    )


def downgrade() -> None:
    # Deactivating is safe for anyone already on a B plan: `active` only governs
    # what may be *bought*, and the entitlement resolver reads the plan row
    # regardless. A retired plan keeps working for its existing subscribers.
    op.execute(
        sa.text(
            "UPDATE plans SET active = false WHERE plan_code IN "
            "('B_BASE', 'B_PLUS', 'B_MULTISEDE')"
        )
    )
    op.drop_column("organizations", "ddl_consent_version")
    op.drop_column("organizations", "ddl_consent_at")
