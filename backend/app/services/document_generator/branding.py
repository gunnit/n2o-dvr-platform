"""Per-organization document branding (logo + letterhead).

Turns the consultancy identity that used to be hardcoded (the committed
``assets/logo.png`` and N2O letterhead) into data resolved from the
``Organization`` row. Everything degrades gracefully to the N2O default so a
sparse org — or the DB-free test harness — never breaks document generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# backend/app/services/document_generator/branding.py -> parents[3] == backend/
DEFAULT_LOGO_PATH: Path = Path(__file__).resolve().parents[3] / "assets" / "logo.png"

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
    ``logo_path`` is the org's uploaded logo path (may be missing on disk);
    use :func:`resolve_logo_path` to get the actual file to embed.
    """

    firm_name: str = DEFAULT_FIRM_NAME
    logo_path: str | None = None
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
            logo_path=_clean(getattr(org, "logo_path", None)),
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
        """`Via Roma 1, 20100 Milano (MI)` from the parts present, or None."""
        city_bits = " ".join(p for p in (self.cap, self.citta) if p)
        if self.provincia:
            city_bits = f"{city_bits} ({self.provincia})".strip()
        parts = [p for p in (self.indirizzo, city_bits.strip()) if p]
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


def resolve_logo_path(branding: Branding) -> Path:
    """Return the logo file to embed: the org's uploaded logo if it exists on
    disk, otherwise the committed default asset."""
    if branding.logo_path:
        candidate = Path(branding.logo_path)
        if candidate.exists():
            return candidate
    return DEFAULT_LOGO_PATH
