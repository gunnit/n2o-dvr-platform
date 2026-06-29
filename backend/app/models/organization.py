import uuid
from datetime import datetime

from sqlalchemy import LargeBinary, String, func
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
    # The logo is stored as bytes in the DB (not on disk): document generation
    # runs on the Celery worker, which mounts a *different* Render disk from the
    # API that receives the upload, so a file path would never be reachable
    # there. Bytes in Postgres are shared by both services. Logos are capped at
    # 5 MB on upload, so this stays small.
    logo_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    logo_content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
