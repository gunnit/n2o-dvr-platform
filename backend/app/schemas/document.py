import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentGenerateRequest(BaseModel):
    tipo_documento: str


class DocumentBatchRequest(BaseModel):
    tipi_documento: list[str]


class DocumentResponse(BaseModel):
    id: uuid.UUID
    azienda_id: uuid.UUID
    tipo_documento: str
    versione: int
    status: str
    file_path: str | None = None
    gdrive_file_id: str | None = None
    # User-facing error line shown next to "bozza" status (US-2.8 AC3).
    # None on success, and non-None on any failed-and-rolled-back record.
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
