"""The Segnala endpoints through the HTTP layer.

Covers the parts of `app/api/v1/feedback.py` that the service-level mirror
tests cannot reach: tenant isolation, what happens to the context the
browser attaches on its own, repeat submissions, and the status→GitHub
transitions the endpoint (not the service) decides.

Needs a Postgres (DATABASE_URL); skipped otherwise, like the other DB tests.
"""

from __future__ import annotations

import asyncio
import os
import uuid

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
    """An organization with one admin, and a bearer token for HTTP calls."""

    def __init__(self, org_id, user_id, token):
        self.org_id = org_id
        self.user_id = user_id
        self.headers = {"Authorization": f"Bearer {token}"}


async def _provision(session) -> Tenant:
    from app.core.security import create_access_token, hash_password

    org_id, user_id = uuid.uuid4(), uuid.uuid4()
    suffix = str(org_id)[:8]

    await session.execute(
        text("INSERT INTO organizations (id, name, account_type) VALUES (:i, :n, 'consultant')"),
        {"i": org_id, "n": f"pytest-feedback-{suffix}"},
    )
    await session.execute(
        text(
            "INSERT INTO users (id, organization_id, email, full_name, hashed_password, role) "
            "VALUES (:i, :o, :e, 'Test Admin', :p, 'admin')"
        ),
        {
            "i": user_id,
            "o": org_id,
            "e": f"admin-{suffix}@example.com",
            "p": hash_password("pytest-Passw0rd!"),
        },
    )
    await session.commit()
    token = create_access_token({"sub": str(user_id), "org": str(org_id), "role": "admin"})
    return Tenant(org_id, user_id, token)


def _with_tenants(body, count: int = 1):
    """Provision `count` isolated tenants, run `body(client, *tenants)`, clean up.

    One event loop for everything — asyncpg binds connections to the loop
    that first used them, and each test runs its own via `asyncio.run`.
    """
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.db.session import engine as app_engine
    from app.main import app

    async def run():
        await app_engine.dispose()
        engine = create_async_engine(_URL)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        tenants: list[Tenant] = []
        try:
            async with factory() as s:
                for _ in range(count):
                    tenants.append(await _provision(s))
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await body(client, *tenants)
        finally:
            async with factory() as s:
                for tenant in tenants:
                    await s.execute(
                        text("DELETE FROM user_feedback WHERE organization_id = :o"),
                        {"o": tenant.org_id},
                    )
                    await s.execute(
                        text("DELETE FROM users WHERE organization_id = :o"),
                        {"o": tenant.org_id},
                    )
                    await s.execute(
                        text("DELETE FROM organizations WHERE id = :o"), {"o": tenant.org_id}
                    )
                await s.commit()
            await engine.dispose()
            await app_engine.dispose()

    return asyncio.run(run())


@pytest.fixture
def silent_mirror(monkeypatch):
    """Record mirror calls instead of reaching api.github.com."""
    from app.services import github_issues

    calls: dict[str, list] = {"create": [], "close": [], "reopen": []}

    async def fake_create(fb):
        calls["create"].append(fb.id)
        return 4200 + len(calls["create"]), "https://github.com/acme/repo/issues/4200"

    async def fake_close(number, reason):
        calls["close"].append((number, reason))

    async def fake_reopen(number):
        calls["reopen"].append(number)

    monkeypatch.setattr(github_issues, "create_issue_from_feedback", fake_create)
    monkeypatch.setattr(github_issues, "close_issue", fake_close)
    monkeypatch.setattr(github_issues, "reopen_issue", fake_reopen)
    return calls


# --- tenant isolation ------------------------------------------------------


def test_list_shows_only_the_callers_organization(silent_mirror):
    """One tenant's segnalazioni must never appear in another's queue."""

    async def body(client, mine, theirs):
        await client.post(
            "/api/v1/feedback",
            json={"type": "bug", "description": "La mia segnalazione"},
            headers=mine.headers,
        )
        await client.post(
            "/api/v1/feedback",
            json={"type": "bug", "description": "Segnalazione di un altro tenant"},
            headers=theirs.headers,
        )

        res = await client.get("/api/v1/feedback", headers=mine.headers)
        assert res.status_code == 200
        rows = res.json()
        assert [r["description"] for r in rows] == ["La mia segnalazione"]

    _with_tenants(body, count=2)


def test_patch_cannot_reach_another_organizations_row(silent_mirror):
    """Guessing an id from another tenant answers 404, and changes nothing."""

    async def body(client, mine, theirs):
        created = await client.post(
            "/api/v1/feedback",
            json={"type": "idea", "description": "Loro idea"},
            headers=theirs.headers,
        )
        foreign_id = created.json()["id"]

        res = await client.patch(
            f"/api/v1/feedback/{foreign_id}",
            json={"status": "risolto"},
            headers=mine.headers,
        )
        assert res.status_code == 404

        still = await client.get("/api/v1/feedback", headers=theirs.headers)
        assert still.json()[0]["status"] == "nuovo"
        assert silent_mirror["close"] == []

    _with_tenants(body, count=2)


# --- browser-supplied context ---------------------------------------------


def test_oversized_browser_context_never_costs_the_operator_the_report(silent_mirror):
    """The operator did not type the URL or the user agent — clamp, don't 422."""

    async def body(client, tenant):
        res = await client.post(
            "/api/v1/feedback",
            json={
                "type": "bug",
                "description": "Il pulsante Salva non risponde",
                "page_url": "https://dvr-sicurezza.it/survey?q=" + "x" * 3000,
                "route": "/survey/" + "y" * 900,
                "user_agent": "Mozilla/5.0 " + "z" * 900,
            },
            headers=tenant.headers,
        )
        assert res.status_code == 201, res.text
        row = res.json()
        assert row["description"] == "Il pulsante Salva non risponde"
        assert len(row["page_url"]) == 2048
        assert len(row["route"]) == 512
        assert len(row["user_agent"]) == 512

    _with_tenants(body)


def test_non_web_page_url_is_dropped_not_stored(silent_mirror):
    """The triage table turns this into a link an admin is invited to click."""

    async def body(client, tenant):
        res = await client.post(
            "/api/v1/feedback",
            json={
                "type": "bug",
                "description": "Segnalazione con URL ostile",
                "page_url": "javascript:alert(document.cookie)",
            },
            headers=tenant.headers,
        )
        assert res.status_code == 201
        assert res.json()["page_url"] is None

    _with_tenants(body)


# --- repeat submissions ----------------------------------------------------


def test_repeat_submission_returns_the_stored_row_and_mirrors_once(silent_mirror):
    """A retried send is one report: one row, one issue in the public repo."""

    async def body(client, tenant):
        payload = {
            "type": "bug",
            "description": "Nella tipologia contrattuale manca: socio lavoratore",
            "route": "/survey/step-2",
        }
        first = await client.post("/api/v1/feedback", json=payload, headers=tenant.headers)
        second = await client.post("/api/v1/feedback", json=payload, headers=tenant.headers)

        assert first.status_code == 201
        assert second.status_code == 201
        assert second.json()["id"] == first.json()["id"]

        listed = await client.get("/api/v1/feedback", headers=tenant.headers)
        assert len(listed.json()) == 1
        assert len(silent_mirror["create"]) == 1

    _with_tenants(body)


def test_a_different_report_is_never_folded_into_the_previous_one(silent_mirror):
    """Only an identical resend is a duplicate — two real reports stay two."""

    async def body(client, tenant):
        await client.post(
            "/api/v1/feedback",
            json={"type": "bug", "description": "Primo problema"},
            headers=tenant.headers,
        )
        await client.post(
            "/api/v1/feedback",
            json={"type": "bug", "description": "Secondo problema"},
            headers=tenant.headers,
        )
        # Same words, different type: still a separate report.
        await client.post(
            "/api/v1/feedback",
            json={"type": "idea", "description": "Primo problema"},
            headers=tenant.headers,
        )

        listed = await client.get("/api/v1/feedback", headers=tenant.headers)
        assert len(listed.json()) == 3
        assert len(silent_mirror["create"]) == 3

    _with_tenants(body)


def test_two_tenants_reporting_the_same_words_both_get_a_row(silent_mirror):
    """The window is per author, so it must not swallow another org's report."""

    async def body(client, mine, theirs):
        payload = {"type": "bug", "description": "Il PDF esce senza logo"}
        await client.post("/api/v1/feedback", json=payload, headers=mine.headers)
        await client.post("/api/v1/feedback", json=payload, headers=theirs.headers)

        assert len((await client.get("/api/v1/feedback", headers=mine.headers)).json()) == 1
        assert len((await client.get("/api/v1/feedback", headers=theirs.headers)).json()) == 1
        assert len(silent_mirror["create"]) == 2

    _with_tenants(body, count=2)


# --- status transitions drive the mirror -----------------------------------


def test_triage_closes_then_reopens_the_mirrored_issue(silent_mirror):
    """`risolto`/`non_fara` close it; going back to an open status reopens it."""

    async def body(client, tenant):
        created = await client.post(
            "/api/v1/feedback",
            json={"type": "bug", "description": "Da triagare"},
            headers=tenant.headers,
        )
        fid = created.json()["id"]
        issue = created.json()["github_issue_number"]
        assert issue is not None

        async def patch(status: str):
            res = await client.patch(
                f"/api/v1/feedback/{fid}", json={"status": status}, headers=tenant.headers
            )
            assert res.status_code == 200, res.text
            return res.json()

        assert (await patch("in_revisione"))["status"] == "in_revisione"
        assert silent_mirror["close"] == []
        assert silent_mirror["reopen"] == []

        await patch("risolto")
        assert silent_mirror["close"] == [(issue, "completed")]

        await patch("non_fara")
        assert silent_mirror["close"] == [(issue, "completed"), (issue, "not_planned")]

        await patch("nuovo")
        assert silent_mirror["reopen"] == [issue]

    _with_tenants(body)


def test_restating_the_current_status_touches_nothing(silent_mirror):
    """Re-selecting the same value in the triage dropdown is not a transition."""

    async def body(client, tenant):
        created = await client.post(
            "/api/v1/feedback",
            json={"type": "bug", "description": "Stato invariato"},
            headers=tenant.headers,
        )
        fid = created.json()["id"]

        await client.patch(
            f"/api/v1/feedback/{fid}", json={"status": "risolto"}, headers=tenant.headers
        )
        await client.patch(
            f"/api/v1/feedback/{fid}", json={"status": "risolto"}, headers=tenant.headers
        )

        assert len(silent_mirror["close"]) == 1
        assert silent_mirror["reopen"] == []

    _with_tenants(body)


def test_an_unmirrored_row_still_triages(silent_mirror, monkeypatch):
    """GitHub being down when the report arrived must not block triage later."""
    from app.services import github_issues

    async def no_mirror(fb):
        return None, None

    monkeypatch.setattr(github_issues, "create_issue_from_feedback", no_mirror)

    async def body(client, tenant):
        created = await client.post(
            "/api/v1/feedback",
            json={"type": "bug", "description": "Mirror non riuscito"},
            headers=tenant.headers,
        )
        assert created.json()["github_issue_number"] is None

        res = await client.patch(
            f"/api/v1/feedback/{created.json()['id']}",
            json={"status": "risolto"},
            headers=tenant.headers,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "risolto"
        assert silent_mirror["close"] == []

    _with_tenants(body)
