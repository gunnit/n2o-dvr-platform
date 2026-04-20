from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.ambiente import AmbienteResponse
from app.schemas.attrezzatura import AttrezzaturaResponse
from app.schemas.azienda import AziendaResponse
from app.schemas.persona import PersonaResponse
from app.schemas.rischio import RischioResponse
from app.schemas.sostanza_chimica import SostanzaChimicaResponse


class SurveyResponse(BaseModel):
    azienda: AziendaResponse
    persone: list[PersonaResponse]
    ambienti: list[AmbienteResponse]
    attrezzature: list[AttrezzaturaResponse]
    sostanze_chimiche: list[SostanzaChimicaResponse]
    rischi: list[RischioResponse]

    model_config = {"from_attributes": True}


class SurveyStepData(BaseModel):
    data: dict[str, Any]


class SurveyCompleteResponse(BaseModel):
    message: str
    survey_status: str


class SurveySignRequest(BaseModel):
    # data URL: "data:image/png;base64,iVBORw0KG..."
    signature_data_url: str = Field(..., min_length=30)
    signed_by_name: str | None = None


class SurveySignResponse(BaseModel):
    survey_status: str
    firma_signed_at: datetime
    firma_signed_by_name: str | None = None


class SurveyRevisionResponse(BaseModel):
    survey_status: str
