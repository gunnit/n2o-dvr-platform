import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Attrezzatura(Base):
    __tablename__ = "attrezzature"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    descrizione: Mapped[str] = mapped_column(String, nullable=False)
    marcatura_ce: Mapped[bool] = mapped_column(Boolean, default=False)
    verifiche_periodiche: Mapped[bool] = mapped_column(Boolean, default=False)

    azienda: Mapped["Azienda"] = relationship(back_populates="attrezzature")
