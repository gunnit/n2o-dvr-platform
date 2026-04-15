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
