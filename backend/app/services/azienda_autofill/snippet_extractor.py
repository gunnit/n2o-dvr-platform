"""Deterministic field extractors over Serper snippets.

Italian registry sites (registroimprese.it, ufficiocamerale.it,
fatturatoitalia.it, registroaziende.it, infoaziende.it, ...) format their
snippets in highly regular ways. Examples we've seen for one P.IVA:

  "Codice Ateco: 62.01: Produzione di software non connesso..."
  "P.IVA: 02735920742 - Codice Fiscale: 02735920742 · Vat Europeo: IT..."
  "REA BR-180454"
  "PEC: pugliai@pec.it"
  "Capitale Sociale: € 10.000,00"

Letting the AI consolidator parse these is wasteful and unreliable — it
sometimes ignores explicit "Field: value" pairs because the system
prompt tells it to be conservative. Instead, run cheap regex over every
snippet and return ``ExtractedFacts`` that the consolidator treats as
ground truth (mirroring how VIES is treated).

These extractors NEVER hit the network and never see PII — they read
the same snippets that already came back from Serper.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.services.azienda_autofill.serper import SerperResult

logger = logging.getLogger(__name__)


# "Codice Ateco: 62.01" or "ATECO: 62.01.00" or "ateco 62.01.1"
_ATECO_RE = re.compile(
    r"\b(?:codice\s+)?ateco[\s:]+(\d{2}\.\d{2}(?:\.\d{1,2})?)",
    re.IGNORECASE,
)

# REA: "REA BR-180454" / "REA: MI-1234567" / "n. REA RM 12345"
_REA_RE = re.compile(
    r"\bREA[\s:]*([A-Z]{2}[\s\-]?\d{3,8})",
    re.IGNORECASE,
)

# PEC: "PEC: pugliai@pec.it" or "pec azienda@pec.it"
_PEC_RE = re.compile(
    r"\bPEC[\s:]+([\w.\-+]+@[\w\-]+\.[\w.\-]+)",
    re.IGNORECASE,
)

# Codice fiscale of a legal entity (11 digits) — only accept if the
# context word "fiscale" / "CF" appears nearby. Plain 11-digit numbers
# could be many things; the explicit label avoids false positives.
_CF_RE = re.compile(
    r"(?:codice\s+fiscale|c\.f\.|^cf)[\s:]+(\d{11})\b",
    re.IGNORECASE | re.MULTILINE,
)

# Capitale sociale: "Capitale Sociale: € 10.000,00" / "capitale sociale 10000 euro"
# Italian thousands use "." and decimals use ",". We strip "." then
# normalise "," -> "." for float conversion.
_CAPITALE_RE = re.compile(
    r"capitale\s+sociale[\s:€]+(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?)",
    re.IGNORECASE,
)

# Forma giuridica: explicit registry pattern "Forma giuridica: SRL" or
# the common "PUGLIAI S.R.L." style anywhere in the snippet. Order
# matters: longer / more specific forms first so SRL doesn't shadow SRLS.
_FORMA_INLINE_RE = re.compile(
    r"\b(S\.R\.L\.S\.|S\.R\.L\.|S\.P\.A\.|S\.A\.P\.A\.|S\.N\.C\.|S\.A\.S\.|"
    r"S\.C\.A\.R\.L\.|SRLS|SRL|SPA|SAPA|SNC|SAS|SCARL|SCRL|"
    r"DITTA\s+INDIVIDUALE|COOPERATIVA|CONSORZIO)\b",
    re.IGNORECASE,
)

_FORMA_NORMALISE = {
    "S.R.L.S.": "SRLS",
    "S.R.L.": "SRL",
    "S.P.A.": "SPA",
    "S.A.P.A.": "SAPA",
    "S.N.C.": "SNC",
    "S.A.S.": "SAS",
    "S.C.A.R.L.": "SCARL",
    "DITTA INDIVIDUALE": "Ditta Individuale",
    "COOPERATIVA": "Cooperativa",
    "CONSORZIO": "Consorzio",
}

# Sito web: "Sito web: www.example.it" / "Website: https://example.com"
_SITO_RE = re.compile(
    r"\b(?:sito\s+web|website|home\s*page)[\s:]+(https?://\S+|www\.\S+)",
    re.IGNORECASE,
)

# Telefono: italian fixed/mobile, with or without +39 / 0039 prefix.
_TEL_RE = re.compile(
    r"\b(?:tel(?:efono)?|phone)[\s.:]*((?:\+?39[\s.-]?)?0?\d{1,4}[\s./-]?\d{3,4}[\s./-]?\d{3,4})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtractedFacts:
    """Facts pulled deterministically from Serper snippets.

    Each field is None when no snippet matched. Each non-None field is
    paired with the index of the Serper result it came from (so we can
    surface the right source URL in the autofill response). Confidence
    is implicitly "medium" — explicit registry-formatted strings, but
    not VIES-grade.
    """

    codice_ateco: str | None = None
    codice_ateco_source_idx: int | None = None
    rea: str | None = None
    rea_source_idx: int | None = None
    pec: str | None = None
    pec_source_idx: int | None = None
    codice_fiscale: str | None = None
    codice_fiscale_source_idx: int | None = None
    capitale_sociale: float | None = None
    capitale_sociale_source_idx: int | None = None
    forma_giuridica: str | None = None
    forma_giuridica_source_idx: int | None = None
    sito_web: str | None = None
    sito_web_source_idx: int | None = None
    telefono: str | None = None
    telefono_source_idx: int | None = None


def _parse_capitale(raw: str) -> float | None:
    """Convert "10.000,00" / "10000" / "10000,50" → float euros."""
    cleaned = raw.strip().replace(".", "").replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    # Sanity floor: < 100€ is almost certainly a parse error (years, etc).
    if value < 100:
        return None
    return value


def _normalise_forma(raw: str) -> str:
    upper = raw.upper().strip()
    return _FORMA_NORMALISE.get(upper, upper)


def extract_from_snippets(results: list[SerperResult]) -> ExtractedFacts:
    """Run every regex over every snippet, keep first hit per field.

    Searches both the title and the snippet body. We don't dedupe: the
    first (= highest-ranked) match wins, which is the right bias because
    Google ranks the most authoritative registry pages first.
    """
    out: dict[str, object] = {}

    for idx, r in enumerate(results):
        haystack = f"{r.title}\n{r.snippet}"

        if "codice_ateco" not in out:
            m = _ATECO_RE.search(haystack)
            if m:
                out["codice_ateco"] = m.group(1)
                out["codice_ateco_source_idx"] = idx

        if "rea" not in out:
            m = _REA_RE.search(haystack)
            if m:
                # Normalise "BR 180454" / "br-180454" → "BR-180454"
                raw = re.sub(r"\s+", "-", m.group(1).strip())
                if "-" not in raw and len(raw) >= 4:
                    raw = f"{raw[:2].upper()}-{raw[2:]}"
                out["rea"] = raw.upper()
                out["rea_source_idx"] = idx

        if "pec" not in out:
            m = _PEC_RE.search(haystack)
            if m:
                out["pec"] = m.group(1).lower()
                out["pec_source_idx"] = idx

        if "codice_fiscale" not in out:
            m = _CF_RE.search(haystack)
            if m:
                out["codice_fiscale"] = m.group(1)
                out["codice_fiscale_source_idx"] = idx

        if "capitale_sociale" not in out:
            m = _CAPITALE_RE.search(haystack)
            if m:
                value = _parse_capitale(m.group(1))
                if value is not None:
                    out["capitale_sociale"] = value
                    out["capitale_sociale_source_idx"] = idx

        if "forma_giuridica" not in out:
            m = _FORMA_INLINE_RE.search(haystack)
            if m:
                out["forma_giuridica"] = _normalise_forma(m.group(1))
                out["forma_giuridica_source_idx"] = idx

        if "sito_web" not in out:
            m = _SITO_RE.search(haystack)
            if m:
                url = m.group(1).strip().rstrip(".,)")
                if url.startswith("www."):
                    url = f"https://{url}"
                out["sito_web"] = url
                out["sito_web_source_idx"] = idx

        if "telefono" not in out:
            m = _TEL_RE.search(haystack)
            if m:
                tel = re.sub(r"[\s./-]", " ", m.group(1)).strip()
                tel = re.sub(r"\s+", " ", tel)
                out["telefono"] = tel
                out["telefono_source_idx"] = idx

    return ExtractedFacts(**out)  # type: ignore[arg-type]


def source_url_for(facts: ExtractedFacts, field: str, results: list[SerperResult]) -> str | None:
    """Look up the Serper link the given fact came from.

    Used by the pipeline to populate ``AziendaAutofillFieldMeta.source_url``
    so the operator can click through to the registry page that supplied
    the value.
    """
    idx_attr = f"{field}_source_idx"
    idx = getattr(facts, idx_attr, None)
    if idx is None or idx >= len(results):
        return None
    return results[idx].link or None
