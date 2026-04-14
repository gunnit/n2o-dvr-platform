"""OpenAI client helpers for the N2O DVR platform.

Uses the Responses API (client.responses.create) for file inputs and
the Chat Completions parse helper (client.chat.completions.parse) for
schema-guaranteed structured outputs via Pydantic models.

Privacy contract (CLAUDE.md):
  - NEVER send codice fiscale, ID documents, or personal health data.
  - Caller is responsible for stripping private fields before calling.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import TypeVar

from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import AIError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Return a module-level singleton async OpenAI client.

    Raises AIError if OPENAI_API_KEY is not configured.
    """
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise AIError("OPENAI_API_KEY is not configured")
        _client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
        )
    return _client


async def generate_text(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    max_output_tokens: int | None = None,
) -> str:
    """Simple text generation via the Responses API.

    Use for short Italian boilerplate (company descriptions, etc.).
    Defaults to OPENAI_MODEL_GENERATION (gpt-5-nano).
    """
    client = get_client()
    input_messages: list[dict] = []
    if system:
        input_messages.append({"role": "system", "content": system})
    input_messages.append({"role": "user", "content": prompt})

    try:
        response = await client.responses.create(
            model=model or settings.OPENAI_MODEL_GENERATION,
            input=input_messages,
            max_output_tokens=max_output_tokens,
        )
    except OpenAIError as exc:
        logger.exception("OpenAI generate_text failed")
        raise AIError(f"AI generation failed: {exc}") from exc

    return response.output_text


async def generate_structured(
    prompt: str,
    *,
    schema: type[T],
    system: str | None = None,
    model: str | None = None,
) -> T:
    """Schema-guaranteed structured output via chat.completions.parse().

    The returned value is a fully-validated Pydantic instance of `schema`.
    Raises AIError on refusal or API failure.
    """
    client = get_client()
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        completion = await client.chat.completions.parse(
            model=model or settings.OPENAI_MODEL_MEASURES,
            messages=messages,
            response_format=schema,
        )
    except OpenAIError as exc:
        logger.exception("OpenAI generate_structured failed")
        raise AIError(f"AI structured generation failed: {exc}") from exc

    message = completion.choices[0].message
    if message.refusal:
        raise AIError(f"Model refused: {message.refusal}")
    if message.parsed is None:
        raise AIError("Model returned no parsed content")
    return message.parsed


async def extract_from_pdf(
    pdf_path: str | Path,
    *,
    schema: type[T],
    instructions: str,
    model: str | None = None,
) -> T:
    """Extract structured data from a PDF via the Responses API.

    The PDF is sent as a base64 input_file alongside the instructions.
    The response is constrained to `schema` via json_schema response_format.

    Defaults to OPENAI_MODEL_EXTRACTION (gpt-5.4-mini) — vision-capable.
    """
    client = get_client()
    path = Path(pdf_path)
    if not path.is_file():
        raise AIError(f"PDF not found: {pdf_path}")

    pdf_bytes = path.read_bytes()
    if len(pdf_bytes) > 10 * 1024 * 1024:
        raise AIError("PDF exceeds 10 MB limit")

    b64 = base64.b64encode(pdf_bytes).decode("ascii")

    try:
        response = await client.responses.parse(
            model=model or settings.OPENAI_MODEL_EXTRACTION,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": path.name,
                            "file_data": f"data:application/pdf;base64,{b64}",
                        },
                        {"type": "input_text", "text": instructions},
                    ],
                }
            ],
            text_format=schema,
        )
    except OpenAIError as exc:
        logger.exception("OpenAI extract_from_pdf failed for %s", path.name)
        raise AIError(f"PDF extraction failed: {exc}") from exc

    parsed = response.output_parsed
    if parsed is None:
        raise AIError("AI returned no parsed content (refusal or empty)")
    return parsed
