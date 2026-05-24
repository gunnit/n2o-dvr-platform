"""Schemas for the DVR §4.1 Programma di Miglioramento (T109).

Five free-text fields aligned with the T109 grid columns. ``priorita`` is
optional and intended to mirror the linked pericolo's ``livello_rischio``
when set, so the renderer can color-band the row.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MisuraMiglioramentoBase(BaseModel):
    misura: str = Field(..., min_length=1)
    misura_miglioramento: str | None = None
    procedura: str | None = None
    risorse: str | None = None
    responsabile: str | None = None
    scadenza: str | None = None
    priorita: str | None = None
    ordine: int = 0
    pericolo_valutazione_id: uuid.UUID | None = None


class MisuraMiglioramentoCreate(MisuraMiglioramentoBase):
    pass


class MisuraMiglioramentoUpdate(BaseModel):
    misura: str | None = None
    misura_miglioramento: str | None = None
    procedura: str | None = None
    risorse: str | None = None
    responsabile: str | None = None
    scadenza: str | None = None
    priorita: str | None = None
    ordine: int | None = None
    pericolo_valutazione_id: uuid.UUID | None = None


class MisuraMiglioramentoResponse(MisuraMiglioramentoBase):
    id: uuid.UUID
    azienda_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
