import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentGenerateRequest(BaseModel):
    tipo_documento: str
    # US-4.4: optional per-generation config. For haccp_forms this carries
    # {"selected_codes": ["SA-01", "SA-03", ...]} so the dialog-driven
    # subset selection survives the async hop into the Celery worker.
    options: dict[str, Any] | None = None


class DocumentBatchRequest(BaseModel):
    tipi_documento: list[str]


class DocumentResponse(BaseModel):
    id: uuid.UUID
    azienda_id: uuid.UUID
    tipo_documento: str
    versione: int
    status: str
    file_path: str | None = None
    gdrive_file_id: str | None = None
    # Google Doc (editable) file ID + derived edit URL. Populated when the
    # user has opened this document for in-browser editing via Google Docs.
    gdoc_file_id: str | None = None
    gdoc_edit_url: str | None = None
    # User-facing error line shown next to "bozza" status (US-2.8 AC3).
    # None on success, and non-None on any failed-and-rolled-back record.
    error_message: str | None = None
    created_at: datetime
    # US-2.9: human-readable name of the user who triggered generation.
    # Resolved via a join on users.full_name in the list/detail endpoints.
    generated_by_name: str | None = None
    # US-5.2 AC2 — true when the survey changed between this document's
    # generation start and completion (or after completion via PUT
    # propagation). Frontend renders an amber "rigenera" banner.
    stale_snapshot: bool = False

    model_config = {"from_attributes": True}


class DocumentEditLinkResponse(BaseModel):
    gdoc_file_id: str
    edit_url: str


class DocumentSnapshotResponse(BaseModel):
    """Structured text snapshot of a generated .docx.

    Returned by the snapshot endpoint (US-2.9) and consumed by the
    frontend diff viewer. The .docx is parsed on demand — we do NOT
    persist snapshots, so regenerating the file upstream will change
    future snapshot output.
    """

    id: uuid.UUID
    versione: int
    generated_at: datetime | None = None
    generated_by_name: str | None = None
    paragraphs: list[str]
    # Tables are flattened to a nested list of cell texts.
    tables: list[list[list[str]]]
