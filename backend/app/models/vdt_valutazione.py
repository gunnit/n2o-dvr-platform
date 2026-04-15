"""VDT (Videoterminali) risk assessment — display screen equipment.

Lavoratore esposto se uso VDT >= 20 ore/settimana (D.Lgs. 81/2008 art. 173).
One row per workstation/worker.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VdtValutazione(Base):
    __tablename__ = "vdt_valutazioni"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    persona_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("persone.id", ondelete="SET NULL"))
    ambiente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ambienti.id", ondelete="SET NULL"))
    postazione: Mapped[str] = mapped_column(String, nullable=False)
    ore_settimanali: Mapped[float] = mapped_column(Numeric, default=0)
    esposto: Mapped[bool] = mapped_column(Boolean, default=False)  # >=20h/week
    # Checklist items (see REFERENCE_DATA.md VDT checklist)
    schermo_conforme: Mapped[bool] = mapped_column(Boolean, default=True)
    tastiera_separata: Mapped[bool] = mapped_column(Boolean, default=True)
    sedile_regolabile: Mapped[bool] = mapped_column(Boolean, default=True)
    poggiapiedi_disponibile: Mapped[bool] = mapped_column(Boolean, default=True)
    illuminazione_adeguata: Mapped[bool] = mapped_column(Boolean, default=True)
    riflessi_assenti: Mapped[bool] = mapped_column(Boolean, default=True)
    spazio_adeguato: Mapped[bool] = mapped_column(Boolean, default=True)
    pause_previste: Mapped[bool] = mapped_column(Boolean, default=True)
    # Outcome
    idoneita_visiva: Mapped[str | None] = mapped_column(String)  # idoneo / con prescrizioni / non idoneo
    periodicita_sorveglianza: Mapped[str | None] = mapped_column(String)  # biennale / quinquennale
    # Health-surveillance scheduling (US-3.5). 5y under 50, 2y for 50+;
    # data_prossima_visita is materialised so the dashboard widgets can do
    # a single indexed range-scan on the whole org.
    data_ultima_visita: Mapped[date | None] = mapped_column(Date)
    data_prossima_visita: Mapped[date | None] = mapped_column(Date, index=True)
    eta_50_plus: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
