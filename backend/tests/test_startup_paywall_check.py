"""The startup check that says the self-serve funnel is a dead end (MB-6.2).

This exists because the check it replaces was silent on the one day it mattered.
On 2026-07-28 production had `ENTITLEMENTS_ENFORCE=true`, a non-empty
`PAYPAL_CLIENT_ID`/`PAYPAL_CLIENT_SECRET` pair that authenticated nowhere (live
keys against the sandbox host), and no `plans.paypal_plan_id` anywhere. Both
signup funnels were dead ends — `GET /billing/plans` returned `[]`, every
`POST /billing/subscribe` answered 409 — and `_warn_on_unescapable_paywall`
logged nothing, because it only asked whether the credentials were *set*.

So the assertion that carries the regression is
`test_credentials_set_but_nothing_sellable_is_reported`: non-empty credentials
must not buy silence.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest

from app import main
from app.config import settings


@dataclass(frozen=True)
class _FakePlan:
    plan_code: str


@pytest.fixture
def catalogue_returns(monkeypatch):
    """Stub the catalogue read, and the session it would open to do it.

    The check is about what the customer's browser would be offered, so the
    seam is `list_purchasable` — the same call `GET /billing/plans` makes.
    """

    def _install(plans, *, raises: Exception | None = None):
        @asynccontextmanager
        async def _session():
            yield object()

        monkeypatch.setattr(main, "async_session_factory", _session)

        async def _list_purchasable(_session, account_type=None):
            if raises is not None:
                raise raises
            return list(plans)

        monkeypatch.setattr(main.catalogue, "list_purchasable", _list_purchasable)

    return _install


@pytest.fixture
def enforcing(monkeypatch):
    monkeypatch.setattr(settings, "ENTITLEMENTS_ENFORCE", True, raising=False)
    monkeypatch.setattr(settings, "PAYPAL_ENV", "sandbox", raising=False)
    yield


def _errors(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]


# --- the regression -------------------------------------------------------


@pytest.mark.asyncio
async def test_credentials_set_but_nothing_sellable_is_reported(
    enforcing, catalogue_returns, monkeypatch, caplog
):
    """Today's production state, exactly: keys present, catalogue unbound."""
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_ID", "AY-looks-fine", raising=False)
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_SECRET", "EL-looks-fine", raising=False)
    catalogue_returns([])

    with caplog.at_level(logging.INFO):
        await main._warn_on_unescapable_paywall()

    assert any("no plan is checkoutable" in m for m in _errors(caplog)), (
        "non-empty credentials must not buy silence — this is the exact state "
        "that stranded every signup for a day"
    )


# --- the cases either side of it ------------------------------------------


@pytest.mark.asyncio
async def test_missing_credentials_are_reported(enforcing, monkeypatch, caplog):
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_ID", "", raising=False)
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_SECRET", "", raising=False)

    with caplog.at_level(logging.INFO):
        await main._warn_on_unescapable_paywall()

    assert any("PayPal is not configured" in m for m in _errors(caplog))


@pytest.mark.asyncio
async def test_a_provisioned_deployment_is_quiet(
    enforcing, catalogue_returns, monkeypatch, caplog
):
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_ID", "AY-looks-fine", raising=False)
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_SECRET", "EL-looks-fine", raising=False)
    catalogue_returns([_FakePlan("A_SOLO"), _FakePlan("B_BASE")])

    with caplog.at_level(logging.INFO):
        await main._warn_on_unescapable_paywall()

    assert not _errors(caplog)
    # Positive confirmation, so a provisioned deploy leaves a trace saying so
    # rather than being indistinguishable from a check that never ran.
    assert any("2 plan(s) checkoutable" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_shadow_mode_says_nothing(catalogue_returns, monkeypatch, caplog):
    """Nothing is a dead end while no gate can raise (INV-1)."""
    monkeypatch.setattr(settings, "ENTITLEMENTS_ENFORCE", False, raising=False)
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_ID", "", raising=False)
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_SECRET", "", raising=False)
    catalogue_returns([])

    with caplog.at_level(logging.INFO):
        await main._warn_on_unescapable_paywall()

    assert not _errors(caplog)


@pytest.mark.asyncio
async def test_an_unreachable_database_does_not_break_boot(
    enforcing, catalogue_returns, monkeypatch, caplog
):
    """The first seconds of a deploy are not a billing fault.

    The check runs in `lifespan`, so anything it raises would take the whole
    service down over a question that is only advisory.
    """
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_ID", "AY-looks-fine", raising=False)
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_SECRET", "EL-looks-fine", raising=False)
    catalogue_returns([], raises=OSError("connection refused"))

    with caplog.at_level(logging.INFO):
        await main._warn_on_unescapable_paywall()  # must not raise

    assert any("could not check the plan catalogue" in m for m in _errors(caplog))
