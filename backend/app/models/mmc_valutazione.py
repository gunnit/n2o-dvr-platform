"""MMC (Movimentazione Manuale dei Carichi) risk assessment — NIOSH method.

One row per task per worker. PLR = CP × A × B × C × D × E × F. IR = peso / PLR.
See FORMULAS_AND_CALCULATIONS.md, REFERENCE_DATA.md (NIOSH factor tables).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MmcValutazione(Base):
    __tablename__ = "mmc_valutazioni"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    persona_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("persone.id", ondelete="SET NULL"))
    ambiente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ambienti.id", ondelete="SET NULL"))
    # Describe the lifting task
    compito: Mapped[str] = mapped_column(String, nullable=False)
    peso_kg: Mapped[float] = mapped_column(Numeric, nullable=False)
    sesso: Mapped[str] = mapped_column(String, default="M")  # M / F (for CP)
    fascia_eta: Mapped[str] = mapped_column(String, default=">18")
    # NIOSH factors
    cp: Mapped[float] = mapped_column(Numeric, default=25.0)  # costante di peso (kg)
    fattore_a: Mapped[float] = mapped_column(Numeric, default=1.0)  # altezza mani da terra
    fattore_b: Mapped[float] = mapped_column(Numeric, default=1.0)  # distanza verticale
    fattore_c: Mapped[float] = mapped_column(Numeric, default=1.0)  # distanza orizzontale
    fattore_d: Mapped[float] = mapped_column(Numeric, default=1.0)  # dislocazione angolare
    fattore_e: Mapped[float] = mapped_column(Numeric, default=1.0)  # giudizio presa
    fattore_f: Mapped[float] = mapped_column(Numeric, default=1.0)  # frequenza
    # Computed
    plr: Mapped[float | None] = mapped_column(Numeric)
    indice_ir: Mapped[float | None] = mapped_column(Numeric)
    livello_rischio: Mapped[str | None] = mapped_column(String)  # VERDE / GIALLO / ROSSO
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
