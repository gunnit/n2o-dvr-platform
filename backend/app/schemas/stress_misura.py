"""Pydantic schemas for the per-client stress corrective-measure library.

See app/api/v1/stress_misure.py and app/models/stress_misura_libreria.py.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

LivelloRischio = Literal["Basso", "Medio", "Alto"]


class StressMisuraLibreriaCreate(BaseModel):
    # azienda_id is taken from the path, not the body
    livello_rischio: LivelloRischio
    testo: str = Field(..., min_length=1)


class StressMisuraLibreriaUpdate(BaseModel):
    testo: str = Field(..., min_length=1)


class StressMisuraLibreriaResponse(BaseModel):
    id: uuid.UUID
    azienda_id: uuid.UUID
    livello_rischio: str
    testo: str
    personalizzato: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
