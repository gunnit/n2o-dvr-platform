import uuid

from pydantic import BaseModel, Field


class AmbienteBase(BaseModel):
    nome: str
    tipo: str
    superficie_mq: float | None = None
    preposto_id: uuid.UUID | None = None
    descrizione_attivita: str | None = None
    # Scheda ambiente shared by the incendio and PEE allegati
    # (segnalazioni 2026-08-25).
    descrizione_locale: str | None = None
    materiali_presenti: str | None = None
    max_persone: int | None = Field(default=None, ge=0)
    sorgenti_innesco: str | None = None


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
    descrizione_locale: str | None = None
    materiali_presenti: str | None = None
    max_persone: int | None = Field(default=None, ge=0)
    sorgenti_innesco: str | None = None


class AmbienteReorder(BaseModel):
    """Payload for PATCH /ambienti/{id}/ordine — swaps the row to a new slot."""

    ordine: int


class AmbienteResponse(AmbienteBase):
    id: uuid.UUID
    azienda_id: uuid.UUID
    ordine: int

    model_config = {"from_attributes": True}
