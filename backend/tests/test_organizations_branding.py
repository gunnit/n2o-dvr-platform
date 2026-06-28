"""Contract tests for the organization branding endpoints.

No live DB (mirrors test_ai_feedback_admin.py): we guard that the routes the
admin branding page + app chrome hit stay registered, and that the
read/update schemas keep the shape the UI renders against.
"""

from __future__ import annotations

from app.schemas.organization import (
    OrganizationBrandingResponse,
    OrganizationBrandingUpdate,
)


def test_branding_routes_registered():
    from app.api.v1.router import api_router

    paths = {
        (method, getattr(r, "path", ""))
        for r in api_router.routes
        for method in getattr(r, "methods", set()) or set()
    }
    assert ("GET", "/api/v1/organizations/me/branding") in paths
    assert ("PUT", "/api/v1/organizations/me/branding") in paths
    assert ("POST", "/api/v1/organizations/me/branding/logo") in paths
    assert ("GET", "/api/v1/organizations/me/branding/logo") in paths
    assert ("DELETE", "/api/v1/organizations/me/branding/logo") in paths


def test_response_schema_shape():
    import uuid

    resp = OrganizationBrandingResponse(
        id=uuid.uuid4(),
        name="Acme Safety SRL",
        has_logo=True,
        partita_iva="01234567890",
    )
    dumped = resp.model_dump()
    assert dumped["name"] == "Acme Safety SRL"
    assert dumped["has_logo"] is True
    assert dumped["partita_iva"] == "01234567890"
    # Unset optional fields default to None, not missing.
    assert dumped["rspp_nome"] is None


def test_update_schema_tracks_only_provided_fields():
    body = OrganizationBrandingUpdate(name="New Firm", telefono="02 1234567")
    provided = body.model_dump(exclude_unset=True)
    assert provided == {"name": "New Firm", "telefono": "02 1234567"}


def test_update_schema_enforces_length_caps():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        OrganizationBrandingUpdate(cap="X" * 17)  # exceeds max_length=16
