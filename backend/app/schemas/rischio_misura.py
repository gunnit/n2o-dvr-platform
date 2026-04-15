"""Pydantic schemas for the per-client risk improvement-measure library (US-2.6).

See app/api/v1/rischi_misure.py and app/models/rischio_misura_libreria.py.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Priorita = Literal["bassa", "media", "alta", "urgente"]
TipoMisura = Literal[
    "tecnica", "organizzativa", "dpi", "formazione", "sorveglianza_sanitaria"
]
Provenance = Literal["ai-accepted", "ai-modified", "manual"]


class RischioMisuraLibreriaCreate(BaseModel):
    # azienda_id is taken from the path, not the body
    categoria_rischio: str = Field(..., min_length=1, max_length=64)
    titolo: str = Field(..., min_length=1, max_length=255)
    descrizione: str = Field(..., min_length=1)
    tipo: TipoMisura = "tecnica"
    priorita: Priorita = "media"
    tempistica: str = Field(default="", max_length=255)
    riferimento_normativo: str | None = None
    provenance: Provenance = "manual"


class RischioMisuraLibreriaUpdate(BaseModel):
    titolo: str | None = Field(default=None, min_length=1, max_length=255)
    descrizione: str | None = Field(default=None, min_length=1)
    tipo: TipoMisura | None = None
    priorita: Priorita | None = None
    tempistica: str | None = Field(default=None, max_length=255)
    riferimento_normativo: str | None = None
    provenance: Provenance | None = None


class RischioMisuraLibreriaResponse(BaseModel):
    id: uuid.UUID
    azienda_id: uuid.UUID
    categoria_rischio: str
    titolo: str
    descrizione: str
    tipo: str
    priorita: str
    tempistica: str
    riferimento_normativo: str | None
    provenance: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
