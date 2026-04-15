import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentoGenerato(Base):
    __tablename__ = "documenti_generati"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    tipo_documento: Mapped[str] = mapped_column(String, nullable=False)
    versione: Mapped[int] = mapped_column(Integer, default=1)
    # Lifecycle: pending -> in_progress -> completed | bozza.
    # "bozza" means an attempt failed and was rolled back (US-2.8 AC3);
    # the partial file is deleted, file_path is NULL, and error_message
    # carries a short Italian explanation for the operator.
    status: Mapped[str] = mapped_column(String, default="pending")
    file_path: Mapped[str | None] = mapped_column(String)
    gdrive_file_id: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    generation_started_at: Mapped[datetime | None] = mapped_column()
    generation_completed_at: Mapped[datetime | None] = mapped_column()
    generated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    azienda: Mapped["Azienda"] = relationship(back_populates="documenti")
