import uuid

from pydantic import BaseModel


class AmbienteBase(BaseModel):
    nome: str
    tipo: str
    superficie_mq: float | None = None
    preposto_id: uuid.UUID | None = None
    descrizione_attivita: str | None = None


class AmbienteCreate(AmbienteBase):
    # `ordine` is server-assigned on create (max(existing)+1) — see feedback
    # #22. Operators can rearrange afterwards via the PATCH /ordine endpoint.
    pass


class AmbienteUpdate(BaseModel):
    nome: str | None = None
    tipo: str | None = None
    superficie_mq: float | None = None
    preposto_id: uuid.UUID | None = None
    descrizione_attivita: str | None = None


class AmbienteReorder(BaseModel):
    """Payload for PATCH /ambienti/{id}/ordine — swaps the row to a new slot."""

    ordine: int


class AmbienteResponse(AmbienteBase):
    id: uuid.UUID
    azienda_id: uuid.UUID
    ordine: int

    model_config = {"from_attributes": True}
