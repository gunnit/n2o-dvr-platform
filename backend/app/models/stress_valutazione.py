"""Stress Lavoro-Correlato assessment — metodologia INAIL.

One row per azienda (or per gruppo omogeneo). Stores the 3 aree of INAIL
checklist: Eventi Sentinella (A), Contenuto del Lavoro (B), Contesto del Lavoro (C).
See REFERENCE_DATA.md for the 76 indicators.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StressValutazione(Base):
    __tablename__ = "stress_valutazioni"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    gruppo_omogeneo: Mapped[str] = mapped_column(String, default="Azienda intera")
    # Feedback #17: per-mansione stress assessments. NULL means "Generale"
    # (legacy / company-wide assessment). The upsert endpoint keys on
    # (azienda_id, gruppo_omogeneo, mansione) so each role gets its own row.
    mansione: Mapped[str | None] = mapped_column(String, nullable=True)
    # Each area stores the indicator responses as JSONB: {indicator_key: bool|int}
    # Scoring per INAIL method (see stress_calculator.py)
    area_a_eventi_sentinella: Mapped[dict] = mapped_column(JSONB, default=dict)
    area_b_contenuto_lavoro: Mapped[dict] = mapped_column(JSONB, default=dict)
    area_c_contesto_lavoro: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Computed totals and level
    punteggio_a: Mapped[int | None] = mapped_column(Integer)
    punteggio_b: Mapped[int | None] = mapped_column(Integer)
    punteggio_c: Mapped[int | None] = mapped_column(Integer)
    punteggio_totale: Mapped[int | None] = mapped_column(Integer)
    livello_rischio: Mapped[str | None] = mapped_column(String)  # BASSO / MEDIO / ALTO
    misure_correttive: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
