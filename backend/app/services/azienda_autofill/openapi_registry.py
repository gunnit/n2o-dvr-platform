"""openapi.com — paid Italian Registro Imprese / visura camerale lookup.

This is a paid, structured complement to the free VIES service. VIES only
gives ragione sociale + sede legale (with address parsing heuristics);
openapi.com returns the full visura camerale shape — including REA,
codice ATECO, forma giuridica, data costituzione, capitale sociale,
PEC, and (critically for issue #11) the list of unità locali / sedi
operative. When operators ask for "API a pagamento per il
completamento della ragione sociale" (feedback issue #6, 2026-05-14)
this is the upgrade they were asking for.

Endpoint (production): https://company.openapi.com/IT-start/{piva}
Endpoint (sandbox):    https://test.ws.openapi.com/IT-start/{piva}

Both require a Bearer token via ``OPENAPI_API_KEY``. Without the key
this source is silently skipped — the pipeline degrades to VIES + Serper
+ Firecrawl + AI as before.

NB: openapi.com bills per call (~€0.20 each on the pay-as-you-go plan).
We only invoke it when the key is configured AND the operator triggered
an autofill — never from a background job. Costs are bounded by operator
clicks, not data volume.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class OpenAPIRegistryResult:
    """Subset of the openapi.com visura response we map onto Azienda.

    Every field is optional — the API doesn't always populate everything
    (especially for very small or just-incorporated entities). Address
    fields come pre-parsed (city, CAP, provincia are separate columns in
    the response, unlike VIES) so no heuristics needed here.
    """

    ragione_sociale: str | None = None
    forma_giuridica: str | None = None
    codice_fiscale: str | None = None
    rea: str | None = None
    codice_ateco: str | None = None
    data_costituzione: str | None = None  # ISO date string
    capitale_sociale: float | None = None
    pec: str | None = None
    sede_legale_via: str | None = None
    sede_legale_citta: str | None = None
    cap_legale: str | None = None
    provincia_legale: str | None = None
    # Issue #11: openapi.com returns the unità locali list. The first
    # one becomes the primary sede_operativa; everything after gets
    # routed to ``sedi_operative_extra`` JSONB. Each item:
    # {via, citta, cap, provincia, comune}.
    sedi_operative: list[dict[str, str]] = field(default_factory=list)


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalise_sede(raw: dict[str, Any]) -> dict[str, str]:
    """Normalise an openapi.com address block into our 5-key shape."""
    return {
        "via": _str_or_none(raw.get("toponimo") and f"{raw.get('toponimo','')} {raw.get('via','')}".strip() or raw.get("via")) or "",
        "citta": _str_or_none(raw.get("comune") or raw.get("citta")) or "",
        "comune": _str_or_none(raw.get("comune")) or "",
        "provincia": (_str_or_none(raw.get("provincia")) or "").upper()[:2],
        "cap": _str_or_none(raw.get("cap")) or "",
    }


def _parse_response(payload: dict[str, Any]) -> OpenAPIRegistryResult:
    """Map the openapi.com JSON envelope onto our result dataclass.

    The API wraps its body under ``data`` (one entry per matched
    company). We take the first one. Field names track the openapi.com
    visura schema (camelCase Italian) — kept in sync with their docs at
    https://developers.openapi.com/categories/business.
    """
    data_list = payload.get("data") if isinstance(payload, dict) else None
    if not data_list:
        return OpenAPIRegistryResult()
    record = data_list[0] if isinstance(data_list, list) else data_list
    if not isinstance(record, dict):
        return OpenAPIRegistryResult()

    indirizzo = record.get("indirizzo") or record.get("sedeLegale") or {}
    if not isinstance(indirizzo, dict):
        indirizzo = {}

    unita_locali_raw = record.get("unitaLocali") or record.get("sediOperative") or []
    sedi_operative: list[dict[str, str]] = []
    if isinstance(unita_locali_raw, list):
        for u in unita_locali_raw:
            if isinstance(u, dict):
                addr = u.get("indirizzo") if isinstance(u.get("indirizzo"), dict) else u
                if isinstance(addr, dict):
                    sedi_operative.append(_normalise_sede(addr))

    return OpenAPIRegistryResult(
        ragione_sociale=_str_or_none(record.get("denominazione") or record.get("ragioneSociale")),
        forma_giuridica=_str_or_none(record.get("formaGiuridica") or record.get("naturaGiuridica")),
        codice_fiscale=_str_or_none(record.get("codiceFiscale")),
        rea=_str_or_none(record.get("rea") or record.get("numeroRea")),
        codice_ateco=_str_or_none(
            record.get("codiceAteco")
            or (isinstance(record.get("ateco"), dict) and record["ateco"].get("codice"))
        ),
        data_costituzione=_str_or_none(record.get("dataCostituzione") or record.get("dataIscrizione")),
        capitale_sociale=_float_or_none(record.get("capitaleSociale") or record.get("capitaleSocialeDeliberato")),
        pec=_str_or_none(record.get("pec") or record.get("pecImpresa")),
        sede_legale_via=_str_or_none(indirizzo.get("via") or indirizzo.get("indirizzo")),
        sede_legale_citta=_str_or_none(indirizzo.get("comune") or indirizzo.get("citta")),
        cap_legale=_str_or_none(indirizzo.get("cap")),
        provincia_legale=(_str_or_none(indirizzo.get("provincia")) or "").upper()[:2] or None,
        sedi_operative=sedi_operative,
    )


async def lookup_openapi_registry(partita_iva: str) -> OpenAPIRegistryResult | None:
    """Call openapi.com IT-start endpoint. Returns None when:

    - ``OPENAPI_API_KEY`` is not configured (feature off).
    - The API errors / times out (soft fail — pipeline records a warning).
    - The response is malformed.

    Never raises on transport / parse failure — autofill is best-effort.
    """
    if not settings.OPENAPI_API_KEY:
        logger.info("OPENAPI_API_KEY not set — skipping openapi.com enrichment")
        return None

    url = settings.OPENAPI_REGISTRY_URL.rstrip("/") + f"/{partita_iva}"
    headers = {
        "Authorization": f"Bearer {settings.OPENAPI_API_KEY}",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.AZIENDA_AUTOFILL_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("openapi.com lookup failed for %s: %s", partita_iva, exc)
        return None

    if response.status_code == 404:
        # Company not found — not an error, just no data. Return an empty
        # result so callers can distinguish "didn't run" (None) from
        # "ran, found nothing".
        return OpenAPIRegistryResult()
    if response.status_code != 200:
        logger.warning(
            "openapi.com returned %d for %s: %s",
            response.status_code,
            partita_iva,
            response.text[:200],
        )
        return None

    try:
        payload = response.json()
    except ValueError:
        logger.warning("openapi.com returned non-JSON for %s", partita_iva)
        return None

    return _parse_response(payload)
