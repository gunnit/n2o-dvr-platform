"""Pydantic schemas for the per-azienda stress lavoro-correlato valutazione.

See app/api/v1/stress_valutazione.py and app/models/stress_valutazione.py.
The valutazione persists the operator's INAIL indicator responses + the
computed scores so a returning operator sees the previous run rather than
a blank checklist (feedback #31 — the "Conferma valutazione" button has
to actually archive something).
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StressValutazioneUpsert(BaseModel):
    """Body for PUT /api/v1/aziende/{azienda_id}/stress/valutazione.

    `answers` carries the raw indicator responses keyed by id ("A.1",
    "B1.3", "C4.8" ...). The server runs the INAIL calculator, then
    persists both the raw answers (split by area) and the computed
    scores. Missing indicators are allowed — they're reported back in
    the response's `unanswered` list.
    """

    answers: dict[str, str] = Field(default_factory=dict)
    gruppo_omogeneo: str | None = None
    misure_correttive: str | None = None
    note: str | None = None


class StressValutazioneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    azienda_id: uuid.UUID
    gruppo_omogeneo: str
    area_a_eventi_sentinella: dict[str, Any]
    area_b_contenuto_lavoro: dict[str, Any]
    area_c_contesto_lavoro: dict[str, Any]
    punteggio_a: int | None
    punteggio_b: int | None
    punteggio_c: int | None
    punteggio_totale: int | None
    livello_rischio: str | None
    misure_correttive: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime
    # Calculator detail returned alongside the persisted row so the
    # frontend can render the level + action without a second call.
    unanswered: list[str] = Field(default_factory=list)
    azione: str | None = None
