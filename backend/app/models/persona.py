import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
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
    ruolo_medico_competente: Mapped[bool] = mapped_column(Boolean, default=False)
    # External consultant flag (feedback #10, 2026-04-29). Many small clients
    # outsource the RSPP and the Medico Competente roles to external
    # professionals — the DVR organigramma must label them as such.
    is_esterno: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Free-text note (originally "qualifiche", now repurposed as free-form note
    # alongside the structured `attrezzature_speciali` flags introduced 2026-04-28).
    qualifiche: Mapped[str | None] = mapped_column(String)
    # Structured equipment / driving authorisations the worker is qualified for.
    # Codes from the canonical set: lavori_in_quota, trabattelli, ponteggi,
    # carrello_elevatore, ple, gru, ruspa_escavatore, patente_cde, adr.
    attrezzature_speciali: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # Per-persona DPI + rischi specifici flags (feedback 2026-04-29). The
    # Medico del Lavoro defines visite-mediche per individual, not per
    # mansione, because two saldatori can have different ambienti or
    # attrezzature speciali. Codes validated against DPI_CATALOG /
    # RISCHI_SPECIFICI_CATALOG in app.services.reference_data.
    dpi_codes: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    rischi_specifici_codes: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    dpi_rischi_note: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    azienda: Mapped["Azienda"] = relationship(back_populates="persone")
    ambienti: Mapped[list["Ambiente"]] = relationship(secondary=persone_ambienti, back_populates="persone")

    @property
    def ambiente_ids(self) -> list[uuid.UUID]:
        """Expose the M2M as a flat id list for serialization (US-1.4)."""
        return [a.id for a in self.ambienti]
