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


class FireRiskRequest(BaseModel):
    inf: int = Field(..., ge=1, le=3, description="Infiammabilita (flammability) score 1-3")
    si: int = Field(..., ge=1, le=3, description="Sorgenti di Innesco (ignition sources) score 1-3")
    pi: int = Field(..., ge=1, le=3, description="Propagazione Incendio (fire propagation) score 1-3")


class FireRiskResponse(BaseModel):
    inf: int
    si: int
    pi: int
    totale: int
    livello: str
    azione: str


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


# ---------------------------------------------------------------------------
# VDT — Videoterminali (D.Lgs. 81/2008 Titolo VII)
# ---------------------------------------------------------------------------


class VdtWorkerInput(BaseModel):
    id: str | None = Field(
        default=None,
        description="Optional stable identifier for the worker (client-generated).",
    )
    nome: str | None = Field(
        default=None,
        description="Optional display name. Privacy rules apply — do NOT send codice fiscale.",
    )
    ore_settimanali: float = Field(
        ...,
        ge=0,
        le=168,
        description="Weekly VDT usage in hours (0-168).",
    )


class VdtAssessmentRequest(BaseModel):
    workers: list[VdtWorkerInput] = Field(
        ...,
        description="List of workers to classify by VDT exposure.",
    )


class VdtWorkerResult(BaseModel):
    id: str | None = None
    nome: str | None = None
    ore_settimanali: float
    esposizione: str
    sorveglianza_sanitaria: bool


class VdtAssessmentResponse(BaseModel):
    workers: list[VdtWorkerResult]
    total: int
    esposti: int
    non_esposti: int


# ---------------------------------------------------------------------------
# Microclima — PMV/PPD (ISO 7730) and PHS (ISO 7933)
# ---------------------------------------------------------------------------


class PmvPpdRequest(BaseModel):
    air_temp: float = Field(
        ..., ge=10, le=40, description="Dry bulb air temperature tdb [°C]"
    )
    mean_radiant_temp: float = Field(
        ..., ge=10, le=40, description="Mean radiant temperature tr [°C]"
    )
    air_velocity: float = Field(
        ..., ge=0, le=2, description="Relative air speed vr [m/s]"
    )
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity rh [%]")
    metabolic_rate: float = Field(
        ..., ge=0.7, le=4.0, description="Metabolic rate met [met]"
    )
    clothing_insulation: float = Field(
        ..., ge=0, le=2.0, description="Clothing insulation clo [clo]"
    )


class PmvPpdResponse(BaseModel):
    pmv: float
    ppd: float
    sensation: str
    category: str  # "A", "B", "C", or "FUORI_SOGLIA"
    compliant: bool


class PhsRequest(BaseModel):
    air_temp: float = Field(
        ..., ge=15, le=50, description="Dry bulb air temperature tdb [°C]"
    )
    mean_radiant_temp: float = Field(
        ..., ge=15, le=60, description="Mean radiant temperature tr [°C]"
    )
    air_velocity: float = Field(..., ge=0, le=3, description="Air speed v [m/s]")
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity rh [%]")
    metabolic_rate: float = Field(
        ..., ge=1.0, le=7.5, description="Metabolic rate met [met]"
    )
    clothing_insulation: float = Field(
        ..., ge=0.1, le=1.0, description="Clothing insulation clo [clo]"
    )
    posture: str = Field(
        default="standing",
        description="Posture: 'sitting' | 'standing' | 'crouching'.",
    )
    acclimatized: bool = Field(
        default=True, description="Whether the worker is heat-acclimatized."
    )
    drink_free: bool = Field(
        default=True, description="Whether workers can drink water freely."
    )
    duration_min: int = Field(
        default=480, ge=1, le=480, description="Work sequence duration [minutes]."
    )


class PhsResponse(BaseModel):
    t_re: float  # Final rectal temperature [°C]
    t_sk: float  # Skin temperature [°C]
    d_lim_t_re: float  # Max exposure time by core temp [min]
    d_lim_loss_50: float  # Max exposure time by dehydration (50th percentile) [min]
    d_lim_loss_95: float  # Max exposure time by dehydration (95th percentile) [min]
    sweat_loss_g: float  # Total cumulative sweat loss [g]
    d_lim: float  # Minimum of the three d_lim values — the binding limit [min]
    livello: str  # "ACCETTABILE" | "LIMITE" | "CRITICO"
