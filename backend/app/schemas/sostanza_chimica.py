import uuid
from datetime import datetime

from pydantic import BaseModel


class SostanzaChimicaBase(BaseModel):
    nome_prodotto: str
    produttore: str | None = None
    attivita_uso: str | None = None
    pittogrammi: list[str] | None = None
    stato_miscela: str | None = None
    frasi_h: list[str] | None = None
    frasi_p: list[str] | None = None
    ai_extracted: bool = False
    ai_confidence: float | None = None
    sds_file_path: str | None = None


class SostanzaChimicaCreate(SostanzaChimicaBase):
    pass


class SostanzaChimicaUpdate(BaseModel):
    nome_prodotto: str | None = None
    produttore: str | None = None
    attivita_uso: str | None = None
    pittogrammi: list[str] | None = None
    stato_miscela: str | None = None
    frasi_h: list[str] | None = None
    frasi_p: list[str] | None = None
    ai_extracted: bool | None = None
    ai_confidence: float | None = None
    sds_file_path: str | None = None


class SostanzaChimicaResponse(SostanzaChimicaBase):
    id: uuid.UUID
    azienda_id: uuid.UUID
    human_reviewed: bool
    created_at: datetime

    model_config = {"from_attributes": True}
