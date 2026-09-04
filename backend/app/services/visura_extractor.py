"""Local plaintext extraction for visura camerale PDFs (US-2.1 AC1).

Visura documents contain PII (legal-rep names, codici fiscali, addresses)
which the project's privacy contract (CLAUDE.md) forbids from being sent
to AI providers. We therefore extract text **locally** with ``pypdf`` and
keep only an anonymised snippet for the description prompt.

The snippet is built by:

1. Joining all page text with a blank line separator.
2. Applying coarse PII redaction (codice fiscale + email + telefono) so
   even if an operator later inspects the snippet, the sensitive bits
   aren't there.
3. Truncating to ``MAX_SNIPPET_CHARS`` so the prompt stays cheap.

The full unredacted text is **NOT** persisted — only the redacted snippet
is. The original PDF stays on disk, accessible only via the API behind the
auth/session boundary.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import IO

logger = logging.getLogger(__name__)


# Soft cap so the AI prompt stays under ~1 KB worth of visura data — plenty
# for "settore, oggetto sociale, capitale sociale" snippets without bloating
# token usage on every Genera con AI click.
MAX_SNIPPET_CHARS = 1_500


# Italian codice fiscale: 16 alphanumeric chars (PF) or 11 digits (PG).
# Both forms are PII and must be stripped before the snippet is stored.
_CF_PATTERN = re.compile(r"\b([A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]|\d{11})\b")
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# Italian phone: optional +39, optional space, then 9-11 digits with
# optional separators. Conservative — false positives are fine here.
_PHONE_PATTERN = re.compile(r"(\+?39[\s.-]?)?\b\d{2,4}[\s./-]?\d{3,4}[\s./-]?\d{3,4}\b")


@dataclass(frozen=True)
class VisuraExtraction:
    """Result of a successful visura extraction."""

    pages: int
    raw_chars: int
    snippet: str

    @property
    def snippet_chars(self) -> int:
        return len(self.snippet)


def _redact(text: str) -> str:
    """Strip codici fiscali, emails, phone numbers from raw visura text."""
    text = _CF_PATTERN.sub("[CF REDATTO]", text)
    text = _EMAIL_PATTERN.sub("[email redatta]", text)
    text = _PHONE_PATTERN.sub("[telefono redatto]", text)
    return text


@dataclass(frozen=True)
class VisuraRawText:
    """Unredacted plaintext of a visura, held in memory for one request only.

    This carries PII (legal-rep names, personal codici fiscali). It must
    never be persisted, logged or handed to an AI helper — the only two
    consumers are :func:`extract_visura_text` (which redacts before storing
    a snippet) and :mod:`app.services.visura_parser` (which pulls out
    company-level fields deterministically and discards the rest).
    """

    pages: int
    text: str


def extract_visura_raw_text(source: str | Path | IO[bytes]) -> VisuraRawText:
    """Read every page of a visura PDF into one string, locally with pypdf.

    Accepts a filesystem path or an open binary stream so the pre-creation
    flow (``POST /aziende/visura/estrai``) can parse an upload straight from
    memory without ever writing the PII-bearing PDF to disk.

    Raises ``ValueError`` if the PDF is unreadable or yields no text at
    all (typical for scanned visure — we don't OCR; the operator can
    re-upload a digitally-generated copy).
    """
    try:
        from pypdf import PdfReader  # noqa: WPS433 — local import keeps cold path off the hot path
    except ImportError as exc:  # pragma: no cover — guarded by requirements.txt
        raise RuntimeError("pypdf non installato — eseguire pip install -r requirements.txt") from exc

    label = Path(source).name if isinstance(source, (str, Path)) else "<upload>"
    reader = PdfReader(str(source) if isinstance(source, (str, Path)) else source)
    pages = len(reader.pages)
    chunks: list[str] = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover — pypdf swallows most issues
            logger.warning("Failed to extract page from %s: %s", label, exc)

    raw = "\n\n".join(chunk.strip() for chunk in chunks if chunk and chunk.strip())
    if len(raw) == 0:
        raise ValueError(
            "Visura illeggibile (probabile scansione senza OCR) — "
            "carica una copia digitale generata dalla CCIAA."
        )
    return VisuraRawText(pages=pages, text=raw)


def extract_visura_text(pdf_path: str | Path) -> VisuraExtraction:
    """Pull text out of the visura PDF, redact PII, truncate.

    Raises ``ValueError`` if the PDF is unreadable or yields no text at
    all (typical for scanned visure — we don't OCR; the operator can
    re-upload a digitally-generated copy).
    """
    raw = extract_visura_raw_text(Path(pdf_path))
    redacted = _redact(raw.text)
    snippet = redacted[:MAX_SNIPPET_CHARS]
    if len(redacted) > MAX_SNIPPET_CHARS:
        snippet = snippet.rstrip() + "\n[…visura troncata]"
    return VisuraExtraction(pages=raw.pages, raw_chars=len(raw.text), snippet=snippet)
