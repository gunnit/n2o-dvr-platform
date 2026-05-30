"""Pydantic schemas for Microclima persistence.

One row per (azienda, ambiente, tipo_ambiente). The 6 inputs (Ta, Tr, Va, Ur,
M, Icl) are stored verbatim; the doc generator re-computes PMV/PPD or PHS from
them at render time, so the persisted derived columns are advisory cache.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TipoAmbiente = Literal["moderato", "severo_caldo", "severo_freddo"]


class MicroclimaBase(BaseModel):
    ambiente_id: uuid.UUID | None = None
    nome_area: str | None = Field(None, max_length=255)
    tipo_ambiente: TipoAmbiente = "moderato"
    temperatura_aria: float = Field(20.0, ge=-20, le=60)
    temperatura_radiante: float = Field(20.0, ge=-20, le=80)
    velocita_aria: float = Field(0.1, ge=0, le=5)
    umidita_relativa: float = Field(50.0, ge=0, le=100)
    metabolismo: float = Field(1.2, ge=0.5, le=8)
    isolamento_vestiario: float = Field(0.5, ge=0, le=3)
    # Cached PMV/PPD outputs (optional — server recomputes if absent).
    pmv: float | None = None
    ppd: float | None = None
    categoria_comfort: str | None = None
    # Cached PHS outputs (severe heat).
    phs_sw_tot: float | None = None
    phs_t_re: float | None = None
    dlim_loss50: float | None = None
    livello_rischio: str | None = None
    note: str | None = None


class MicroclimaCreate(MicroclimaBase):
    pass


class MicroclimaUpdate(BaseModel):
    ambiente_id: uuid.UUID | None = None
    nome_area: str | None = Field(None, max_length=255)
    tipo_ambiente: TipoAmbiente | None = None
    temperatura_aria: float | None = Field(None, ge=-20, le=60)
    temperatura_radiante: float | None = Field(None, ge=-20, le=80)
    velocita_aria: float | None = Field(None, ge=0, le=5)
    umidita_relativa: float | None = Field(None, ge=0, le=100)
    metabolismo: float | None = Field(None, ge=0.5, le=8)
    isolamento_vestiario: float | None = Field(None, ge=0, le=3)
    pmv: float | None = None
    ppd: float | None = None
    categoria_comfort: str | None = None
    phs_sw_tot: float | None = None
    phs_t_re: float | None = None
    dlim_loss50: float | None = None
    livello_rischio: str | None = None
    note: str | None = None


class MicroclimaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    azienda_id: uuid.UUID
    ambiente_id: uuid.UUID | None
    nome_area: str | None
    tipo_ambiente: str

    temperatura_aria: float
    temperatura_radiante: float
    velocita_aria: float
    umidita_relativa: float
    metabolismo: float
    isolamento_vestiario: float

    pmv: float | None
    ppd: float | None
    categoria_comfort: str | None

    phs_sw_tot: float | None
    phs_t_re: float | None
    dlim_loss50: float | None
    livello_rischio: str | None

    note: str | None
    created_at: datetime
    updated_at: datetime
