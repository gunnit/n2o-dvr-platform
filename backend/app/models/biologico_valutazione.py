"""Rischio Biologico assessment — 3 variants: alimentare / asilo / dentisti.

D.Lgs. 81/2008 Titolo X + Reg. CE 852/2004 (alimentare).
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BiologicoValutazione(Base):
    __tablename__ = "biologico_valutazioni"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    settore: Mapped[str] = mapped_column(String, nullable=False)  # alimentare / asilo / dentisti
    ambiente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ambienti.id", ondelete="SET NULL"))
    # Agenti biologici identificati (lista di dict con nome, gruppo di rischio, via esposizione)
    agenti_identificati: Mapped[list] = mapped_column(JSONB, default=list)
    # Misure protettive (procedure)
    misure_protettive: Mapped[list] = mapped_column(JSONB, default=list)
    # DPI richiesti
    dpi_richiesti: Mapped[list] = mapped_column(JSONB, default=list)
    # Protocollo sanitario (vaccinazioni, sorveglianza sanitaria, esami periodici)
    protocollo_sanitario: Mapped[str | None] = mapped_column(Text)
    formazione_specifica: Mapped[str | None] = mapped_column(Text)
    livello_rischio: Mapped[str | None] = mapped_column(String)  # BASSO / MEDIO / ALTO
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
