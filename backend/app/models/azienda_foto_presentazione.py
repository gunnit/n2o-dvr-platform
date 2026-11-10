import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AziendaFotoPresentazione(Base):
    """The one photo printed under "Presentazione dell'azienda" in the DVR.

    A separate 1:1 table so azienda list queries never load the bytes. They
    live in the database (like ``AmbienteFoto.document_image_bytes``) because
    the Celery worker that builds the document does not share the API's disk.
    Only the normalised document image is kept, never the original upload.
    """

    __tablename__ = "azienda_foto_presentazione"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("aziende.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    document_image_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
