"""POS — Piano Operativo di Sicurezza.

D.Lgs. 81/2008 Titolo IV Allegato XV. Costruzione — fasi lavorative.
"""

import uuid
from datetime import datetime, date

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text, func
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
    # Soggetti di riferimento — D.Lgs. 81/2008 All. XV punto 3.2.1 lettera b.
    # `coordinatore_sicurezza` historically meant the CSE (esecuzione). We
    # keep that semantic and add a separate `coordinatore_progettazione`
    # (CSP) plus the other roles Luca flagged on the 2026-05-25 POS template.
    committente: Mapped[str | None] = mapped_column(String)
    progettista_responsabile: Mapped[str | None] = mapped_column(String)
    direttore_lavori: Mapped[str | None] = mapped_column(String)
    direttore_operativo_edilizia: Mapped[str | None] = mapped_column(String)
    direttore_operativo_impianti: Mapped[str | None] = mapped_column(String)
    responsabile_lavori: Mapped[str | None] = mapped_column(String)
    coordinatore_progettazione: Mapped[str | None] = mapped_column(String)
    coordinatore_sicurezza: Mapped[str | None] = mapped_column(String)  # CSE
    data_inizio: Mapped[date | None] = mapped_column(Date)
    data_fine: Mapped[date | None] = mapped_column(Date)
    importo_lavori: Mapped[float | None] = mapped_column(Numeric)
    numero_massimo_lavoratori: Mapped[int | None] = mapped_column()
    # Modalità organizzative — All. XV punto 3.2.1 lettera c. Free-text so the
    # operator can mirror the cantiere reality (es. "07:00–12:00 / 13:00–18:00,
    # lun–ven" or "turni 6:00–14:00 / 14:00–22:00").
    orario_lavoro_cantiere: Mapped[str | None] = mapped_column(Text)
    turni_descrizione: Mapped[str | None] = mapped_column(Text)
    riunioni_coordinamento: Mapped[str | None] = mapped_column(Text)
    # Organizzazione logistica del cantiere. `monoblocchi_installati=False` is
    # the common case in small electrical/impiantistica cantieri (Luca's
    # 2026-05-25 example explicitly: "NON SARANNO INSTALLATI MONOBLOCCHI").
    monoblocchi_installati: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    monoblocchi_dettagli: Mapped[str | None] = mapped_column(Text)
    modalita_pasti: Mapped[str | None] = mapped_column(Text)
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
