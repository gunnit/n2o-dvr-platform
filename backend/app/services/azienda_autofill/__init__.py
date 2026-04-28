"""Azienda autofill — derive an Azienda payload from a P.IVA.

Public surface is ``autofill_from_piva`` which orchestrates the four
data sources (VIES, Serper, Firecrawl, AI consolidator) and returns an
``AziendaAutofillResponse`` ready for the frontend.

Privacy contract (CLAUDE.md):
  - VIES, Serper queries, Firecrawl scrapes are all PUBLIC company data.
    No PII (codice fiscale of natural persons, identity docs, health data)
    is sent or returned by this pipeline.
  - The AI consolidator only sees public web data — same privacy posture
    as the existing visura snippet flow.
"""

from app.services.azienda_autofill.pipeline import autofill_from_piva

__all__ = ["autofill_from_piva"]
