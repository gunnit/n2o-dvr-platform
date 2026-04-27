import uuid

from pydantic import BaseModel


class AttrezzaturaBase(BaseModel):
    descrizione: str
    marcatura_ce: bool = False
    verifiche_periodiche: bool = False


class AttrezzaturaCreate(AttrezzaturaBase):
    # Phase 2.3 / bug B5 — required: every attrezzatura must be tied to one
    # ambiente of the same azienda. The API validates the relationship.
    ambiente_id: uuid.UUID


class AttrezzaturaUpdate(BaseModel):
    descrizione: str | None = None
    marcatura_ce: bool | None = None
    verifiche_periodiche: bool | None = None
    ambiente_id: uuid.UUID | None = None


class AttrezzaturaResponse(AttrezzaturaBase):
    id: uuid.UUID
    azienda_id: uuid.UUID
    ambiente_id: uuid.UUID

    model_config = {"from_attributes": True}
