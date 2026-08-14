"""Unit tests for the DUVRI rischi-interferenziali AI suggester.

The OpenAI client is mocked at the module seam (``generate_structured``),
so these pin the *contract*: what context reaches the model, and how the
raw response is post-validated before the operator sees it.
"""

from __future__ import annotations

import pytest

from app.services.ai import duvri_interferenze_suggester as mod
from app.services.ai.duvri_interferenze_suggester import (
    InterferenzaSuggerita,
    InterferenzeSuggerite,
    suggest_interferenze,
)


def _canned_response(items: list[InterferenzaSuggerita]) -> InterferenzeSuggerite:
    return InterferenzeSuggerite(items=items, sintesi="Quadro di sintesi.")


def _item(**overrides) -> InterferenzaSuggerita:
    base = dict(
        titolo="Rumore verso aree adiacenti",
        rischio="Esposizione del personale del committente al rumore delle lavorazioni.",
        misure="Sfasamento orario delle lavorazioni rumorose; informare il personale.",
        dpi=["Otoprotettori"],
        riferimento="D.Lgs. 81/2008 art. 26",
    )
    base.update(overrides)
    return InterferenzaSuggerita(**base)


@pytest.mark.asyncio
async def test_prompt_carries_work_context_and_exclusions(monkeypatch):
    """Equipment labels, oggetto, luoghi, existing risks and fired static
    rules must all reach the model — and nothing else does (PII contract:
    the signature has no slot for names or fiscal ids)."""
    captured: dict = {}

    async def fake_generate_structured(prompt, *, schema, system, reasoning_effort):
        captured["prompt"] = prompt
        captured["system"] = system
        captured["schema"] = schema
        captured["reasoning_effort"] = reasoning_effort
        return _canned_response([_item()])

    monkeypatch.setattr(mod, "generate_structured", fake_generate_structured)

    result = await suggest_interferenze(
        oggetto_appalto="Rifacimento copertura capannone",
        attrezzature=[("ponteggio", None), ("saldatrice", "saldatrice a filo")],
        luoghi=["Capannone produttivo (tipo: produzione)"],
        interferenze_esistenti=["Caduta di materiali da ponteggio"],
        regole_standard_attive=[
            "Innesco di incendio da saldatura: Saldatura ad arco o a gas..."
        ],
    )

    prompt = captured["prompt"]
    # Equipment codes are humanized with the same labels the operator saw.
    assert "Ponteggio" in prompt
    assert "Saldatrice" in prompt
    assert "saldatrice a filo" in prompt
    assert "Rifacimento copertura capannone" in prompt
    assert "Capannone produttivo" in prompt
    # Both exclusion lists are present so the AI complements, not duplicates.
    assert "Caduta di materiali da ponteggio" in prompt
    assert "Innesco di incendio da saldatura" in prompt
    assert "non riproporle" in prompt

    # The suggester is a DUVRI/art.26 specialist at the shared tier.
    assert "art. 26" in captured["system"]
    assert captured["schema"] is InterferenzeSuggerite
    assert captured["reasoning_effort"] == "low"

    assert len(result.items) == 1
    assert result.sintesi == "Quadro di sintesi."


@pytest.mark.asyncio
async def test_duplicates_of_existing_risks_are_dropped(monkeypatch):
    """A suggestion whose rischio matches an already-identified one
    (modulo case/whitespace) never reaches the operator."""

    async def fake_generate_structured(prompt, **_kwargs):
        return _canned_response(
            [
                _item(rischio="  investimento PEDONI da  muletto "),
                _item(
                    titolo="Viabilità di cantiere",
                    rischio="Interferenza dei mezzi in ingresso con la viabilita del committente.",
                ),
            ]
        )

    monkeypatch.setattr(mod, "generate_structured", fake_generate_structured)

    result = await suggest_interferenze(
        oggetto_appalto=None,
        attrezzature=[("muletto", None)],
        luoghi=[],
        interferenze_esistenti=["Investimento pedoni da muletto"],
        regole_standard_attive=[],
    )

    assert len(result.items) == 1
    assert result.items[0].titolo == "Viabilità di cantiere"


@pytest.mark.asyncio
async def test_output_is_clamped_to_interferenza_item_limits(monkeypatch):
    """rischio/misure are truncated to the InterferenzaItem schema limits
    (500/2000) and blank DPI entries dropped, so an accepted suggestion
    always passes validation on the DUVRI save path."""

    async def fake_generate_structured(prompt, **_kwargs):
        return _canned_response(
            [
                _item(
                    rischio="R" * 600,
                    misure="M" * 2500,
                    dpi=["Casco", "  ", ""],
                )
            ]
        )

    monkeypatch.setattr(mod, "generate_structured", fake_generate_structured)

    result = await suggest_interferenze(
        oggetto_appalto="Manutenzione impianti",
        attrezzature=[("attrezzature_elettriche_portatili", None)],
        luoghi=[],
        interferenze_esistenti=[],
        regole_standard_attive=[],
    )

    item = result.items[0]
    assert len(item.rischio) == 500
    assert len(item.misure) == 2000
    assert item.dpi == ["Casco"]


@pytest.mark.asyncio
async def test_item_count_is_capped(monkeypatch):
    """An over-eager model response is capped at 8 suggestions."""

    async def fake_generate_structured(prompt, **_kwargs):
        return _canned_response(
            [_item(rischio=f"Rischio interferenziale numero {i}") for i in range(12)]
        )

    monkeypatch.setattr(mod, "generate_structured", fake_generate_structured)

    result = await suggest_interferenze(
        oggetto_appalto=None,
        attrezzature=[("demolizioni", None)],
        luoghi=[],
        interferenze_esistenti=[],
        regole_standard_attive=[],
    )

    assert len(result.items) == 8


def test_equipment_labels_cover_the_static_catalog():
    """Every canonical contractor equipment code has an Italian label, so
    the model never reads a raw snake_case code for a catalog chip."""
    from app.data.duvri_interference_rules import CONTRACTOR_EQUIPMENT_TYPES

    missing = [
        t for t in CONTRACTOR_EQUIPMENT_TYPES if t not in mod.EQUIPMENT_LABELS
    ]
    assert not missing, f"labels missing for: {missing}"
