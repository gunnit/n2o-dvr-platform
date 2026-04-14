from pydantic import BaseModel, Field


class RiskIndexRequest(BaseModel):
    probabilita_p: int = Field(..., ge=1, le=4, description="Probability (1-4)")
    danno_d: int = Field(..., ge=1, le=4, description="Damage severity (1-4)")


class RiskIndexResponse(BaseModel):
    probabilita_p: int
    danno_d: int
    indice_i: int
    livello_rischio: str


class NioshRequest(BaseModel):
    peso_sollevato: float = Field(..., gt=0, description="Actual weight lifted (kg)")
    cp: float = Field(..., gt=0, description="Costante di peso (reference weight, kg)")
    fattore_a: float = Field(..., gt=0, le=1, description="Altezza da terra (height factor)")
    fattore_b: float = Field(..., gt=0, le=1, description="Dislocazione verticale (vertical displacement factor)")
    fattore_c: float = Field(..., gt=0, le=1, description="Distanza orizzontale (horizontal distance factor)")
    fattore_d: float = Field(..., gt=0, le=1, description="Asimmetria (asymmetry factor)")
    fattore_e: float = Field(..., gt=0, le=1, description="Presa (grip factor)")
    fattore_f: float = Field(..., gt=0, le=1, description="Frequenza (frequency factor)")


class NioshResponse(BaseModel):
    plr: float
    ir: float
    livello: str


class StressIndicator(BaseModel):
    id: str
    area: str
    text: str
    scoring: str
    note: str


class StressIndicatorsResponse(BaseModel):
    indicators: list[StressIndicator]


class StressAssessmentRequest(BaseModel):
    answers: dict[str, str] = Field(
        ...,
        description=(
            "Mapping of indicator id to answer. "
            "Expected values: 'DIMINUITO'|'INALTERATO'|'AUMENTATO' for tripartite, "
            "'SI'|'NO' for binary/binary_inverted/binary_heavy."
        ),
    )


class StressSubAreaResult(BaseModel):
    score: int
    max: int
    livello: str


class StressAssessmentResponse(BaseModel):
    area_a_raw: int
    area_a_converted: int
    area_a_livello: str
    sub_areas_b: dict[str, StressSubAreaResult]
    area_b_total: int
    area_b_livello: str
    sub_areas_c: dict[str, StressSubAreaResult]
    area_c_total: int
    area_c_livello: str
    totale: int
    livello: str
    azione: str
    misure: list[str]
    unanswered: list[str]
