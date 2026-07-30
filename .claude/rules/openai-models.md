---
paths:
  - "backend/app/services/**"
  - "backend/app/tasks/**"
  - "backend/app/config.py"
---

# OpenAI SDK contract

Your training data may insist the latest OpenAI model is `gpt-4.1` or `gpt-4o`. It isn't. The frontier is **`gpt-5.5`** (1M context, image input, reasoning). There is **no** `gpt-5.5-mini` — the smaller tiers are `gpt-5.4-mini` and `gpt-5.4-nano`. Never "correct" a `gpt-5.x` string to an older name.

## Model assignments (configurable in `backend/app/config.py`)

| Setting | Model | Used for |
|---|---|---|
| `OPENAI_MODEL_EXTRACTION` | `gpt-5.5` | SDS PDF extraction (vision + structured outputs) — accuracy-critical |
| `OPENAI_MODEL_PREMIUM` | `gpt-5.5` | "Max quality" toggle for hard cases |
| `OPENAI_MODEL_MEASURES` | `gpt-5.4-mini` | Improvement measures, attrezzature suggester (domain reasoning) |
| `OPENAI_MODEL_GENERATION` | `gpt-5.4-nano` | Short Italian boilerplate (company descriptions) |

## Responses API, not Chat Completions

All gpt-5.x models are reasoning models and belong on the Responses API (`client.responses.create` / `.parse`). The helpers in `backend/app/services/ai/client.py` are already there — keep them there.

```python
resp = await client.responses.create(
    model="gpt-5.4-nano",
    input=[{"role": "user", "content": "..."}],   # not messages=
    reasoning={"effort": "none"},
    max_output_tokens=500,                        # not max_tokens=
)
text = resp.output_text

resp = await client.responses.parse(
    model="gpt-5.5",
    input=[...],
    text_format=MySchema,                         # not response_format=
    reasoning={"effort": "medium"},
)
obj: MySchema = resp.output_parsed
```

Image and PDF input uses `{"type": "input_image", ...}` / `{"type": "input_file", ...}` content parts, not the Chat-style `image_url` shape.

## Reasoning effort — the silent budget killer

Valid values differ by model (re-confirmed against the live API 2026-06-08):

- `gpt-5`: `minimal | low | medium | high`
- `gpt-5.4-mini`, `gpt-5.4-nano`, `gpt-5.5`: `none | low | medium | high | xhigh` — **no `minimal`**; passing it returns `400 invalid_request_error`.

`gpt-5.4-mini` (= `OPENAI_MODEL_MEASURES`) used to accept `minimal` and no longer does. Use `"low"` for the lightest practical tier (what `pos_phase_suggester.py` does), or `"none"` for zero reasoning. `client.py` accepts the `minimal` vocabulary at the call site and `_normalize_effort` translates it to `none` for the none-vocab models — keep that translation in sync when adding a model.

Reasoning tokens count against `max_output_tokens` **before** any visible output. With a tight budget and default effort, `output_text` comes back empty. Boilerplate generation: always the lightest tier. SDS extraction: `medium` by default, `high` only for ambiguous documents.

## Privacy

Never send codice fiscale, identity documents or personal health data to any OpenAI endpoint. The caller strips these before calling `ai/client.py` — the client does not sanitize.
