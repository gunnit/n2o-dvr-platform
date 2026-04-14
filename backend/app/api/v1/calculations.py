from fastapi import APIRouter

from app.schemas.calculation import NioshRequest, NioshResponse, RiskIndexRequest, RiskIndexResponse

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
