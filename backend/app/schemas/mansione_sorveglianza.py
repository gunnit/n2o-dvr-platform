"""Schemas for per-mansione DPI + rischi specifici (sorveglianza sanitaria)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.services.reference_data import (
    DPI_CATALOG,
    RISCHI_SPECIFICI_CATALOG,
)


class MansioneSorveglianzaBase(BaseModel):
    mansione_nome: str = Field(..., min_length=1, max_length=200)
    dpi_codes: list[str] = Field(default_factory=list)
    rischi_specifici_codes: list[str] = Field(default_factory=list)
    note: str | None = None

    @field_validator("dpi_codes")
    @classmethod
    def _dpi_codes_known(cls, v: list[str]) -> list[str]:
        unknown = [c for c in v if c not in DPI_CATALOG]
        if unknown:
            raise ValueError(f"DPI codes non riconosciuti: {unknown}")
        # Deduplicate while preserving operator's tick order
        seen: set[str] = set()
        out: list[str] = []
        for c in v:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    @field_validator("rischi_specifici_codes")
    @classmethod
    def _rischi_codes_known(cls, v: list[str]) -> list[str]:
        unknown = [c for c in v if c not in RISCHI_SPECIFICI_CATALOG]
        if unknown:
            raise ValueError(f"Codici rischio specifico non riconosciuti: {unknown}")
        seen: set[str] = set()
        out: list[str] = []
        for c in v:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out


class MansioneSorveglianzaUpsert(MansioneSorveglianzaBase):
    """Request body for upserting one mansione row by its nome."""


class MansioneSorveglianzaResponse(MansioneSorveglianzaBase):
    id: uuid.UUID
    azienda_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
