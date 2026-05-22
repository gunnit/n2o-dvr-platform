"""Microclima assessment — PMV/PPD (UNI EN ISO 7730) + PHS (UNI EN ISO 7933).

One row per ambiente.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MicroclimaValutazione(Base):
    __tablename__ = "microclima_valutazioni"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    ambiente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ambienti.id", ondelete="SET NULL"))
    nome_area: Mapped[str | None] = mapped_column(String(255))
    # Whether to evaluate moderate (PMV/PPD) or severe heat (PHS)
    tipo_ambiente: Mapped[str] = mapped_column(String, default="moderato")  # moderato / severo_caldo / severo_freddo
    # PMV/PPD inputs
    temperatura_aria: Mapped[float] = mapped_column(Numeric, default=20.0)  # °C
    temperatura_radiante: Mapped[float] = mapped_column(Numeric, default=20.0)  # °C
    velocita_aria: Mapped[float] = mapped_column(Numeric, default=0.1)  # m/s
    umidita_relativa: Mapped[float] = mapped_column(Numeric, default=50.0)  # %
    metabolismo: Mapped[float] = mapped_column(Numeric, default=1.2)  # met
    isolamento_vestiario: Mapped[float] = mapped_column(Numeric, default=0.5)  # clo
    # Computed
    pmv: Mapped[float | None] = mapped_column(Numeric)
    ppd: Mapped[float | None] = mapped_column(Numeric)
    categoria_comfort: Mapped[str | None] = mapped_column(String)  # A / B / C
    # PHS (severe heat) outputs
    phs_sw_tot: Mapped[float | None] = mapped_column(Numeric)  # sudorazione totale
    phs_t_re: Mapped[float | None] = mapped_column(Numeric)  # temperatura rettale
    dlim_loss50: Mapped[float | None] = mapped_column(Numeric)  # durata limite esposizione
    livello_rischio: Mapped[str | None] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
