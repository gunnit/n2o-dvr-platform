"""Unit tests for US-1.6 — client countersignature persistence.

Pins three things that downstream code (frontend wizard, audit log, DVR
regeneration) all rely on:

  * ``_decode_signature_data_url`` accepts legitimate canvas PNGs and
    rejects anything that would corrupt storage.
  * The schema contract for ``SurveySignRequest`` / ``SurveySignResponse``
    matches what the frontend sends/consumes.
  * The three new routes (``/sign``, ``/signature``, ``/revision``) are
    registered under ``/api/v1/aziende/{id}/survey``.
  * The ``Azienda`` ORM exposes ``firma_png`` / ``firma_signed_at`` /
    ``firma_signed_by_name`` with the right types — the migration and the
    model must not drift apart.
"""

from __future__ import annotations

import base64

import pytest
from pydantic import ValidationError

from app.api.v1.survey import (
    SURVEY_STATUS_FIRMATO,
    SURVEY_STATUS_REVISIONE,
    _decode_signature_data_url,
)
from app.core.exceptions import BadRequestError
from app.schemas.survey import (
    SurveyRevisionResponse,
    SurveySignRequest,
    SurveySignResponse,
)


# 1x1 transparent PNG — the smallest valid payload we can exercise the
# happy path with without cooking up canvas output at test time.
_MINIMAL_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a"  # PNG signature
    "0000000d49484452000000010000000108060000001f15c4890000000a"
    "49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
)
_MINIMAL_PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    _MINIMAL_PNG_BYTES
).decode()


# ---------------------------------------------------------------------------
# Data URL decoder
# ---------------------------------------------------------------------------


def test_decode_accepts_minimal_canvas_png():
    raw = _decode_signature_data_url(_MINIMAL_PNG_DATA_URL)
    assert raw == _MINIMAL_PNG_BYTES
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")


def test_decode_rejects_empty_payload():
    with pytest.raises(BadRequestError):
        _decode_signature_data_url("")


def test_decode_rejects_unsupported_mime():
    # The canvas only emits image/png; anything else (jpeg, webp, svg)
    # would have come from a hand-crafted request.
    with pytest.raises(BadRequestError):
        _decode_signature_data_url("data:image/jpeg;base64,AAAA")


def test_decode_rejects_non_png_bytes_behind_png_prefix():
    # Attacker could claim image/png but paste arbitrary bytes. Magic-byte
    # check catches it and protects anyone that later assumes PNG-ness
    # (e.g. embedding into a .docx).
    fake = base64.b64encode(b"not-a-real-png").decode()
    with pytest.raises(BadRequestError):
        _decode_signature_data_url(f"data:image/png;base64,{fake}")


def test_decode_rejects_corrupt_base64():
    with pytest.raises(BadRequestError):
        _decode_signature_data_url("data:image/png;base64,!!!!not-base64!!!!")


def test_decode_rejects_oversize_payload():
    # One byte past the 1 MB cap.
    huge = b"\x89PNG\r\n\x1a\n" + b"A" * 1_000_001
    data_url = "data:image/png;base64," + base64.b64encode(huge).decode()
    with pytest.raises(BadRequestError):
        _decode_signature_data_url(data_url)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


def test_sign_request_defaults_signed_by_name_to_none():
    body = SurveySignRequest(signature_data_url=_MINIMAL_PNG_DATA_URL)
    assert body.signed_by_name is None


def test_sign_request_preserves_signed_by_name():
    body = SurveySignRequest(
        signature_data_url=_MINIMAL_PNG_DATA_URL,
        signed_by_name="Luca Marchetti",
    )
    assert body.signed_by_name == "Luca Marchetti"


def test_sign_request_requires_signature_field():
    with pytest.raises(ValidationError):
        SurveySignRequest()  # type: ignore[call-arg]


def test_sign_response_carries_server_timestamp_and_firmato_status():
    from datetime import datetime, timezone

    resp = SurveySignResponse(
        message="ok",
        survey_status=SURVEY_STATUS_FIRMATO,
        firma_signed_at=datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc),
        firma_signed_by_name=None,
    )
    # Frontend relies on this field name to render the "Data e ora firma"
    # row — renaming would break step-riepilogo.tsx.
    assert "firma_signed_at" in resp.model_dump()
    assert resp.survey_status == "firmato"


def test_revision_response_shape():
    resp = SurveyRevisionResponse(
        message="Revisione aperta",
        survey_status=SURVEY_STATUS_REVISIONE,
    )
    assert resp.survey_status == "in_revisione"


# ---------------------------------------------------------------------------
# Route + ORM contract
# ---------------------------------------------------------------------------


def test_router_registers_sign_signature_and_revision_routes():
    """Fail loudly if any of the three US-1.6 endpoints ever gets unwired."""
    from app.api.v1.router import api_router

    paths = {
        (method, getattr(r, "path", ""))
        for r in api_router.routes
        for method in getattr(r, "methods", set()) or set()
    }
    base = "/api/v1/aziende/{azienda_id}/survey"
    assert ("POST", f"{base}/sign") in paths, "POST /sign missing"
    assert ("GET", f"{base}/signature") in paths, "GET /signature missing"
    assert ("POST", f"{base}/revision") in paths, "POST /revision missing"


def test_azienda_model_exposes_signature_columns():
    from app.models.azienda import Azienda

    cols = {c.name: c for c in Azienda.__table__.columns}
    assert "firma_png" in cols, "firma_png column missing"
    assert "firma_signed_at" in cols, "firma_signed_at column missing"
    assert "firma_signed_by_name" in cols, "firma_signed_by_name column missing"
    # All three are nullable by design — a pre-signing Azienda must still
    # round-trip through the ORM.
    assert cols["firma_png"].nullable is True
    assert cols["firma_signed_at"].nullable is True
    assert cols["firma_signed_by_name"].nullable is True


def test_survey_status_lifecycle_constants_match_frontend():
    # Changing these strings breaks the wizard's read-only gating — pin
    # them here so any accidental rename flunks CI.
    assert SURVEY_STATUS_FIRMATO == "firmato"
    assert SURVEY_STATUS_REVISIONE == "in_revisione"
