"""Pydantic schemas for Rischio Incendio (D.M. 03/09/2021) persistence.

One IncendioValutazione row per (azienda, ambiente). Score = INF + SI + PI;
total + livello are PostgreSQL-computed columns, so they appear only on
responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Livello = Literal["BASSO", "MEDIO", "ALTO"]


class IncendioBase(BaseModel):
    ambiente_id: uuid.UUID | None = None
    nome_area: str | None = Field(None, max_length=255)
    inf: int = Field(..., ge=1, le=3)
    si: int = Field(..., ge=1, le=3)
    pi: int = Field(..., ge=1, le=3)
    note: str | None = None
    misure_prevenzione: str | None = None
    estintori_presenti: int = Field(0, ge=0)
    idranti_presenti: int = Field(0, ge=0)
    uscite_emergenza: int = Field(0, ge=0)


class IncendioCreate(IncendioBase):
    pass


class IncendioUpdate(BaseModel):
    ambiente_id: uuid.UUID | None = None
    nome_area: str | None = Field(None, max_length=255)
    inf: int | None = Field(None, ge=1, le=3)
    si: int | None = Field(None, ge=1, le=3)
    pi: int | None = Field(None, ge=1, le=3)
    note: str | None = None
    misure_prevenzione: str | None = None
    estintori_presenti: int | None = Field(None, ge=0)
    idranti_presenti: int | None = Field(None, ge=0)
    uscite_emergenza: int | None = Field(None, ge=0)


class IncendioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    azienda_id: uuid.UUID
    ambiente_id: uuid.UUID | None
    nome_area: str | None

    inf: int
    si: int
    pi: int
    punteggio_totale: int | None
    livello_rischio: Livello | None

    note: str | None
    misure_prevenzione: str | None
    estintori_presenti: int
    idranti_presenti: int
    uscite_emergenza: int

    created_at: datetime
    updated_at: datetime
