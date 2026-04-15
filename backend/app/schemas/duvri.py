"""DUVRI schemas (US-4.5).

A Duvri instance is one contract between the principal (committente, the
parent Azienda) and one contractor (appaltatore). A given Azienda can own
multiple Duvri rows — one per appalto.
"""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InterferenzaItem(BaseModel):
    """One identified interference risk + how it's being handled."""

    rischio: str = Field(..., max_length=500)
    misure: str = Field(..., max_length=2000)
    dpi: str | None = Field(None, max_length=500)


class DuvriBase(BaseModel):
    appaltatore_ragione_sociale: str = Field(..., min_length=1, max_length=255)
    appaltatore_partita_iva: str | None = Field(None, max_length=32)
    appaltatore_referente: str | None = Field(None, max_length=255)
    oggetto_appalto: str = Field(..., min_length=1, max_length=4000)
    data_inizio: date | None = None
    data_fine: date | None = None
    importo_appalto: float | None = None
    interferenze: list[InterferenzaItem] = Field(default_factory=list)
    costi_sicurezza: float | None = None
    note: str | None = None


class DuvriCreate(DuvriBase):
    pass


class DuvriUpdate(BaseModel):
    appaltatore_ragione_sociale: str | None = Field(None, min_length=1, max_length=255)
    appaltatore_partita_iva: str | None = Field(None, max_length=32)
    appaltatore_referente: str | None = Field(None, max_length=255)
    oggetto_appalto: str | None = Field(None, min_length=1, max_length=4000)
    data_inizio: date | None = None
    data_fine: date | None = None
    importo_appalto: float | None = None
    interferenze: list[InterferenzaItem] | None = None
    costi_sicurezza: float | None = None
    note: str | None = None


class DuvriResponse(DuvriBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    azienda_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    # Surfaced flag the client uses to render the "Dati committente aggiornati"
    # banner per AC3. Computed in the endpoint by comparing parent Azienda's
    # updated_at to this Duvri's updated_at; not persisted.
    committente_outdated: bool = False
    committente_snapshot: dict[str, Any] | None = None
