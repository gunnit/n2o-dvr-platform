"""Pydantic schemas for the Gestanti cross-reference & decision API.

All user-facing strings are Italian; keys and field names are English per the
project convention.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.data.dlgs_151_2001 import Allegato


class CrossReferenceRequest(BaseModel):
    worker_id: uuid.UUID = Field(
        ..., description="Persona.id della lavoratrice da valutare"
    )


class RiskMatch(BaseModel):
    risk_key: str
    allegato: Allegato
    descrizione: str
    suggested_alternative_mansione: str | None = None
    is_new: bool = Field(
        False,
        description=(
            "True se il match non era presente nell'ultima valutazione salvata "
            "per questa lavoratrice. Usato dall'UI per il badge 'Nuovo'."
        ),
    )
    decision: Literal["accept", "reject", None] | None = Field(
        None,
        description=(
            "Decisione persistita dall'operatore per questo rischio. None se "
            "non ancora deciso."
        ),
    )
    justification: str | None = None
    misura_alternativa: str | None = None


class CrossReferenceResponse(BaseModel):
    worker_id: uuid.UUID
    worker_nominativo: str
    worker_mansione: str | None
    cleared: bool = Field(
        ..., description="True se nessun rischio incompatibile e' stato trovato."
    )
    matches: list[RiskMatch]
    valutazione_id: uuid.UUID | None = Field(
        None,
        description=(
            "Id della valutazione esistente per la lavoratrice, se presente. "
            "Null se la cross-reference non ha ancora generato una valutazione."
        ),
    )


class DecisionRequest(BaseModel):
    risk_key: str = Field(..., min_length=1)
    action: Literal["accept", "reject"]
    justification: str | None = Field(
        None,
        description=(
            "Obbligatoria quando action == 'accept': motivazione della "
            "riallocazione accettata."
        ),
    )
    misura_alternativa: str | None = Field(
        None,
        description=(
            "Obbligatoria quando action == 'reject': descrizione della misura "
            "alternativa adottata al posto della riallocazione."
        ),
    )

    @field_validator("justification")
    @classmethod
    def _justification_min_length(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v.strip()) < 10:
            raise ValueError(
                "La motivazione deve contenere almeno 10 caratteri."
            )
        return v.strip()

    @field_validator("misura_alternativa")
    @classmethod
    def _misura_min_length(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v.strip()) < 10:
            raise ValueError(
                "La misura alternativa deve contenere almeno 10 caratteri."
            )
        return v.strip()


class DecisionResponse(BaseModel):
    valutazione_id: uuid.UUID
    persisted_decisions: list[dict]
