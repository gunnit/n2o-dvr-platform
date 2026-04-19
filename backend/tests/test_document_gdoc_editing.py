"""Unit tests for the Google Docs round-trip editing flow.

Pins the contract that the frontend documents page and DVR editing flow
depend on: the new column on DocumentoGenerato, the new response schema,
the route registrations, the derived edit URL helper in `_doc_to_response`,
and the MVP scope-gate that currently limits the flow to `dvr_master`.

Tests stay unit-level — no live DB — matching test_survey_snapshot.py.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from app.api.v1.documents import _GDOC_EDITABLE_TYPES, _doc_to_response
from app.models.documento_generato import DocumentoGenerato
from app.schemas.document import DocumentEditLinkResponse, DocumentResponse


# ---------------------------------------------------------------------------
# Model column + schema contract
# ---------------------------------------------------------------------------


def test_documento_generato_has_gdoc_file_id_column():
    cols = {c.name: c for c in DocumentoGenerato.__table__.columns}
    assert "gdoc_file_id" in cols, "gdoc_file_id column missing"
    assert cols["gdoc_file_id"].nullable is True


def test_document_response_carries_gdoc_fields():
    payload = {
        "id": uuid.uuid4(),
        "azienda_id": uuid.uuid4(),
        "tipo_documento": "dvr_master",
        "versione": 1,
        "status": "completed",
        "created_at": "2026-04-15T12:00:00+00:00",
        "gdoc_file_id": "1abcDEF",
        "gdoc_edit_url": "https://docs.google.com/document/d/1abcDEF/edit",
    }
    resp = DocumentResponse(**payload)
    assert resp.gdoc_file_id == "1abcDEF"
    assert resp.gdoc_edit_url.endswith("/1abcDEF/edit")


def test_document_response_gdoc_fields_default_none():
    payload = {
        "id": uuid.uuid4(),
        "azienda_id": uuid.uuid4(),
        "tipo_documento": "dvr_master",
        "versione": 1,
        "status": "completed",
        "created_at": "2026-04-15T12:00:00+00:00",
    }
    resp = DocumentResponse(**payload)
    assert resp.gdoc_file_id is None
    assert resp.gdoc_edit_url is None


def test_edit_link_response_shape():
    resp = DocumentEditLinkResponse(
        gdoc_file_id="abc", edit_url="https://docs.google.com/document/d/abc/edit"
    )
    assert resp.gdoc_file_id == "abc"
    assert "docs.google.com" in resp.edit_url


# ---------------------------------------------------------------------------
# _doc_to_response derives the edit URL from gdoc_file_id
# ---------------------------------------------------------------------------


class _FakeDoc:
    """Stand-in for DocumentoGenerato with the attrs `_doc_to_response` reads."""

    def __init__(self, gdoc_file_id=None, options=None):
        self.id = uuid.uuid4()
        self.azienda_id = uuid.uuid4()
        self.tipo_documento = "dvr_master"
        self.versione = 1
        self.status = "completed"
        self.file_path = None
        self.gdrive_file_id = None
        self.gdoc_file_id = gdoc_file_id
        self.options = options
        self.error_message = None
        self.created_at = datetime(2026, 4, 15, 12, 0, 0)
        self.stale_snapshot = False


def test_doc_to_response_builds_edit_url_when_gdoc_file_id_present():
    fake = _FakeDoc(gdoc_file_id="xyz123")
    resp = _doc_to_response(fake, generated_by_name=None)
    assert resp.gdoc_file_id == "xyz123"
    assert resp.gdoc_edit_url == "https://docs.google.com/document/d/xyz123/edit"


def test_doc_to_response_leaves_edit_url_none_when_no_gdoc_id():
    fake = _FakeDoc(gdoc_file_id=None)
    resp = _doc_to_response(fake, generated_by_name=None)
    assert resp.gdoc_file_id is None
    assert resp.gdoc_edit_url is None


def test_doc_to_response_derives_edited_in_gdocs_from_options():
    """Version-history badge reads this flag; it must survive the JSONB round-trip."""
    edited = _FakeDoc(options={"edited_in_gdocs": True})
    assert _doc_to_response(edited, None).edited_in_gdocs is True

    fresh = _FakeDoc(options=None)
    assert _doc_to_response(fresh, None).edited_in_gdocs is False

    unrelated = _FakeDoc(options={"selected_codes": ["SA-01"]})
    assert _doc_to_response(unrelated, None).edited_in_gdocs is False


def test_document_response_edited_in_gdocs_defaults_false():
    """Legacy rows with no options field must deserialize without error."""
    payload = {
        "id": uuid.uuid4(),
        "azienda_id": uuid.uuid4(),
        "tipo_documento": "dvr_master",
        "versione": 1,
        "status": "completed",
        "created_at": "2026-04-15T12:00:00+00:00",
    }
    resp = DocumentResponse(**payload)
    assert resp.edited_in_gdocs is False


# ---------------------------------------------------------------------------
# MVP scope-gate
# ---------------------------------------------------------------------------


def test_only_dvr_master_is_gdoc_editable():
    """Keep the MVP gate tight — expand deliberately once round-trip is proven."""
    assert _GDOC_EDITABLE_TYPES == {"dvr_master"}


# ---------------------------------------------------------------------------
# Route registration — the frontend calls these exact paths
# ---------------------------------------------------------------------------


def test_router_registers_open_and_sync_endpoints():
    from app.api.v1.router import api_router

    paths = {
        (method, getattr(r, "path", ""))
        for r in api_router.routes
        for method in getattr(r, "methods", set()) or set()
    }
    assert ("POST", "/api/v1/documenti/{document_id}/open-for-editing") in paths
    assert ("POST", "/api/v1/documenti/{document_id}/sync-from-gdoc") in paths
    # Discard endpoint — frontend "Scarta modifiche" button.
    assert ("DELETE", "/api/v1/documenti/{document_id}/gdoc") in paths


# ---------------------------------------------------------------------------
# gdrive_service — async helpers exist and degrade gracefully when creds
# are absent (the service is best-effort across the codebase).
# ---------------------------------------------------------------------------


def test_gdrive_helpers_return_none_without_credentials(monkeypatch):
    """With no Google credentials, all three helpers must degrade gracefully.

    This mirrors the existing `upload_generated_document` contract: the
    Celery generation pipeline must never fail because of a missing token.
    """
    from app.services import gdrive_service

    # Force _load_credentials to return None so the helpers short-circuit
    # without needing a real Google token file.
    monkeypatch.setattr(gdrive_service, "_load_credentials", lambda: None)

    async def _run():
        assert await gdrive_service.create_gdoc_from_docx_bytes(b"x", "f.docx", "Co") is None
        assert await gdrive_service.share_anyone_with_link("fake-id") is False
        assert await gdrive_service.export_gdoc_as_docx("fake-id") is None
        # New helpers introduced for dirty-check + self-cleanup
        assert await gdrive_service.get_gdoc_times("fake-id") is None
        assert await gdrive_service.delete_gdoc("fake-id") is False

    asyncio.run(_run())
