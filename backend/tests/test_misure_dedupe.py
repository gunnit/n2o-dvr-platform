"""Measure de-duplication helpers (segnalazione 2026-08-21)."""

from app.services.misure_dedupe import join_risk_labels, normalize_measure_key


def test_key_ignores_case_accents_punctuation_and_function_words():
    a = normalize_measure_key("Formazione specifica dei lavoratori.")
    b = normalize_measure_key("formazione specifica lavoratori")
    c = normalize_measure_key("FORMAZIONE SPECIFICA DEI LAVORATORI!")
    assert a == b == c == "formazione specifica lavoratori"


def test_key_strips_elided_articles():
    assert normalize_measure_key("Verifica periodica dell'attrezzatura") == (
        "verifica periodica attrezzatura"
    )
    assert normalize_measure_key("Verifica periodica delle attrezzature") != (
        normalize_measure_key("Verifica periodica dell'attrezzatura")
    )


def test_key_keeps_content_words_apart():
    assert normalize_measure_key("Installare aspirazione localizzata") != (
        normalize_measure_key("Installare protezione localizzata")
    )


def test_empty_title_gives_empty_key():
    assert normalize_measure_key(None) == ""
    assert normalize_measure_key("   ") == ""
    assert normalize_measure_key("---") == ""


def test_join_appends_new_label_once():
    joined = join_risk_labels("Cadute dall'alto", "Urti e schiacciamenti")
    assert joined == "Cadute dall'alto; Urti e schiacciamenti"
    again = join_risk_labels(joined, "urti e schiacciamenti")
    assert again == joined


def test_join_handles_empty_sides():
    assert join_risk_labels(None, "Rumore") == "Rumore"
    assert join_risk_labels("Rumore", None) == "Rumore"
    assert join_risk_labels("", "  Rumore   forte ") == "Rumore forte"
    assert join_risk_labels("Rumore; ", "Vibrazioni") == "Rumore; Vibrazioni"
