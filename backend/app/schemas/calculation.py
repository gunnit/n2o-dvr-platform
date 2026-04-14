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
