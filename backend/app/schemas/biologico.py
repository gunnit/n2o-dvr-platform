"""Pydantic schemas for Rischio Biologico (D.Lgs. 81/2008 Titolo X).

One BiologicoValutazione row per (azienda, settore). Upsert semantics: POST
either creates a new row or overwrites the existing one for that settore.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Settore = Literal["alimentare", "asilo", "dentisti"]
Livello = Literal["BASSO", "MEDIO", "ALTO"]


class RispostaCheckItem(BaseModel):
    id: str
    risposta: Literal["SI", "NO", "NA"]


class BiologicoBase(BaseModel):
    settore: Settore
    ambiente_id: uuid.UUID | None = None
    agenti_identificati: list[dict[str, Any]] = Field(default_factory=list)
    misure_protettive: list[dict[str, Any]] = Field(default_factory=list)
    dpi_richiesti: list[dict[str, Any]] = Field(default_factory=list)
    protocollo_sanitario: str | None = None
    formazione_specifica: str | None = None
    livello_rischio: Livello | None = None
    risposte_checklist: list[RispostaCheckItem] = Field(default_factory=list)
    note: str | None = None


class BiologicoCreate(BiologicoBase):
    pass


class BiologicoUpdate(BaseModel):
    ambiente_id: uuid.UUID | None = None
    agenti_identificati: list[dict[str, Any]] | None = None
    misure_protettive: list[dict[str, Any]] | None = None
    dpi_richiesti: list[dict[str, Any]] | None = None
    protocollo_sanitario: str | None = None
    formazione_specifica: str | None = None
    livello_rischio: Livello | None = None
    risposte_checklist: list[RispostaCheckItem] | None = None
    note: str | None = None


class BiologicoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    azienda_id: uuid.UUID
    settore: str
    ambiente_id: uuid.UUID | None
    agenti_identificati: list[Any]
    misure_protettive: list[Any]
    dpi_richiesti: list[Any]
    protocollo_sanitario: str | None
    formazione_specifica: str | None
    livello_rischio: str | None
    risposte_checklist: list[Any]
    note: str | None
    created_at: datetime
