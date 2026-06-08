"""DUVRI schemas (US-4.5).

A Duvri instance is one contract between the principal (committente, the
parent Azienda) and one contractor (appaltatore). A given Azienda can own
multiple Duvri rows — one per appalto.
"""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_dpi_to_list(v: Any) -> list[str] | None:
    """Accept ``dpi`` as ``None``, a single string (legacy rules-engine shape),
    or a list of strings (canonical persisted shape). Always return
    ``list[str] | None`` so the response schema is stable."""
    if v is None:
        return None
    if isinstance(v, str):
        # Treat comma-separated legacy strings as a single entry; the docx
        # generator will flatten again.
        return [v] if v.strip() else None
    if isinstance(v, list):
        return [str(x) for x in v if x is not None]
    return [str(v)]


class InterferenzaItem(BaseModel):
    """One identified interference risk + how it's being handled."""

    rischio: str = Field(..., max_length=500)
    misure: str = Field(..., max_length=2000)
    # Accept either list[str] (canonical — seed fixture + rules-engine mirror)
    # or a legacy single string. Normalised to list[str] on the way out so the
    # response model is consistent for the frontend.
    dpi: list[str] | None = None

    @field_validator("dpi", mode="before")
    @classmethod
    def _coerce_dpi(cls, v: Any) -> list[str] | None:
        return _normalize_dpi_to_list(v)


class AppaltatoreAttrezzatura(BaseModel):
    tipo: str = Field(..., max_length=64)
    descrizione: str | None = Field(None, max_length=255)


class InterferenzaDecisione(BaseModel):
    rule_id: str = Field(..., max_length=128)
    decision: str = Field(..., pattern=r"^(accept|reject)$")
    custom_text: str | None = Field(None, max_length=2000)


class DuvriBase(BaseModel):
    appaltatore_ragione_sociale: str = Field(..., min_length=1, max_length=255)
    appaltatore_partita_iva: str | None = Field(None, max_length=32)
    appaltatore_referente: str | None = Field(None, max_length=255)
    oggetto_appalto: str = Field(..., min_length=1, max_length=4000)
    data_inizio: date | None = None
    data_fine: date | None = None
    interferenze: list[InterferenzaItem] = Field(default_factory=list)
    attrezzature_appaltatore: list[AppaltatoreAttrezzatura] = Field(
        default_factory=list
    )
    interferenze_decisioni: list[InterferenzaDecisione] = Field(default_factory=list)
    note: str | None = None


class DuvriCreate(DuvriBase):
    pass


class DuvriUpdate(BaseModel):
    appaltatore_ragione_sociale: str | None = Field(None, min_length=1, max_length=255)
    appaltatore_partita_iva: str | None = Field(None, max_length=32)
    appaltatore_referente: str | None = Field(None, max_length=255)
    oggetto_appalto: str | None = Field(None, min_length=1, max_length=4000)
    data_inizio: date | None = None
    data_fine: date | None = None
    interferenze: list[InterferenzaItem] | None = None
    attrezzature_appaltatore: list[AppaltatoreAttrezzatura] | None = None
    interferenze_decisioni: list[InterferenzaDecisione] | None = None
    note: str | None = None


class InterferenceSuggestion(BaseModel):
    rule_id: str
    contractor_eq: str
    titolo: str
    rischio: str
    misure: str
    # Same flexible shape as InterferenzaItem above so API responses are
    # consistent whether the source is the live rules engine (string) or a
    # persisted interferenza (list).
    dpi: list[str] | None = None
    riferimento: str
    decision: str | None = None  # accept | reject if previously decided

    @field_validator("dpi", mode="before")
    @classmethod
    def _coerce_dpi(cls, v: Any) -> list[str] | None:
        return _normalize_dpi_to_list(v)


class AnalyzeInterferencesResponse(BaseModel):
    suggestions: list[InterferenceSuggestion]
    no_interference_detected: bool
    contractor_equipment: list[str]


class InterferenceDecisionBody(BaseModel):
    rule_id: str = Field(..., max_length=128)
    decision: str = Field(..., pattern=r"^(accept|reject)$")
    custom_text: str | None = Field(None, max_length=2000)


class DuvriResponse(DuvriBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    azienda_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    # Surfaced flag the client uses to render the "Dati committente aggiornati"
    # banner per AC3. Computed in the endpoint by comparing parent Azienda's
    # updated_at to this Duvri's updated_at; not persisted.
    committente_outdated: bool = False
    committente_snapshot: dict[str, Any] | None = None
