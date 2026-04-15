"""Unit tests for calculation services.

Reference values from docs/context/FORMULAS_AND_CALCULATIONS.md.
"""

from app.services.risk_calculator import (
    calculate_fire_risk,
    calculate_niosh,
    calculate_risk_index,
)


def test_risk_index_formula():
    # I = 2*D + P
    r = calculate_risk_index(p=1, d=1)
    assert r["indice_i"] == 3
    assert r["livello_rischio"] == "ACCETTABILE"

    r = calculate_risk_index(p=2, d=2)
    assert r["indice_i"] == 6
    assert r["livello_rischio"] == "MODESTO"

    r = calculate_risk_index(p=4, d=4)
    assert r["indice_i"] == 12
    assert r["livello_rischio"] == "GRAVISSIMO"


def test_risk_index_boundaries():
    # 4 -> ACCETTABILE, 5 -> MODESTO
    r = calculate_risk_index(p=2, d=1)  # 2*1 + 2 = 4
    assert r["livello_rischio"] == "ACCETTABILE"
    r = calculate_risk_index(p=1, d=2)  # 2*2 + 1 = 5
    assert r["livello_rischio"] == "MODESTO"
    # 8 -> GRAVE, 9 -> GRAVISSIMO
    r = calculate_risk_index(p=4, d=2)  # 2*2 + 4 = 8
    assert r["livello_rischio"] == "GRAVE"
    r = calculate_risk_index(p=3, d=3)  # 2*3 + 3 = 9
    assert r["livello_rischio"] == "GRAVISSIMO"


def test_niosh_plr_and_ir():
    r = calculate_niosh(cp=25, a=1.0, b=1.0, c=1.0, d=1.0, e=1.0, f=1.0, peso_reale=10)
    assert r["plr"] == 25.0
    assert r["ir"] == 0.4
    assert r["area_rischio"] == "VERDE"


def test_niosh_red_zone():
    r = calculate_niosh(cp=25, a=0.8, b=0.8, c=0.8, d=0.8, e=0.8, f=0.8, peso_reale=20)
    assert r["area_rischio"] in ("GIALLA", "ROSSA")


def test_fire_risk_low():
    r = calculate_fire_risk(1, 1, 1)
    assert r["totale"] == 3 and r["livello"] == "Basso"


def test_fire_risk_medium():
    r = calculate_fire_risk(2, 2, 2)
    assert r["totale"] == 6 and r["livello"] == "Medio"


def test_fire_risk_high():
    r = calculate_fire_risk(3, 3, 3)
    assert r["totale"] == 9 and r["livello"] == "Alto"


def test_fire_risk_validates_range():
    import pytest
    with pytest.raises(ValueError):
        calculate_fire_risk(0, 1, 1)
    with pytest.raises(ValueError):
        calculate_fire_risk(4, 1, 1)


# ---------------------------------------------------------------------------
# NIOSH CP lookup (Agent A1 — MMC, US-3.2)
# ---------------------------------------------------------------------------


from app.data.niosh_cp import get_default_cp


def test_niosh_cp_male_adult():
    assert get_default_cp("M", 30) == 25


def test_niosh_cp_male_young():
    assert get_default_cp("M", 17) == 20


def test_niosh_cp_male_senior():
    assert get_default_cp("M", 50) == 20


def test_niosh_cp_female_adult():
    assert get_default_cp("F", 30) == 20


def test_niosh_cp_female_young():
    assert get_default_cp("F", 16) == 15


def test_niosh_cp_female_senior():
    assert get_default_cp("F", 55) == 15


def test_niosh_cp_invalid_sex():
    import pytest
    with pytest.raises(ValueError):
        get_default_cp("X", 30)


def test_niosh_cp_negative_age():
    import pytest
    with pytest.raises(ValueError):
        get_default_cp("M", -1)


def test_niosh_cp_endpoint_happy():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/calculate/niosh-cp", params={"sesso": "M", "eta": 30})
    assert r.status_code == 200
    body = r.json()
    assert body["cp"] == 25
    assert body["fascia"] == "adulto"


def test_niosh_cp_endpoint_female_young():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/calculate/niosh-cp", params={"sesso": "F", "eta": 16})
    assert r.status_code == 200
    body = r.json()
    assert body["cp"] == 15
    assert body["fascia"] == "giovane"


def test_niosh_cp_endpoint_rejects_bad_sex():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/calculate/niosh-cp", params={"sesso": "Z", "eta": 30})
    assert r.status_code == 422


def test_niosh_cp_endpoint_rejects_bad_age():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/calculate/niosh-cp", params={"sesso": "M", "eta": 10})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Fire measures lookup (Agent A2 — Incendio, US-3.11/3.12)
# Source: D.M. 03/09/2021, D.Lgs. 81/2008 art. 46.
# ---------------------------------------------------------------------------


from app.data.fire_measures import get_measures_for_level


def test_fire_measures_basso_has_min_3():
    measures = get_measures_for_level("Basso")
    assert len(measures) >= 3
    assert all(isinstance(m, str) and len(m) > 10 for m in measures)


def test_fire_measures_medio():
    measures = get_measures_for_level("Medio")
    assert len(measures) >= 3
    assert any(
        "emergenza" in m.lower() or "rilevazione" in m.lower() for m in measures
    )


def test_fire_measures_alto():
    measures = get_measures_for_level("Alto")
    assert len(measures) >= 3
    # VVF reference should appear for Alto
    assert any(
        "vvf" in m.lower() or "vv.f" in m.lower() or "antincendio" in m.lower()
        for m in measures
    )


def test_fire_measures_invalid():
    import pytest
    with pytest.raises(ValueError):
        get_measures_for_level("Estremo")


def test_fire_measures_returns_fresh_copy():
    """Mutating the returned list must not affect subsequent calls."""
    first = get_measures_for_level("Basso")
    first.append("mutated")
    second = get_measures_for_level("Basso")
    assert "mutated" not in second


def test_fire_measures_endpoint():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/calculate/fire-measures", params={"livello": "Alto"})
    assert r.status_code == 200
    body = r.json()
    assert body["livello"] == "Alto"
    assert len(body["misure"]) >= 3


def test_fire_measures_endpoint_invalid():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/calculate/fire-measures", params={"livello": "Estremo"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Biologico sector checklist (Agent A4 — Biologico, US-3.15)
# Source: D.Lgs. 81/2008 Titolo X, Reg. CE 852/2004, ISS guidelines.
# ---------------------------------------------------------------------------


from app.services.document_generator.reference_data_biologico import (
    ALIMENTARE_CHECKLIST,
    ASILO_CHECKLIST,
    DENTISTI_CHECKLIST,
    classify_biologico,
    get_checklist,
)


def test_biologico_checklist_shape_alimentare():
    items = get_checklist("alimentare")
    assert 10 <= len(items) <= 12
    for it in items:
        assert set(it.keys()) >= {"id", "descrizione", "criticita"}
        assert it["criticita"] in {"alta", "media", "bassa"}
    ids = [it["id"] for it in items]
    assert len(ids) == len(set(ids))


def test_biologico_checklist_shape_asilo():
    items = get_checklist("asilo")
    assert 10 <= len(items) <= 12
    assert all(it["id"].startswith("AS.") for it in items)


def test_biologico_checklist_shape_dentisti():
    items = get_checklist("dentisti")
    assert 10 <= len(items) <= 12
    assert all(it["id"].startswith("DE.") for it in items)


def test_biologico_checklist_constants_exposed():
    assert len(ALIMENTARE_CHECKLIST) >= 10
    assert len(ASILO_CHECKLIST) >= 10
    assert len(DENTISTI_CHECKLIST) >= 10


def test_biologico_checklist_unknown_sector():
    import pytest
    with pytest.raises(ValueError):
        get_checklist("aerospaziale")


def test_biologico_checklist_case_insensitive():
    # Accept "ALIMENTARE" / " Alimentare " the same as "alimentare".
    assert get_checklist("ALIMENTARE") == ALIMENTARE_CHECKLIST
    assert get_checklist(" Asilo ") == ASILO_CHECKLIST


def test_biologico_classify_all_si_is_basso():
    risposte = [{"id": it["id"], "risposta": "SI"} for it in ALIMENTARE_CHECKLIST]
    r = classify_biologico("alimentare", risposte)
    assert r["livello"] == "BASSO"
    assert r["no_weight"] == 0
    assert r["unanswered"] == []
    assert r["settore"] == "alimentare"


def test_biologico_classify_all_no_is_alto():
    risposte = [{"id": it["id"], "risposta": "NO"} for it in DENTISTI_CHECKLIST]
    r = classify_biologico("dentisti", risposte)
    assert r["livello"] == "ALTO"
    assert r["ratio"] == 1.0


def test_biologico_classify_na_excludes_from_denominator():
    # All items marked NA -> ratio is 0/0 -> BASSO (ratio 0.0)
    risposte = [{"id": it["id"], "risposta": "NA"} for it in ASILO_CHECKLIST]
    r = classify_biologico("asilo", risposte)
    assert r["max_weight"] == 0
    assert r["no_weight"] == 0
    assert r["ratio"] == 0.0
    assert r["livello"] == "BASSO"


def test_biologico_classify_medio_band():
    catalog = ALIMENTARE_CHECKLIST
    weights = {"alta": 3, "media": 2, "bassa": 1}
    total = sum(weights[it["criticita"]] for it in catalog)
    risposte: list[dict] = []
    accumulated_no = 0
    # Target ratio ~0.25 -> inside the MEDIO band (0.15..0.40)
    target = total * 0.25
    for it in catalog:
        w = weights[it["criticita"]]
        if accumulated_no + w <= target:
            risposte.append({"id": it["id"], "risposta": "NO"})
            accumulated_no += w
        else:
            risposte.append({"id": it["id"], "risposta": "SI"})
    r = classify_biologico("alimentare", risposte)
    assert r["livello"] == "MEDIO", f"expected MEDIO, got {r}"


def test_biologico_classify_high_criticity_alta_drives_alto():
    # NO on every "alta" item + SI on the rest -> ALTO (alta items dominate).
    risposte = []
    for it in DENTISTI_CHECKLIST:
        ans = "NO" if it["criticita"] == "alta" else "SI"
        risposte.append({"id": it["id"], "risposta": ans})
    r = classify_biologico("dentisti", risposte)
    assert r["livello"] == "ALTO"


def test_biologico_classify_unanswered_items_tracked():
    risposte = [{"id": ASILO_CHECKLIST[0]["id"], "risposta": "SI"}]
    r = classify_biologico("asilo", risposte)
    assert len(r["unanswered"]) == len(ASILO_CHECKLIST) - 1
    assert r["livello"] == "BASSO"


def test_biologico_classify_invalid_answer_ignored():
    risposte = [{"id": ALIMENTARE_CHECKLIST[0]["id"], "risposta": "FORSE"}]
    r = classify_biologico("alimentare", risposte)
    assert ALIMENTARE_CHECKLIST[0]["id"] in r["unanswered"]


def test_biologico_checklist_endpoint_alimentare():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.get(
        "/api/v1/calculate/biologico-checklist", params={"settore": "alimentare"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["settore"] == "alimentare"
    assert 10 <= len(body["items"]) <= 12
    first = body["items"][0]
    assert set(first.keys()) >= {"id", "descrizione", "criticita"}


def test_biologico_checklist_endpoint_asilo():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.get(
        "/api/v1/calculate/biologico-checklist", params={"settore": "asilo"}
    )
    assert r.status_code == 200
    assert r.json()["settore"] == "asilo"


def test_biologico_checklist_endpoint_dentisti():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.get(
        "/api/v1/calculate/biologico-checklist", params={"settore": "dentisti"}
    )
    assert r.status_code == 200
    assert r.json()["settore"] == "dentisti"


def test_biologico_checklist_endpoint_invalid_sector():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.get(
        "/api/v1/calculate/biologico-checklist", params={"settore": "bizantino"}
    )
    assert r.status_code == 422
