"""POS — Piano Operativo di Sicurezza.

D.Lgs. 81/2008 Titolo IV Allegato XV. Costruzione — fasi lavorative.
"""

import uuid
from datetime import datetime, date

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Pos(Base):
    __tablename__ = "pos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    # Cantiere
    cantiere_indirizzo: Mapped[str] = mapped_column(String, nullable=False)
    cantiere_descrizione: Mapped[str | None] = mapped_column(Text)
    committente: Mapped[str | None] = mapped_column(String)
    direttore_lavori: Mapped[str | None] = mapped_column(String)
    coordinatore_sicurezza: Mapped[str | None] = mapped_column(String)
    data_inizio: Mapped[date | None] = mapped_column(Date)
    data_fine: Mapped[date | None] = mapped_column(Date)
    importo_lavori: Mapped[float | None] = mapped_column(Numeric)
    numero_massimo_lavoratori: Mapped[int | None] = mapped_column()
    # Typical work phases (JSON list of dicts: {fase, descrizione, rischi, dpi, mezzi})
    fasi_lavorative: Mapped[list] = mapped_column(JSONB, default=list)
    # Noise, vibration, NIOSH per phase (summary)
    valutazione_rumore: Mapped[dict] = mapped_column(JSONB, default=dict)
    valutazione_vibrazioni: Mapped[dict] = mapped_column(JSONB, default=dict)
    mezzi_attrezzature: Mapped[list] = mapped_column(JSONB, default=list)
    sostanze_pericolose: Mapped[list] = mapped_column(JSONB, default=list)
    # DPI matrix (US-4.8): {phase_key: {role_key: [dpi_codes]}} — operator-edited
    # copy. Starts empty; populated on first "rigenera dai default" call or via
    # cell override. See services/dpi_rules.py for the rule engine.
    dpi_matrix: Mapped[dict] = mapped_column(JSONB, default=dict)
    dpi_matrix_roles: Mapped[list] = mapped_column(JSONB, default=list)
    dpi_matrix_phases: Mapped[list] = mapped_column(JSONB, default=list)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
