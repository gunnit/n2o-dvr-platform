"""Pydantic schemas for the pericoli catalog and per-azienda children."""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel


class PericoloLibreriaResponse(BaseModel):
    """Catalog row — read-only from the API."""

    id: uuid.UUID
    code: str
    categoria: str
    macro_categoria: str
    pericolo: str
    condizioni_esposizione: str | None = None
    rischio: str | None = None
    misure_prevenzione: str | None = None
    p_default: int | None = None
    d_default: int | None = None
    valutazione_riferimento: str | None = None
    ambiente_tipi: list[str] = []
    attrezzatura_keywords: list[str] = []

    model_config = {"from_attributes": True}


class PericoloSuggestionItem(BaseModel):
    """Catalog row plus context for why it surfaced.

    Sent by the suggester endpoint so the UI can render a "Suggerito perché:
    Cucina + Affettatrice" chip. ``triggered_by_attrezzature`` lists the
    descriptions of attrezzature whose keywords matched.
    """

    pericolo: PericoloLibreriaResponse
    matches_ambiente: bool
    triggered_by_attrezzature: list[str] = []


class PericoloSuggestionResponse(BaseModel):
    ambiente_tipo: str | None
    attrezzature_count: int
    items: list[PericoloSuggestionItem]


class PericoloValutazioneBase(BaseModel):
    pericolo_libreria_id: uuid.UUID | None = None
    source: Literal["catalog", "custom"] = "catalog"
    pericolo: str
    condizioni_esposizione: str | None = None
    rischio: str | None = None
    misure_prevenzione: str | None = None
    probabilita_p: int | None = None
    danno_d: int | None = None
    valutazione_riferimento: str | None = None
    applicabile: bool = True
    ordine: int = 0


class PericoloValutazioneCreate(PericoloValutazioneBase):
    pass


class PericoloValutazioneUpdate(BaseModel):
    pericolo: str | None = None
    condizioni_esposizione: str | None = None
    rischio: str | None = None
    misure_prevenzione: str | None = None
    probabilita_p: int | None = None
    danno_d: int | None = None
    valutazione_riferimento: str | None = None
    applicabile: bool | None = None
    ordine: int | None = None


class PericoloValutazioneResponse(PericoloValutazioneBase):
    id: uuid.UUID
    valutazione_rischio_id: uuid.UUID
    indice_i: int | None = None
    livello_rischio: str | None = None

    model_config = {"from_attributes": True}


class PericoliBatchItem(PericoloValutazioneBase):
    """A row in a batch upsert — id present means update, absent means insert."""

    id: uuid.UUID | None = None


class PericoliBatchRequest(BaseModel):
    items: list[PericoliBatchItem]
