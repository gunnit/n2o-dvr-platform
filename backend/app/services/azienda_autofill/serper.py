"""Serper.dev — Google search for P.IVA enrichment.

Given an Italian P.IVA, runs ``"P.IVA <piva>"`` on Google and returns the
top-N results (title + snippet + link). Italian company-registry sites
(registroimprese.it, ufficiocamerale.it, paginebianche, telematicocb.it)
typically rank well for these queries and their snippets often contain
the very fields we want — codice ATECO, REA, PEC, sito web, capitale
sociale, forma giuridica.

We don't parse the snippets server-side. The raw snippets are passed to
the AI consolidator (``consolidator.py``) which is much better at
handling the format variation across registry sites than a regex army.

API: https://serper.dev — free tier: 2,500 queries/month, paid is
$0.0003/query. Cheap enough to call on every autofill.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


SERPER_URL = "https://google.serper.dev/search"


@dataclass(frozen=True)
class SerperResult:
    title: str
    snippet: str
    link: str


async def search_piva(partita_iva: str) -> list[SerperResult]:
    """Run a Google search for the P.IVA. Returns [] on missing key / failure.

    The search is biased to Italian results (``gl=it``, ``hl=it``) because
    Italian registry sites are the targets — global results just dilute
    the snippet quality.
    """
    if not settings.SERPER_API_KEY:
        logger.info("SERPER_API_KEY not set — skipping Serper enrichment")
        return []

    payload = {
        "q": f'"P.IVA {partita_iva}" OR "Partita IVA {partita_iva}"',
        "gl": "it",
        "hl": "it",
        "num": 10,
    }
    headers = {
        "X-API-KEY": settings.SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.AZIENDA_AUTOFILL_TIMEOUT_SECONDS) as client:
            response = await client.post(SERPER_URL, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("Serper lookup failed for %s: %s", partita_iva, exc)
        return []

    if response.status_code != 200:
        logger.warning("Serper returned %d for %s", response.status_code, partita_iva)
        return []

    try:
        data = response.json()
    except ValueError:
        logger.warning("Serper returned non-JSON for %s", partita_iva)
        return []

    organic = data.get("organic", []) or []
    results: list[SerperResult] = []
    for item in organic:
        title = (item.get("title") or "").strip()
        snippet = (item.get("snippet") or "").strip()
        link = (item.get("link") or "").strip()
        if not (title or snippet):
            continue
        results.append(SerperResult(title=title, snippet=snippet, link=link))
    return results
