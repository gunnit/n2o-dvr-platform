"""GATE 2 — the paywall proven through the HTTP layer, not the UI.

INV-5: frontend gating is cosmetic. These tests call the FastAPI app directly
with a valid token and assert the 402 arrives, which is what a `curl`, a stale
tab, or a determined customer would hit.

They also assert the converse, which matters more commercially: an org on the
founding plan is completely unaffected. If any of these turn red for
`A_FOUNDING`, flipping `ENTITLEMENTS_ENFORCE` would break the live tenant.

Needs a Postgres (DATABASE_URL); skipped otherwise, like the other DB tests.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta

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


# --- fixtures --------------------------------------------------------------


class Tenant:
    """An org + admin + azienda, with a bearer token for HTTP calls."""

    def __init__(self, org_id, user_id, azienda_id, token):
        self.org_id = org_id
        self.user_id = user_id
        self.azienda_id = azienda_id
        self.headers = {"Authorization": f"Bearer {token}"}


async def _provision(session, *, plan_code: str, plan_kwargs: dict) -> Tenant:
    from app.core.security import create_access_token, hash_password

    org_id, user_id, azienda_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    suffix = str(org_id)[:8]

    await session.execute(
        text("INSERT INTO organizations (id, name) VALUES (:i, :n)"),
        {"i": org_id, "n": f"pytest-402-{suffix}"},
    )
    await session.execute(
        text(
            "INSERT INTO users (id, organization_id, email, full_name, hashed_password, role) "
            "VALUES (:i, :o, :e, 'Test Admin', :p, 'admin')"
        ),
        {"i": user_id, "o": org_id, "e": f"admin-{suffix}@example.com",
         "p": hash_password("pytest-Passw0rd!")},
    )
    await session.execute(
        text(
            "INSERT INTO aziende (id, organization_id, ragione_sociale, survey_status) "
            "VALUES (:a, :o, 'Cliente 402', 'draft')"
        ),
        {"a": azienda_id, "o": org_id},
    )

    cols = dict(
        plan_code=plan_code, model="B", display_name=plan_code,
        price_year_cents=0, seats=1, max_companies=None, max_sites=None,
        ai_credits_year=0, allowed_doc_types=None,
    )
    cols.update(plan_kwargs)
    await session.execute(
        text(
            """
            INSERT INTO plans (plan_code, model, display_name, price_year_cents, seats,
                               max_companies, max_sites, ai_credits_year, allowed_doc_types)
            VALUES (:plan_code, :model, :display_name, :price_year_cents, :seats,
                    :max_companies, :max_sites, :ai_credits_year,
                    CAST(:allowed_doc_types AS jsonb))
            ON CONFLICT (plan_code) DO UPDATE SET
                seats = EXCLUDED.seats,
                max_companies = EXCLUDED.max_companies,
                ai_credits_year = EXCLUDED.ai_credits_year,
                allowed_doc_types = EXCLUDED.allowed_doc_types
            """
        ),
        cols,
    )
    now = datetime.utcnow()
    await session.execute(
        text(
            """
            INSERT INTO subscriptions (id, organization_id, plan_code, status,
                                       current_period_start, current_period_end)
            VALUES (:i, :o, :p, 'active', :s, :e)
            """
        ),
        {"i": uuid.uuid4(), "o": org_id, "p": plan_code,
         "s": now - timedelta(days=1), "e": now + timedelta(days=364)},
    )
    await session.commit()
    token = create_access_token({"sub": str(user_id), "org": str(org_id), "role": "admin"})
    return Tenant(org_id, user_id, azienda_id, token)


def _with_tenant(plan_code: str, enforce: bool, body, **plan_kwargs):
    """Provision a tenant, run `body(client, tenant)`, then clean up.

    One event loop for everything (asyncpg binds connections to their loop),
    and enforcement is toggled around the call rather than globally so the
    tests can run in any order.
    """
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings
    from app.main import app

    from app.db.session import engine as app_engine

    async def run():
        # The app's own engine is module-level and pools connections bound to
        # whichever event loop first used them. Each test runs its own loop via
        # asyncio.run, so the pool must be dropped on the way in and out or the
        # second test hits "attached to a different loop".
        await app_engine.dispose()
        engine = create_async_engine(_URL)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        original = settings.ENTITLEMENTS_ENFORCE
        settings.ENTITLEMENTS_ENFORCE = enforce
        tenant = None
        try:
            async with factory() as s:
                tenant = await _provision(s, plan_code=plan_code, plan_kwargs=plan_kwargs)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await body(client, tenant)
        finally:
            settings.ENTITLEMENTS_ENFORCE = original
            if tenant is not None:
                async with factory() as s:
                    for table, col in (
                        ("active_company_periods", "organization_id"),
                        ("ai_usage_events", "organization_id"),
                        ("usage_counters", "organization_id"),
                        ("subscriptions", "organization_id"),
                        ("documenti_generati", None),
                        ("aziende", "organization_id"),
                        ("users", "organization_id"),
                        ("organizations", "id"),
                    ):
                        if table == "documenti_generati":
                            await s.execute(
                                text(
                                    "DELETE FROM documenti_generati WHERE azienda_id IN "
                                    "(SELECT id FROM aziende WHERE organization_id = :o)"
                                ),
                                {"o": tenant.org_id},
                            )
                        else:
                            await s.execute(
                                text(f"DELETE FROM {table} WHERE {col} = :o"),
                                {"o": tenant.org_id},
                            )
                    await s.commit()
            await engine.dispose()
            await app_engine.dispose()

    return asyncio.run(run())


# --- doc-type gate (MB-2.1, INV-9) ----------------------------------------


def test_unentitled_doc_type_is_402_over_http():
    """A Model B plan without POS must not be able to generate one, however the
    request is made. This is the channel-conflict guardrail."""

    async def body(client, t):
        return await client.post(
            f"/api/v1/aziende/{t.azienda_id}/documents/generate",
            params={"azienda_id": str(t.azienda_id)},
            json={"tipo_documento": "pos"},
            headers=t.headers,
        )

    resp = _with_tenant(
        "PYTEST_B_NOPOS", True, body,
        allowed_doc_types='["dvr_master"]', ai_credits_year=100,
    )
    assert resp.status_code == 402, resp.text
    assert "piano" in resp.json()["detail"].lower()


def test_entitled_doc_type_is_not_blocked():
    async def body(client, t):
        return await client.post(
            f"/api/v1/aziende/{t.azienda_id}/documents/generate",
            params={"azienda_id": str(t.azienda_id)},
            json={"tipo_documento": "allegato_mmc"},
            headers=t.headers,
        )

    resp = _with_tenant(
        "PYTEST_B_MMC", True, body,
        allowed_doc_types='["allegato_mmc"]', ai_credits_year=100,
    )
    # 202 accepted (or a broker hiccup) — anything but a payment refusal.
    assert resp.status_code != 402, resp.text


def test_shadow_mode_lets_the_unentitled_type_through():
    """INV-1: with enforcement off, the same request that 402s above succeeds.
    This is what makes the Phase-2 deploy safe to ship before the flag flip."""

    async def body(client, t):
        return await client.post(
            f"/api/v1/aziende/{t.azienda_id}/documents/generate",
            params={"azienda_id": str(t.azienda_id)},
            json={"tipo_documento": "pos"},
            headers=t.headers,
        )

    resp = _with_tenant(
        "PYTEST_B_SHADOW", False, body,
        allowed_doc_types='["dvr_master"]', ai_credits_year=100,
    )
    assert resp.status_code != 402, resp.text


def test_founding_plan_can_generate_every_document_type():
    """The live tenant is on A_FOUNDING. If this fails, flipping the flag
    breaks production."""

    async def body(client, t):
        out = {}
        for tipo in ("dvr_master", "pos", "haccp", "duvri", "pee_comune"):
            r = await client.post(
                f"/api/v1/aziende/{t.azienda_id}/documents/generate",
                params={"azienda_id": str(t.azienda_id)},
                json={"tipo_documento": tipo},
                headers=t.headers,
            )
            out[tipo] = r.status_code
        return out

    codes = _with_tenant(
        "PYTEST_A_FOUNDING", True, body,
        model="A", allowed_doc_types=None, ai_credits_year=None,
        max_companies=None, seats=5,
    )
    assert all(c != 402 for c in codes.values()), codes


# --- company ceiling (MB-2.3) ---------------------------------------------


def test_company_beyond_the_ceiling_is_402():
    """max_companies=0 means the first new company already exceeds it."""

    async def body(client, t):
        return await client.post(
            f"/api/v1/aziende/{t.azienda_id}/documents/generate",
            params={"azienda_id": str(t.azienda_id)},
            json={"tipo_documento": "dvr_master"},
            headers=t.headers,
        )

    resp = _with_tenant(
        "PYTEST_A_NOCOMP", True, body,
        model="A", allowed_doc_types=None, ai_credits_year=None, max_companies=0,
    )
    assert resp.status_code == 402, resp.text
    assert "aziende" in resp.json()["detail"]


# --- seats (MB-2.5) --------------------------------------------------------


def test_seat_overflow_is_402_over_http():
    """The org already has its admin; a 1-seat plan must refuse the second."""

    async def body(client, t):
        return await client.post(
            "/api/v1/users",
            json={
                "email": f"second-{uuid.uuid4().hex[:8]}@example.com",
                "password": "pytest-Passw0rd!",
                "full_name": "Second User",
                "role": "operatore_ufficio",
            },
            headers=t.headers,
        )

    resp = _with_tenant("PYTEST_1SEAT", True, body, seats=1, ai_credits_year=None)
    assert resp.status_code == 402, resp.text
    assert "utenti" in resp.json()["detail"]


def test_seat_within_the_plan_is_allowed():
    async def body(client, t):
        return await client.post(
            "/api/v1/users",
            json={
                "email": f"second-{uuid.uuid4().hex[:8]}@example.com",
                "password": "pytest-Passw0rd!",
                "full_name": "Second User",
                "role": "operatore_ufficio",
            },
            headers=t.headers,
        )

    resp = _with_tenant("PYTEST_5SEAT", True, body, seats=5, ai_credits_year=None)
    assert resp.status_code == 201, resp.text


# --- AI credits (MB-2.4) ---------------------------------------------------


def test_exhausted_credits_402_before_reaching_openai(monkeypatch):
    """A 0-credit plan must be refused *before* the provider is contacted —
    INV-7, charge only for work you will actually do."""
    called = {"n": 0}

    async def _never(*args, **kwargs):  # pragma: no cover - must not run
        called["n"] += 1
        raise AssertionError("OpenAI was contacted despite exhausted credits")

    import app.api.v1.aziende as aziende_router

    monkeypatch.setattr(aziende_router, "generate_company_description", _never)

    async def body(client, t):
        return await client.post(
            f"/api/v1/aziende/{t.azienda_id}/genera-descrizione",
            headers=t.headers,
        )

    resp = _with_tenant(
        "PYTEST_NOCREDIT", True, body,
        model="A", allowed_doc_types=None, ai_credits_year=0, max_companies=None,
    )
    assert resp.status_code == 402, resp.text
    assert called["n"] == 0, "the AI service was called despite a 402"
