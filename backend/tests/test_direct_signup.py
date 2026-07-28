"""Direct (Model B) signup and the channel guardrail on checkout.

MB-5.1/5.4/5.7. Three things have to hold for the direct channel to be safe to
open:

* a tenant becomes `direct` **because of which endpoint was called**, never
  because of a field a caller can set;
* no tenant is provisioned without the datore-di-lavoro acknowledgement, and the
  wording it agreed to is recorded;
* a direct tenant can buy Model B plans and *only* Model B plans — the purchase
  half of INV-9, checked server-side because the UI is cosmetic (INV-5).

Needs a Postgres (DATABASE_URL); skipped otherwise, like the other DB tests.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from sqlalchemy import text

from app.core.security import decode_access_token
from app.data.ddl_consent import DDL_CONSENT_VERSION
from app.db.session import _normalize_async_url

_URL = _normalize_async_url(os.environ["DATABASE_URL"]) if os.environ.get("DATABASE_URL") else None


def _reachable() -> bool:
    if not _URL:
        return False
    from sqlalchemy.ext.asyncio import create_async_engine

    async def probe() -> bool:
        eng = create_async_engine(_URL)
        try:
            async with eng.connect() as c:
                await c.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
        finally:
            await eng.dispose()

    try:
        return asyncio.run(probe())
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _reachable(), reason="needs a reachable Postgres in DATABASE_URL"
)

# Two throwaway plan rows, one per channel, both checkoutable. The real
# catalogue's Model B rows carry no `paypal_plan_id` until the PayPal setup
# script has run against a merchant account, so they would be filtered out of
# `/billing/plans` here for a reason that has nothing to do with what we test.
A_PLAN = "PYTEST_DIRECT_A"
B_PLAN = "PYTEST_DIRECT_B"


def _run(body, *, patches: dict | None = None):
    """Run `body(client, factory)` against the app, then clean up every tenant
    this test module created."""
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.billing import paypal_client
    from app.db.session import engine as app_engine
    from app.main import app

    async def run():
        await app_engine.dispose()
        engine = create_async_engine(_URL)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        saved = {name: getattr(paypal_client, name) for name in (patches or {})}
        for name, value in (patches or {}).items():
            setattr(paypal_client, name, value)
        try:
            async with factory() as s:
                for code, model in ((A_PLAN, "A"), (B_PLAN, "B")):
                    await s.execute(
                        text(
                            """
                            INSERT INTO plans (plan_code, model, display_name,
                                               price_year_cents, seats, max_companies,
                                               max_sites, ai_credits_year,
                                               paypal_plan_id, active)
                            VALUES (:c, :m, 'Pytest Direct', 49000, 2, 10, 1, 500,
                                    :pp, true)
                            ON CONFLICT (plan_code) DO UPDATE
                                SET paypal_plan_id = EXCLUDED.paypal_plan_id,
                                    active = true
                            """
                        ),
                        {"c": code, "m": model, "pp": f"P-PYTEST{model}0000000000001"},
                    )
                await s.commit()
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await body(client, factory)
        finally:
            for name, value in saved.items():
                setattr(paypal_client, name, value)
            async with factory() as s:
                await s.execute(
                    text(
                        "DELETE FROM subscriptions WHERE organization_id IN "
                        "(SELECT id FROM organizations WHERE name LIKE 'pytest-direct-%')"
                    )
                )
                await s.execute(
                    text(
                        "DELETE FROM users WHERE organization_id IN "
                        "(SELECT id FROM organizations WHERE name LIKE 'pytest-direct-%')"
                    )
                )
                await s.execute(
                    text("DELETE FROM organizations WHERE name LIKE 'pytest-direct-%'")
                )
                await s.execute(
                    text("DELETE FROM plans WHERE plan_code IN (:a, :b)"),
                    {"a": A_PLAN, "b": B_PLAN},
                )
                await s.commit()
            await engine.dispose()
            await app_engine.dispose()

    return asyncio.run(run())


def _signup_payload(**overrides) -> dict:
    suffix = uuid.uuid4().hex[:10]
    payload = {
        "full_name": "Mario Rossi",
        "email": f"direct-{suffix}@example.com",
        "password": "pytest-Passw0rd!",
        "organization_name": f"pytest-direct-{suffix}",
        "consenso_datore_lavoro": True,
        "consenso_versione": DDL_CONSENT_VERSION,
    }
    payload.update(overrides)
    return payload


async def _org_row(factory, name: str):
    async with factory() as s:
        return (
            await s.execute(
                text(
                    "SELECT account_type, ddl_consent_at, ddl_consent_version "
                    "FROM organizations WHERE name = :n"
                ),
                {"n": name},
            )
        ).first()


# --- MB-5.4 / MB-5.7 — provisioning a direct tenant -------------------------


def test_register_direct_creates_a_direct_tenant_and_records_the_consent():
    payload = _signup_payload()

    async def body(client, factory):
        resp = await client.post("/api/v1/auth/register-direct", json=payload)
        return resp, await _org_row(factory, payload["organization_name"])

    resp, org = _run(body)
    assert resp.status_code == 201, resp.text

    account_type, consent_at, consent_version = org
    assert account_type == "direct"
    # The consent is evidence, so both halves must be there: *when* it was given
    # and *which wording* — a timestamp alone cannot be reproduced later.
    assert consent_at is not None
    assert consent_version == DDL_CONSENT_VERSION

    claims = decode_access_token(resp.json()["access_token"])
    assert claims["account_type"] == "direct"
    # INV-3: the token says which channel, never what the channel is worth.
    assert not {"plan", "plan_code", "credits", "limits"} & set(claims)


def test_register_direct_refuses_without_the_consent_and_provisions_nothing():
    payload = _signup_payload(consenso_datore_lavoro=False)

    async def body(client, factory):
        resp = await client.post("/api/v1/auth/register-direct", json=payload)
        return resp, await _org_row(factory, payload["organization_name"])

    resp, org = _run(body)
    assert resp.status_code == 422, resp.text
    # A half-provisioned tenant would be worse than a refusal: it could sign in
    # and buy a plan having never seen the acknowledgement.
    assert org is None


def test_register_direct_refuses_a_consent_version_it_does_not_know():
    """The form is showing wording this deploy cannot reproduce. Refusing beats
    stamping consent to text nobody can produce in a dispute."""
    payload = _signup_payload(consenso_versione="1999-01")

    async def body(client, factory):
        resp = await client.post("/api/v1/auth/register-direct", json=payload)
        return resp, await _org_row(factory, payload["organization_name"])

    resp, org = _run(body)
    assert resp.status_code == 422, resp.text
    assert org is None


def test_consultant_register_is_unchanged_and_cannot_be_talked_into_direct():
    """`account_type` is a property of the endpoint, not of the request body."""
    payload = _signup_payload()
    payload["account_type"] = "direct"  # ignored: not a field on RegisterRequest

    async def body(client, factory):
        resp = await client.post("/api/v1/auth/register", json=payload)
        return resp, await _org_row(factory, payload["organization_name"])

    resp, org = _run(body)
    assert resp.status_code == 201, resp.text
    assert org[0] == "consultant"
    assert org[1] is None, "a consultant org must carry no datore-di-lavoro consent"
    assert decode_access_token(resp.json()["access_token"])["account_type"] == "consultant"


def test_login_carries_the_account_type_from_the_database():
    """Not from the token being replaced — the DB is the authority (INV-3), so a
    tenant whose channel changed gets the new one on the next sign-in."""
    payload = _signup_payload()

    async def body(client, factory):
        await client.post("/api/v1/auth/register-direct", json=payload)
        return await client.post(
            "/api/v1/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )

    resp = _run(body)
    assert resp.status_code == 200, resp.text
    assert decode_access_token(resp.json()["access_token"])["account_type"] == "direct"


# --- INV-9 — the purchase-side channel guardrail ----------------------------


def test_a_direct_tenant_is_offered_model_b_plans_only():
    payload = _signup_payload()

    async def body(client, factory):
        reg = await client.post("/api/v1/auth/register-direct", json=payload)
        headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
        return await client.get("/api/v1/billing/plans", headers=headers)

    resp = _run(body)
    assert resp.status_code == 200, resp.text
    codes = {p["plan_code"] for p in resp.json()}
    assert B_PLAN in codes
    assert A_PLAN not in codes
    assert all(p["model"] == "B" for p in resp.json())


def test_a_direct_tenant_cannot_buy_a_consultant_plan():
    """The real paywall is here, not in the price list: a direct tenant that
    POSTs a Model A plan code straight at the API must be refused."""
    payload = _signup_payload()
    called = []

    async def never(*args, **kwargs):  # pragma: no cover - must not run
        called.append(args)
        raise AssertionError("PayPal was called for a cross-channel purchase")

    async def body(client, factory):
        reg = await client.post("/api/v1/auth/register-direct", json=payload)
        headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
        return await client.post(
            "/api/v1/billing/subscribe", json={"plan_code": A_PLAN}, headers=headers
        )

    resp = _run(body, patches={"create_subscription": never})
    assert resp.status_code == 403, resp.text
    assert not called
