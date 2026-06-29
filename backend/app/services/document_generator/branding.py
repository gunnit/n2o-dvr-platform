"""Per-organization document branding (logo + letterhead).

Turns the consultancy identity that used to be hardcoded (the committed
``assets/logo.png`` and N2O letterhead) into data resolved from the
``Organization`` row. Everything degrades gracefully to the N2O default so a
sparse org — or the DB-free test harness — never breaks document generation.

The logo is stored as bytes on the Organization (see the model) rather than a
disk path, because document generation runs on the Celery worker, which mounts
a different Render disk from the API that receives the upload.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

# Single source of truth for the committed fallback logo (review finding #9).
from app.services.document_generator.docx_utils import LOGO_PATH as DEFAULT_LOGO_PATH

# Fallback firm name (N2O is the consultancy that owns this install today).
DEFAULT_FIRM_NAME = "N2O SRL"


def _clean(value: str | None) -> str | None:
    """Normalise a possibly-empty DB string to ``None`` when blank."""
    if value is None:
        return None
    text = value.strip()
    return text or None


@dataclass
class Branding:
    """Resolved consultancy branding for one document generation run.

    ``firm_name`` always has a value (defaults to N2O). All other fields are
    optional; generators render the letterhead block only from what's present.
    ``logo_bytes`` is the org's uploaded logo image; use
    :func:`resolve_logo_source` to get the thing to embed (the bytes, or the
    committed default).
    """

    firm_name: str = DEFAULT_FIRM_NAME
    logo_bytes: bytes | None = None
    logo_content_type: str | None = None
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

    @classmethod
    def default(cls) -> "Branding":
        """N2O fallback branding (committed logo, default firm name)."""
        return cls()

    @classmethod
    def from_organization(cls, org) -> "Branding":
        """Build branding from an ``Organization`` row (or anything duck-typed).

        Defensive: a ``None`` org, or a blank firm name, falls back to the N2O
        default. Never raises — generation must not crash on sparse data.
        """
        if org is None:
            return cls.default()
        return cls(
            firm_name=_clean(getattr(org, "name", None)) or DEFAULT_FIRM_NAME,
            logo_bytes=getattr(org, "logo_bytes", None) or None,
            logo_content_type=_clean(getattr(org, "logo_content_type", None)),
            indirizzo=_clean(getattr(org, "indirizzo", None)),
            cap=_clean(getattr(org, "cap", None)),
            citta=_clean(getattr(org, "citta", None)),
            provincia=_clean(getattr(org, "provincia", None)),
            partita_iva=_clean(getattr(org, "partita_iva", None)),
            codice_fiscale=_clean(getattr(org, "codice_fiscale", None)),
            telefono=_clean(getattr(org, "telefono", None)),
            email=_clean(getattr(org, "email", None)),
            sito_web=_clean(getattr(org, "sito_web", None)),
            rspp_nome=_clean(getattr(org, "rspp_nome", None)),
        )

    def address_line(self) -> str | None:
        """`Via Roma 1, 20100 Milano (MI)` from the parts present, or None.

        The province is only ever appended in parentheses when there's a city
        to attach it to — otherwise a province-only org would print a stray
        `(MI)` fragment (review finding #6).
        """
        city_bits = " ".join(p for p in (self.cap, self.citta) if p)
        if city_bits and self.provincia:
            city_bits = f"{city_bits} ({self.provincia})"
        elif not city_bits and self.provincia:
            city_bits = self.provincia
        parts = [p for p in (self.indirizzo, city_bits) if p]
        return ", ".join(parts) or None

    def contact_line(self) -> str | None:
        """`Tel. … · email · sito` from the parts present, or None."""
        bits = []
        if self.telefono:
            bits.append(f"Tel. {self.telefono}")
        if self.email:
            bits.append(self.email)
        if self.sito_web:
            bits.append(self.sito_web)
        return " · ".join(bits) or None

    def has_letterhead_detail(self) -> bool:
        """True if there's any letterhead text beyond the bare firm name."""
        return any(
            (
                self.indirizzo,
                self.cap,
                self.citta,
                self.provincia,
                self.partita_iva,
                self.codice_fiscale,
                self.telefono,
                self.email,
                self.sito_web,
                self.rspp_nome,
            )
        )

    def is_configured(self) -> bool:
        """True if the org has actually customised its branding (vs the bare
        N2O default). Used to gate additive document elements so un-configured
        orgs see no output change."""
        return (
            self.has_letterhead_detail()
            or self.firm_name != DEFAULT_FIRM_NAME
            or bool(self.logo_bytes)
        )


def resolve_logo_source(branding: Branding):
    """Return something ``python-docx`` ``add_picture`` can embed: the org's
    uploaded logo bytes (as a fresh ``BytesIO``) if present, else the committed
    default logo path, else ``None`` when even the default is missing."""
    if branding.logo_bytes:
        return io.BytesIO(branding.logo_bytes)
    if DEFAULT_LOGO_PATH.exists():
        return str(DEFAULT_LOGO_PATH)
    return None
