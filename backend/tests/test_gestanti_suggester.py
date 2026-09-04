"""Unit tests for the gestanti per-mansione AI suggester.

Client request (segnalazione 2026-08-25): "integrare un tasto AI che
riconosce per ogni mansione i rischi a cui è sottoposta una lavoratrice
gestante e mi va a introdurre delle limitazioni [...] o mi definisce la
lavoratrice non compatibile con la mansione."

The OpenAI client is mocked at the module seam (``generate_structured``),
so these pin the *contract*, following test_duvri_interferenze_suggester:

 1. Privacy — the prompt is built from the mansione, the azienda's
    activity, the assessed hazards and the equipment. A persona's name and
    codice fiscale, the azienda's own codice fiscale and a pregnancy date
    never reach the model even when they are reachable from the objects
    the builder is handed.
 2. Server-side validation — unknown catalog keys are dropped, duplicates
    collapsed, blank lines removed.
 3. Response model — the esito is one of the three per-mansione esiti and
    nothing else; extra fields are rejected.
 4. Endpoint shape — POST /gestanti/mansioni/suggerisci exists, sits before
    the /gestanti/{valutazione_id} routes, is gated on ASSESSMENTS_WRITE
    and meters the AI call (the same structural checks
    test_billing_enforcement / test_permissions apply elsewhere).
"""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import get_args

import pytest
from pydantic import ValidationError

from app.data.dlgs_151_2001 import INCOMPATIBLE_RISKS
from app.schemas.gestanti import EsitoMansione, GestantiMansioneSuggestRequest
from app.services.ai import gestanti_suggester as mod
from app.services.ai.gestanti_suggester import (
    SYSTEM_PROMPT,
    GestantiMansioneSuggerita,
    PericoloContesto,
    build_context,
    build_prompt,
    sanitize_rischi_keys,
    sanitize_suggestion,
    suggest_gestanti_mansione,
)

BACKEND = Path(__file__).resolve().parents[1]
GESTANTI_ROUTER = BACKEND / "app" / "api" / "v1" / "gestanti.py"

# Deliberately realistic PII so a substring check is meaningful.
PERSONA_NOME = "Maria Rossi"
PERSONA_CF = "RSSMRA85M41H501Z"
AZIENDA_CF = "BNCLCU70A01F205X"
DATA_PARTO = date(2026, 12, 24)


def _fake_azienda():
    """An azienda that *carries* PII the builder must not reach for."""
    persona = SimpleNamespace(
        nominativo=PERSONA_NOME,
        codice_fiscale=PERSONA_CF,
        mansione="Saldatrice",
        sesso="F",
    )
    gestante = SimpleNamespace(
        persona=persona,
        stato="gestante",
        data_presunto_parto=DATA_PARTO,
        data_notifica=date(2026, 5, 3),
    )
    return SimpleNamespace(
        id="azienda-1",
        ragione_sociale=f"Ditta {PERSONA_NOME}",  # ditta individuale: the owner's name
        codice_fiscale=AZIENDA_CF,
        partita_iva="01234567890",
        attivita="Carpenteria metallica",
        codice_ateco="25.11.00",
        descrizione_attivita="Produzione di strutture metalliche saldate",
        persone=[persona],
        gestanti=[gestante],
    )


def _pericoli():
    return [
        PericoloContesto(
            ambiente="Officina",
            categoria="Chimici",
            pericolo="Fumi di saldatura",
            condizioni="Saldatura a filo 4 h/giorno",
            livello="GRAVE",
        ),
        PericoloContesto(
            ambiente="Officina",
            categoria="Fisici",
            pericolo="Rumore da smerigliatura",
            livello="MODESTO",
        ),
    ]


def _attrezzature():
    return [
        SimpleNamespace(descrizione="Saldatrice a filo"),
        SimpleNamespace(descrizione="Smerigliatrice angolare"),
        SimpleNamespace(descrizione="saldatrice a filo"),  # duplicate, case-insensitive
        SimpleNamespace(descrizione="   "),  # blank
    ]


def _suggestion(**overrides) -> GestantiMansioneSuggerita:
    base = dict(
        rischi=["chemical_exposure_cmr", "noise_exposure"],
        rischi_aggiuntivi=[],
        limitazioni=["Esonero dalle operazioni di saldatura"],
        esito_proposto="compatibile_con_limitazioni",
        motivazione="Fumi di saldatura e rumore emergono dal DVR.",
        riferimenti_normativi=["Allegato B D.Lgs. 151/2001"],
    )
    base.update(overrides)
    return GestantiMansioneSuggerita(**base)


# ---------------------------------------------------------------------------
# 1. Privacy — what the prompt carries, and what it must never carry
# ---------------------------------------------------------------------------


def test_context_carries_mansione_activity_hazards_and_equipment():
    text = build_context("Saldatrice", _fake_azienda(), _pericoli(), _attrezzature())
    assert "Mansione da valutare: Saldatrice" in text
    assert "Carpenteria metallica" in text
    assert "25.11.00" in text
    assert "Produzione di strutture metalliche saldate" in text
    assert "[Officina] Chimici: Fumi di saldatura" in text
    assert "Saldatura a filo 4 h/giorno" in text
    assert "livello: GRAVE" in text
    assert "Saldatrice a filo" in text
    assert "Smerigliatrice angolare" in text
    # Duplicates collapse case-insensitively; blanks are skipped.
    assert text.count("aldatrice a filo") == 1


def test_context_contains_no_pii():
    """The builder is handed an azienda that exposes a persona (name + CF),
    a pregnancy row (dates) and its own codice fiscale. None may leak."""
    text = build_context("Saldatrice", _fake_azienda(), _pericoli(), _attrezzature())
    assert PERSONA_NOME not in text
    assert "Rossi" not in text
    assert PERSONA_CF not in text
    assert AZIENDA_CF not in text
    assert "01234567890" not in text
    assert DATA_PARTO.isoformat() not in text
    assert "2026-05-03" not in text
    # The pregnancy row itself (stato) is never described either.
    assert "gestante" not in text.lower()


def test_prompt_contains_catalog_vocabulary_and_no_pii():
    prompt = build_prompt("Saldatrice", _fake_azienda(), _pericoli(), _attrezzature())
    for key, info in INCOMPATIBLE_RISKS.items():
        assert key in prompt
        assert f"(Allegato {info['allegato']})" in prompt
    assert PERSONA_NOME not in prompt
    assert PERSONA_CF not in prompt
    assert AZIENDA_CF not in prompt


def test_context_without_hazards_says_so():
    text = build_context("Impiegata", _fake_azienda(), [], [])
    assert "nessuno disponibile" in text
    assert "nessuna dichiarata" in text


def test_context_caps_hazard_and_equipment_lists():
    many = [
        PericoloContesto(ambiente="A", categoria="C", pericolo=f"p{i}")
        for i in range(mod.MAX_PERICOLI_IN_PROMPT + 5)
    ]
    tools = [
        SimpleNamespace(descrizione=f"attrezzo {i}")
        for i in range(mod.MAX_ATTREZZATURE_IN_PROMPT + 3)
    ]
    text = build_context("Operaia", _fake_azienda(), many, tools)
    assert "altri 5 pericoli omessi" in text
    assert "altre 3 attrezzature omesse" in text


def test_system_prompt_frames_esito_as_a_proposal():
    """Decision from the 2026-09-04 call: the AI only proposes; the RSPP /
    medico competente confirm. The prompt must say so."""
    low = SYSTEM_PROMPT.lower()
    assert "proposta" in low
    assert "rspp" in low
    assert "medico competente" in low
    assert "non_compatibile" in SYSTEM_PROMPT
    assert "151/2001" in SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_suggest_sends_only_the_privacy_safe_prompt(monkeypatch):
    captured: dict = {}

    async def fake_generate_structured(prompt, *, schema, system, reasoning_effort):
        captured["prompt"] = prompt
        captured["schema"] = schema
        captured["system"] = system
        captured["reasoning_effort"] = reasoning_effort
        return _suggestion()

    monkeypatch.setattr(mod, "generate_structured", fake_generate_structured)

    result = await suggest_gestanti_mansione(
        "Saldatrice", _fake_azienda(), _pericoli(), _attrezzature()
    )

    assert captured["schema"] is GestantiMansioneSuggerita
    assert captured["system"] is SYSTEM_PROMPT
    assert captured["reasoning_effort"] == "medium"
    assert PERSONA_NOME not in captured["prompt"]
    assert PERSONA_CF not in captured["prompt"]
    assert "Fumi di saldatura" in captured["prompt"]
    assert result.esito_proposto == "compatibile_con_limitazioni"
    assert result.rischi == ["chemical_exposure_cmr", "noise_exposure"]


# ---------------------------------------------------------------------------
# 2. Server-side validation of the model output
# ---------------------------------------------------------------------------


def test_sanitize_rischi_keys_drops_unknown_and_duplicates():
    keys = [
        "night_shift",
        "lavoro_notturno",  # re-spelled: not a catalog key
        " night_shift ",  # whitespace variant of a key already kept
        "manual_handling_heavy",
        "",
        "NIGHT_SHIFT",  # case matters: keys are exact
    ]
    assert sanitize_rischi_keys(keys) == ["night_shift", "manual_handling_heavy"]


def test_sanitize_rischi_keys_keeps_every_catalog_key():
    assert sanitize_rischi_keys(list(INCOMPATIBLE_RISKS)) == list(INCOMPATIBLE_RISKS)


def test_sanitize_rischi_keys_handles_empty():
    assert sanitize_rischi_keys([]) == []


@pytest.mark.asyncio
async def test_suggest_filters_unknown_keys_and_blank_lines(monkeypatch):
    async def fake_generate_structured(prompt, *, schema, system, reasoning_effort):
        return _suggestion(
            rischi=["prolonged_standing", "made_up_key", "prolonged_standing"],
            rischi_aggiuntivi=["", "  Stress da pubblico  ", "Stress da pubblico"],
            limitazioni=["Postazione seduta", "   "],
            riferimenti_normativi=[" Allegato A lett. G ", ""],
            motivazione="  Proposta.  ",
        )

    monkeypatch.setattr(mod, "generate_structured", fake_generate_structured)
    result = await suggest_gestanti_mansione("Commessa", _fake_azienda(), [], [])

    assert result.rischi == ["prolonged_standing"]
    assert result.rischi_aggiuntivi == ["Stress da pubblico"]
    assert result.limitazioni == ["Postazione seduta"]
    assert result.riferimenti_normativi == ["Allegato A lett. G"]
    assert result.motivazione == "Proposta."


def test_sanitize_suggestion_is_pure():
    raw = _suggestion(rischi=["ionizing_radiation", "nope"])
    cleaned = sanitize_suggestion(raw)
    assert cleaned.rischi == ["ionizing_radiation"]
    assert raw.rischi == ["ionizing_radiation", "nope"]  # input untouched


# ---------------------------------------------------------------------------
# 3. Response model — esito vocabulary and strictness
# ---------------------------------------------------------------------------


def test_response_model_rejects_unknown_esito():
    with pytest.raises(ValidationError):
        _suggestion(esito_proposto="forse")
    with pytest.raises(ValidationError):
        _suggestion(esito_proposto="non compatibile")  # space, not underscore


@pytest.mark.parametrize("esito", get_args(EsitoMansione))
def test_response_model_accepts_every_per_mansione_esito(esito):
    assert _suggestion(esito_proposto=esito).esito_proposto == esito


def test_response_model_esiti_match_the_upsert_vocabulary():
    """The AI proposes exactly the values PUT /gestanti/mansioni accepts, so
    'Applica' can copy esito_proposto into the form verbatim."""
    ai_esiti = set(get_args(GestantiMansioneSuggerita.model_fields["esito_proposto"].annotation))
    assert ai_esiti == set(get_args(EsitoMansione))


def test_response_model_forbids_extra_fields():
    with pytest.raises(ValidationError):
        GestantiMansioneSuggerita(**_suggestion().model_dump(), lavoratrice="x")


def test_suggest_request_normalizes_and_validates_mansione():
    body = GestantiMansioneSuggestRequest(mansione="  Aiuto   cuoco ")
    assert body.mansione == "Aiuto cuoco"
    assert set(GestantiMansioneSuggestRequest.model_fields) == {"mansione"}
    with pytest.raises(ValidationError):
        GestantiMansioneSuggestRequest(mansione=" a ")


# ---------------------------------------------------------------------------
# 4. Endpoint shape — registered, ordered, gated, metered, never persisting
# ---------------------------------------------------------------------------

SUGGEST_PATH = "/aziende/{azienda_id}/gestanti/mansioni/suggerisci"


def test_suggest_route_registered_before_uuid_routes():
    from app.api.v1.gestanti import router
    from tests.conftest import route_pairs

    assert ("POST", SUGGEST_PATH) in route_pairs(router)
    paths = [getattr(r, "path", None) for r in router.routes]
    assert paths.index(SUGGEST_PATH) < paths.index(
        "/aziende/{azienda_id}/gestanti/{valutazione_id}"
    )


def _endpoint_node(name: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(GESTANTI_ROUTER.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    pytest.fail(f"{name} not found in gestanti.py")


def test_suggest_endpoint_is_capability_gated_and_metered():
    node = _endpoint_node("suggerisci_gestanti_mansione")
    # `get_source_segment` covers the body only; the decorator (where the
    # route-level `dependencies=[...]` guard lives) is reached through the
    # AST walk, the way test_permissions reads the same shape.
    src = ast.get_source_segment(GESTANTI_ROUTER.read_text(encoding="utf-8"), node)
    calls = {
        n.func.id
        for n in ast.walk(node)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    assert "require_capability" in calls
    assert "ASSESSMENTS_WRITE" in names
    args = {a.arg for a in node.args.args + node.args.kwonlyargs}
    assert "ent" in args, "the AI endpoint must resolve entitlements per request"
    assert "get_entitlements" in names
    assert "metered" in calls, "the OpenAI call must be charged before it runs"
    assert 'metered(org_id, "reasoning", f"gestanti-mansione:' in src


def test_suggest_endpoint_never_persists():
    """The AI proposes; the operator saves through PUT /gestanti/mansioni."""
    node = _endpoint_node("suggerisci_gestanti_mansione")
    src = ast.get_source_segment(GESTANTI_ROUTER.read_text(encoding="utf-8"), node)
    assert "db.add(" not in src
    assert "db.commit(" not in src  # metered() commits the ledger, the endpoint nothing
    assert "GestantiValutazione" not in src.replace("GestantiMansioneValutazione", "")
