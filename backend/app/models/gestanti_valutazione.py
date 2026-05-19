"""Gestanti/Puerpere/Allattamento assessment — D.Lgs. 151/2001.

One row per persona (lavoratrice) che ha notificato. Mappa rischi vietati
e misure di adeguamento.
"""

import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.persona import Persona


class GestantiValutazione(Base):
    __tablename__ = "gestanti_valutazioni"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    persona_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persone.id", ondelete="CASCADE"))
    # Eager-load this when generating the allegato (lazy access raises
    # MissingGreenlet in the async session). See data_loader.load_gestanti.
    persona: Mapped["Persona"] = relationship(lazy="raise_on_sql")
    stato: Mapped[str] = mapped_column(String, default="gestante")  # gestante / puerpera / allattamento
    data_notifica: Mapped[date | None] = mapped_column(Date)
    data_presunto_parto: Mapped[date | None] = mapped_column(Date)
    # Rischi identificati (mappati agli Allegati A, B, C del D.Lgs. 151/2001)
    rischi_vietati: Mapped[list] = mapped_column(JSONB, default=list)  # list of dicts
    misure_adeguamento: Mapped[str | None] = mapped_column(Text)
    mansione_alternativa: Mapped[str | None] = mapped_column(Text)
    richiesta_astensione_anticipata: Mapped[bool] = mapped_column(Boolean, default=False)
    firma_lavoratrice: Mapped[str | None] = mapped_column(String)
    firma_datore_lavoro: Mapped[str | None] = mapped_column(String)
    firma_rspp: Mapped[str | None] = mapped_column(String)
    firma_medico_competente: Mapped[str | None] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
