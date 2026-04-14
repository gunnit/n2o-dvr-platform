from fastapi import APIRouter

from app.schemas.calculation import (
    FireRiskRequest,
    FireRiskResponse,
    NioshRequest,
    NioshResponse,
    RiskIndexRequest,
    RiskIndexResponse,
    StressAssessmentRequest,
    StressAssessmentResponse,
    StressIndicatorsResponse,
)
from app.services.risk_calculator import calculate_fire_risk
from app.services.stress_calculator import (
    INDICATORS as STRESS_INDICATORS,
    calculate_stress,
    get_default_measures,
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
