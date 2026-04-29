"""OpenAI client helpers for the N2O DVR platform.

All helpers go through the Responses API (`client.responses.create` /
`client.responses.parse`) — OpenAI's recommended surface for gpt-5.x
reasoning models. Schema-guaranteed structured outputs use
`text_format=<PydanticModel>` (the Responses-API equivalent of
`response_format` from Chat Completions).

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


def _normalize_effort(model_name: str, effort: str) -> str:
    """Map reasoning-effort values across gpt-5.x generations.

    Supported `reasoning.effort` values vary by model. As of April 2026:
      - gpt-5, gpt-5.4-mini: `minimal | low | medium | high`
      - gpt-5.4-nano, gpt-5.5: `none | low | medium | high | xhigh`
        (the lowest level is named `none`, and `minimal` is rejected with
        a 400 invalid_request_error)

    Callers pass the `minimal` vocabulary by default and we translate at
    call time so env-driven model bumps don't break.
    """
    uses_none_vocab = (
        model_name.startswith("gpt-5.5") or "nano" in model_name
    )
    if effort == "minimal" and uses_none_vocab:
        return "none"
    if effort == "none" and not uses_none_vocab:
        return "minimal"
    return effort


async def generate_text(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    max_output_tokens: int | None = None,
    reasoning_effort: str = "minimal",
) -> str:
    """Simple text generation via the Responses API.

    Use for short Italian boilerplate (company descriptions, etc.).
    Defaults to OPENAI_MODEL_GENERATION (gpt-5.4-nano).

    `gpt-5*` models are reasoning models: `max_output_tokens` caps the sum of
    reasoning AND visible output, so we pin effort to "minimal" for plain
    boilerplate — otherwise reasoning silently eats the whole budget and
    `output_text` comes back empty. The effort value is auto-translated for
    gpt-5.5 (which uses `none` for the same level).
    """
    client = get_client()
    resolved_model = model or settings.OPENAI_MODEL_GENERATION
    effort = _normalize_effort(resolved_model, reasoning_effort)
    input_messages: list[dict] = []
    if system:
        input_messages.append({"role": "system", "content": system})
    input_messages.append({"role": "user", "content": prompt})

    try:
        response = await client.responses.create(
            model=resolved_model,
            input=input_messages,
            max_output_tokens=max_output_tokens,
            reasoning={"effort": effort},
        )
    except OpenAIError as exc:
        logger.exception("OpenAI generate_text failed")
        raise AIError(f"AI generation failed: {exc}") from exc

    text = response.output_text or ""
    status = getattr(response, "status", None)
    incomplete = getattr(response, "incomplete_details", None)
    if status == "incomplete" or not text.strip():
        reason = getattr(incomplete, "reason", None) if incomplete else None
        logger.error(
            "generate_text returned no usable text (status=%s, reason=%s, len=%d)",
            status,
            reason,
            len(text),
        )
        raise AIError(
            "L'AI ha terminato senza produrre testo"
            + (f" (motivo: {reason})" if reason else "")
            + ". Riprova o aumenta il budget di token."
        )
    return text


async def generate_structured(
    prompt: str,
    *,
    schema: type[T],
    system: str | None = None,
    model: str | None = None,
    reasoning_effort: str = "low",
) -> T:
    """Schema-guaranteed structured output via the Responses API.

    Uses `client.responses.parse(text_format=schema, ...)` — the surface
    OpenAI recommends for gpt-5.x reasoning models. Returns a fully-validated
    Pydantic instance of `schema`. Raises AIError on refusal or API failure.

    `reasoning_effort` defaults to "low" — most domain-reasoning workloads
    in this app (single-risk measure suggestions, equipment lists) don't
    need deep chain-of-thought. Pass "medium" for multi-axis evaluations
    (e.g. the 11-category rischi suggester).
    """
    client = get_client()
    resolved_model = model or settings.OPENAI_MODEL_MEASURES
    effort = _normalize_effort(resolved_model, reasoning_effort)
    input_messages: list[dict] = []
    if system:
        input_messages.append({"role": "system", "content": system})
    input_messages.append({"role": "user", "content": prompt})

    try:
        response = await client.responses.parse(
            model=resolved_model,
            input=input_messages,
            text_format=schema,
            reasoning={"effort": effort},
        )
    except OpenAIError as exc:
        logger.exception("OpenAI generate_structured failed")
        raise AIError(f"AI structured generation failed: {exc}") from exc

    parsed = response.output_parsed
    if parsed is None:
        raise AIError("AI returned no parsed content (refusal or empty)")
    return parsed


async def extract_from_pdf(
    pdf_path: str | Path,
    *,
    schema: type[T],
    instructions: str,
    model: str | None = None,
    reasoning_effort: str = "medium",
) -> T:
    """Extract structured data from a PDF via the Responses API.

    The PDF is sent as a base64 input_file alongside the instructions.
    The response is constrained to `schema` via Pydantic `text_format`.

    Defaults to OPENAI_MODEL_EXTRACTION (gpt-5.5) — flagship vision model
    with 1M context, used for SDS extraction where chemical accuracy matters.
    `reasoning_effort` defaults to "medium" because SDS layouts vary widely
    and pictogram/H-phrase recall benefits from a real reasoning pass; bump
    to "high" for known-hard documents, drop to "low" for batch reruns.
    """
    client = get_client()
    path = Path(pdf_path)
    if not path.is_file():
        raise AIError(f"PDF not found: {pdf_path}")

    pdf_bytes = path.read_bytes()
    if len(pdf_bytes) > 10 * 1024 * 1024:
        raise AIError("PDF exceeds 10 MB limit")

    b64 = base64.b64encode(pdf_bytes).decode("ascii")
    resolved_model = model or settings.OPENAI_MODEL_EXTRACTION
    effort = _normalize_effort(resolved_model, reasoning_effort)

    try:
        response = await client.responses.parse(
            model=resolved_model,
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
            reasoning={"effort": effort},
        )
    except OpenAIError as exc:
        logger.exception("OpenAI extract_from_pdf failed for %s", path.name)
        raise AIError(f"PDF extraction failed: {exc}") from exc

    parsed = response.output_parsed
    if parsed is None:
        raise AIError("AI returned no parsed content (refusal or empty)")
    return parsed


# Image extension → MIME type for the input_image data URL. HEIC isn't
# supported as input_image by OpenAI; callers should resolve it server-side
# (or skip those photos) before calling this helper.
_IMAGE_EXT_TO_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


async def extract_from_images(
    image_paths: list[str | Path],
    *,
    schema: type[T],
    instructions: str,
    system: str | None = None,
    model: str | None = None,
    reasoning_effort: str = "low",
) -> T:
    """Extract structured data from one or more images via the Responses API.

    Sends each image as a base64 `input_image` data URL alongside the
    instructions. The response is constrained to `schema` via Pydantic.

    Defaults to OPENAI_MODEL_EXTRACTION (gpt-5.5) at `low` reasoning effort —
    object identification in clear photos doesn't need deep chain-of-thought,
    and `low` keeps latency under ~10s for typical 3-photo batches.

    Raises AIError on missing files, unsupported extensions, refusals, or
    empty parses.
    """
    client = get_client()
    if not image_paths:
        raise AIError("At least one image is required")

    content: list[dict] = []
    for raw in image_paths:
        path = Path(raw)
        if not path.is_file():
            raise AIError(f"Image not found: {path}")
        ext = path.suffix.lower()
        mime = _IMAGE_EXT_TO_MIME.get(ext)
        if not mime:
            raise AIError(f"Unsupported image format: {ext}")
        img_bytes = path.read_bytes()
        if len(img_bytes) > 20 * 1024 * 1024:
            raise AIError(f"Image exceeds 20 MB limit: {path.name}")
        b64 = base64.b64encode(img_bytes).decode("ascii")
        content.append(
            {
                "type": "input_image",
                "image_url": f"data:{mime};base64,{b64}",
            }
        )
    content.append({"type": "input_text", "text": instructions})

    input_messages: list[dict] = []
    if system:
        input_messages.append({"role": "system", "content": system})
    input_messages.append({"role": "user", "content": content})

    resolved_model = model or settings.OPENAI_MODEL_EXTRACTION
    effort = _normalize_effort(resolved_model, reasoning_effort)
    try:
        response = await client.responses.parse(
            model=resolved_model,
            input=input_messages,
            text_format=schema,
            reasoning={"effort": effort},
        )
    except OpenAIError as exc:
        logger.exception(
            "OpenAI extract_from_images failed (%d images)", len(image_paths)
        )
        raise AIError(f"Image extraction failed: {exc}") from exc

    parsed = response.output_parsed
    if parsed is None:
        raise AIError("AI returned no parsed content (refusal or empty)")
    return parsed
