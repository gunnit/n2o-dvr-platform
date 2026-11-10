import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, SerializerFunctionWrapHandler, model_serializer


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
# The block model mirrors services/document_preview.parse_docx_preview 1:1
# (parse_docx_to_blocks is its frozen legacy subset) — the frontend renders
# these shapes directly, and every `addr` is a stable address the PATCH
# /overrides endpoint accepts back. Keep the two in lock-step: a field added
# here must be emitted by the parser.
#
# Fields marked "layout redesign" are the spec 2026-11-10 §4.3.1 additions.
# All are optional with a default, so an old client ignores them and an old
# payload (or an old document) still validates.
# ---------------------------------------------------------------------------

PreviewAlignment = Literal["left", "center", "right", "justify"]


class DocumentPreviewStyleProps(BaseModel):
    """Paragraph look in points and "RRGGBB" (layout redesign).

    Serialized with only the fields it holds. In ``style_props`` that is all
    of them, *resolved*: the style, then its ``basedOn`` chain, then
    ``docDefaults``; ``bold``/``italic``/``caps`` are then always true or
    false, and any other value nothing in the chain sets is null. As a
    paragraph's ``direct`` it holds only what the paragraph sets itself (a
    missing key: not set; null: set to "auto" colour or body-text level).
    There ``font_size_pt``, ``bold``, ``italic``, ``caps`` and ``color`` come
    from the paragraph mark's run properties, which give an empty paragraph
    its height.
    """

    font_size_pt: float | None = None
    bold: bool | None = None
    italic: bool | None = None
    caps: bool | None = None
    # "RRGGBB"; None for "auto" or not set.
    color: str | None = None
    alignment: PreviewAlignment | None = None
    space_before_pt: float | None = None
    space_after_pt: float | None = None
    indent_left_pt: float | None = None
    # 1-9 (w:outlineLvl + 1); None for body text.
    outline_level: int | None = None

    @model_serializer(mode="wrap")
    def _held_fields_only(self, handler: SerializerFunctionWrapHandler) -> dict:
        # A paragraph's direct formatting is a handful of keys; spelling out
        # the other nulls on every paragraph of a DVR costs ~10% of the payload.
        data = handler(self)
        return {key: value for key, value in data.items() if key in self.model_fields_set}


class DocumentPreviewList(BaseModel):
    """List membership from numPr and numbering.xml (layout redesign)."""

    # w:ilvl, 0-based.
    level: int
    # A bullet's glyph as drawn ("•", "▪" — symbol-font code points mapped);
    # for numbered formats the lvlText pattern, e.g. "%1.".
    glyph: str


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
    # Layout redesign: the run itself sets capitals (w:caps).
    caps: bool = False


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
    alignment: PreviewAlignment | None = None
    # False when the paragraph carries drawings or field machinery (TOC) —
    # the apply side skips overrides on locked paragraphs too.
    editable: bool
    runs: list[DocumentPreviewRun]
    # Pictures drawn in the text. A full-page art picture is not one: it is
    # the paragraph's background_image_id.
    images: list[DocumentPreviewImage] = Field(default_factory=list)
    # Layout redesign — effective outline level 1-9 (direct, else the
    # style's), for the sidebar index; None for body text.
    outline_level: int | None = None
    # Layout redesign — the paragraph's own formatting; None when it has none.
    direct: DocumentPreviewStyleProps | None = None
    # Layout redesign — the art page this paragraph opens (wp:docPr named
    # "vera-art:<role>:<key>"), and that page's background picture: a
    # main-part rId for /preview/images/{image_id}.
    page_role: Literal["cover", "divider", "back_cover"] | None = None
    background_image_id: str | None = None
    # Layout redesign — the paragraph ends a section (pPr carries w:sectPr):
    # what follows starts on a new sheet.
    section_break_after: bool = False
    # Layout redesign — kept last: a field named "list" shadows the builtin
    # for any annotation after it in this class body.
    list: DocumentPreviewList | None = None


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
    # Layout redesign — tcPr/vAlign ("both" is drawn centred); None when unset.
    v_align: Literal["top", "center", "bottom"] | None = None


class DocumentPreviewTableBlock(BaseModel):
    kind: Literal["table"] = "table"
    addr: str
    rows: list[list[DocumentPreviewCell]]
    # Layout redesign — tblGrid column widths as percentages of the table
    # (they sum to ~100); None without a grid.
    col_widths_pct: list[float] | None = None


DocumentPreviewBlock = Annotated[
    DocumentPreviewParagraphBlock | DocumentPreviewTableBlock,
    Field(discriminator="kind"),
]


class DocumentPreviewFurniture(BaseModel):
    """Running header and footer of the body's final section (layout redesign).

    The header's first paragraph with text, split at its first tab (title |
    client); the footer's text before its right tab without field results
    (the revision line); the footer's first inline picture as a part-scoped
    image id, "ftr:<part>:<rId>", for /preview/images/{image_id}.
    """

    header_left: str | None = None
    header_right: str | None = None
    footer_text: str | None = None
    footer_logo_image_id: str | None = None


class DocumentPreviewPageSetup(BaseModel):
    """Page size and margins of the body's final section, in points (layout
    redesign). Donor-template documents keep their own geometry."""

    width_pt: float | None = None
    height_pt: float | None = None
    margin_top_pt: float | None = None
    margin_bottom_pt: float | None = None
    margin_left_pt: float | None = None
    margin_right_pt: float | None = None


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
    # Layout redesign — None when the final section has no header or footer.
    furniture: DocumentPreviewFurniture | None = None
    page_setup: DocumentPreviewPageSetup | None = None
    # Layout redesign — each paragraph style the blocks use, keyed by the
    # name in their "style" field, resolved (see DocumentPreviewStyleProps).
    style_props: dict[str, DocumentPreviewStyleProps] = Field(default_factory=dict)


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
