"""Firecrawl — scrape the company website for descrizione + contacts.

Given a candidate company URL (typically the homepage discovered by the
Serper step), Firecrawl returns clean Markdown of the page. We don't do
fancy schema-extraction here — extracting structured fields from a
homepage is hit-or-miss across templates, so we just hand the Markdown
to the AI consolidator alongside the Serper snippets.

API: https://docs.firecrawl.dev/api-reference/endpoint/scrape
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"

# Cap the markdown we forward to the AI. A typical homepage is 2-15 KB; we
# truncate at 8 KB to keep token cost predictable while still catching
# footers (where PEC/email/telefono usually live).
_MAX_MARKDOWN_CHARS = 8_000


@dataclass(frozen=True)
class FirecrawlScrape:
    url: str
    markdown: str


async def scrape_site(url: str) -> FirecrawlScrape | None:
    """Scrape a URL with Firecrawl. Returns None on missing key / failure.

    The URL is taken as-is — no protocol normalisation. Pass the canonical
    homepage discovered by the Serper step, or skip the call if Serper
    didn't find a domain.
    """
    if not settings.FIRECRAWL_API_KEY:
        logger.info("FIRECRAWL_API_KEY not set — skipping site scrape")
        return None
    if not url:
        return None

    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
        # Block images/scripts to keep latency low — we only need text.
        "blockAds": True,
    }
    headers = {
        "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.AZIENDA_AUTOFILL_TIMEOUT_SECONDS) as client:
            response = await client.post(FIRECRAWL_SCRAPE_URL, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("Firecrawl scrape failed for %s: %s", url, exc)
        return None

    if response.status_code != 200:
        logger.warning("Firecrawl returned %d for %s", response.status_code, url)
        return None

    try:
        data = response.json()
    except ValueError:
        logger.warning("Firecrawl returned non-JSON for %s", url)
        return None

    # Firecrawl v1 wraps the result under "data".
    result = data.get("data") or {}
    markdown = (result.get("markdown") or "").strip()
    if not markdown:
        return None
    if len(markdown) > _MAX_MARKDOWN_CHARS:
        markdown = markdown[:_MAX_MARKDOWN_CHARS] + "\n\n[...troncato]"
    return FirecrawlScrape(url=url, markdown=markdown)
