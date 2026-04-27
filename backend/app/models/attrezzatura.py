import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Attrezzatura(Base):
    __tablename__ = "attrezzature"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    # Phase 2.3 / bug B5 — every piece of equipment lives in exactly one
    # ambiente. The migration backfilled legacy rows to the oldest ambiente
    # of their azienda; new rows must specify it explicitly.
    ambiente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ambienti.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    descrizione: Mapped[str] = mapped_column(String, nullable=False)
    marcatura_ce: Mapped[bool] = mapped_column(Boolean, default=False)
    verifiche_periodiche: Mapped[bool] = mapped_column(Boolean, default=False)

    azienda: Mapped["Azienda"] = relationship(back_populates="attrezzature")
    ambiente: Mapped["Ambiente"] = relationship(back_populates="attrezzature")
