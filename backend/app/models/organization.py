import uuid
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # --- Branding / letterhead (per-organization, all optional) ---------------
    # `name` doubles as the firm name printed on document letterhead.
    # `logo_path` points at an uploaded logo on Render Disk; when null/missing
    # the document generators fall back to the committed default asset.
    logo_path: Mapped[str | None] = mapped_column(String, nullable=True)
    indirizzo: Mapped[str | None] = mapped_column(String, nullable=True)
    cap: Mapped[str | None] = mapped_column(String(16), nullable=True)
    citta: Mapped[str | None] = mapped_column(String, nullable=True)
    provincia: Mapped[str | None] = mapped_column(String(8), nullable=True)
    partita_iva: Mapped[str | None] = mapped_column(String(32), nullable=True)
    codice_fiscale: Mapped[str | None] = mapped_column(String(32), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    sito_web: Mapped[str | None] = mapped_column(String, nullable=True)
    rspp_nome: Mapped[str | None] = mapped_column(String, nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    aziende: Mapped[list["Azienda"]] = relationship(back_populates="organization")
