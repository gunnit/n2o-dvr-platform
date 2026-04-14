import uuid

from pydantic import BaseModel


class AttrezzaturaBase(BaseModel):
    descrizione: str
    marcatura_ce: bool = False
    verifiche_periodiche: bool = False


class AttrezzaturaCreate(AttrezzaturaBase):
    pass


class AttrezzaturaUpdate(BaseModel):
    descrizione: str | None = None
    marcatura_ce: bool | None = None
    verifiche_periodiche: bool | None = None


class AttrezzaturaResponse(AttrezzaturaBase):
    id: uuid.UUID
    azienda_id: uuid.UUID

    model_config = {"from_attributes": True}
