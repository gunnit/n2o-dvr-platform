from fastapi import APIRouter, HTTPException

from app.data.niosh_cp import get_default_cp
from app.schemas.calculation import (
    FireRiskRequest,
    FireRiskResponse,
    NioshCpResponse,
    NioshRequest,
    NioshResponse,
    PhsRequest,
    PhsResponse,
    PmvPpdRequest,
    PmvPpdResponse,
    RiskIndexRequest,
    RiskIndexResponse,
    StressAssessmentRequest,
    StressAssessmentResponse,
    StressIndicatorsResponse,
    VdtAssessmentRequest,
    VdtAssessmentResponse,
    VdtWorkerResult,
)
from app.services.microclima_calculator import calculate_phs, calculate_pmv_ppd
from app.services.risk_calculator import calculate_fire_risk
from app.services.stress_calculator import (
    INDICATORS as STRESS_INDICATORS,
    calculate_stress,
    get_default_measures,
)
from app.services.vdt_calculator import (
    classify_exposure,
    requires_health_surveillance,
)

router = APIRouter(prefix="/calculate", tags=["calculations"])


def _risk_level(indice: int) -> str:
    """Return risk level label based on index I = 2*D + P."""
    if indice <= 4:
        return "ACCETTABILE"
    if indice <= 6:
        return "MODESTO"
    if indice <= 8:
        return "GRAVE"
    return "GRAVISSIMO"


def _niosh_level(ir: float) -> str:
    """Return NIOSH risk level based on the lifting index IR."""
    if ir <= 0.75:
        return "GREEN"
    if ir <= 1.0:
        return "YELLOW"
    return "RED"


@router.post("/risk-index", response_model=RiskIndexResponse)
async def calculate_risk_index(body: RiskIndexRequest):
    """Calculate risk index I = 2*D + P and return level.

    Range 3-12:
      3-4 = ACCETTABILE
      5-6 = MODESTO
      7-8 = GRAVE
      9-12 = GRAVISSIMO
    """
    indice = 2 * body.danno_d + body.probabilita_p
    return RiskIndexResponse(
        probabilita_p=body.probabilita_p,
        danno_d=body.danno_d,
        indice_i=indice,
        livello_rischio=_risk_level(indice),
    )


@router.post("/niosh", response_model=NioshResponse)
async def calculate_niosh(body: NioshRequest):
    """Calculate NIOSH PLR and Lifting Index (IR).

    PLR = CP x A x B x C x D x E x F
    IR  = Peso Sollevato / PLR

    Levels:
      IR <= 0.75 = GREEN (acceptable)
      0.75 < IR <= 1.0 = YELLOW (borderline)
      IR > 1.0 = RED (risk)
    """
    plr = (
        body.cp
        * body.fattore_a
        * body.fattore_b
        * body.fattore_c
        * body.fattore_d
        * body.fattore_e
        * body.fattore_f
    )

    ir = body.peso_sollevato / plr if plr > 0 else float("inf")

    return NioshResponse(
        plr=round(plr, 4),
        ir=round(ir, 4),
        livello=_niosh_level(ir),
    )


@router.get("/stress/indicators", response_model=StressIndicatorsResponse)
async def list_stress_indicators():
    """Return the full INAIL stress indicator catalog.

    The frontend uses this to render the checklist. Each indicator carries
    its area (A, B1..C4), Italian text, scoring mode, and an operator note.
    """
    return StressIndicatorsResponse(indicators=list(STRESS_INDICATORS))


@router.post("/stress", response_model=StressAssessmentResponse)
async def calculate_stress_assessment(body: StressAssessmentRequest):
    """Score an INAIL stress lavoro-correlato assessment.

    Returns per-area sub-totals, area totals, overall band (BASSO/MEDIO/ALTO),
    the recommended action text, and a suggested list of corrective measures.
    Unanswered indicator ids are reported so the caller can flag incomplete
    assessments without blocking the computation.
    """
    result = calculate_stress(body.answers)
    misure = get_default_measures(result["livello"])
    return StressAssessmentResponse(**result, misure=misure)


_FIRE_AZIONE = {
    "Basso": (
        "Rischio incendio basso: mantenere in efficienza le misure di prevenzione e "
        "protezione esistenti, verificare periodicamente estintori, vie di esodo e "
        "segnaletica, e aggiornare la formazione antincendio del personale."
    ),
    "Medio": (
        "Rischio incendio medio: adottare misure aggiuntive di prevenzione e protezione "
        "(rilevazione automatica, compartimentazione, controllo sorgenti di innesco), "
        "designare e formare gli addetti alla gestione dell'emergenza e aggiornare il "
        "piano di emergenza ed evacuazione."
    ),
    "Alto": (
        "Rischio incendio alto: attivare immediatamente misure straordinarie di prevenzione "
        "e protezione, coinvolgere il professionista antincendio, presentare SCIA ai VV.F. "
        "ove dovuta, adottare impianti di rilevazione e spegnimento automatici e garantire "
        "formazione di livello 3 agli addetti all'emergenza."
    ),
}


@router.post("/fire-risk", response_model=FireRiskResponse)
async def calculate_fire_risk_endpoint(body: FireRiskRequest):
    """Calculate composite fire risk level (D.M. 03/09/2021).

    Formula: Livello = INF + SI + PI, where each component is scored 1-3.

    Parameters:
      - INF: Infiammabilita (flammability of substances present)
      - SI:  Sorgenti di Innesco (ignition sources)
      - PI:  Propagazione Incendio (fire propagation likelihood)

    Bands:
      3-4 = Basso
      5-7 = Medio
      8-9 = Alto

    Returns per-component scores, total, risk level, and the recommended
    action text in Italian for the level.
    """
    result = calculate_fire_risk(body.inf, body.si, body.pi)
    azione = _FIRE_AZIONE.get(result["livello"], "")
    return FireRiskResponse(**result, azione=azione)


@router.post("/vdt", response_model=VdtAssessmentResponse)
async def calculate_vdt(body: VdtAssessmentRequest):
    """Classify a list of workers by VDT (Videoterminali) exposure.

    Per D.Lgs. 81/2008 Titolo VII (art. 173), a worker who uses a VDT
    >= 20 hours/week is classified as "Esposto" and is subject to
    mandatory sorveglianza sanitaria (eye/sight examination before
    assignment and at intervals set by the medico competente — typically
    5 years, or 2 years for workers over 50).

    For each worker, returns:
      - esposizione: "ESPOSTO" | "NON_ESPOSTO"
      - sorveglianza_sanitaria: bool (True iff ESPOSTO)

    Plus aggregate counts (total, esposti, non_esposti) for the whole group.
    """
    results: list[VdtWorkerResult] = []
    esposti = 0
    for w in body.workers:
        exposure = classify_exposure(w.ore_settimanali)
        surveillance = requires_health_surveillance(exposure)
        if surveillance:
            esposti += 1
        results.append(
            VdtWorkerResult(
                id=w.id,
                nome=w.nome,
                ore_settimanali=w.ore_settimanali,
                esposizione=exposure,
                sorveglianza_sanitaria=surveillance,
            )
        )
    total = len(results)
    return VdtAssessmentResponse(
        workers=results,
        total=total,
        esposti=esposti,
        non_esposti=total - esposti,
    )


@router.post("/microclima/pmv", response_model=PmvPpdResponse)
async def calculate_microclima_pmv(body: PmvPpdRequest):
    """Calculate thermal comfort PMV/PPD per ISO 7730.

    PMV (Predicted Mean Vote) quantifies thermal sensation on a -3..+3 scale.
    PPD (Predicted Percentage of Dissatisfied) is derived from PMV.

    Comfort categories (ISO 7730:2006):
      A: PPD < 6%  and |PMV| < 0.2
      B: PPD < 10% and |PMV| < 0.5
      C: PPD < 15% and |PMV| < 0.7

    A scenario is "compliant" when it meets at least category C. PMV sensation
    labels are returned in Italian per the N2O reporting convention.

    Input ranges enforced by the schema (office-scenario defaults typical):
      air_temp / mean_radiant_temp: 10-40 °C
      air_velocity: 0-2 m/s, humidity: 0-100 %,
      metabolic_rate: 0.7-4.0 met, clothing_insulation: 0-2.0 clo
    """
    return PmvPpdResponse(
        **calculate_pmv_ppd(
            air_temp=body.air_temp,
            mean_radiant_temp=body.mean_radiant_temp,
            air_velocity=body.air_velocity,
            humidity=body.humidity,
            metabolic_rate=body.metabolic_rate,
            clothing_insulation=body.clothing_insulation,
        )
    )


@router.post("/microclima/phs", response_model=PhsResponse)
async def calculate_microclima_phs(body: PhsRequest):
    """Calculate Predicted Heat Strain (PHS) per ISO 7933:2023.

    Intended for severe heat exposure (foundries, summer construction sites,
    bakeries, glass/steel works, etc.). Predicts final rectal temperature
    and maximum allowable exposure time (Dlim) under three constraints:

      - d_lim_t_re: limited by core temperature rise (heat accumulation)
      - d_lim_loss_50: limited by cumulative dehydration (mean worker)
      - d_lim_loss_95: limited by cumulative dehydration (95th percentile)

    The binding limit `d_lim` is the minimum of the three. Levels:
      - ACCETTABILE: d_lim >= duration_min (full shift tolerable)
      - LIMITE: 60 <= d_lim < duration_min (reduced exposure required)
      - CRITICO: d_lim < 60 (intervention required)

    Posture options: "sitting" | "standing" | "crouching".
    Input ranges: tdb 15-50, tr 15-60, v 0-3 m/s, met 1.0-7.5, clo 0.1-1.0.
    """
    return PhsResponse(
        **calculate_phs(
            air_temp=body.air_temp,
            mean_radiant_temp=body.mean_radiant_temp,
            air_velocity=body.air_velocity,
            humidity=body.humidity,
            metabolic_rate=body.metabolic_rate,
            clothing_insulation=body.clothing_insulation,
            posture=body.posture,
            acclimatized=body.acclimatized,
            drink_free=body.drink_free,
            duration_min=body.duration_min,
        )
    )


@router.get("/niosh-cp", response_model=NioshCpResponse)
async def niosh_cp(sesso: str, eta: int) -> NioshCpResponse:
    """Return the default NIOSH weight constant for a worker's sex+age.

    Age bands: giovane (15-17), adulto (18-45), anziano (>45).
    Per D.Lgs. 81/2008 Allegato XXXIII and ISO 11228-1.
    """
    try:
        cp = get_default_cp(sesso, eta)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if eta <= 17:
        fascia = "giovane"
    elif eta <= 45:
        fascia = "adulto"
    else:
        fascia = "anziano"
    return NioshCpResponse(cp=cp, sesso=sesso, eta=eta, fascia=fascia)  # type: ignore[arg-type]
