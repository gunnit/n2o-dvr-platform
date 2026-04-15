import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.persone_ambienti import persone_ambienti


class Persona(Base):
    __tablename__ = "persone"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    nominativo: Mapped[str] = mapped_column(String, nullable=False)
    codice_fiscale: Mapped[str | None] = mapped_column(String)
    mansione: Mapped[str | None] = mapped_column(String)
    tipologia_contrattuale: Mapped[str | None] = mapped_column(String)
    sesso: Mapped[str | None] = mapped_column(String)
    fascia_eta: Mapped[str | None] = mapped_column(String, default=">18")
    ruolo_rspp: Mapped[bool] = mapped_column(Boolean, default=False)
    ruolo_rls: Mapped[bool] = mapped_column(Boolean, default=False)
    ruolo_primo_soccorso: Mapped[bool] = mapped_column(Boolean, default=False)
    ruolo_antincendio: Mapped[bool] = mapped_column(Boolean, default=False)
    ruolo_preposto: Mapped[bool] = mapped_column(Boolean, default=False)
    ruolo_datore_lavoro: Mapped[bool] = mapped_column(Boolean, default=False)
    # US-1.4: free-text qualifications (attestati, patenti, corsi di formazione).
    qualifiche: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    azienda: Mapped["Azienda"] = relationship(back_populates="persone")
    ambienti: Mapped[list["Ambiente"]] = relationship(secondary=persone_ambienti, back_populates="persone")

    @property
    def ambiente_ids(self) -> list[uuid.UUID]:
        """Expose the M2M as a flat id list for serialization (US-1.4)."""
        return [a.id for a in self.ambienti]
