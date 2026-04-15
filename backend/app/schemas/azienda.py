import uuid
from datetime import date, datetime

from pydantic import BaseModel


class AziendaBase(BaseModel):
    ragione_sociale: str
    partita_iva: str | None = None
    sede_legale_via: str | None = None
    sede_legale_citta: str | None = None
    sede_operativa_via: str | None = None
    sede_operativa_citta: str | None = None
    attivita: str | None = None
    codice_ateco: str | None = None
    orario_lavoro: str | None = None
    metratura_totale: float | None = None
    zona_sismica: int | None = None
    descrizione_attivita: str | None = None
    contesto_territoriale: str | None = None
    data_scadenza_dvr: date | None = None


class AziendaCreate(AziendaBase):
    pass


class AziendaUpdate(BaseModel):
    ragione_sociale: str | None = None
    partita_iva: str | None = None
    sede_legale_via: str | None = None
    sede_legale_citta: str | None = None
    sede_operativa_via: str | None = None
    sede_operativa_citta: str | None = None
    attivita: str | None = None
    codice_ateco: str | None = None
    orario_lavoro: str | None = None
    metratura_totale: float | None = None
    zona_sismica: int | None = None
    descrizione_attivita: str | None = None
    contesto_territoriale: str | None = None
    data_scadenza_dvr: date | None = None
    survey_status: str | None = None


class AziendaResponse(AziendaBase):
    id: uuid.UUID
    survey_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
