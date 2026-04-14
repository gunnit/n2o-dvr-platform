import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Azienda(Base):
    __tablename__ = "aziende"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    ragione_sociale: Mapped[str] = mapped_column(String, nullable=False)
    partita_iva: Mapped[str | None] = mapped_column(String)
    sede_legale_via: Mapped[str | None] = mapped_column(String)
    sede_legale_citta: Mapped[str | None] = mapped_column(String)
    sede_operativa_via: Mapped[str | None] = mapped_column(String)
    sede_operativa_citta: Mapped[str | None] = mapped_column(String)
    attivita: Mapped[str | None] = mapped_column(Text)
    codice_ateco: Mapped[str | None] = mapped_column(String)
    orario_lavoro: Mapped[str | None] = mapped_column(String)
    metratura_totale: Mapped[float | None] = mapped_column(Numeric)
    zona_sismica: Mapped[int | None] = mapped_column(Integer)
    descrizione_attivita: Mapped[str | None] = mapped_column(Text)
    contesto_territoriale: Mapped[str | None] = mapped_column(Text)
    survey_status: Mapped[str] = mapped_column(String, default="draft")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="aziende")
    persone: Mapped[list["Persona"]] = relationship(back_populates="azienda", cascade="all, delete-orphan")
    ambienti: Mapped[list["Ambiente"]] = relationship(back_populates="azienda", cascade="all, delete-orphan")
    attrezzature: Mapped[list["Attrezzatura"]] = relationship(back_populates="azienda", cascade="all, delete-orphan")
    sostanze_chimiche: Mapped[list["SostanzaChimica"]] = relationship(back_populates="azienda", cascade="all, delete-orphan")
    documenti: Mapped[list["DocumentoGenerato"]] = relationship(back_populates="azienda", cascade="all, delete-orphan")
