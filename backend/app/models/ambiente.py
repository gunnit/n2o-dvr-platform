import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.persone_ambienti import persone_ambienti


class Ambiente(Base):
    __tablename__ = "ambienti"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    nome: Mapped[str] = mapped_column(String, nullable=False)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    superficie_mq: Mapped[float | None] = mapped_column(Numeric)
    preposto_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("persone.id"))
    descrizione_attivita: Mapped[str | None] = mapped_column(Text)
    # Scheda ambiente (segnalazioni 2026-08-25, incendio + PEE): the same
    # three facts both allegati need, entered once here so the operator
    # never types them twice. ``superficie_mq`` above is the metratura.
    # ``max_persone`` is always operator-entered; the other three can be
    # proposed from the ambiente photos (vision) and confirmed.
    descrizione_locale: Mapped[str | None] = mapped_column(Text)
    materiali_presenti: Mapped[str | None] = mapped_column(Text)
    max_persone: Mapped[int | None] = mapped_column(Integer)
    sorgenti_innesco: Mapped[str | None] = mapped_column(Text)
    # Operator-controlled display order within an azienda. Feedback #22
    # (2026-05-18): the list endpoint had no ordering, so insertion order
    # was effectively random — operators want both predictable ordering
    # *and* a way to reshuffle (up/down arrows in the survey UI). We
    # auto-assign max(ordine)+1 on create and let the PATCH endpoint move
    # rows around individually.
    ordine: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    azienda: Mapped["Azienda"] = relationship(back_populates="ambienti")
    persone: Mapped[list["Persona"]] = relationship(secondary=persone_ambienti, back_populates="ambienti")
    valutazioni_rischio: Mapped[list["ValutazioneRischio"]] = relationship(back_populates="ambiente", cascade="all, delete-orphan")
    attrezzature: Mapped[list["Attrezzatura"]] = relationship(back_populates="ambiente", cascade="all, delete-orphan")
