"""HACCP config + CCP schemas (US-4.3)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CcpEntry(BaseModel):
    """One Critical Control Point entry on an azienda's HACCP config."""

    codice: str = Field(..., min_length=1)
    nome: str = Field(..., min_length=1)
    fase: str = ""
    pericolo: str = ""
    limite_critico: str = ""
    monitoraggio: str = ""
    azione_correttiva: str = ""
    frequenza: str = ""


class AttrezzaturaHaccp(BaseModel):
    """One piece of equipment, flagged if subject to HACCP control (#65)."""

    nome: str = Field(..., min_length=1)
    sotto_controllo_haccp: bool = False


class HaccpConfigBase(BaseModel):
    tipologia_attivita: str | None = Field(
        default=None,
        description=(
            "Activity-type slug from the /haccp/_meta/activity-types catalog. "
            "Setting this to a known slug pre-loads the default CCPs."
        ),
    )
    numero_pasti_giorno: int | None = None
    tipi_alimenti_trattati: list[str] = Field(default_factory=list)
    responsabile_haccp: str | None = None
    note: str | None = None
    ccps: list[CcpEntry] = Field(default_factory=list)
    attrezzature: list[AttrezzaturaHaccp] = Field(default_factory=list)


class HaccpConfigUpsert(HaccpConfigBase):
    """PUT body — a full replace of the config shape."""


class HaccpConfigResponse(HaccpConfigBase):
    id: uuid.UUID
    azienda_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HaccpActivityTypeResponse(BaseModel):
    slug: str
    nome: str
    descrizione: str
    ccp_count: int


class HaccpActivityTypesList(BaseModel):
    items: list[HaccpActivityTypeResponse]


class HaccpRegenerateCcpsRequest(BaseModel):
    """Body for ``POST /haccp/config/regenerate-ccps``.

    ``strategy`` controls AC3's edit-then-merge behaviour:

      * ``replace`` — nuke existing CCPs and load the activity defaults.
      * ``merge``   — preserve operator-edited rows and operator-added
                      customs; add any new defaults the activity brings in.
    """

    strategy: str = Field(default="merge", pattern="^(replace|merge)$")


class HaccpRegenerateCcpsResponse(BaseModel):
    ccps: list[CcpEntry]
    preserved_codici: list[str] = Field(
        default_factory=list,
        description="Codici of CCPs that were kept because the operator had edits.",
    )
    # Carry enough metadata back that the frontend can pop a toast without a
    # follow-up request.
    strategy: str
    tipologia_attivita: str | None = None


# Generic shapes used for FastAPI responses that echo arbitrary dicts.
HaccpConfigRawDict = dict[str, Any]
