"""Autofill pipeline — what happens when the web sources are gone.

Segnalazione 2026-08-19 ("compila CAP e sede operativa ... molto impreciso")
was filed while Serper was out of credits. With no snippets, no facts and
no homepage the AI consolidator saw VIES alone and guessed the rest. The
pipeline now skips the model in that state and tells the operator which
fields to fill by hand.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.azienda_autofill import pipeline
from app.services.azienda_autofill.consolidator import ConsolidatedAzienda
from app.services.azienda_autofill.serper import SerperResult

PIVA = "01234567890"


def _vies():
    return SimpleNamespace(
        is_valid=True,
        ragione_sociale="ACME SRL",
        sede_legale_via="Via Roma 1",
        sede_legale_citta="Milano",
        cap_legale="20100",
        provincia_legale="MI",
        raw_address=None,
    )


@pytest.fixture
def sources(monkeypatch):
    calls: dict[str, int] = {"consolidate": 0}

    async def fake_vies(_piva):
        return _vies()

    async def fake_openapi(_piva):
        return None

    async def fake_consolidate(**_kwargs):
        calls["consolidate"] += 1
        return ConsolidatedAzienda(cap_operativa="20121", sede_operativa_citta="Milano")

    monkeypatch.setattr(pipeline, "lookup_vies", fake_vies)
    monkeypatch.setattr(pipeline, "lookup_openapi_registry", fake_openapi)
    monkeypatch.setattr(pipeline, "consolidate", fake_consolidate)
    return calls


@pytest.mark.asyncio
async def test_no_web_sources_skips_the_consolidator_and_warns(monkeypatch, sources):
    async def no_serper(_piva):
        return []

    monkeypatch.setattr(pipeline, "search_piva", no_serper)

    response = await pipeline.autofill_from_piva(PIVA)

    assert sources["consolidate"] == 0
    # VIES still lands, with its provenance.
    assert response.values["ragione_sociale"] == "ACME SRL"
    assert response.meta["ragione_sociale"].source == "VIES"
    # Nothing the model would have guessed.
    assert "cap_operativa" not in response.values
    assert "sede_operativa_citta" not in response.values
    assert any("CAP e sede operativa" in w for w in response.warnings)


@pytest.mark.asyncio
async def test_web_sources_present_still_consolidate(monkeypatch, sources):
    async def some_serper(_piva):
        return [SerperResult(title="ACME SRL - P.IVA", snippet="Sede: Milano", link="")]

    async def no_scrape(_url):
        return None

    monkeypatch.setattr(pipeline, "search_piva", some_serper)
    monkeypatch.setattr(pipeline, "scrape_site", no_scrape)

    response = await pipeline.autofill_from_piva(PIVA)

    assert sources["consolidate"] == 1
    assert response.values["cap_operativa"] == "20121"
    assert not any("CAP e sede operativa" in w for w in response.warnings)
