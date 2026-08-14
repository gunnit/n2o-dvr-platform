"""Pydantic schemas for the Gestanti cross-reference & decision API.

All user-facing strings are Italian; keys and field names are English per the
project convention.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.data.dlgs_151_2001 import Allegato


Stato = Literal["gestante", "puerpera", "allattamento"]

# Esito della valutazione preventiva per mansione (art. 11 D.Lgs. 151/2001).
EsitoMansione = Literal[
    "compatibile", "compatibile_con_limitazioni", "non_compatibile"
]


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


# -----------------------------------------------------------------------------
# CRUD schemas — one row per (persona). Lets the frontend create/load/edit the
# signature block + state alongside the decision flow.
# -----------------------------------------------------------------------------


class GestantiCreate(BaseModel):
    persona_id: uuid.UUID
    stato: Stato = "gestante"
    data_notifica: date | None = None
    data_presunto_parto: date | None = None
    misure_adeguamento: str | None = None
    mansione_alternativa: str | None = None
    richiesta_astensione_anticipata: bool = False
    firma_lavoratrice: str | None = None
    firma_datore_lavoro: str | None = None
    firma_rspp: str | None = None
    firma_medico_competente: str | None = None
    note: str | None = None


class GestantiUpdate(BaseModel):
    stato: Stato | None = None
    data_notifica: date | None = None
    data_presunto_parto: date | None = None
    misure_adeguamento: str | None = None
    mansione_alternativa: str | None = None
    richiesta_astensione_anticipata: bool | None = None
    firma_lavoratrice: str | None = None
    firma_datore_lavoro: str | None = None
    firma_rspp: str | None = None
    firma_medico_competente: str | None = None
    note: str | None = None


class GestantiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    azienda_id: uuid.UUID
    persona_id: uuid.UUID
    stato: str
    data_notifica: date | None
    data_presunto_parto: date | None
    rischi_vietati: list[Any]
    misure_adeguamento: str | None
    mansione_alternativa: str | None
    richiesta_astensione_anticipata: bool
    firma_lavoratrice: str | None
    firma_datore_lavoro: str | None
    firma_rspp: str | None
    firma_medico_competente: str | None
    note: str | None
    created_at: datetime


# -----------------------------------------------------------------------------
# Preventive per-mansione assessment (art. 11 D.Lgs. 151/2001) — objective
# valutazione with NO worker attached. One row per (azienda, mansione).
# -----------------------------------------------------------------------------


class CatalogRisk(BaseModel):
    """One D.Lgs. 151/2001 catalog entry, as prefixed into the mansione form."""

    risk_key: str
    allegato: Allegato
    descrizione: str


class MansioneRischio(CatalogRisk):
    """A risk retained by the operator for a mansione, with optional misura.

    Same JSONB row shape as ``GestantiValutazione.rischi_vietati`` (the
    generator's row-mapping already understands ``misura``).
    """

    misura: str | None = None


class GestantiMansioneUpsert(BaseModel):
    mansione: str = Field(..., min_length=2, max_length=200)
    esito: EsitoMansione = "compatibile"
    rischi: list[MansioneRischio] | None = Field(
        None,
        description=(
            "Rischi confermati dall'operatore. Se omesso (null) il server "
            "prefilla i rischi suggeriti dal catalogo D.Lgs. 151/2001 per la "
            "mansione; una lista vuota significa 'nessun rischio'."
        ),
    )
    misure: str | None = Field(
        None,
        description=(
            "Misure di prevenzione/limitazioni. Obbligatorie quando esito != "
            "'compatibile'."
        ),
    )
    note: str | None = None

    @field_validator("mansione")
    @classmethod
    def _normalize_mansione(cls, v: str) -> str:
        v = " ".join(v.strip().split())
        if len(v) < 2:
            raise ValueError("La mansione deve contenere almeno 2 caratteri.")
        return v

    @model_validator(mode="after")
    def _misure_required_unless_compatibile(self) -> "GestantiMansioneUpsert":
        if self.esito != "compatibile":
            if not self.misure or len(self.misure.strip()) < 10:
                raise ValueError(
                    "Le misure/limitazioni sono obbligatorie (almeno 10 "
                    "caratteri) quando l'esito non e' 'compatibile'."
                )
        return self


class GestantiMansioneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    azienda_id: uuid.UUID
    mansione: str
    esito: str
    rischi: list[Any]
    misure: str | None
    note: str | None
    created_at: datetime


class GestantiMansioneOverviewItem(BaseModel):
    mansione: str
    num_persone: int = Field(
        0, description="Persone (di ogni sesso) censite con questa mansione."
    )
    num_lavoratrici: int = Field(
        0, description="Lavoratrici (sesso F) censite con questa mansione."
    )
    suggested_risks: list[CatalogRisk] = Field(
        default_factory=list,
        description=(
            "Rischi suggeriti dal catalogo D.Lgs. 151/2001 per la mansione "
            "(prefill: l'operatore rivede, non reinserisce)."
        ),
    )
    valutazione: GestantiMansioneResponse | None = None


class GestantiMansioniOverview(BaseModel):
    items: list[GestantiMansioneOverviewItem]
