"""monetization phase 6 (MB-6.1): give every pre-existing org a subscription row

Revision ID: e7f8a9b0c1d2
Revises: ab1c2d3e4f5a
Create Date: 2026-07-28

MB-1.3 promised that every organization would own a `subscriptions` row and
never delivered it. `resolve_entitlements()` covered for the gap with a fully
permissive fallback that reported `A_FOUNDING / active / seats = 2**31-1`.

That was defensible while the only tenants were established ones. It stopped
being defensible when `a73220a` opened self-serve signup: a brand-new company
that had paid nothing also owns no subscription row, so it hit the same
fallback and was told — in the UI, in writing — that it held an active founding
partner plan with unlimited everything. The channel guardrail went with it,
because the fallback grants `allowed_doc_types = NULL`, so POS and HACCP were
reachable from a direct tenant.

MB-6.1 splits the two cases in `app/billing/entitlements.py`: a missing
subscription now resolves to an honest *unsubscribed* state that is not active.
That split is only safe once no established tenant is sitting in it — which is
what this migration guarantees.

Every organization without a subscription row at this point in history predates
self-serve signup, so it is exactly the population MB-1.3 meant to grandfather.
Each gets an `A_FOUNDING` row, `status = 'active'`, with a three-year period
starting from the organization's own `created_at` (the founding term is not
renegotiated annually — see OPEN-DECISION-2).

Behaviour-preserving by construction: these orgs were already being *reported*
as A_FOUNDING/active. The only thing that changes is that it is now true in the
database instead of being invented per-request, so INV-1 survives someone
flipping `ENTITLEMENTS_ENFORCE` on.

Downgrade removes only the rows this migration could have created — an
`A_FOUNDING` subscription carrying no PayPal identifiers. A real purchase always
has `paypal_subscription_id` set, so it can never be swept up.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "ab1c2d3e4f5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # gen_random_uuid() is pgcrypto, available on Render Postgres 18 as a
    # built-in since 13. `ON CONFLICT DO NOTHING` guards the UNIQUE on
    # organization_id so a re-run is a no-op rather than an error.
    op.execute(
        """
        INSERT INTO subscriptions (
            id, organization_id, plan_code, status,
            current_period_start, current_period_end, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            o.id,
            'A_FOUNDING',
            'active',
            COALESCE(o.created_at, now()),
            COALESCE(o.created_at, now()) + INTERVAL '3 years',
            now(),
            now()
        FROM organizations o
        LEFT JOIN subscriptions s ON s.organization_id = o.id
        WHERE s.id IS NULL
        ON CONFLICT (organization_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM subscriptions
        WHERE plan_code = 'A_FOUNDING'
          AND paypal_subscription_id IS NULL
          AND paypal_payer_id IS NULL
        """
    )
