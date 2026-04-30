"""MMC (Movimentazione Manuale dei Carichi) risk assessment - NIOSH method.

One row per task per worker. PLR = CP * A * B * C * D * E * F. IR = peso / PLR.
See FORMULAS_AND_CALCULATIONS.md, REFERENCE_DATA.md (NIOSH factor tables).

The model stores both the NIOSH *inputs* (altezza_cm, dislocazione_cm, ...)
and the derived *multipliers* (fattore_a..fattore_f). The inputs are needed
to render the per-worker assessment grid in the generated MMC document
(template T14 layout). The multipliers are denormalized so the document
generator and dashboards don't have to recompute on every read.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MmcValutazione(Base):
    __tablename__ = "mmc_valutazioni"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    persona_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("persone.id", ondelete="SET NULL"))
    ambiente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ambienti.id", ondelete="SET NULL"))

    # Task description
    compito: Mapped[str] = mapped_column(String, nullable=False)
    peso_kg: Mapped[float] = mapped_column(Numeric, nullable=False)
    sesso: Mapped[str] = mapped_column(String, default="M")  # M / F (for CP)
    fascia_eta: Mapped[str] = mapped_column(String, default=">18")

    # NIOSH inputs (cm / degrees / atti-min / minutes / ordinal)
    altezza_cm: Mapped[int | None] = mapped_column(Integer)
    dislocazione_cm: Mapped[int | None] = mapped_column(Integer)
    distanza_cm: Mapped[int | None] = mapped_column(Integer)
    angolo_gradi: Mapped[int | None] = mapped_column(Integer)
    giudizio_presa: Mapped[str | None] = mapped_column(String)  # Buono | Discreto | Scarso
    frequenza_atti_min: Mapped[float | None] = mapped_column(Numeric)
    durata_min: Mapped[int | None] = mapped_column(Integer)

    # NIOSH derived multipliers
    cp: Mapped[float] = mapped_column(Numeric, default=25.0)
    fattore_a: Mapped[float] = mapped_column(Numeric, default=1.0)
    fattore_b: Mapped[float] = mapped_column(Numeric, default=1.0)
    fattore_c: Mapped[float] = mapped_column(Numeric, default=1.0)
    fattore_d: Mapped[float] = mapped_column(Numeric, default=1.0)
    fattore_e: Mapped[float] = mapped_column(Numeric, default=1.0)
    fattore_f: Mapped[float] = mapped_column(Numeric, default=1.0)

    # Computed
    plr: Mapped[float | None] = mapped_column(Numeric)
    indice_ir: Mapped[float | None] = mapped_column(Numeric)
    livello_rischio: Mapped[str | None] = mapped_column(String)  # VERDE / GIALLO / ROSSO
    area_classificazione: Mapped[str | None] = mapped_column(String)  # Verde / Gialla / Rossa

    note: Mapped[str | None] = mapped_column(Text)
    misure_proposte: Mapped[str | None] = mapped_column(Text)  # Programma di Attuazione

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
