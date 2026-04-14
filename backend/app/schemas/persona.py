import uuid

from pydantic import BaseModel


class PersonaBase(BaseModel):
    nominativo: str
    codice_fiscale: str | None = None
    mansione: str | None = None
    tipologia_contrattuale: str | None = None
    sesso: str | None = None
    fascia_eta: str | None = ">18"
    ruolo_rspp: bool = False
    ruolo_rls: bool = False
    ruolo_primo_soccorso: bool = False
    ruolo_antincendio: bool = False
    ruolo_preposto: bool = False
    ruolo_datore_lavoro: bool = False


class PersonaCreate(PersonaBase):
    pass


class PersonaUpdate(BaseModel):
    nominativo: str | None = None
    codice_fiscale: str | None = None
    mansione: str | None = None
    tipologia_contrattuale: str | None = None
    sesso: str | None = None
    fascia_eta: str | None = None
    ruolo_rspp: bool | None = None
    ruolo_rls: bool | None = None
    ruolo_primo_soccorso: bool | None = None
    ruolo_antincendio: bool | None = None
    ruolo_preposto: bool | None = None
    ruolo_datore_lavoro: bool | None = None


class PersonaResponse(PersonaBase):
    id: uuid.UUID
    azienda_id: uuid.UUID

    model_config = {"from_attributes": True}
