"""Tests for the GitHub Issues feedback mirror.

We patch httpx.AsyncClient with a MockTransport so the service runs its
real request-building code (headers, payload shape, URL) end-to-end —
just without hitting api.github.com. That way regressions in the payload
shape get caught here, not by a 422 in production.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.config import settings
from app.services import github_issues


def _make_fb(**overrides: Any) -> Any:
    """Build a stand-in for UserFeedback that the service can read.

    The service only reads attributes — never touches the session — so
    a SimpleNamespace is enough and avoids dragging in SQLAlchemy state.
    """
    defaults: dict[str, Any] = dict(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        type="bug",
        description="NELLA TIPOLOGIA CONTRATTUALE MANCA: SOCIO LAVORATORE",
        page_url="https://dvr-sicurezza.it/survey/abc",
        route="/survey/abc",
        user_agent="Mozilla/5.0",
        status="nuovo",
        github_issue_number=None,
        github_issue_url=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.fixture
def configure_github(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "ghp_test_token", raising=False)
    monkeypatch.setattr(settings, "GITHUB_REPO", "acme/test-repo", raising=False)
    monkeypatch.setattr(
        settings, "GITHUB_FEEDBACK_LABELS", ["user-feedback"], raising=False
    )


def _install_transport(monkeypatch, handler):
    """Force every httpx.AsyncClient(...) in the service to use this handler."""
    transport = httpx.MockTransport(handler)
    real_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)


@pytest.mark.asyncio
async def test_create_issue_success(monkeypatch, configure_github):
    seen: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["method"] = req.method
        seen["headers"] = dict(req.headers)
        seen["json"] = req.read().decode()
        return httpx.Response(
            201,
            json={
                "number": 42,
                "html_url": "https://github.com/acme/test-repo/issues/42",
            },
        )

    _install_transport(monkeypatch, handler)

    fb = _make_fb()
    number, url = await github_issues.create_issue_from_feedback(
        fb, user_label="Mario Rossi"
    )

    assert number == 42
    assert url == "https://github.com/acme/test-repo/issues/42"
    assert seen["method"] == "POST"
    assert seen["url"] == "https://api.github.com/repos/acme/test-repo/issues"
    assert seen["headers"]["authorization"] == "Bearer ghp_test_token"
    # Labels include the configured default plus the type-derived one.
    body = seen["json"]
    assert "user-feedback" in body
    assert "bug" in body
    assert "Mario Rossi" in body
    assert str(fb.id) in body


@pytest.mark.asyncio
async def test_create_issue_no_token_is_noop(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "", raising=False)
    called = False

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(201, json={})

    _install_transport(monkeypatch, handler)
    number, url = await github_issues.create_issue_from_feedback(
        _make_fb(), user_label=None
    )
    assert (number, url) == (None, None)
    assert called is False, "no token = no HTTP call"


@pytest.mark.asyncio
async def test_create_issue_4xx_logs_and_returns_none(monkeypatch, configure_github):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "Validation failed"})

    _install_transport(monkeypatch, handler)
    number, url = await github_issues.create_issue_from_feedback(
        _make_fb(), user_label=None
    )
    assert (number, url) == (None, None)


@pytest.mark.asyncio
async def test_create_issue_network_error_returns_none(monkeypatch, configure_github):
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    _install_transport(monkeypatch, handler)
    number, url = await github_issues.create_issue_from_feedback(
        _make_fb(), user_label=None
    )
    assert (number, url) == (None, None)


@pytest.mark.asyncio
async def test_close_issue_sends_state_reason(monkeypatch, configure_github):
    seen: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["method"] = req.method
        seen["body"] = req.read().decode()
        return httpx.Response(200, json={})

    _install_transport(monkeypatch, handler)
    await github_issues.close_issue(42, "not_planned")
    assert seen["method"] == "PATCH"
    assert seen["url"] == "https://api.github.com/repos/acme/test-repo/issues/42"
    assert "closed" in seen["body"]
    assert "not_planned" in seen["body"]


@pytest.mark.asyncio
async def test_build_title_truncates_and_prefixes():
    fb = _make_fb(
        type="idea",
        description="x" * 200,
    )
    title = github_issues._build_title(fb)
    assert title.startswith("[Idea] ")
    assert title.endswith("...")
    # Prefix (7 chars) + 77 truncated body + "..." = 87 max
    assert len(title) <= 90
