"""Rischio Incendio assessment — D.M. 03/09/2021.

One row per ambiente. Score = INF + SI + PI, ciascuno 1-3.
Classificazione: 3-4 = Basso, 5-7 = Medio, 8-9 = Alto.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Computed

from app.db.base import Base


class IncendioValutazione(Base):
    __tablename__ = "incendio_valutazioni"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    ambiente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ambienti.id", ondelete="SET NULL"))
    # Inflammability / Sources of ignition / Persons (presenza persone)
    inf: Mapped[int] = mapped_column(Integer, default=1)  # 1-3
    si: Mapped[int] = mapped_column(Integer, default=1)
    pi: Mapped[int] = mapped_column(Integer, default=1)
    punteggio_totale: Mapped[int | None] = mapped_column(Integer, Computed("inf + si + pi", persisted=True))
    livello_rischio: Mapped[str | None] = mapped_column(
        String,
        Computed(
            "CASE "
            "WHEN (inf + si + pi) <= 4 THEN 'BASSO' "
            "WHEN (inf + si + pi) <= 7 THEN 'MEDIO' "
            "ELSE 'ALTO' END",
            persisted=True,
        ),
    )
    note: Mapped[str | None] = mapped_column(Text)
    misure_prevenzione: Mapped[str | None] = mapped_column(Text)
    estintori_presenti: Mapped[int] = mapped_column(Integer, default=0)
    idranti_presenti: Mapped[int] = mapped_column(Integer, default=0)
    uscite_emergenza: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
