"""HACCP main manual configuration + 16 self-check forms (SA-01 … SA-16).

Reg. CE 852/2004 + Reg. CE 178/2002. Mostly boilerplate + few azienda fields.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HaccpConfig(Base):
    """Main HACCP manual config for an azienda."""

    __tablename__ = "haccp_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    tipologia_attivita: Mapped[str | None] = mapped_column(String)  # ristorazione / mensa aziendale / bar / etc.
    numero_pasti_giorno: Mapped[int | None] = mapped_column()
    tipi_alimenti_trattati: Mapped[list] = mapped_column(JSONB, default=list)
    # CCPs (Critical Control Points) configurati per questa azienda
    ccps: Mapped[list] = mapped_column(JSONB, default=list)
    responsabile_haccp: Mapped[str | None] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class HaccpFormState(Base):
    """State / ultima compilazione di ciascun form SA-01…SA-16."""

    __tablename__ = "haccp_form_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    form_code: Mapped[str] = mapped_column(String, nullable=False)  # SA-01, SA-02, ..., SA-16
    form_title: Mapped[str] = mapped_column(String, nullable=False)
    # Free-form data payload for the form (list of rows)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
