"""monetization phase 1: seed plan catalogue and grandfather existing orgs

Data-only. Creates no schema and changes no behavior — the entitlement gates
are still inert (`ENTITLEMENTS_ENFORCE` defaults to false).

This must ship in the SAME deploy as the resolver (INV-1). The resolver's
fallback is permissive, so a missing subscription row over-grants rather than
locks out — but "every org over-granted" is not a state to run production in.

What it does, all idempotently:
  1. backfill `organizations.account_type` (belt-and-braces: the Phase-0 ALTER
     carried a NOT NULL default, so Postgres already backfilled every row);
  2. seed the plan catalogue;
  3. put every existing organization on A_FOUNDING for 3 years;
  4. record the companies already active this period, so the Model A meter
     doesn't start from a false zero when Phase 2 turns it on.

Verified against production before writing (read-only): 6 organizations, all
internal/test, newest user 2026-05-28, no public signups. Grandfathering all of
them is therefore free of commercial risk. Note there is **no organization
named "N2O"** — the tenant hasn't been provisioned yet, so this migration keys
off "every existing org" rather than a name match, which is also what MB-1.3's
acceptance criterion actually requires ("every existing org has exactly one
active subscription").

Revision ID: de3f4a5b6c7d
Revises: cd2e3f4a5b6c
Create Date: 2026-07-27 12:00:00.000000

The plan rows are literal here rather than imported from
app.billing.plan_catalogue: a migration is frozen history and must keep
applying even after that module is refactored. tests/test_plan_catalogue.py
asserts the two stay in agreement.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "de3f4a5b6c7d"
down_revision: Union[str, None] = "cd2e3f4a5b6c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (plan_code, model, display_name, price_year_cents, seats, max_companies,
#  max_sites, ai_credits_year, allowed_doc_types_json, features_json, active)
_B_BASE = (
    '["dvr_master","allegato_mmc","allegato_vdt","allegato_stress",'
    '"allegato_gestanti","allegato_incendio"]'
)
_B_PLUS = (
    '["dvr_master","allegato_mmc","allegato_vdt","allegato_stress",'
    '"allegato_gestanti","allegato_incendio","allegato_microclima",'
    '"allegato_microclima_severo","allegato_biologico_alimentare",'
    '"allegato_biologico_asilo","allegato_biologico_dentisti",'
    '"pee_azienda","duvri"]'
)
# POS / HACCP deliberately absent from every Model B plan — OPEN-DECISION-1.
_B_MULTI = (
    '["dvr_master","allegato_mmc","allegato_vdt","allegato_stress",'
    '"allegato_gestanti","allegato_incendio","allegato_microclima",'
    '"allegato_microclima_severo","allegato_biologico_alimentare",'
    '"allegato_biologico_asilo","allegato_biologico_dentisti",'
    '"pee_azienda","duvri","pee_comune"]'
)

PLANS = [
    ("A_SOLO", "A", "Solo", 149000, 1, 15, None, 2500, None,
     '{"white_label_domain": false, "sub_tenants": 0, "api": "none",'
     ' "data_certa": false, "rspp_reviews_included": 0}', True),
    ("A_STUDIO", "A", "Studio", 390000, 5, 60, None, 9000, None,
     '{"white_label_domain": false, "sub_tenants": 0, "api": "read",'
     ' "data_certa": false, "rspp_reviews_included": 0, "template_migrations": 1}', True),
    ("A_NETWORK", "A", "Network", 890000, 15, 200, None, 30000, None,
     '{"white_label_domain": true, "sub_tenants": 10, "api": "full",'
     ' "data_certa": true, "rspp_reviews_included": 0}', True),
    ("A_ENTERPRISE", "A", "Enterprise", 1800000, 40, None, None, None, None,
     '{"white_label_domain": true, "sub_tenants": null, "api": "full",'
     ' "webhooks": true, "data_certa": true, "rspp_reviews_included": 0}', True),
    ("A_FOUNDING", "A", "Founding Partner", 0, 5, 60, None, 9000, None,
     '{"white_label_domain": true, "sub_tenants": 0, "api": "read",'
     ' "data_certa": true, "rspp_reviews_included": 0, "founding": true}', True),
    # Model B seeded inactive — not sellable until Phase 5.
    ("B_BASE", "B", "Base", 49000, 2, None, 1, 500, _B_BASE,
     '{"white_label_domain": false, "sub_tenants": 0, "api": "none",'
     ' "data_certa": false, "rspp_reviews_included": 0}', False),
    ("B_PLUS", "B", "Plus", 99000, 5, None, 3, 1000, _B_PLUS,
     '{"white_label_domain": false, "sub_tenants": 0, "api": "none",'
     ' "data_certa": true, "rspp_reviews_included": 1}', False),
    ("B_MULTISEDE", "B", "Multi-sede", 240000, 15, None, 10, 2500, _B_MULTI,
     '{"white_label_domain": false, "sub_tenants": 0, "api": "none",'
     ' "data_certa": true, "rspp_reviews_included": 2}', False),
]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. MB-1.1 — no-op unless a row somehow escaped the Phase-0 default.
    conn.execute(
        sa.text(
            "UPDATE organizations SET account_type = 'consultant' "
            "WHERE account_type IS NULL OR account_type = ''"
        )
    )

    # 2. MB-1.2 — seed the catalogue. DO NOTHING, not DO UPDATE: if an operator
    #    has already tuned a price by hand, a re-run must not stomp it. Use
    #    scripts/seed_plans.py to push deliberate catalogue changes.
    for (code, model, name, price, seats, max_comp, max_sites,
         credits, docs, features, active) in PLANS:
        conn.execute(
            sa.text(
                """
                INSERT INTO plans (plan_code, model, display_name, price_year_cents,
                                   seats, max_companies, max_sites, ai_credits_year,
                                   allowed_doc_types, features, active)
                VALUES (:code, :model, :name, :price, :seats, :max_comp, :max_sites,
                        :credits, CAST(:docs AS jsonb), CAST(:features AS jsonb), :active)
                ON CONFLICT (plan_code) DO NOTHING
                """
            ),
            {
                "code": code, "model": model, "name": name, "price": price,
                "seats": seats, "max_comp": max_comp, "max_sites": max_sites,
                "credits": credits, "docs": docs, "features": features,
                "active": active,
            },
        )

    # 3. MB-1.3 — one A_FOUNDING subscription per organization that lacks one.
    #    The period starts at the org's own creation date so the usage meters
    #    line up with the tenant's actual history rather than the deploy date.
    conn.execute(
        sa.text(
            """
            INSERT INTO subscriptions (id, organization_id, plan_code, status,
                                       current_period_start, current_period_end)
            SELECT gen_random_uuid(), o.id, 'A_FOUNDING', 'active',
                   date_trunc('month', o.created_at),
                   date_trunc('month', o.created_at) + interval '3 years'
              FROM organizations o
             WHERE NOT EXISTS (
                   SELECT 1 FROM subscriptions s WHERE s.organization_id = o.id
             )
            """
        )
    )

    # 4. MB-1.4 — seed the Model A meter from work already done this period, so
    #    a tenant isn't handed a fresh allowance of companies it already used.
    #
    #    `period_start` is the start of the *subscription* period (plan §4.4/§4.6),
    #    not the calendar month: plans are annual (three years for founding), and
    #    `max_companies` / `ai_credits_year` are per-period allowances. Keying the
    #    meter on a month would both mis-key every row against what the metering
    #    code computes and silently exclude most of the period's history.
    conn.execute(
        sa.text(
            """
            INSERT INTO active_company_periods (organization_id, azienda_id,
                                                period_start, first_activated_at)
            SELECT a.organization_id,
                   a.id,
                   s.current_period_start::date,
                   min(d.created_at)
              FROM documenti_generati d
              JOIN aziende a       ON a.id = d.azienda_id
              JOIN subscriptions s ON s.organization_id = a.organization_id
             WHERE d.status IN ('completed', 'ready')
               AND s.current_period_start IS NOT NULL
               AND d.created_at >= s.current_period_start
             GROUP BY a.organization_id, a.id, s.current_period_start
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    # Data-only, and every row is reconstructible by re-running upgrade().
    # Subscriptions go first (FK to plans). Usage rows are left alone: deleting
    # a customer's recorded consumption to undo a migration would be worse than
    # leaving it, and the ON CONFLICT makes a re-run harmless.
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM subscriptions WHERE plan_code = 'A_FOUNDING'"))
    conn.execute(
        sa.text(
            "DELETE FROM plans WHERE plan_code IN "
            "('A_SOLO','A_STUDIO','A_NETWORK','A_ENTERPRISE','A_FOUNDING',"
            " 'B_BASE','B_PLUS','B_MULTISEDE') "
            # Never orphan a live subscription — if anything still points at a
            # plan, keep the row.
            "AND NOT EXISTS (SELECT 1 FROM subscriptions s WHERE s.plan_code = plans.plan_code)"
        )
    )
