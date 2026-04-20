"""Mansione-level DPI + rischi specifici for sorveglianza sanitaria.

Keyed by (azienda_id, mansione_nome) rather than persona_id because the
Medico del Lavoro writes the visite-mediche protocol per mansione, not per
individual. Multiple persone that share a mansione (e.g. three saldatori)
collapse to one row here, keeping the in-field flagging quick.

Source lists in ``services.reference_data.DPI_CATALOG`` +
``RISCHI_SPECIFICI_CATALOG`` provide the code validation; this model just
persists the operator's selections as JSON arrays of those codes.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MansioneSorveglianza(Base):
    __tablename__ = "mansioni_sorveglianza"
    __table_args__ = (
        UniqueConstraint(
            "azienda_id",
            "mansione_nome",
            name="uq_mansioni_sorveglianza_azienda_mansione",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    azienda_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("aziende.id", ondelete="CASCADE"), nullable=False
    )
    mansione_nome: Mapped[str] = mapped_column(String, nullable=False)
    dpi_codes: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    rischi_specifici_codes: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    azienda: Mapped["Azienda"] = relationship()
