import uuid

from pydantic import BaseModel


class AmbienteBase(BaseModel):
    nome: str
    tipo: str
    superficie_mq: float | None = None
    preposto_id: uuid.UUID | None = None
    descrizione_attivita: str | None = None


class AmbienteCreate(AmbienteBase):
    pass


class AmbienteUpdate(BaseModel):
    nome: str | None = None
    tipo: str | None = None
    superficie_mq: float | None = None
    preposto_id: uuid.UUID | None = None
    descrizione_attivita: str | None = None


class AmbienteResponse(AmbienteBase):
    id: uuid.UUID
    azienda_id: uuid.UUID

    model_config = {"from_attributes": True}
