"""VIES (EU VAT Information Exchange System) lookup.

Free, deterministic, no API key. Given an Italian P.IVA, returns the
canonical ragione sociale and indirizzo sede legale as registered with
Agenzia delle Entrate. This is the highest-confidence source in the
autofill pipeline — VIES results are tagged ``confidence=high``.

Endpoint: https://ec.europa.eu/taxation_customs/vies/rest-api/ms/IT/vat/<piva>

VIES returns the address as a single multi-line string (street + city +
CAP + provincia interleaved). We parse it conservatively: keep the full
string as ``sede_legale_via`` fallback, then try to peel off CAP / city
/ provincia using Italian postal-format heuristics.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


VIES_REST_URL = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/IT/vat/{piva}"


@dataclass(frozen=True)
class VIESResult:
    """Parsed VIES response. All fields are public registry data."""

    is_valid: bool
    ragione_sociale: str | None
    sede_legale_via: str | None
    sede_legale_citta: str | None
    cap_legale: str | None
    provincia_legale: str | None
    raw_address: str | None


# CAP (5 digits) + city + " (PROVINCIA)" or "PROVINCIA". Examples seen in
# real VIES responses:
#   "00100 ROMA RM"
#   "20121 MILANO (MI)"
#   "VIA ROMA 1 - 00100 ROMA"
_ADDRESS_TAIL_RE = re.compile(
    r"(?P<cap>\d{5})\s+(?P<citta>[A-ZÀ-ſ'\s]+?)\s*(?:\(\s*)?(?P<prov>[A-Z]{2})\)?\s*$",
    re.UNICODE,
)


def _parse_address(raw: str | None) -> tuple[str | None, str | None, str | None, str | None]:
    """Best-effort split of the VIES address blob.

    Returns (via, citta, cap, provincia). All can be None — VIES sometimes
    returns "---" or just "ITALIA" for entities that opted out of address
    publication. The full ``raw`` string is also kept on the result so
    operators can reconstruct it if our heuristics get it wrong.
    """
    if not raw:
        return None, None, None, None
    text = raw.replace("\n", " ").strip()
    if not text or text == "---":
        return None, None, None, None

    match = _ADDRESS_TAIL_RE.search(text)
    if match:
        cap = match.group("cap")
        citta = match.group("citta").strip().title()
        prov = match.group("prov").upper()
        # Everything before the CAP is the street; trim trailing punctuation.
        via = text[: match.start()].strip().rstrip(",-").strip().title() or None
        return via, citta, cap, prov

    # Fallback: just keep the whole string as via, leave the rest blank.
    return text.title(), None, None, None


async def lookup_vies(partita_iva: str) -> VIESResult | None:
    """Look up an Italian P.IVA against VIES. Returns None on transport error.

    The VIES service is publicly hosted by the EU and historically flaky —
    it can return 502/503 under load. We treat any network failure as a
    soft miss (the autofill pipeline records a warning and proceeds with
    the other sources) rather than aborting the whole operation.
    """
    url = VIES_REST_URL.format(piva=partita_iva)
    try:
        async with httpx.AsyncClient(timeout=settings.AZIENDA_AUTOFILL_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        logger.warning("VIES lookup failed for %s: %s", partita_iva, exc)
        return None

    if response.status_code != 200:
        logger.warning("VIES returned %d for %s", response.status_code, partita_iva)
        return None

    try:
        data = response.json()
    except ValueError:
        logger.warning("VIES returned non-JSON for %s", partita_iva)
        return None

    is_valid = bool(data.get("isValid") or data.get("valid"))
    name = (data.get("name") or "").strip() or None
    address = (data.get("address") or "").strip() or None
    via, citta, cap, prov = _parse_address(address)

    return VIESResult(
        is_valid=is_valid,
        ragione_sociale=name if is_valid else None,
        sede_legale_via=via if is_valid else None,
        sede_legale_citta=citta if is_valid else None,
        cap_legale=cap if is_valid else None,
        provincia_legale=prov if is_valid else None,
        raw_address=address,
    )
