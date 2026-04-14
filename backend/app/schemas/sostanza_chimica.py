import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SostanzaChimicaBase(BaseModel):
    nome_prodotto: str
    produttore: str | None = None
    attivita_uso: str | None = None
    pittogrammi: list[str] | None = None
    stato_miscela: str | None = None
    frasi_h: list[str] | None = None
    frasi_p: list[str] | None = None
    ai_extracted: bool = False
    ai_confidence: float | None = None
    extraction_status: str | None = None
    extraction_error: str | None = None
    sds_file_path: str | None = None


class SostanzaChimicaCreate(SostanzaChimicaBase):
    pass


class SostanzaChimicaUpdate(BaseModel):
    nome_prodotto: str | None = None
    produttore: str | None = None
    attivita_uso: str | None = None
    pittogrammi: list[str] | None = None
    stato_miscela: str | None = None
    frasi_h: list[str] | None = None
    frasi_p: list[str] | None = None
    ai_extracted: bool | None = None
    ai_confidence: float | None = None
    sds_file_path: str | None = None


class SostanzaChimicaResponse(SostanzaChimicaBase):
    id: uuid.UUID
    azienda_id: uuid.UUID
    human_reviewed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Batch SDS upload (US-1.8) ---


class BatchUploadFileResult(BaseModel):
    """One row in the response of POST /batch-upload."""

    filename: str
    sostanza_id: uuid.UUID | None = None
    status: Literal["queued", "failed"]
    reason: str | None = None


class BatchUploadResponse(BaseModel):
    results: list[BatchUploadFileResult]


class BatchStatusItem(BaseModel):
    """Lightweight row for polling extraction progress."""

    sostanza_id: uuid.UUID
    nome_prodotto: str
    extraction_status: str | None
    extraction_error: str | None = None
    ai_confidence: float | None = None

    model_config = {"from_attributes": True}


class BatchStatusResponse(BaseModel):
    items: list[BatchStatusItem]
