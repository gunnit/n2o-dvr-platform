import uuid

from pydantic import BaseModel, Field


class RischioBase(BaseModel):
    categoria_rischio: str
    applicabile: bool = False
    pericolo: str | None = None
    condizioni_esposizione: str | None = None
    rischio: str | None = None
    misure_prevenzione: str | None = None
    probabilita_p: int | None = Field(None, ge=1, le=4)
    danno_d: int | None = Field(None, ge=1, le=4)


class RischioCreate(RischioBase):
    pass


class RischioUpdate(BaseModel):
    applicabile: bool | None = None
    pericolo: str | None = None
    condizioni_esposizione: str | None = None
    rischio: str | None = None
    misure_prevenzione: str | None = None
    probabilita_p: int | None = Field(None, ge=1, le=4)
    danno_d: int | None = Field(None, ge=1, le=4)


class RischioResponse(RischioBase):
    id: uuid.UUID
    ambiente_id: uuid.UUID
    indice_i: int | None = None
    livello_rischio: str | None = None

    model_config = {"from_attributes": True}
