"""The billing HTTP surface: entitlements, checkout guards, and the webhook.

The webhook is the sole writer of subscription state (INV-2), so its tests are
the important ones here: an event that is unverified, replayed, or out of order
must never move a customer to a state they did not pay for.

Needs a Postgres (DATABASE_URL); skipped otherwise, like the other DB tests.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

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

PLAN_CODE = "PYTEST_BILL_A"
PAYPAL_PLAN_ID = "P-PYTESTPLAN000000000001"


class Tenant:
    def __init__(self, org_id, user_id, azienda_id, token):
        self.org_id = org_id
        self.user_id = user_id
        self.azienda_id = azienda_id
        self.headers = {"Authorization": f"Bearer {token}"}


async def _provision(session, *, status: str = "active", paypal_sub: str | None = None) -> Tenant:
    from app.core.security import create_access_token, hash_password

    org_id, user_id, azienda_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    suffix = str(org_id)[:8]

    await session.execute(
        text("INSERT INTO organizations (id, name) VALUES (:i, :n)"),
        {"i": org_id, "n": f"pytest-bill-{suffix}"},
    )
    await session.execute(
        text(
            "INSERT INTO users (id, organization_id, email, full_name, hashed_password, role) "
            "VALUES (:i, :o, :e, 'Test Admin', :p, 'admin')"
        ),
        {"i": user_id, "o": org_id, "e": f"bill-{suffix}@example.com",
         "p": hash_password("pytest-Passw0rd!")},
    )
    await session.execute(
        text(
            "INSERT INTO aziende (id, organization_id, ragione_sociale, survey_status) "
            "VALUES (:a, :o, 'Cliente Billing', 'draft')"
        ),
        {"a": azienda_id, "o": org_id},
    )
    await session.execute(
        text(
            """
            INSERT INTO plans (plan_code, model, display_name, price_year_cents, seats,
                               max_companies, ai_credits_year, paypal_plan_id, active)
            VALUES (:c, 'A', 'Pytest Billing', 149000, 3, 10, 500, :pp, true)
            ON CONFLICT (plan_code) DO UPDATE SET paypal_plan_id = EXCLUDED.paypal_plan_id
            """
        ),
        {"c": PLAN_CODE, "pp": PAYPAL_PLAN_ID},
    )
    now = datetime.now(timezone.utc)
    await session.execute(
        text(
            """
            INSERT INTO subscriptions (id, organization_id, plan_code, status,
                                       paypal_subscription_id,
                                       current_period_start, current_period_end)
            VALUES (:i, :o, :p, :st, :ps, :s, :e)
            """
        ),
        {"i": uuid.uuid4(), "o": org_id, "p": PLAN_CODE, "st": status, "ps": paypal_sub,
         "s": now - timedelta(days=1), "e": now + timedelta(days=364)},
    )
    await session.commit()
    token = create_access_token({"sub": str(user_id), "org": str(org_id), "role": "admin"})
    return Tenant(org_id, user_id, azienda_id, token)


def _run(body, *, enforce: bool = False, status: str = "active",
         paypal_sub: str | None = None, patches: dict | None = None):
    """Provision a tenant, run `body(client, tenant, factory)`, then clean up."""
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.billing import paypal_client
    from app.config import settings
    from app.db.session import engine as app_engine
    from app.main import app

    async def run():
        await app_engine.dispose()
        engine = create_async_engine(_URL)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        original_enforce = settings.ENTITLEMENTS_ENFORCE
        settings.ENTITLEMENTS_ENFORCE = enforce
        saved = {name: getattr(paypal_client, name) for name in (patches or {})}
        for name, value in (patches or {}).items():
            setattr(paypal_client, name, value)
        tenant = None
        try:
            async with factory() as s:
                tenant = await _provision(s, status=status, paypal_sub=paypal_sub)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await body(client, tenant, factory)
        finally:
            settings.ENTITLEMENTS_ENFORCE = original_enforce
            for name, value in saved.items():
                setattr(paypal_client, name, value)
            if tenant is not None:
                async with factory() as s:
                    await s.execute(
                        text("DELETE FROM billing_webhook_events WHERE event_id LIKE 'WH-PYTEST%'")
                    )
                    await s.execute(
                        text(
                            "DELETE FROM documenti_generati WHERE azienda_id IN "
                            "(SELECT id FROM aziende WHERE organization_id = :o)"
                        ),
                        {"o": tenant.org_id},
                    )
                    for table, col in (
                        ("active_company_periods", "organization_id"),
                        ("ai_usage_events", "organization_id"),
                        ("usage_counters", "organization_id"),
                        ("subscriptions", "organization_id"),
                        ("aziende", "organization_id"),
                        ("users", "organization_id"),
                        ("organizations", "id"),
                    ):
                        await s.execute(
                            text(f"DELETE FROM {table} WHERE {col} = :o"), {"o": tenant.org_id}
                        )
                    await s.commit()
            await engine.dispose()
            await app_engine.dispose()

    return asyncio.run(run())


async def _status_of(factory, org_id) -> tuple[str, str]:
    async with factory() as s:
        row = (
            await s.execute(
                text("SELECT status, plan_code FROM subscriptions WHERE organization_id = :o"),
                {"o": org_id},
            )
        ).first()
    return row[0], row[1]


# --- MB-3.3 entitlements ---------------------------------------------------


def test_entitlements_reports_plan_limits_and_usage():
    async def body(client, t, factory):
        return await client.get("/api/v1/billing/entitlements", headers=t.headers)

    resp = _run(body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["plan_code"] == PLAN_CODE
    assert data["status"] == "active"
    assert data["is_active"] is True
    assert data["seats"] == 3
    assert data["usage"]["ai_credits_used"] == 0
    assert data["usage"]["ai_credits_allowance"] == 500
    assert data["usage"]["active_companies"] == 0


def test_entitlements_exposes_whether_the_paywall_actually_bites():
    """`enforced` is how the UI knows not to claim something is blocked while
    shadow mode is still letting it through."""

    async def body(client, t, factory):
        return await client.get("/api/v1/billing/entitlements", headers=t.headers)

    assert _run(body, enforce=False).json()["enforced"] is False
    assert _run(body, enforce=True).json()["enforced"] is True


def test_entitlements_requires_auth():
    async def body(client, t, factory):
        return await client.get("/api/v1/billing/entitlements")

    assert _run(body).status_code in (401, 403)


def test_plans_lists_only_checkoutable_plans():
    async def body(client, t, factory):
        return await client.get("/api/v1/billing/plans", headers=t.headers)

    resp = _run(body)
    assert resp.status_code == 200, resp.text
    codes = {p["plan_code"] for p in resp.json()}
    assert PLAN_CODE in codes
    # A_FOUNDING is €0 and has no PayPal plan — it must never be offered.
    assert "A_FOUNDING" not in codes


# --- MB-4.2 subscribe guards ------------------------------------------------


# The subscribe guards must be asserted independently of whether this machine
# happens to have PayPal credentials in .env — CI deliberately runs with
# PAYPAL_CLIENT_ID="" and would otherwise see 503 for all of these.
_CONFIGURED = {"is_configured": lambda: True}


def test_subscribe_is_unavailable_when_paypal_is_not_configured():
    """The state of a fresh environment: say so plainly rather than 500."""

    async def body(client, t, factory):
        return await client.post(
            "/api/v1/billing/subscribe", json={"plan_code": PLAN_CODE}, headers=t.headers
        )

    assert _run(body, patches={"is_configured": lambda: False}).status_code == 503


def test_subscribe_rejects_an_unknown_plan():
    async def body(client, t, factory):
        return await client.post(
            "/api/v1/billing/subscribe", json={"plan_code": "NOPE"}, headers=t.headers
        )

    assert _run(body, patches=_CONFIGURED).status_code == 404


def test_subscribe_refuses_a_plan_with_no_paypal_id():
    """A plan the Phase-4 setup script has not published cannot be bought — a
    409, not a 500 halfway through a checkout."""

    async def body(client, t, factory):
        async with factory() as s:
            await s.execute(
                text(
                    "INSERT INTO plans (plan_code, model, display_name, price_year_cents, "
                    "seats, ai_credits_year, active) "
                    "VALUES ('PYTEST_NOPP', 'A', 'No PayPal', 10000, 1, 10, true) "
                    "ON CONFLICT (plan_code) DO NOTHING"
                )
            )
            await s.commit()
        try:
            return await client.post(
                "/api/v1/billing/subscribe",
                json={"plan_code": "PYTEST_NOPP"},
                headers=t.headers,
            )
        finally:
            async with factory() as s:
                await s.execute(text("DELETE FROM plans WHERE plan_code = 'PYTEST_NOPP'"))
                await s.commit()

    assert _run(body, patches=_CONFIGURED).status_code == 409


def test_cancel_without_a_paypal_subscription_is_a_409():
    async def body(client, t, factory):
        return await client.post("/api/v1/billing/cancel", json={}, headers=t.headers)

    resp = _run(body, paypal_sub=None)
    assert resp.status_code == 409
    assert "abbonamento" in resp.json()["detail"].lower()


# --- MB-4.3 the webhook -----------------------------------------------------


def _event(event_type: str, sub_id: str, event_id: str = "WH-PYTEST-1") -> bytes:
    return json.dumps(
        {"id": event_id, "event_type": event_type, "resource": {"id": sub_id}}
    ).encode()


def _paypal_resource(sub_id: str, org_id, status: str = "ACTIVE") -> dict:
    return {
        "id": sub_id,
        "status": status,
        "plan_id": PAYPAL_PLAN_ID,
        "custom_id": str(org_id),
        "subscriber": {"payer_id": "PAYER123"},
        "start_time": "2026-07-01T00:00:00Z",
        "billing_info": {
            "last_payment": {"time": "2026-07-01T00:00:00Z"},
            "next_billing_time": "2027-07-01T00:00:00Z",
        },
    }


async def _ok_verify(headers, raw):
    return True


async def _bad_verify(headers, raw):
    return False


def test_unverified_webhook_is_rejected_and_not_recorded():
    """The security boundary. An unsigned event must not reach the ledger, let
    alone move subscription state."""

    async def body(client, t, factory):
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=_event("BILLING.SUBSCRIPTION.ACTIVATED", "I-PYTEST1"),
            headers={"content-type": "application/json"},
        )
        async with factory() as s:
            count = (
                await s.execute(
                    text("SELECT count(*) FROM billing_webhook_events WHERE event_id LIKE 'WH-PYTEST%'")
                )
            ).scalar()
        return resp, count

    resp, count = _run(body, patches={"verify_webhook_signature": _bad_verify})
    assert resp.status_code == 401
    assert count == 0


def test_activated_webhook_activates_the_subscription():
    async def body(client, t, factory):
        async def fake_get(sub_id):
            return _paypal_resource(sub_id, t.org_id, "ACTIVE")

        from app.billing import paypal_client

        paypal_client.get_subscription = fake_get
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=_event("BILLING.SUBSCRIPTION.ACTIVATED", "I-PYTEST1"),
            headers={"content-type": "application/json"},
        )
        return resp, await _status_of(factory, t.org_id)

    resp, (status, plan_code) = _run(
        body, status="trialing", patches={"verify_webhook_signature": _ok_verify,
                                          "get_subscription": None},
    )
    assert resp.status_code == 200, resp.text
    assert status == "active"
    assert plan_code == PLAN_CODE


def test_suspended_webhook_moves_to_past_due_not_canceled():
    """Dunning grace: PayPal retries for days and the customer keeps working."""

    async def body(client, t, factory):
        from app.billing import paypal_client

        async def fake_get(sub_id):
            return _paypal_resource(sub_id, t.org_id, "SUSPENDED")

        paypal_client.get_subscription = fake_get
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=_event("BILLING.SUBSCRIPTION.SUSPENDED", "I-PYTEST1"),
            headers={"content-type": "application/json"},
        )
        return resp, await _status_of(factory, t.org_id)

    resp, (status, _) = _run(
        body, paypal_sub="I-PYTEST1",
        patches={"verify_webhook_signature": _ok_verify, "get_subscription": None},
    )
    assert resp.status_code == 200, resp.text
    assert status == "past_due"


def test_cancelled_webhook_cancels():
    async def body(client, t, factory):
        from app.billing import paypal_client

        async def fake_get(sub_id):
            return _paypal_resource(sub_id, t.org_id, "CANCELLED")

        paypal_client.get_subscription = fake_get
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=_event("BILLING.SUBSCRIPTION.CANCELLED", "I-PYTEST1"),
            headers={"content-type": "application/json"},
        )
        return resp, await _status_of(factory, t.org_id)

    resp, (status, _) = _run(
        body, paypal_sub="I-PYTEST1",
        patches={"verify_webhook_signature": _ok_verify, "get_subscription": None},
    )
    assert resp.status_code == 200
    assert status == "canceled"


def test_replayed_webhook_is_handled_exactly_once():
    """PayPal retries until it gets a 2xx, and retries can overlap. The second
    delivery must be a no-op, not a second state change."""

    async def body(client, t, factory):
        from app.billing import paypal_client

        calls = []

        async def fake_get(sub_id):
            calls.append(sub_id)
            return _paypal_resource(sub_id, t.org_id, "ACTIVE")

        paypal_client.get_subscription = fake_get
        payload = _event("BILLING.SUBSCRIPTION.ACTIVATED", "I-PYTEST1", "WH-PYTEST-DUP")
        headers = {"content-type": "application/json"}
        first = await client.post("/api/v1/billing/webhook", content=payload, headers=headers)
        second = await client.post("/api/v1/billing/webhook", content=payload, headers=headers)
        async with factory() as s:
            rows = (
                await s.execute(
                    text("SELECT count(*) FROM billing_webhook_events WHERE event_id = 'WH-PYTEST-DUP'")
                )
            ).scalar()
        return first, second, len(calls), rows

    first, second, call_count, rows = _run(
        body, status="trialing",
        patches={"verify_webhook_signature": _ok_verify, "get_subscription": None},
    )
    assert first.status_code == 200 and first.json()["status"] == "ok"
    assert second.status_code == 200 and second.json()["status"] == "duplicate"
    # PayPal was only consulted once — the replay short-circuited on the claim.
    assert call_count == 1
    assert rows == 1


def test_unhandled_event_type_is_acknowledged_not_retried():
    """Returning non-2xx would make PayPal redeliver an event we deliberately
    ignore, forever."""

    async def body(client, t, factory):
        return await client.post(
            "/api/v1/billing/webhook",
            content=_event("CUSTOMER.DISPUTE.CREATED", "I-PYTEST1", "WH-PYTEST-IGN"),
            headers={"content-type": "application/json"},
        )

    resp = _run(body, patches={"verify_webhook_signature": _ok_verify})
    assert resp.status_code == 200
    assert "ignored" in resp.json()["outcome"]


def test_webhook_for_an_unknown_subscription_does_not_crash():
    async def body(client, t, factory):
        from app.billing import paypal_client

        async def fake_get(sub_id):
            return None

        paypal_client.get_subscription = fake_get
        return await client.post(
            "/api/v1/billing/webhook",
            content=_event("BILLING.SUBSCRIPTION.ACTIVATED", "I-GHOST", "WH-PYTEST-GHOST"),
            headers={"content-type": "application/json"},
        )

    resp = _run(
        body, patches={"verify_webhook_signature": _ok_verify, "get_subscription": None}
    )
    assert resp.status_code == 200
    assert "ignored" in resp.json()["outcome"]


# --- MB-4.5 dunning -> read-only --------------------------------------------


def test_canceled_subscription_cannot_generate_new_documents():
    """The lapsed-subscription gate at the single dispatch chokepoint."""

    async def body(client, t, factory):
        return await client.post(
            f"/api/v1/aziende/{t.azienda_id}/documents/generate",
            params={"azienda_id": str(t.azienda_id)},
            json={"tipo_documento": "dvr_master"},
            headers=t.headers,
        )

    resp = _run(body, enforce=True, status="canceled")
    assert resp.status_code == 402, resp.text
    assert "abbonamento" in resp.json()["detail"].lower()


def test_past_due_subscription_can_still_generate():
    """Mid-dunning a customer must not lose their DVR — PayPal is still retrying."""

    async def body(client, t, factory):
        return await client.post(
            f"/api/v1/aziende/{t.azienda_id}/documents/generate",
            params={"azienda_id": str(t.azienda_id)},
            json={"tipo_documento": "dvr_master"},
            headers=t.headers,
        )

    resp = _run(body, enforce=True, status="past_due")
    assert resp.status_code != 402, resp.text


# --- MB-3.1 admin -----------------------------------------------------------


def test_admin_can_set_a_plan_by_hand():
    async def body(client, t, factory):
        resp = await client.post(
            f"/api/v1/billing/admin/organizations/{t.org_id}/plan",
            json={"plan_code": PLAN_CODE, "status": "active", "months": 12},
            headers=t.headers,
        )
        return resp, await _status_of(factory, t.org_id)

    resp, (status, plan_code) = _run(body, status="canceled")
    assert resp.status_code == 200, resp.text
    assert status == "active" and plan_code == PLAN_CODE


def test_admin_set_plan_rejects_a_bad_status():
    async def body(client, t, factory):
        return await client.post(
            f"/api/v1/billing/admin/organizations/{t.org_id}/plan",
            json={"plan_code": PLAN_CODE, "status": "gratis", "months": 12},
            headers=t.headers,
        )

    assert _run(body).status_code == 422
