import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, Text, func
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
    data_scadenza_dvr: Mapped[date | None] = mapped_column(Date)
    survey_status: Mapped[str] = mapped_column(String, default="draft")
    # US-2.1 AC1 — visura camerale upload. The PDF is stored on the local
    # disk (path) and a locally-extracted plaintext snippet is cached on the
    # row so the AI prompt can use it without re-parsing the file. **PII
    # never leaves the box** — only the snippet (which has CF/email/phone
    # redacted by the extractor) is forwarded to the model.
    # `visura_uploaded_at` doubles as a "visura present" signal for the
    # frontend.
    visura_pdf_path: Mapped[str | None] = mapped_column(Text)
    visura_extracted_text: Mapped[str | None] = mapped_column(Text)
    visura_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # US-1.6 AC3: client signature stored as raw PNG bytes. `firma_png` is
    # deferred in queries because it can be large; only endpoints that need
    # it load it explicitly.
    firma_png: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    firma_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    firma_signed_by_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="aziende")
    persone: Mapped[list["Persona"]] = relationship(back_populates="azienda", cascade="all, delete-orphan")
    ambienti: Mapped[list["Ambiente"]] = relationship(back_populates="azienda", cascade="all, delete-orphan")
    attrezzature: Mapped[list["Attrezzatura"]] = relationship(back_populates="azienda", cascade="all, delete-orphan")
    sostanze_chimiche: Mapped[list["SostanzaChimica"]] = relationship(back_populates="azienda", cascade="all, delete-orphan")
    documenti: Mapped[list["DocumentoGenerato"]] = relationship(back_populates="azienda", cascade="all, delete-orphan")
