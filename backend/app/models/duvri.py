"""DUVRI — Documento Unico Valutazione Rischi Interferenze.

D.Lgs. 81/2008 art. 26. Appalto con committente + ditta appaltatrice.
"""

import uuid
from datetime import datetime, date

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Duvri(Base):
    __tablename__ = "duvri"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))  # committente
    # Contractor (ditta appaltatrice)
    appaltatore_ragione_sociale: Mapped[str] = mapped_column(String, nullable=False)
    appaltatore_partita_iva: Mapped[str | None] = mapped_column(String)
    appaltatore_referente: Mapped[str | None] = mapped_column(String)
    # Contract
    oggetto_appalto: Mapped[str] = mapped_column(Text, nullable=False)
    data_inizio: Mapped[date | None] = mapped_column(Date)
    data_fine: Mapped[date | None] = mapped_column(Date)
    importo_appalto: Mapped[float | None] = mapped_column(Numeric)
    # Interferences identified
    interferenze: Mapped[list] = mapped_column(JSONB, default=list)  # list of {rischio, misure, dpi}
    # Safety costs (costi della sicurezza da interferenza)
    costi_sicurezza: Mapped[float | None] = mapped_column(Numeric)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
