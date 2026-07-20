import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

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
    # True when this row was produced by syncing edits back from Google Docs.
    # Derived server-side from options.edited_in_gdocs so the frontend can
    # surface a "Modificato in Google Docs" badge on the version history row
    # without re-parsing the options JSON.
    edited_in_gdocs: bool = False
    # True when this row was minted by folding inline preview overrides into
    # a new version (POST /documenti/{id}/save-edited-version). Derived
    # server-side from options.edited_inline so the frontend can surface a
    # "Modificato" badge without re-parsing the options JSON.
    edited_inline: bool = False
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


# ---------------------------------------------------------------------------
# In-browser preview + inline editing (documenti/{id}/preview & /overrides)
#
# The block model mirrors services/document_preview.parse_docx_to_blocks
# 1:1 — the frontend renders these shapes directly, and every `addr` is a
# stable address the PATCH /overrides endpoint accepts back. Keep the two
# in lock-step: a field added here must be emitted by the parser.
# ---------------------------------------------------------------------------


class DocumentPreviewRun(BaseModel):
    """One formatted text run inside a paragraph."""

    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    # "RRGGBB" when the run sets an explicit color; None when inherited.
    color: str | None = None
    # Font size in points; None when inherited from the style.
    size: float | None = None


class DocumentPreviewImage(BaseModel):
    """Inline image reference — fetched via /preview/images/{image_id}."""

    image_id: str
    width_px: int | None = None
    height_px: int | None = None


class DocumentPreviewCellParagraph(BaseModel):
    """Paragraph inside a table cell — addr is "table:row:cell:para"."""

    addr: str
    style: str | None = None
    # 1-4 when the style is "Heading N" / "Titolo N", else None.
    heading_level: int | None = None
    alignment: Literal["left", "center", "right", "justify"] | None = None
    # False when the paragraph carries drawings or field machinery (TOC) —
    # the apply side skips overrides on locked paragraphs too.
    editable: bool
    runs: list[DocumentPreviewRun]
    images: list[DocumentPreviewImage] = Field(default_factory=list)


class DocumentPreviewParagraphBlock(DocumentPreviewCellParagraph):
    """Top-level paragraph block — addr is the body index, e.g. "12"."""

    kind: Literal["paragraph"] = "paragraph"
    page_break_before: bool = False


class DocumentPreviewCell(BaseModel):
    addr: str
    paragraphs: list[DocumentPreviewCellParagraph]
    # tcPr/shd @fill as "RRGGBB"; None when "auto" or absent.
    shading: str | None = None
    # gridSpan — horizontal merge width, 1 when unmerged.
    col_span: int = 1
    v_merge: Literal["restart", "continue"] | None = None


class DocumentPreviewTableBlock(BaseModel):
    kind: Literal["table"] = "table"
    addr: str
    rows: list[list[DocumentPreviewCell]]


DocumentPreviewBlock = Annotated[
    DocumentPreviewParagraphBlock | DocumentPreviewTableBlock,
    Field(discriminator="kind"),
]


class DocumentPreviewResponse(BaseModel):
    """Full preview payload: document metadata + block model + saved overrides."""

    id: uuid.UUID
    azienda_id: uuid.UUID
    azienda_nome: str
    tipo_documento: str
    versione: int
    file_name: str | None = None
    stale_snapshot: bool = False
    # generation_completed_at as ISO string; None on legacy rows.
    generated_at: str | None = None
    blocks: list[DocumentPreviewBlock]
    # Currently saved overrides keyed by block address ({} when none).
    overrides: dict[str, str] = Field(default_factory=dict)


class OverridesPatchRequest(BaseModel):
    """Merge-patch for content overrides: null value deletes that address.

    Size limits guard the API and the JSONB column: at most 500 addresses
    per request and 20k chars per value (a paragraph is a few hundred chars
    in practice). The endpoint additionally caps the MERGED map at ~2MB
    serialized so repeated PATCHes can't bloat the row unboundedly.
    """

    set: Annotated[
        dict[str, Annotated[str, Field(max_length=20000)] | None],
        Field(max_length=500),
    ]


class OverridesResponse(BaseModel):
    """Full override map after a PATCH — the frontend replaces its copy."""

    overrides: dict[str, str]
