"""Pydantic schemas for the per-azienda description revision history (US-2.1).

Mirrors :class:`app.models.description_revision.DescriptionRevision` for the
``GET /aziende/{id}/description-revisions`` and restore endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DescriptionRevisionResponse(BaseModel):
    id: uuid.UUID
    azienda_id: uuid.UUID
    # 'ai' | 'manual' — application-level enum, see
    # ``app.models.description_revision.ALLOWED_SOURCES``.
    source: str
    content: str
    generated_by: uuid.UUID | None = None
    generated_by_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DescriptionRevisionRestoreResponse(BaseModel):
    """Returned by ``POST /description-revisions/{rev_id}/restore``.

    Carries the new revision row (because restoring snapshots a fresh
    ``manual`` revision rather than overwriting in place) plus the new
    ``descrizione_attivita`` value the frontend should reflect locally.
    """

    descrizione_attivita: str
    revision: DescriptionRevisionResponse


class VisuraUploadResponse(BaseModel):
    """Returned by ``POST /aziende/{id}/visura``.

    The frontend uses ``extracted_chars`` to decide whether to surface a
    "estratto N caratteri dalla visura" hint above the description editor.
    The full extracted text is *not* sent back — the operator can re-upload
    if they want to inspect it; the file is stored server-side.
    """

    visura_uploaded_at: datetime
    extracted_chars: int = Field(ge=0)
    pages: int = Field(ge=0)
