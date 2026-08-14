"""Pydantic schemas for Microclima persistence.

One row per (azienda, ambiente, tipo_ambiente). The 6 inputs (Ta, Tr, Va, Ur,
M, Icl) are stored verbatim; the doc generator re-computes PMV/PPD, PHS or
IREQ from them at render time, so the persisted derived columns are advisory
cache.

Input bounds accommodate all three evaluation types: severe cold (UNI EN
ISO 11079) needs air temperatures down to −50 °C (blast freezers, outdoor
winter work) and wind speeds up to 20 m/s.
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
    temperatura_aria: float = Field(20.0, ge=-50, le=60)
    temperatura_radiante: float = Field(20.0, ge=-50, le=80)
    velocita_aria: float = Field(0.1, ge=0, le=20)
    umidita_relativa: float = Field(50.0, ge=0, le=100)
    metabolismo: float = Field(1.2, ge=0.5, le=8)
    isolamento_vestiario: float = Field(0.5, ge=0, le=5)
    # Cached PMV/PPD outputs (optional — server recomputes if absent).
    pmv: float | None = None
    ppd: float | None = None
    categoria_comfort: str | None = None
    # Cached PHS outputs (severe heat).
    phs_sw_tot: float | None = None
    phs_t_re: float | None = None
    dlim_loss50: float | None = None
    # Cached IREQ outputs (severe cold, UNI EN ISO 11079).
    ireq_neutral: float | None = None
    ireq_minimal: float | None = None
    t_wind_chill: float | None = None
    dle_freddo: float | None = None
    livello_rischio: str | None = None
    note: str | None = None


class MicroclimaCreate(MicroclimaBase):
    pass


class MicroclimaUpdate(BaseModel):
    ambiente_id: uuid.UUID | None = None
    nome_area: str | None = Field(None, max_length=255)
    tipo_ambiente: TipoAmbiente | None = None
    temperatura_aria: float | None = Field(None, ge=-50, le=60)
    temperatura_radiante: float | None = Field(None, ge=-50, le=80)
    velocita_aria: float | None = Field(None, ge=0, le=20)
    umidita_relativa: float | None = Field(None, ge=0, le=100)
    metabolismo: float | None = Field(None, ge=0.5, le=8)
    isolamento_vestiario: float | None = Field(None, ge=0, le=5)
    pmv: float | None = None
    ppd: float | None = None
    categoria_comfort: str | None = None
    phs_sw_tot: float | None = None
    phs_t_re: float | None = None
    dlim_loss50: float | None = None
    ireq_neutral: float | None = None
    ireq_minimal: float | None = None
    t_wind_chill: float | None = None
    dle_freddo: float | None = None
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

    ireq_neutral: float | None
    ireq_minimal: float | None
    t_wind_chill: float | None
    dle_freddo: float | None

    livello_rischio: str | None

    note: str | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# IREQ live-calculation schemas (severe cold, UNI EN ISO 11079).
#
# These live here — not in schemas/calculation.py — because the cold-stress
# preview endpoint is hosted on the microclima router, keeping the whole
# freddo surface inside the microclima module.
# ---------------------------------------------------------------------------


class IreqCalcRequest(BaseModel):
    air_temp: float = Field(
        ..., ge=-50, le=10, description="Air temperature t_a [°C] — cold environments only"
    )
    mean_radiant_temp: float = Field(
        ..., ge=-50, le=15, description="Mean radiant temperature t_r [°C]"
    )
    air_velocity: float = Field(
        ..., ge=0, le=20, description="Air / wind speed at body level [m/s]"
    )
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity [%]")
    metabolic_rate: float = Field(
        ..., ge=0.8, le=5.0, description="Metabolic rate [met]"
    )
    clothing_insulation: float = Field(
        ..., ge=0, le=5.0, description="Basic clothing insulation worn Icl [clo]"
    )
    duration_min: int = Field(
        default=480, ge=1, le=480, description="Planned exposure duration [minutes]"
    )


class IreqCalcResponse(BaseModel):
    t_o: float  # operative temperature [°C]
    ireq_neutral: float  # required clothing insulation, neutral criterion [clo]
    ireq_minimal: float  # required clothing insulation, minimal criterion [clo]
    icl: float  # clothing insulation worn (echoed) [clo]
    delta_clo: float  # extra insulation recommended (>= 0) [clo]
    dle_min: float | None  # duration-limited exposure [min]; None if not binding
    t_wc: float | None  # wind chill temperature [°C]; None above 10 °C
    frostbite_risk: str  # BASSO | MODERATO | ALTO | ESTREMO | NON_APPLICABILE
    livello: str  # ACCETTABILE | LIMITE | CRITICO
