"""OpenAI provider failures must stay operationally useful without leaking billing text."""

from __future__ import annotations

import logging

import httpx
import pytest
from openai import RateLimitError

from app.core.exceptions import AIError
from app.services.ai import client as ai_client


class _FailingResponses:
    def __init__(self, error: RateLimitError) -> None:
        self.error = error

    async def create(self, **_kwargs):
        raise self.error


class _FailingClient:
    def __init__(self, error: RateLimitError) -> None:
        self.responses = _FailingResponses(error)


def _rate_limit_error(*, code: str, error_type: str, message: str) -> RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(429, request=request)
    return RateLimitError(
        message,
        response=response,
        body={
            "error": {
                "message": message,
                "type": error_type,
                "code": code,
            }
        },
    )


@pytest.mark.asyncio
async def test_provider_balance_exhaustion_is_sanitized_without_customer_billing_claim(
    monkeypatch,
    caplog,
):
    raw = "You have no credits remaining. See https://provider.example/billing."
    error = _rate_limit_error(
        code="credit_balance_exhausted",
        error_type="insufficient_quota",
        message=raw,
    )
    monkeypatch.setattr(ai_client, "get_client", lambda: _FailingClient(error))

    with caplog.at_level(logging.ERROR, logger=ai_client.__name__):
        with pytest.raises(AIError) as excinfo:
            await ai_client.generate_text("safe synthetic prompt")

    detail = excinfo.value.detail
    assert "temporaneamente non disponibile" in detail
    assert "credit" not in detail.casefold()
    assert raw not in detail
    assert "provider.example" not in detail
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__ is True

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "provider=openai" in logged
    assert "operation=generate_text" in logged
    assert "provider_code=credit_balance_exhausted" in logged
    assert raw not in logged
    assert "provider.example" not in logged


@pytest.mark.asyncio
async def test_transient_rate_limit_stays_distinguishable_without_raw_provider_text(
    monkeypatch,
    caplog,
):
    raw = "Raw transient provider message that must not reach the customer"
    error = _rate_limit_error(
        code="rate_limit_exceeded",
        error_type="rate_limit_error",
        message=raw,
    )
    monkeypatch.setattr(ai_client, "get_client", lambda: _FailingClient(error))

    with caplog.at_level(logging.ERROR, logger=ai_client.__name__):
        with pytest.raises(AIError) as excinfo:
            await ai_client.generate_text("safe synthetic prompt")

    assert "temporaneamente sovraccarico" in excinfo.value.detail
    assert raw not in excinfo.value.detail
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "provider_code=rate_limit_exceeded" in logged
    assert "provider_type=rate_limit_error" in logged
    assert raw not in logged
