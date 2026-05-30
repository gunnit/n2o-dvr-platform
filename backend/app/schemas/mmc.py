"""Pydantic schemas for MMC (Movimentazione Manuale dei Carichi) persistence.

Closes US-3.1 / US-3.2 / US-3.3 — operator records one or more lifting tasks
per worker, server runs NIOSH math, returns the persisted row(s).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


GiudizioPresa = Literal["Buono", "Discreto", "Scarso"]
LivelloRischio = Literal["VERDE", "GIALLO", "ROSSO"]
Area = Literal["Verde", "Gialla", "Rossa"]


class MmcValutazioneBase(BaseModel):
    persona_id: uuid.UUID | None = None
    ambiente_id: uuid.UUID | None = None

    compito: str = Field(..., min_length=1, max_length=500)
    # Cap raised from 100 to 200 — operators do record extreme lifts (drums,
    # motors) precisely so the resulting IR can flag them as ROSSA. 200 still
    # catches typos like "1010".
    peso_kg: float = Field(..., gt=0, le=200)
    sesso: Literal["M", "F"] = "M"
    fascia_eta: str = ">18"

    # NIOSH inputs (optional; if provided, server recomputes multipliers + PLR)
    altezza_cm: int | None = Field(None, ge=0, le=200)
    dislocazione_cm: int | None = Field(None, ge=0, le=200)
    distanza_cm: int | None = Field(None, ge=0, le=100)
    angolo_gradi: int | None = Field(None, ge=0, le=180)
    giudizio_presa: GiudizioPresa | None = None
    frequenza_atti_min: float | None = Field(None, ge=0, le=30)
    durata_min: int | None = Field(None, ge=0, le=480)

    # Optional pre-computed multipliers (used as fallback when inputs absent).
    # CP cap aligned with POS (le=40) to cover NIOSH overrides without surprising 422s.
    cp: float | None = Field(None, gt=0, le=40)
    fattore_a: float | None = Field(None, ge=0, le=1)
    fattore_b: float | None = Field(None, ge=0, le=1)
    fattore_c: float | None = Field(None, ge=0, le=1)
    fattore_d: float | None = Field(None, ge=0, le=1)
    fattore_e: float | None = Field(None, ge=0, le=1)
    fattore_f: float | None = Field(None, ge=0, le=1)

    note: str | None = None
    misure_proposte: str | None = None


class MmcValutazioneCreate(MmcValutazioneBase):
    pass


class MmcValutazioneUpdate(BaseModel):
    persona_id: uuid.UUID | None = None
    ambiente_id: uuid.UUID | None = None
    compito: str | None = Field(None, min_length=1, max_length=500)
    peso_kg: float | None = Field(None, gt=0, le=200)
    sesso: Literal["M", "F"] | None = None
    fascia_eta: str | None = None
    altezza_cm: int | None = Field(None, ge=0, le=200)
    dislocazione_cm: int | None = Field(None, ge=0, le=200)
    distanza_cm: int | None = Field(None, ge=0, le=100)
    angolo_gradi: int | None = Field(None, ge=0, le=180)
    giudizio_presa: GiudizioPresa | None = None
    frequenza_atti_min: float | None = Field(None, ge=0, le=30)
    durata_min: int | None = Field(None, ge=0, le=480)
    note: str | None = None
    misure_proposte: str | None = None


class MmcValutazioneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    azienda_id: uuid.UUID
    persona_id: uuid.UUID | None
    ambiente_id: uuid.UUID | None

    compito: str
    peso_kg: float
    sesso: str
    fascia_eta: str

    altezza_cm: int | None
    dislocazione_cm: int | None
    distanza_cm: int | None
    angolo_gradi: int | None
    giudizio_presa: str | None
    frequenza_atti_min: float | None
    durata_min: int | None

    cp: float
    fattore_a: float
    fattore_b: float
    fattore_c: float
    fattore_d: float
    fattore_e: float
    fattore_f: float

    plr: float | None
    indice_ir: float | None
    livello_rischio: str | None
    area_classificazione: str | None

    note: str | None
    misure_proposte: str | None

    created_at: datetime
    updated_at: datetime
