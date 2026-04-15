"""Tests for the admin AI-feedback view (US-5.3).

We don't spin up a DB here — the admin endpoints in `app.api.v1.ai_feedback`
are gated by `require_role("admin")` and lean entirely on standard
SQLAlchemy + Pydantic primitives. What we CAN guard against statically is:

  * the routes are registered under the expected paths so the frontend
    panel can't 404 silently after a refactor,
  * the response schemas keep the contract the panel renders against
    (entity_type / counts / labels), and
  * the JSONB context preview helper survives the most common shapes the
    measures-panel sends today.

For full request/response coverage we'd need an async DB fixture; that's
deferred to the QA flow same as the rest of the AI feedback module.
"""

from __future__ import annotations

import pytest

from app.api.v1.ai_feedback import (
    FeedbackSummary,
    FeedbackSummaryRow,
    RecentFeedbackRow,
    _context_preview,
)


# ---------------------------------------------------------------------------
# Route registration — fail loudly if the admin paths drift
# ---------------------------------------------------------------------------


def test_router_registers_admin_summary_and_recent():
    """The admin panel hits /admin/summary + /admin/recent — keep them."""
    from app.api.v1.router import api_router

    paths = {
        (method, getattr(r, "path", ""))
        for r in api_router.routes
        for method in getattr(r, "methods", set()) or set()
    }
    assert ("GET", "/api/v1/ai-feedback/admin/summary") in paths
    assert ("GET", "/api/v1/ai-feedback/admin/recent") in paths
    # And the original POST endpoint stays — the panel reads, the
    # measures-panel writes; both must keep working.
    assert ("POST", "/api/v1/ai-feedback") in paths


# ---------------------------------------------------------------------------
# Response schema contract
# ---------------------------------------------------------------------------


def test_summary_schema_shape():
    summary = FeedbackSummary(
        rows=[
            FeedbackSummaryRow(
                entity_type="misura_suggerita",
                thumbs_down_count=12,
                thumbs_up_count=4,
            )
        ],
        total_thumbs_down=12,
        total_thumbs_up=4,
    )
    dumped = summary.model_dump()
    assert dumped["total_thumbs_down"] == 12
    assert dumped["total_thumbs_up"] == 4
    row = dumped["rows"][0]
    # The frontend KPI cards key off these field names — don't rename
    # without updating the page in lockstep.
    assert row["entity_type"] == "misura_suggerita"
    assert row["thumbs_down_count"] == 12
    assert row["thumbs_up_count"] == 4


def test_recent_row_accepts_minimal_payload():
    """A signal with no azienda + no user must still serialize cleanly."""
    from datetime import datetime, timezone

    row = RecentFeedbackRow(
        id="00000000-0000-0000-0000-000000000001",
        signal="thumbs_down",
        entity_type="company_description",
        entity_id=None,
        reason=None,
        azienda_id=None,
        azienda_label=None,
        user_id=None,
        user_label=None,
        context_preview=None,
        created_at=datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc),
    )
    dumped = row.model_dump()
    assert dumped["azienda_label"] is None
    assert dumped["user_label"] is None
    assert dumped["signal"] == "thumbs_down"


# ---------------------------------------------------------------------------
# Context preview — exercises the heuristic that powers the panel's
# "what was rejected" cell
# ---------------------------------------------------------------------------


def test_context_preview_returns_none_for_empty():
    assert _context_preview(None) is None
    assert _context_preview({}) is None


def test_context_preview_prefers_testo_field():
    """measures-panel sends context.testo with the original AI suggestion."""
    out = _context_preview({"testo": "Installare riparo fisso", "altro": 42})
    assert out == "Installare riparo fisso"


def test_context_preview_falls_back_to_first_string():
    out = _context_preview({"foo": 1, "bar": "Pausa ogni 90 minuti"})
    assert out == "Pausa ogni 90 minuti"


def test_context_preview_truncates_long_text():
    long = "x" * 200
    out = _context_preview({"testo": long})
    assert out is not None
    # 140 + ellipsis
    assert len(out) == 141
    assert out.endswith("…")


@pytest.mark.parametrize(
    "ctx",
    [
        {"testo": "  "},  # whitespace-only — not useful, drop
        {"testo": ""},
        {"counts": 12},  # no string at all
    ],
)
def test_context_preview_skips_useless_payloads(ctx):
    assert _context_preview(ctx) is None
