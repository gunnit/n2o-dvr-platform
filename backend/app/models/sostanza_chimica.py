import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SostanzaChimica(Base):
    __tablename__ = "sostanze_chimiche"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    nome_prodotto: Mapped[str] = mapped_column(String, nullable=False)
    produttore: Mapped[str | None] = mapped_column(String)
    attivita_uso: Mapped[str | None] = mapped_column(Text)
    destinazione_uso: Mapped[str | None] = mapped_column(Text)
    pittogrammi: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    stato_miscela: Mapped[str | None] = mapped_column(String)
    frasi_h: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    frasi_p: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    ai_extracted: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_confidence: Mapped[float | None] = mapped_column(Numeric)
    # Extraction lifecycle: None (manual) | pending | processing | completed | failed
    extraction_status: Mapped[str | None] = mapped_column(String)
    extraction_error: Mapped[str | None] = mapped_column(Text)
    human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    sds_file_path: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    azienda: Mapped["Azienda"] = relationship(back_populates="sostanze_chimiche")
