import uuid
from datetime import datetime

from pydantic import BaseModel


class AmbienteFotoResponse(BaseModel):
    id: uuid.UUID
    ambiente_id: uuid.UUID
    filename: str
    file_path: str
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}
