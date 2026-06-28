"""Schemas for organization branding / letterhead (per-org)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class OrganizationBrandingResponse(BaseModel):
    """Branding as read by the admin UI, app chrome, and document generation."""

    id: uuid.UUID
    name: str
    has_logo: bool = False
    indirizzo: str | None = None
    cap: str | None = None
    citta: str | None = None
    provincia: str | None = None
    partita_iva: str | None = None
    codice_fiscale: str | None = None
    telefono: str | None = None
    email: str | None = None
    sito_web: str | None = None
    rspp_nome: str | None = None

    model_config = {"from_attributes": True}


class OrganizationBrandingUpdate(BaseModel):
    """Admin-editable letterhead fields. All optional; only provided keys are
    applied (PATCH-style merge). ``name`` is the firm name on the letterhead.

    Empty strings are treated as "clear this field" by the endpoint, so the
    admin can blank a value back out."""

    name: str | None = Field(default=None, max_length=255)
    indirizzo: str | None = Field(default=None, max_length=255)
    cap: str | None = Field(default=None, max_length=16)
    citta: str | None = Field(default=None, max_length=255)
    provincia: str | None = Field(default=None, max_length=8)
    partita_iva: str | None = Field(default=None, max_length=32)
    codice_fiscale: str | None = Field(default=None, max_length=32)
    telefono: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)
    sito_web: str | None = Field(default=None, max_length=255)
    rspp_nome: str | None = Field(default=None, max_length=255)
