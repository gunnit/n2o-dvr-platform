"""Pydantic schemas for the protocollo sanitario per mansione."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Fonte = Literal["ai", "manuale", "ai_modificato"]

# Overall cadence of the visita periodica. Art. 41 c. 2 lett. b) D.Lgs.
# 81/2008: "di norma una volta l'anno", a different cadence being the MC's
# call; VDT is quinquennale/biennale by art. 176. Kept as a closed list so
# the DVR column and the AI proposal share one vocabulary.
PERIODICITA_OPTIONS: tuple[str, ...] = (
    "semestrale",
    "annuale",
    "biennale",
    "triennale",
    "quinquennale",
)


def normalize_mansione(value: str | None) -> str:
    """Collapse whitespace; the upsert key is ``normalize_mansione(x).lower()``."""
    return " ".join((value or "").strip().split())


class Accertamento(BaseModel):
    esame: str = Field(..., min_length=2, max_length=200)
    periodicita: str = Field("", max_length=100)

    @field_validator("esame", "periodicita")
    @classmethod
    def _strip(cls, v: str) -> str:
        return " ".join((v or "").strip().split())


class MalattiaCorrelata(BaseModel):
    codice: str | None = Field(
        None,
        max_length=80,
        description="Codice della tabella di riferimento, se la voce proviene da li'.",
    )
    malattia: str = Field(..., min_length=2, max_length=300)
    riferimento: str | None = Field(None, max_length=300)

    @field_validator("malattia")
    @classmethod
    def _strip(cls, v: str) -> str:
        return " ".join((v or "").strip().split())


class RischioSpecificoItem(BaseModel):
    code: str
    etichetta: str


class DpiItem(BaseModel):
    code: str
    etichetta: str


class MalattiaRiferimento(BaseModel):
    """One row of the reference table, as shown to the operator and the AI."""

    codice: str
    malattia: str
    agente_o_rischio: str
    tabella: str
    tabellata: bool
    rischi_specifici_codes: list[str]
    categorie: list[str]


class ProtocolloSanitarioUpsert(BaseModel):
    mansione: str = Field(..., min_length=2, max_length=200)
    rischi_specifici: list[RischioSpecificoItem] | None = Field(
        None,
        description=(
            "Snapshot dei rischi specifici della mansione. Se omesso (null) il "
            "server lo ricava dai flag delle persone con quella mansione."
        ),
    )
    accertamenti: list[Accertamento] = Field(default_factory=list)
    periodicita: str | None = Field(None, max_length=60)
    malattie_correlate: list[MalattiaCorrelata] = Field(default_factory=list)
    note: str | None = None
    fonte: Fonte = "manuale"

    @field_validator("mansione")
    @classmethod
    def _normalize(cls, v: str) -> str:
        v = normalize_mansione(v)
        if len(v) < 2:
            raise ValueError("La mansione deve contenere almeno 2 caratteri.")
        return v

    @field_validator("periodicita")
    @classmethod
    def _periodicita(cls, v: str | None) -> str | None:
        v = normalize_mansione(v).lower() if v else None
        return v or None


class ProtocolloSanitarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    azienda_id: uuid.UUID
    mansione: str
    rischi_specifici: list[Any]
    accertamenti: list[Any]
    periodicita: str | None
    malattie_correlate: list[Any]
    note: str | None
    fonte: str
    created_at: datetime
    updated_at: datetime


class ProtocolloMansioneItem(BaseModel):
    mansione: str
    num_persone: int = Field(
        0, description="Persone censite con questa mansione (solo il conteggio)."
    )
    rischi_specifici: list[RischioSpecificoItem] = Field(default_factory=list)
    dpi: list[DpiItem] = Field(default_factory=list)
    malattie_riferimento: list[MalattiaRiferimento] = Field(
        default_factory=list,
        description=(
            "Malattie professionali della tabella di riferimento correlate ai "
            "rischi specifici della mansione (prefill, da confermare dal MC)."
        ),
    )
    protocollo: ProtocolloSanitarioResponse | None = None


class ProtocolloMansioniOverview(BaseModel):
    items: list[ProtocolloMansioneItem]
    periodicita_options: list[str] = Field(
        default_factory=lambda: list(PERIODICITA_OPTIONS)
    )


class SuggerisciProtocolloRequest(BaseModel):
    mansione: str = Field(..., min_length=2, max_length=200)

    @field_validator("mansione")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_mansione(v)


class AccertamentoProposto(BaseModel):
    esame: str
    periodicita: str
    motivazione: str


class ProtocolloSuggeritoResponse(BaseModel):
    mansione: str
    accertamenti: list[AccertamentoProposto]
    periodicita: str
    malattie_correlate: list[MalattiaCorrelata]
    motivazione: str
