"""The 402 an operator reads when an AI action is refused.

Three different states fail the same allowance test in ``spend_credits``:
no subscription resolved, a lapsed subscription, and genuinely exhausted
credits. They used to share one message — "Crediti AI esauriti" — which is
true for exactly one of them.

That cost us a diagnosis. On 2026-07-31 an operator reported "MI DICE CHE
HO FINITO I CREDITI MA IN REALTA' LI HO", four days after the billing
rollout, and the report could not be pinned to a cause because all three
paths said the same thing. These tests keep the three apart.
"""

from __future__ import annotations

from datetime import date

from app.billing.entitlements import Entitlements
from app.billing.metering import _denial_detail


def _ent(**overrides) -> Entitlements:
    base = dict(
        account_type="consultant",
        plan_code="A_SOLO",
        allowed_doc_types=None,
        seats=1,
        max_companies=15,
        max_sites=None,
        ai_credits_year=2500,
        features={},
        status="active",
        period_start=date(2026, 1, 1),
    )
    base.update(overrides)
    return Entitlements(**base)


def test_exhausted_plan_says_credits_are_finished():
    """The one case the original wording actually described."""
    detail = _denial_detail(_ent(ai_credits_year=0))
    assert "esauriti" in detail.lower()
    assert "upgrade" in detail.lower() or "pacchetto" in detail.lower()


def test_unsubscribed_org_is_not_told_it_ran_out_of_credits():
    """`_unsubscribed_entitlements` sets ai_credits_year=0 on purpose, so the
    first credit is refused. Saying "hai finito i crediti" to an org that was
    never granted any is false, and sends the operator to buy a top-up pack
    that would not help — the missing thing is the plan itself."""
    detail = _denial_detail(_ent(plan_code=None, status="none", ai_credits_year=0))
    assert "esauriti" not in detail.lower()
    assert "piano" in detail.lower()


def test_unsubscribed_message_covers_the_payment_settling_race():
    """A customer who has just paid may reach an AI action before PayPal's
    webhook lands. Telling them to reload beats telling them to buy again."""
    detail = _denial_detail(_ent(plan_code=None, status="none", ai_credits_year=0))
    assert "ricarica" in detail.lower()


def test_lapsed_subscription_names_its_state_and_keeps_the_retention_promise():
    """A canceled tenant is `subscribed` but not `is_active`. D.Lgs. 81/2008
    retention means reads survive a lapse (CLAUDE.md), so the message must not
    imply the documents are gone."""
    detail = _denial_detail(_ent(status="canceled"))
    assert "canceled" in detail
    assert "rinnova" in detail.lower()
    assert "scaricabili" in detail.lower()


def test_past_due_still_counts_as_active_and_gets_the_credits_message():
    """`past_due` is in ACTIVE_STATUSES — PayPal retries over several days and
    a customer must not lose AI mid-dunning. It is not the lapsed branch."""
    detail = _denial_detail(_ent(status="past_due", ai_credits_year=0))
    assert "esauriti" in detail.lower()
