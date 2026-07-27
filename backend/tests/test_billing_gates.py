"""Shadow-mode and enforcement behavior of the entitlement gates (MB-1.5).

The property that matters most here is the one that protects the live tenant:
with ``ENTITLEMENTS_ENFORCE`` false, **no gate may ever raise**, no matter how
far over its limit an org is. That is what makes the Phase-1 deploy safe and
the GATE-1 observation window meaningful.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date

import pytest
from fastapi import HTTPException

from app.billing import gates
from app.billing.entitlements import Entitlements
from app.config import settings

ORG = uuid.UUID("22222222-2222-2222-2222-222222222222")


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


@pytest.fixture
def enforcing(monkeypatch):
    monkeypatch.setattr(settings, "ENTITLEMENTS_ENFORCE", True, raising=False)
    yield


@pytest.fixture
def shadow(monkeypatch):
    monkeypatch.setattr(settings, "ENTITLEMENTS_ENFORCE", False, raising=False)
    yield


# --- INV-1: shadow mode never blocks --------------------------------------


def test_no_gate_raises_in_shadow_mode(shadow, caplog):
    """Every gate, maximally violated, still lets the request through."""
    ent = _ent(
        plan_code="B_BASE",
        allowed_doc_types=frozenset({"dvr_master"}),
        seats=1,
        max_companies=1,
        max_sites=1,
        status="canceled",
    )
    with caplog.at_level(logging.INFO):
        gates.ensure_doc_type_allowed(ent, "pos", ORG)
        gates.ensure_seat_available(ent, 99, ORG)
        gates.ensure_company_slot(ent, 99, already_active=False, org_id=ORG)
        gates.ensure_site_slot(ent, 99, ORG)
        gates.ensure_subscription_active(ent, ORG)

    logged = [r.getMessage() for r in caplog.records if "WOULD_402" in r.getMessage()]
    assert len(logged) == 5, logged
    # Greppable and carrying enough to diagnose without the request context.
    reasons = {m.split("reason=")[1].split()[0] for m in logged}
    assert reasons == {"doc_type", "seats", "companies", "sites", "subscription"}
    assert all(f"org={ORG}" in m and "plan=B_BASE" in m for m in logged)


# --- doc types (INV-9) -----------------------------------------------------


def test_doc_type_gate_blocks_pos_for_model_b(enforcing):
    ent = _ent(plan_code="B_BASE", allowed_doc_types=frozenset({"dvr_master"}))
    gates.ensure_doc_type_allowed(ent, "dvr_master", ORG)      # entitled
    gates.ensure_doc_type_allowed(ent, "DVR_MASTER", ORG)      # casing folded
    with pytest.raises(HTTPException) as exc:
        gates.ensure_doc_type_allowed(ent, "pos", ORG)
    assert exc.value.status_code == 402
    # Message reaches the operator's UI, so it must be Italian and actionable.
    assert "piano" in exc.value.detail and "upgrade" in exc.value.detail


def test_model_a_plans_pass_every_doc_type(enforcing):
    from app.billing.constants import ALL_DOC_TYPES

    ent = _ent(allowed_doc_types=None)
    for tipo in ALL_DOC_TYPES:
        gates.ensure_doc_type_allowed(ent, tipo, ORG)  # must not raise


# --- seats -----------------------------------------------------------------


@pytest.mark.parametrize("current,ok", [(0, True), (4, True), (5, False), (9, False)])
def test_seat_gate_is_off_by_one_correct(enforcing, current, ok):
    """A 5-seat plan admits a 5th user and refuses a 6th."""
    ent = _ent(seats=5)
    if ok:
        gates.ensure_seat_available(ent, current, ORG)
    else:
        with pytest.raises(HTTPException) as exc:
            gates.ensure_seat_available(ent, current, ORG)
        assert exc.value.status_code == 402


# --- active companies ------------------------------------------------------


def test_company_already_active_this_period_is_free(enforcing):
    """A company counted this period keeps generating even at the ceiling —
    otherwise a consultant at 15/15 could not finish the 15th company's docs."""
    ent = _ent(max_companies=15)
    gates.ensure_company_slot(ent, active_companies=15, already_active=True, org_id=ORG)


def test_new_company_beyond_the_ceiling_is_blocked(enforcing):
    ent = _ent(max_companies=15)
    gates.ensure_company_slot(ent, active_companies=14, already_active=False, org_id=ORG)
    with pytest.raises(HTTPException) as exc:
        gates.ensure_company_slot(ent, active_companies=15, already_active=False, org_id=ORG)
    assert exc.value.status_code == 402
    assert "15 aziende" in exc.value.detail


def test_unlimited_companies_never_blocks(enforcing):
    ent = _ent(plan_code="A_ENTERPRISE", max_companies=None)
    gates.ensure_company_slot(ent, active_companies=10_000, already_active=False, org_id=ORG)


def test_unlimited_sites_never_blocks(enforcing):
    # Model A plans have max_sites = NULL; the site gate must be inert for them.
    gates.ensure_site_slot(_ent(max_sites=None), 10_000, ORG)


# --- subscription status ---------------------------------------------------


@pytest.mark.parametrize("status_,blocks", [
    ("active", False),
    ("trialing", False),
    # Dunning grace — losing your DVR mid-retry would be unacceptable.
    ("past_due", False),
    ("canceled", True),
])
def test_subscription_gate_follows_status(enforcing, status_, blocks):
    ent = _ent(status=status_)
    if blocks:
        with pytest.raises(HTTPException) as exc:
            gates.ensure_subscription_active(ent, ORG)
        assert exc.value.status_code == 402
        # Read access survives; only new generation stops (D.Lgs. retention).
        assert "scaricare" in exc.value.detail
    else:
        gates.ensure_subscription_active(ent, ORG)


# --- period keying ---------------------------------------------------------


def test_meter_period_follows_the_subscription_not_the_calendar():
    """Plans are annual; keying meters on the calendar month would mis-key every
    row against what the migration wrote."""
    ent = _ent(period_start=date(2026, 4, 1))
    assert ent.meter_period_start == date(2026, 4, 1)


def test_meter_period_falls_back_when_there_is_no_subscription():
    ent = _ent(period_start=None)
    assert ent.meter_period_start == date.today().replace(day=1)
