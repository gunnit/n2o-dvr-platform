"""Orchestrates the autofill pipeline.

Flow:
    VIES        ─┐
    Serper      ─┼── parallel ──> consolidator ──> AziendaAutofillResponse
                 │
    [Firecrawl is sequential because it needs the URL discovered by Serper]

We run VIES + Serper concurrently for latency. Firecrawl waits on Serper
because we need the homepage URL it surfaces. End-to-end target: <8s on
warm caches, <12s worst case.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import urlparse

from app.config import settings
from app.core.exceptions import AIError
from app.schemas.azienda import (
    AziendaAutofillFieldMeta,
    AziendaAutofillResponse,
    Confidence,
)
from app.services.azienda_autofill.consolidator import (
    ConsolidatedAzienda,
    consolidate,
)
from app.services.azienda_autofill.firecrawl import scrape_site
from app.services.azienda_autofill.openapi_registry import (
    OpenAPIRegistryResult,
    lookup_openapi_registry,
)
from app.services.azienda_autofill.serper import SerperResult, search_piva
from app.services.azienda_autofill.snippet_extractor import (
    ExtractedFacts,
    extract_from_snippets,
    source_url_for,
)
from app.services.azienda_autofill.vies import VIESResult, lookup_vies

logger = logging.getLogger(__name__)


# Domains that look like company homepages — used to filter Serper results
# down to a likely "sito_web" target. We exclude registries, directories,
# and aggregators because their pages are about the company, not the
# company's own site. The list grows over time as we hit new registries
# in the wild (PUGLIAI test 2026-04-28 surfaced fatturatoitalia +
# registroaziende that weren't in the first cut).
_NON_HOMEPAGE_DOMAINS = (
    # Italian camera-di-commercio registries / aggregators
    "registroimprese.it",
    "ufficiocamerale.it",
    "fatturatoitalia.it",
    "registroaziende.it",
    "infoaziende.it",
    "imprese.io",
    "infoimprese.it",
    "telematicocb.it",
    "guidamonaci.it",
    "tuttitalia.it",
    "partitaiva.online",
    "partitaiva.it",
    "aziende.virgilio.it",
    "italiainformazioni.com",
    "kompass.com",
    "europages.it",
    "europages.com",
    "dnb.com",
    # Maps / directories
    "paginebianche.it",
    "paginegialle.it",
    # Social
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    # Search / encyclopaedia / video
    "google.com",
    "bing.com",
    "wikipedia.org",
    "youtube.com",
    # Govt
    "europa.eu",
    "aifa.gov.it",
    "agenziaentrate.gov.it",
    "gazzettaufficiale.it",
)


def _pick_homepage(serper: list[SerperResult], partita_iva: str | None = None) -> str | None:
    """Pick the most likely company homepage from Serper results.

    Two filters:
      1. Exclude known registry / directory / social domains.
      2. Exclude URLs whose path contains the P.IVA — those are profile
         pages on aggregators we haven't seen before (the path-PIVA
         pattern is the universal tell of an aggregator).

    We don't try anything smarter than that — the consolidator gets all
    the snippets anyway, so a wrong pick only costs one Firecrawl call's
    worth of irrelevant markdown.
    """
    for r in serper:
        if not r.link:
            continue
        try:
            parsed = urlparse(r.link)
        except ValueError:
            continue
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if not host:
            continue
        if any(host == d or host.endswith("." + d) for d in _NON_HOMEPAGE_DOMAINS):
            continue
        if partita_iva and partita_iva in (parsed.path or ""):
            continue
        return f"{parsed.scheme}://{parsed.hostname}/"
    return None


def _domain_from_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return None
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


# Codice ATECO normaliser: registries sometimes return "62.01" or "62.01.00"
# or "62.0100" — squash to canonical "XX.XX" / "XX.XX.XX".
_ATECO_RAW_RE = re.compile(r"\b(\d{2})\.?(\d{2})(?:\.?(\d{1,2}))?\b")


def _normalize_ateco(value: str | None) -> str | None:
    if not value:
        return None
    match = _ATECO_RAW_RE.search(value)
    if not match:
        return None
    a, b, c = match.groups()
    return f"{a}.{b}.{c}" if c else f"{a}.{b}"


def _normalize_provincia(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().upper()
    if len(cleaned) == 2 and cleaned.isalpha():
        return cleaned
    return None


def _normalize_cap(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return digits if len(digits) == 5 else None


def _plausible_data_costituzione(value: Any) -> Any:
    """Drop hallucinated dates with year < 1900 (LLM sometimes fabricates
    '0101-01-01' from a REA / postcode it parsed as a year)."""
    if value is None:
        return None
    try:
        year = int(str(value)[:4])
    except (TypeError, ValueError):
        return None
    if year < 1900:
        return None
    return value


def _build_response(
    *,
    partita_iva: str,
    vies: VIESResult | None,
    openapi_reg: OpenAPIRegistryResult | None,
    serper: list[SerperResult],
    facts: ExtractedFacts,
    homepage_url: str | None,
    consolidated: ConsolidatedAzienda | None,
    warnings: list[str],
) -> AziendaAutofillResponse:
    """Compose the AziendaAutofillResponse, layering sources by priority.

    Priority (highest first):
      1. VIES — anything it returned for ragione sociale + sede legale
      2. ExtractedFacts — deterministic regex over Serper snippets
         (ATECO, REA, PEC, CF, capitale, forma giuridica, telefono, sito)
      3. AI consolidator — everything else (descriptive fields, gaps)
      4. Heuristics — sito_web inferred from homepage_url even if AI missed

    Each populated field gets a meta entry with confidence + source.
    """
    values: dict[str, Any] = {}
    meta: dict[str, AziendaAutofillFieldMeta] = {}

    def _set(field: str, value: Any, confidence: Confidence, source: str, source_url: str | None = None) -> None:
        if value is None or value == "":
            return
        values[field] = value
        meta[field] = AziendaAutofillFieldMeta(
            confidence=confidence,
            source=source,
            source_url=source_url,
        )

    # 1. VIES — high confidence, deterministic
    if vies and vies.is_valid:
        _set("ragione_sociale", vies.ragione_sociale, "high", "VIES", "https://ec.europa.eu/taxation_customs/vies/")
        _set("sede_legale_via", vies.sede_legale_via, "high", "VIES")
        _set("sede_legale_citta", vies.sede_legale_citta, "high", "VIES")
        _set("cap_legale", vies.cap_legale, "high", "VIES")
        _set("provincia_legale", vies.provincia_legale, "high", "VIES")

    # 1b. openapi.com Registro Imprese — paid, structured visura. We mark
    # high confidence too because it's the official Italian camera di
    # commercio data, with stronger schema guarantees than the snippet
    # parser. VIES already-set fields aren't overwritten (the `_set`
    # helper noops on present keys via the higher priority loop above —
    # but `_set` itself doesn't dedupe, so we check explicitly).
    if openapi_reg:
        _registry_specs: tuple[tuple[str, Any], ...] = (
            ("ragione_sociale", openapi_reg.ragione_sociale),
            ("forma_giuridica", openapi_reg.forma_giuridica),
            ("codice_fiscale", openapi_reg.codice_fiscale),
            ("rea", openapi_reg.rea),
            ("codice_ateco", _normalize_ateco(openapi_reg.codice_ateco)),
            ("data_costituzione", _plausible_data_costituzione(openapi_reg.data_costituzione)),
            ("capitale_sociale", openapi_reg.capitale_sociale),
            ("pec", openapi_reg.pec),
            ("sede_legale_via", openapi_reg.sede_legale_via),
            ("sede_legale_citta", openapi_reg.sede_legale_citta),
            ("cap_legale", _normalize_cap(openapi_reg.cap_legale)),
            ("provincia_legale", _normalize_provincia(openapi_reg.provincia_legale)),
        )
        for field, value in _registry_specs:
            if field in values:
                continue
            _set(field, value, "high", "openapi.com Registro Imprese")
        # Issue #11: unità locali → primary sede operativa + extras list.
        unita = openapi_reg.sedi_operative or []
        if unita:
            primary = unita[0]
            for field, key in (
                ("sede_operativa_via", "via"),
                ("sede_operativa_citta", "citta"),
                ("cap_operativa", "cap"),
                ("provincia_operativa", "provincia"),
            ):
                if field in values:
                    continue
                v = primary.get(key)
                if field == "cap_operativa":
                    v = _normalize_cap(v)
                elif field == "provincia_operativa":
                    v = _normalize_provincia(v)
                _set(field, v, "high", "openapi.com Registro Imprese")
            if len(unita) > 1:
                # The frontend's autofill merger ignores keys not in
                # AziendaFormState, but the create payload now accepts
                # sedi_operative_extra — surface it so the operator's
                # subsequent submit carries them. Confidence stays high
                # because each entry came from the registry.
                extras = [s for s in unita[1:] if any(s.values())]
                if extras:
                    values["sedi_operative_extra"] = extras  # type: ignore[assignment]
                    meta["sedi_operative_extra"] = AziendaAutofillFieldMeta(
                        confidence="high",
                        source="openapi.com Registro Imprese",
                    )

    # 2. Deterministic snippet extractors — medium confidence, but the
    # fields are explicit "Field: value" matches in registry-formatted
    # text, so they're far more reliable than AI inference. Each has the
    # source URL of the snippet it came from for the verify-tooltip.
    _ext_specs: tuple[tuple[str, Any, str], ...] = (
        ("codice_ateco", facts.codice_ateco, "Registro Imprese (snippet)"),
        ("rea", facts.rea, "Registro Imprese (snippet)"),
        ("pec", facts.pec, "Registro Imprese (snippet)"),
        ("codice_fiscale", facts.codice_fiscale, "Registro Imprese (snippet)"),
        ("capitale_sociale", facts.capitale_sociale, "Registro Imprese (snippet)"),
        ("forma_giuridica", facts.forma_giuridica, "Registro Imprese (snippet)"),
        ("sito_web", facts.sito_web, "Registro Imprese (snippet)"),
        ("telefono", facts.telefono, "Registro Imprese (snippet)"),
    )
    for field, value, source in _ext_specs:
        if field in values:
            continue
        _set(field, value, "medium", source, source_url_for(facts, field, serper))

    # 2. AI consolidator — medium confidence (snippet-derived) or low (markdown-derived)
    if consolidated:
        # Field name -> (source label, default confidence)
        ai_fields: dict[str, tuple[str, Confidence]] = {
            "ragione_sociale": ("Google + AI", "medium"),
            "codice_fiscale": ("Google + AI", "medium"),
            "forma_giuridica": ("Google + AI", "medium"),
            "sede_legale_via": ("Google + AI", "medium"),
            "sede_legale_citta": ("Google + AI", "medium"),
            "cap_legale": ("Google + AI", "medium"),
            "provincia_legale": ("Google + AI", "medium"),
            "sede_operativa_via": ("Google + AI", "medium"),
            "sede_operativa_citta": ("Google + AI", "medium"),
            "cap_operativa": ("Google + AI", "medium"),
            "provincia_operativa": ("Google + AI", "medium"),
            "codice_ateco": ("Google + AI", "medium"),
            "attivita": ("AI da sito aziendale", "low"),
            "pec": ("Google + AI", "medium"),
            "email": ("Sito aziendale", "low"),
            "telefono": ("Sito aziendale", "low"),
            "sito_web": ("Google", "high"),
            "numero_dipendenti_dichiarati": ("AI da sito aziendale", "low"),
            "capitale_sociale": ("Google + AI", "medium"),
            "rea": ("Google + AI", "medium"),
            "data_costituzione": ("Google + AI", "medium"),
        }
        consolidated_dict = consolidated.model_dump()
        # Light normalisation on a few formatting-sensitive fields
        consolidated_dict["codice_ateco"] = _normalize_ateco(consolidated_dict.get("codice_ateco"))
        consolidated_dict["provincia_legale"] = _normalize_provincia(consolidated_dict.get("provincia_legale"))
        consolidated_dict["provincia_operativa"] = _normalize_provincia(consolidated_dict.get("provincia_operativa"))
        consolidated_dict["cap_legale"] = _normalize_cap(consolidated_dict.get("cap_legale"))
        consolidated_dict["cap_operativa"] = _normalize_cap(consolidated_dict.get("cap_operativa"))
        consolidated_dict["data_costituzione"] = _plausible_data_costituzione(
            consolidated_dict.get("data_costituzione")
        )
        for field, (source, conf) in ai_fields.items():
            if field in values:
                continue  # VIES already supplied this
            value = consolidated_dict.get(field)
            if value is None or value == "":
                continue
            # Date fields need ISO string for the JSON response
            if field == "data_costituzione" and hasattr(value, "isoformat"):
                value = value.isoformat()
            _set(field, value, conf, source)

    # 3. Heuristic: if we found a homepage but the AI didn't surface
    # sito_web, fall back to it. The AI sometimes drops obvious URLs.
    if "sito_web" not in values and homepage_url:
        _set(
            "sito_web",
            homepage_url.rstrip("/"),
            "medium",
            "Google (primo risultato)",
            homepage_url,
        )

    return AziendaAutofillResponse(
        partita_iva=partita_iva,
        values=values,
        meta=meta,
        warnings=warnings,
    )


async def autofill_from_piva(partita_iva: str) -> AziendaAutofillResponse:
    """Run the full autofill pipeline for a P.IVA.

    Soft-fails per source: if VIES is down or Serper has no key, the
    response still comes back with whatever the working sources produced.
    Only catastrophic failures (e.g. AI consolidator returns nothing
    *and* no source produced data) raise.
    """
    warnings: list[str] = []

    # Run VIES + Serper + openapi.com (paid Registro Imprese) concurrently —
    # they don't depend on each other. openapi.com is the paid upgrade
    # operators asked for in feedback #6 (2026-05-14): structured visura
    # with REA/ATECO/sede + unità locali, vs the snippet-derived data we
    # used before. Soft-fails when ``OPENAPI_API_KEY`` is unset.
    vies_task = asyncio.create_task(lookup_vies(partita_iva))
    serper_task = asyncio.create_task(search_piva(partita_iva))
    openapi_task = asyncio.create_task(lookup_openapi_registry(partita_iva))
    vies, serper, openapi_reg = await asyncio.gather(
        vies_task, serper_task, openapi_task
    )

    if vies is None:
        warnings.append("VIES non disponibile.")
    elif not vies.is_valid:
        warnings.append("VIES: P.IVA non valida o non registrata.")

    if not serper:
        warnings.append("Ricerca Google non disponibile (Serper key mancante o errore).")

    if openapi_reg is None:
        # Only warn when the key was configured (a transport / auth
        # failure). Missing key is the expected dev / sandbox state — the
        # source is just opted out, no UI noise needed.
        if settings.OPENAPI_API_KEY:
            warnings.append("openapi.com Registro Imprese non disponibile.")

    # Deterministic snippet extraction (no network, no AI). These are
    # the "Field: value" hits from registry snippets — ATECO, REA, PEC,
    # capitale, forma giuridica, etc. Treated as ground truth alongside
    # VIES.
    facts = extract_from_snippets(serper)

    # Prefer the snippet-extracted sito_web if we got one — it points
    # straight at the company's own site (registry pages list it
    # explicitly), bypassing the homepage-pick heuristic.
    homepage_url = facts.sito_web or _pick_homepage(serper, partita_iva)
    firecrawl_scrape = await scrape_site(homepage_url) if homepage_url else None
    if homepage_url and firecrawl_scrape is None:
        warnings.append(f"Scrape del sito {homepage_url} non riuscito.")

    # Run the AI consolidator over whatever we have.
    consolidated: ConsolidatedAzienda | None = None
    try:
        consolidated = await consolidate(
            partita_iva=partita_iva,
            vies=vies,
            facts=facts,
            serper_results=serper,
            firecrawl_scrape=firecrawl_scrape,
        )
    except AIError as exc:
        logger.warning("Autofill AI consolidator failed for %s: %s", partita_iva, exc)
        warnings.append(f"AI non disponibile: {exc}")

    response = _build_response(
        partita_iva=partita_iva,
        vies=vies,
        openapi_reg=openapi_reg,
        serper=serper,
        facts=facts,
        homepage_url=homepage_url,
        consolidated=consolidated,
        warnings=warnings,
    )

    # Catastrophic case: nothing came back from any source.
    if not response.values:
        raise AIError(
            "Nessun dato trovato per questa P.IVA. Verifica il numero o "
            "compila il modulo manualmente."
        )

    return response
