"""`paypal_setup --bind-only` — the reconcile that runs on every deploy.

Two properties carry the safety argument, and both get an explicit test rather
than being left to a reading of the code:

* **it never writes to PayPal** — every request it makes is a GET, so putting it
  on the deploy path cannot create, reprice or activate a commercial object;
* **it always exits 0** — it runs in `preDeployCommand`, so anything it raises
  would abort a production deploy over a reconcile that is advisory.

The scenario it exists for is `test_binds_a_plan_whose_id_is_missing`: the
merchant holds the plan, the `plans` row exists, and only the join between them
is absent. That was production on 2026-07-28, and it made both signup funnels
dead ends.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest

from app.billing.plan_catalogue import PLANS_BY_CODE
from scripts import paypal_setup

PRODUCT_ID = "PROD-59E111111A742631C"


# --- doubles ---------------------------------------------------------------


@dataclass
class _Row:
    """Stands in for a `plans` row — only the two fields `bind` touches."""

    plan_code: str
    paypal_plan_id: str | None = None


class _Resp:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.content = b"{}"
        self.text = "{}"

    def json(self) -> dict:
        return self._payload


class _Session:
    def __init__(self, rows: list[_Row]) -> None:
        self.rows = rows
        self.commits = 0

    async def execute(self, _stmt):
        rows = self.rows

        class _Result:
            @staticmethod
            def scalars():
                return list(rows)

        return _Result()

    async def commit(self) -> None:
        self.commits += 1


@pytest.fixture
def paypal(monkeypatch):
    """Wire a fake PayPal and a fake database, and record every call made."""
    calls: list[tuple[str, str]] = []
    state: dict = {"session": None}

    def _install(
        *,
        rows: list[_Row],
        remote_plans: dict[str, str] | None = None,
        product: str | None = PRODUCT_ID,
        configured: bool = True,
        raises: Exception | None = None,
    ):
        """`remote_plans` maps PayPal plan *name* -> plan id."""
        remote_plans = remote_plans or {}
        by_id = {pid: name for name, pid in remote_plans.items()}

        monkeypatch.setattr(
            paypal_setup.paypal_client, "is_configured", lambda: configured
        )

        async def _request(method: str, path: str, **_kwargs):
            calls.append((method, path))
            if raises is not None:
                raise raises
            if path.startswith("/v1/catalogs/products"):
                products = [{"id": product, "name": paypal_setup.PRODUCT_NAME}] if product else []
                return _Resp(200, {"products": products})
            if path.startswith("/v1/billing/plans?"):
                return _Resp(
                    200,
                    {"plans": [{"id": pid, "name": n} for n, pid in remote_plans.items()]},
                )
            if path.startswith("/v1/billing/plans/"):
                plan_id = path.rsplit("/", 1)[-1]
                if plan_id not in by_id:
                    return _Resp(404)
                return _Resp(200, {"id": plan_id, "name": by_id[plan_id]})
            raise AssertionError(f"unexpected PayPal call: {method} {path}")

        monkeypatch.setattr(paypal_setup.paypal_client, "request", _request)

        session = _Session(rows)
        state["session"] = session

        @asynccontextmanager
        async def _factory():
            yield session

        monkeypatch.setattr(paypal_setup, "async_session_factory", _factory)
        return session

    _install.calls = calls
    _install.state = state
    return _install


def _name(code: str) -> str:
    return paypal_setup.plan_name(PLANS_BY_CODE[code])


def _errors(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]


# --- the safety properties -------------------------------------------------


@pytest.mark.asyncio
async def test_bind_only_ever_reads_from_paypal(paypal):
    """The whole reason this is allowed on the deploy path."""
    paypal(
        rows=[_Row("A_SOLO"), _Row("B_BASE", "P-stale")],
        remote_plans={_name("A_SOLO"): "P-solo", _name("B_BASE"): "P-base"},
    )

    assert await paypal_setup.bind() == 0

    assert paypal.calls, "expected it to talk to PayPal at all"
    assert all(method == "GET" for method, _ in paypal.calls), paypal.calls


@pytest.mark.asyncio
async def test_a_paypal_outage_does_not_fail_the_deploy(paypal, caplog):
    paypal(
        rows=[_Row("A_SOLO")],
        raises=paypal_setup.paypal_client.PayPalError("GET", "/v1/catalogs/products", 401, "nope"),
    )

    with caplog.at_level(logging.INFO):
        assert await paypal_setup.bind() == 0

    assert any("reconcile failed" in m for m in _errors(caplog))


@pytest.mark.asyncio
async def test_unconfigured_paypal_is_a_quiet_no_op(paypal, caplog):
    session = paypal(rows=[_Row("A_SOLO")], configured=False)

    with caplog.at_level(logging.INFO):
        assert await paypal_setup.bind() == 0

    assert not paypal.calls
    assert session.commits == 0
    assert not _errors(caplog)


# --- what it is for --------------------------------------------------------


@pytest.mark.asyncio
async def test_binds_a_plan_whose_id_is_missing(paypal):
    """Production on 2026-07-28: plan at PayPal, row in the table, no join."""
    session = paypal(
        rows=[_Row("A_SOLO"), _Row("B_BASE")],
        remote_plans={_name("A_SOLO"): "P-solo", _name("B_BASE"): "P-base"},
    )

    assert await paypal_setup.bind() == 0

    assert {r.plan_code: r.paypal_plan_id for r in session.rows} == {
        "A_SOLO": "P-solo",
        "B_BASE": "P-base",
    }
    assert session.commits == 1


@pytest.mark.asyncio
async def test_an_id_paypal_still_recognises_is_left_alone(paypal):
    """No write, and no commit — a healthy deploy must be a no-op."""
    session = paypal(
        rows=[_Row("A_SOLO", "P-solo")],
        remote_plans={_name("A_SOLO"): "P-solo"},
    )

    assert await paypal_setup.bind() == 0

    assert session.rows[0].paypal_plan_id == "P-solo"
    assert session.commits == 0


@pytest.mark.asyncio
async def test_an_id_from_the_other_environment_is_re_resolved(paypal, caplog):
    """Sandbox ids in a live database (§4b-bis) — rebind rather than trust."""
    session = paypal(
        rows=[_Row("A_SOLO", "P-sandbox-leftover")],
        remote_plans={_name("A_SOLO"): "P-live"},
    )

    with caplog.at_level(logging.INFO):
        assert await paypal_setup.bind() == 0

    assert session.rows[0].paypal_plan_id == "P-live"
    assert any("is unknown in" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_a_plan_missing_at_paypal_is_reported_not_invented(paypal, caplog):
    """Creating it is a commercial act — say so and leave it to a human."""
    session = paypal(rows=[_Row("A_SOLO")], remote_plans={})

    with caplog.at_level(logging.INFO):
        assert await paypal_setup.bind() == 0

    assert session.rows[0].paypal_plan_id is None
    assert session.commits == 0
    assert any("A_SOLO" in m and "scripts.paypal_setup" in m for m in _errors(caplog))


@pytest.mark.asyncio
async def test_an_unprovisioned_merchant_creates_no_product(paypal, caplog):
    session = paypal(rows=[_Row("A_SOLO")], product=None)

    with caplog.at_level(logging.INFO):
        assert await paypal_setup.bind() == 0

    assert all(method == "GET" for method, _ in paypal.calls), paypal.calls
    assert session.commits == 0
