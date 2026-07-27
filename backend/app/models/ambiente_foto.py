import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AmbienteFoto(Base):
    __tablename__ = "ambienti_foto"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Indexed: every read is `WHERE ambiente_id = :id` (app/api/v1/ambienti.py).
    # Created by migration b8c9d0e1f2a3 as ix_ambienti_foto_ambiente_id, which is
    # also the name SQLAlchemy derives from index=True.
    ambiente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ambienti.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    ambiente: Mapped["Ambiente"] = relationship()
