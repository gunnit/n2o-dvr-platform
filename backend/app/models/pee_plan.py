"""Piano di Emergenza ed Evacuazione (PEE) — D.M. 02/09/2021.

Variants: aziendale (single tenant) or comunale (multi-tenant building).
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PeePlan(Base):
    __tablename__ = "pee_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String, default="azienda")  # azienda / comune
    # Emergency team
    squadra_emergenza: Mapped[list] = mapped_column(JSONB, default=list)
    addetti_primo_soccorso: Mapped[list] = mapped_column(JSONB, default=list)
    addetti_antincendio: Mapped[list] = mapped_column(JSONB, default=list)
    coordinatore_emergenza: Mapped[str | None] = mapped_column(String)
    # Contact numbers
    telefoni_emergenza: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Scenario procedures A-E
    scenari: Mapped[list] = mapped_column(JSONB, default=list)
    punto_raccolta: Mapped[str | None] = mapped_column(String)
    # Evacuation times & paths
    vie_fuga: Mapped[str | None] = mapped_column(Text)
    tempo_evacuazione_stimato_min: Mapped[int | None] = mapped_column(Integer)
    # Drill schedule
    frequenza_prove: Mapped[str] = mapped_column(String, default="annuale")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
