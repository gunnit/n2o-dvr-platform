"""Unit tests for US-2.1 — visura upload + description revision history.

Pins the contracts the frontend (and the AI prompt builder) rely on so
later refactors can't silently drop a field, rename a route, or break the
PII redaction rule.

These are deliberately *unit* tests (no live DB / HTTP) — they mirror the
style of ``test_survey_signature.py`` and run in milliseconds.
"""

from __future__ import annotations

import io
import uuid

import pytest

from app.models.description_revision import (
    ALLOWED_SOURCES,
    SOURCE_AI,
    SOURCE_MANUAL,
    DescriptionRevision,
)
from app.schemas.description_revision import (
    DescriptionRevisionResponse,
    DescriptionRevisionRestoreResponse,
    VisuraUploadResponse,
)
from app.services.visura_extractor import (
    MAX_SNIPPET_CHARS,
    VisuraExtraction,
    _redact,
    extract_visura_text,
)


# ---------------------------------------------------------------------------
# ORM contract
# ---------------------------------------------------------------------------


def test_description_revision_table_columns():
    cols = {c.name: c for c in DescriptionRevision.__table__.columns}
    assert "id" in cols
    assert "azienda_id" in cols
    assert "source" in cols
    assert "content" in cols
    assert "generated_by" in cols
    assert "created_at" in cols
    # Tenancy + content are NOT NULL — anything else nullable.
    assert cols["azienda_id"].nullable is False
    assert cols["source"].nullable is False
    assert cols["content"].nullable is False
    assert cols["generated_by"].nullable is True


def test_description_revision_source_constants_match_frontend():
    # Frontend `description-history.tsx` switches on these literal values
    # to decide between the AI badge and the manual badge — pin them.
    assert SOURCE_AI == "ai"
    assert SOURCE_MANUAL == "manual"
    assert SOURCE_AI in ALLOWED_SOURCES
    assert SOURCE_MANUAL in ALLOWED_SOURCES


def test_azienda_model_exposes_visura_columns():
    from app.models.azienda import Azienda

    cols = {c.name: c for c in Azienda.__table__.columns}
    assert "visura_pdf_path" in cols, "visura_pdf_path column missing"
    assert "visura_extracted_text" in cols, "visura_extracted_text column missing"
    assert "visura_uploaded_at" in cols, "visura_uploaded_at column missing"
    # All three are nullable — pre-upload aziende must round-trip cleanly.
    assert cols["visura_pdf_path"].nullable is True
    assert cols["visura_extracted_text"].nullable is True
    assert cols["visura_uploaded_at"].nullable is True


# ---------------------------------------------------------------------------
# Schema contracts
# ---------------------------------------------------------------------------


def test_description_revision_response_minimal_payload():
    payload = {
        "id": uuid.uuid4(),
        "azienda_id": uuid.uuid4(),
        "source": SOURCE_AI,
        "content": "Descrizione AI di prova",
        "created_at": "2026-04-15T12:00:00+00:00",
    }
    resp = DescriptionRevisionResponse(**payload)
    # generated_by + generated_by_name default to None for legacy rows
    # where the user has been deleted (FK is ON DELETE SET NULL).
    assert resp.generated_by is None
    assert resp.generated_by_name is None
    assert resp.source == SOURCE_AI


def test_description_revision_restore_response_carries_new_revision():
    rev = DescriptionRevisionResponse(
        id=uuid.uuid4(),
        azienda_id=uuid.uuid4(),
        source=SOURCE_MANUAL,
        content="Restore",
        created_at="2026-04-15T12:00:00+00:00",
    )
    out = DescriptionRevisionRestoreResponse(
        descrizione_attivita="Restore",
        revision=rev,
    )
    # Frontend mutates Azienda.descrizione_attivita with this string.
    assert out.descrizione_attivita == "Restore"
    assert out.revision.source == SOURCE_MANUAL


def test_visura_upload_response_validates_non_negative_counts():
    out = VisuraUploadResponse(
        visura_uploaded_at="2026-04-15T12:00:00+00:00",
        extracted_chars=512,
        pages=2,
    )
    assert out.extracted_chars == 512
    assert out.pages == 2

    # `Field(ge=0)` should reject a negative count — guards against the
    # extractor returning a sentinel.
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        VisuraUploadResponse(
            visura_uploaded_at="2026-04-15T12:00:00+00:00",
            extracted_chars=-1,
            pages=0,
        )


# ---------------------------------------------------------------------------
# Visura PII redaction
# ---------------------------------------------------------------------------


def test_redact_strips_codice_fiscale_persona_fisica():
    raw = "Legale rappresentante: Mario Rossi (CF: RSSMRA80A01H501U)"
    out = _redact(raw)
    assert "RSSMRA80A01H501U" not in out
    assert "[CF REDATTO]" in out


def test_redact_strips_codice_fiscale_persona_giuridica():
    raw = "Codice fiscale azienda: 12345678901"
    out = _redact(raw)
    assert "12345678901" not in out
    assert "[CF REDATTO]" in out


def test_redact_strips_email_and_phone():
    raw = "Contatti: info@example.com - tel. +39 02 1234 5678"
    out = _redact(raw)
    assert "info@example.com" not in out
    assert "[email redatta]" in out
    # Phone number — exact format varies; we just need it gone.
    assert "1234" not in out


def test_redact_keeps_business_data():
    # Settore + ATECO + capitale should survive redaction so they reach the
    # AI prompt — that's literally the value the visura adds.
    raw = (
        "Oggetto sociale: produzione di componenti meccanici. "
        "ATECO: 25.62.00. Capitale sociale: 50.000 EUR i.v."
    )
    out = _redact(raw)
    assert "produzione di componenti meccanici" in out
    assert "25.62.00" in out
    assert "Capitale sociale" in out


# ---------------------------------------------------------------------------
# Visura extractor
# ---------------------------------------------------------------------------


def _make_pdf(text: str) -> bytes:
    """Build an in-memory PDF with one page of plaintext.

    Uses pypdf's writer so we don't need reportlab. We synthesise a minimal
    page via PdfWriter.add_blank_page and inject text via a content stream.
    """
    from pypdf import PdfWriter
    from pypdf.generic import (
        ArrayObject,
        ContentStream,
        DecodedStreamObject,
        DictionaryObject,
        FloatObject,
        NameObject,
        NumberObject,
        TextStringObject,
    )

    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)

    # Build a tiny BT/ET text-showing content stream. Helvetica is a
    # standard 14-font that PDF readers handle without an embedded font.
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream_text = (
        b"BT\n"
        b"/F1 12 Tf\n"
        b"50 800 Td\n"
        b"("
        + safe.encode("latin-1", errors="replace")
        + b") Tj\n"
        b"ET\n"
    )
    content = DecodedStreamObject()
    content.set_data(stream_text)

    # Wire a Helvetica font resource to /F1.
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )

    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = content

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_extract_visura_text_redacts_pii_in_snippet(tmp_path):
    pdf_bytes = _make_pdf(
        "Visura ordinaria. Legale rappresentante CF RSSMRA80A01H501U "
        "Email info@acme.it. Oggetto: produzione di componenti."
    )
    pdf_path = tmp_path / "visura.pdf"
    pdf_path.write_bytes(pdf_bytes)

    extraction = extract_visura_text(pdf_path)
    assert isinstance(extraction, VisuraExtraction)
    assert extraction.pages == 1
    assert extraction.raw_chars > 0
    # PII gone, business content preserved.
    assert "RSSMRA80A01H501U" not in extraction.snippet
    assert "info@acme.it" not in extraction.snippet
    assert "produzione di componenti" in extraction.snippet


def test_extract_visura_text_truncates_to_snippet_cap(tmp_path):
    long_text = "Settore: meccanica. " * 500  # ~10_000 chars
    pdf_path = tmp_path / "big.pdf"
    pdf_path.write_bytes(_make_pdf(long_text))

    extraction = extract_visura_text(pdf_path)
    assert extraction.raw_chars > MAX_SNIPPET_CHARS
    # Snippet length is capped + a truncation marker is appended.
    assert len(extraction.snippet) <= MAX_SNIPPET_CHARS + len("\n[…visura troncata]")
    assert extraction.snippet.endswith("[…visura troncata]")


def test_extract_visura_text_raises_on_empty_pdf(tmp_path):
    # A blank-page PDF (no text) is the typical "scanned visura" failure
    # mode — the extractor must raise so the route returns a 400 with the
    # operator-friendly message.
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    pdf_path = tmp_path / "scanned.pdf"
    pdf_path.write_bytes(buf.getvalue())

    with pytest.raises(ValueError):
        extract_visura_text(pdf_path)


# ---------------------------------------------------------------------------
# AI prompt builder uses visura text
# ---------------------------------------------------------------------------


def test_company_description_context_includes_visura_snippet():
    """When ``Azienda.visura_extracted_text`` is set, the prompt must
    surface it under a clearly-labelled section so the model treats it as
    additional grounding context.
    """
    from app.services.ai.company_description import _build_context

    class _StubAzienda:
        ragione_sociale = "Acme Meccanica SRL"
        codice_ateco = "25.62.00"
        attivita = None
        sede_operativa_citta = None
        metratura_totale = None
        orario_lavoro = None
        zona_sismica = None
        visura_extracted_text = (
            "Oggetto sociale: produzione di componenti meccanici. "
            "Capitale sociale: 50.000 EUR i.v."
        )
        ambienti = []
        persone = []

    context = _build_context(_StubAzienda())
    assert "Estratto visura camerale" in context
    assert "produzione di componenti meccanici" in context


def test_company_description_context_skips_visura_when_absent():
    from app.services.ai.company_description import _build_context

    class _StubAzienda:
        ragione_sociale = "Acme"
        codice_ateco = None
        attivita = None
        sede_operativa_citta = None
        metratura_totale = None
        orario_lavoro = None
        zona_sismica = None
        visura_extracted_text = None
        ambienti = []
        persone = []

    context = _build_context(_StubAzienda())
    assert "visura" not in context.lower()


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def test_router_registers_visura_and_revisions_routes():
    """Fail loudly if any of the three US-2.1 endpoints ever gets unwired."""
    from app.api.v1.router import api_router

    paths = {
        (method, getattr(r, "path", ""))
        for r in api_router.routes
        for method in getattr(r, "methods", set()) or set()
    }
    base = "/api/v1/aziende/{azienda_id}"
    assert ("POST", f"{base}/visura") in paths, "POST /visura missing"
    assert ("GET", f"{base}/description-revisions") in paths, "GET /description-revisions missing"
    assert (
        "POST",
        f"{base}/description-revisions/{{revision_id}}/restore",
    ) in paths, "POST /description-revisions/.../restore missing"


def test_azienda_response_exposes_visura_uploaded_at():
    """Frontend reads `azienda.visura_uploaded_at` to render the
    "visura caricata il …" hint in the description editor card."""
    from app.schemas.azienda import AziendaResponse

    fields = AziendaResponse.model_fields
    assert "visura_uploaded_at" in fields
