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


def extract_visura_text(pdf_path: str | Path) -> VisuraExtraction:
    """Pull text out of the visura PDF, redact PII, truncate.

    Raises ``ValueError`` if the PDF is unreadable or yields no text at
    all (typical for scanned visure — we don't OCR; the operator can
    re-upload a digitally-generated copy).
    """
    path = Path(pdf_path)
    try:
        from pypdf import PdfReader  # noqa: WPS433 — local import keeps cold path off the hot path
    except ImportError as exc:  # pragma: no cover — guarded by requirements.txt
        raise RuntimeError("pypdf non installato — eseguire pip install -r requirements.txt") from exc

    reader = PdfReader(str(path))
    pages = len(reader.pages)
    chunks: list[str] = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover — pypdf swallows most issues
            logger.warning("Failed to extract page from %s: %s", path.name, exc)

    raw = "\n\n".join(chunk.strip() for chunk in chunks if chunk and chunk.strip())
    raw_chars = len(raw)
    if raw_chars == 0:
        raise ValueError(
            "Visura illeggibile (probabile scansione senza OCR) — "
            "carica una copia digitale generata dalla CCIAA."
        )

    redacted = _redact(raw)
    snippet = redacted[:MAX_SNIPPET_CHARS]
    if len(redacted) > MAX_SNIPPET_CHARS:
        snippet = snippet.rstrip() + "\n[…visura troncata]"
    return VisuraExtraction(pages=pages, raw_chars=raw_chars, snippet=snippet)
