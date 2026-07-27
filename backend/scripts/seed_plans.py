"""Upsert the plan catalogue from app.billing.plan_catalogue into `plans`.

The Phase-1 migration seeds the catalogue once so a deploy is self-sufficient.
This script re-applies it whenever the catalogue changes — a price rise, a new
tier, activating the Model B plans in Phase 5.

    python -m scripts.seed_plans            # apply
    python -m scripts.seed_plans --dry-run  # show what would change

Idempotent. `paypal_plan_id` is never touched: the Phase-4 PayPal setup script
owns that column, and clobbering it would detach a live subscription from its
billing plan.
"""

import argparse
import asyncio
import logging
import sys

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.billing.plan_catalogue import PLAN_CATALOGUE, validate_catalogue
from app.db.session import async_session_factory
from app.models.plan import Plan

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Everything except the primary key and paypal_plan_id.
_UPDATABLE = (
    "model",
    "display_name",
    "price_year_cents",
    "seats",
    "max_companies",
    "max_sites",
    "ai_credits_year",
    "allowed_doc_types",
    "features",
    "active",
)


async def seed(dry_run: bool = False) -> int:
    validate_catalogue()

    async with async_session_factory() as session:
        existing = {
            p.plan_code: p for p in (await session.execute(select(Plan))).scalars()
        }

        created, updated, unchanged = [], [], []
        for plan in PLAN_CATALOGUE:
            code = plan["plan_code"]
            current = existing.get(code)
            if current is None:
                created.append(code)
                continue
            diffs = [
                f"{f}: {getattr(current, f)!r} -> {plan[f]!r}"
                for f in _UPDATABLE
                if getattr(current, f) != plan[f]
            ]
            (updated if diffs else unchanged).append(code)
            for d in diffs:
                log.info("  %s %s", code, d)

        if dry_run:
            log.info(
                "DRY RUN — would create %d, update %d, leave %d unchanged",
                len(created), len(updated), len(unchanged),
            )
            return 0

        for plan in PLAN_CATALOGUE:
            stmt = insert(Plan).values(**plan)
            await session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[Plan.plan_code],
                    set_={f: stmt.excluded[f] for f in _UPDATABLE},
                )
            )
        await session.commit()

    log.info(
        "Seeded %d plans (created %d, updated %d, unchanged %d)",
        len(PLAN_CATALOGUE), len(created), len(updated), len(unchanged),
    )
    if created:
        log.info("  created: %s", ", ".join(created))
    if updated:
        log.info("  updated: %s", ", ".join(updated))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="report changes without writing"
    )
    args = parser.parse_args()
    return asyncio.run(seed(dry_run=args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
