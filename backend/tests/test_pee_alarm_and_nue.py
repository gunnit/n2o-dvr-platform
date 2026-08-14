"""PEE client requests (Aug 2026): tipologia di allarme + NUE 112.

1. The plan config gains a "tipologia di allarme" field that round-trips
   through the GET/PUT schemas and prefills a sensible default.
2. Point A of the *incendio* and *evacuazione generale* procedures renders
   the configured alarm type instead of hardcoded wording.
3. All national emergency numbers render as the Numero Unico di Emergenza
   (NUE) 112; company-internal numbers pass through untouched.

These are pure unit tests (no DB): DB-backed round-trips are covered by the
generator tests in test_generators.py via the fixture harness.
"""

import re

from app.data.pee_procedures import (
    DEFAULT_TIPOLOGIA_ALLARME,
    TIPOLOGIA_ALLARME_PLACEHOLDER,
    get_standard_procedure,
    get_standard_procedures,
    merge_with_overrides,
    normalize_emergency_number,
)

LEGACY_RE = re.compile(r"\b(113|115|117|118|1515|1530)\b")


def _proc(events: list[dict], codice: str, lettera: str) -> dict:
    evt = next(e for e in events if e["codice"] == codice)
    return next(p for p in evt["procedure"] if p["lettera"] == lettera)


# ---------------------------------------------------------------------------
# Tipologia di allarme in the standard procedures
# ---------------------------------------------------------------------------


def test_point_a_renders_configured_alarm_for_incendio_and_evacuazione():
    events = merge_with_overrides(None, tipologia_allarme="Tromba da stadio")
    assert "Tromba da stadio" in _proc(events, "incendio", "A")["testo"]
    assert "Tromba da stadio" in _proc(events, "evacuazione_generale", "A")["testo"]


def test_point_a_falls_back_to_default_alarm_and_leaves_no_placeholder():
    for events in (merge_with_overrides(None), merge_with_overrides(None, tipologia_allarme="  ")):
        assert DEFAULT_TIPOLOGIA_ALLARME in _proc(events, "incendio", "A")["testo"]
        assert DEFAULT_TIPOLOGIA_ALLARME in _proc(events, "evacuazione_generale", "A")["testo"]
        for evt in events:
            for p in evt["procedure"]:
                assert TIPOLOGIA_ALLARME_PLACEHOLDER not in p["testo"]


def test_personalized_override_text_is_rendered_verbatim():
    overrides = [
        {
            "codice": "incendio",
            "titolo": "Incendio",
            "procedure": [
                {
                    "lettera": "A",
                    "titolo": "Rilevamento e allarme",
                    "testo": "Testo scritto dall'operatore.",
                    "personalizzata": True,
                }
            ],
        }
    ]
    events = merge_with_overrides(overrides, tipologia_allarme="Campanella")
    proc = _proc(events, "incendio", "A")
    assert proc["testo"] == "Testo scritto dall'operatore."
    assert proc["personalizzata"] is True
    # The other event still gets the substitution.
    assert "Campanella" in _proc(events, "evacuazione_generale", "A")["testo"]


def test_get_standard_procedure_substitutes_alarm_case_insensitive_letter():
    proc = get_standard_procedure("incendio", "a", tipologia_allarme="Sirena bitonale")
    assert proc is not None
    assert "Sirena bitonale" in proc["testo"]


# ---------------------------------------------------------------------------
# NUE 112
# ---------------------------------------------------------------------------


def test_standard_texts_reference_only_nue_112():
    for evt in get_standard_procedures():
        for p in evt["procedure"]:
            assert not LEGACY_RE.search(p["testo"]), (evt["codice"], p["lettera"], p["testo"])
    events = get_standard_procedures()
    for codice in ("incendio", "allagamento", "fuga_gas", "evacuazione_generale", "terremoto"):
        assert "Numero Unico di Emergenza (NUE) 112" in _proc(events, codice, "B")["testo"]


def test_normalize_emergency_number_maps_legacy_numbers_to_112():
    assert normalize_emergency_number("115") == "112"
    assert normalize_emergency_number("118") == "112"
    assert normalize_emergency_number("113") == "112"
    assert normalize_emergency_number("112") == "112"
    assert normalize_emergency_number(" 115 / 118 ") == "112"


def test_normalize_emergency_number_keeps_internal_numbers():
    assert normalize_emergency_number("0521 456789") == "0521 456789"
    assert normalize_emergency_number("+39 0521 000000") == "+39 0521 000000"
    # An internal extension that happens to be 115 is not an emergency number.
    assert normalize_emergency_number("int. 115") == "int. 115"
    assert normalize_emergency_number("") == ""
    assert normalize_emergency_number(None) == ""


# ---------------------------------------------------------------------------
# Plan config schema round-trip (no DB)
# ---------------------------------------------------------------------------


def test_plan_config_round_trips_tipologia_allarme():
    from app.api.v1.pee_procedures import PeePlanConfigBody, _plan_to_response
    from app.models.pee_plan import PeePlan

    assert _plan_to_response(PeePlan(tipologia_allarme="Campanella")).tipologia_allarme == "Campanella"
    # Free text ("Altro") round-trips verbatim.
    assert (
        _plan_to_response(PeePlan(tipologia_allarme="Fischietto del capoturno")).tipologia_allarme
        == "Fischietto del capoturno"
    )
    # Unset column and missing row both prefill the default.
    assert _plan_to_response(PeePlan()).tipologia_allarme == DEFAULT_TIPOLOGIA_ALLARME
    assert _plan_to_response(None).tipologia_allarme == DEFAULT_TIPOLOGIA_ALLARME


def test_plan_config_body_partial_update_semantics():
    from app.api.v1.pee_procedures import PeePlanConfigBody

    body = PeePlanConfigBody(tipologia_allarme="Avviso a voce")
    assert body.model_dump(exclude_unset=True) == {"tipologia_allarme": "Avviso a voce"}
    # Omitted field must not clobber a stored value on PUT.
    assert "tipologia_allarme" not in PeePlanConfigBody().model_dump(exclude_unset=True)
