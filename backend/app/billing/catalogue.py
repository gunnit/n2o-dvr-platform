"""Read access to the ``plans`` table for callers outside ``app.billing``.

``.importlinter`` forbids ``app.api`` from importing ``app.models.plan``, so the
billing endpoints reach the catalogue through here. That is the point of the
contract: the API asks *what may this tenant buy*, not *what rows are in the
plans table*, and the two can diverge (a retired plan is still readable for
existing subscribers but must never appear in a purchase list).
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan


@dataclass(frozen=True)
class PurchasablePlan:
    plan_code: str
    model: str
    display_name: str
    price_year_cents: int
    seats: int
    max_companies: int | None
    max_sites: int | None
    ai_credits_year: int | None
    features: dict[str, Any]
    # None when the Phase-4 setup script has not run for this plan (or for
    # A_FOUNDING, which is never sold). A plan without one cannot be checked out.
    paypal_plan_id: str | None

    @property
    def is_checkoutable(self) -> bool:
        return bool(self.paypal_plan_id) and self.price_year_cents > 0


def _to_purchasable(plan: Plan) -> PurchasablePlan:
    return PurchasablePlan(
        plan_code=plan.plan_code,
        model=plan.model,
        display_name=plan.display_name,
        price_year_cents=plan.price_year_cents,
        seats=plan.seats,
        max_companies=plan.max_companies,
        max_sites=plan.max_sites,
        ai_credits_year=plan.ai_credits_year,
        features=dict(plan.features or {}),
        paypal_plan_id=plan.paypal_plan_id,
    )


async def list_purchasable(db: AsyncSession, account_type: str | None = None) -> list[PurchasablePlan]:
    """Plans a tenant may buy today.

    Filtered to ``active`` — a retired plan keeps working for whoever is on it
    but must not be offered to anyone new. Model B plans are inactive until
    Phase 5, so consultants are all this returns for now.
    """
    stmt = select(Plan).where(Plan.active.is_(True)).order_by(Plan.model, Plan.price_year_cents)
    plans = [_to_purchasable(p) for p in (await db.execute(stmt)).scalars()]
    # Model A plans are sold to consultants, Model B direct to companies. Never
    # show a tenant the other channel's price list.
    if account_type == "consultant":
        plans = [p for p in plans if p.model == "A"]
    elif account_type == "direct":
        plans = [p for p in plans if p.model == "B"]
    return [p for p in plans if p.is_checkoutable]


async def get_plan(plan_code: str, db: AsyncSession) -> PurchasablePlan | None:
    plan = (
        await db.execute(select(Plan).where(Plan.plan_code == plan_code))
    ).scalar_one_or_none()
    return None if plan is None else _to_purchasable(plan)
