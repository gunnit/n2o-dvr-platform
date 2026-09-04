"""Protocollo sanitario aziendale — one row per (azienda, mansione).

Segnalazione 2026-08-25: the "Protocollo sanitario aziendale" section must
be fillable with AI and must list the occupational diseases the workers
are exposed to. The protocol is deliberately per MANSIONE, never per
person: it carries the accertamenti and their cadence the Medico
Competente prescribes for a role (art. 41 D.Lgs. 81/2008), not anyone's
health record. No column here may ever hold an individual's health data.

``fonte`` records provenance for the reviewer: "ai" (AI proposal applied
as-is), "ai_modificato" (AI proposal edited by the operator) or "manuale".
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProtocolloSanitarioMansione(Base):
    __tablename__ = "protocolli_sanitari_mansioni"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    azienda_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("aziende.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mansione: Mapped[str] = mapped_column(String, nullable=False)
    # Snapshot of the aggregated rischi specifici the protocol was written
    # against: list of {code, etichetta}. Kept on the row so the DVR can
    # show what the MC actually reviewed even if the persone flags move.
    rischi_specifici: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # list of {esame, periodicita}
    accertamenti: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # Overall cadence of the visita periodica: "annuale", "biennale", ...
    periodicita: Mapped[str | None] = mapped_column(String)
    # list of {codice?, malattia, riferimento}
    malattie_correlate: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    note: Mapped[str | None] = mapped_column(Text)
    # "ai" | "manuale" | "ai_modificato"
    fonte: Mapped[str] = mapped_column(
        String, nullable=False, default="manuale", server_default="manuale"
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


# One protocol per mansione, case-insensitively: "Saldatore" and "saldatore"
# are the same role. The API normalises whitespace before matching; the
# index is the last line of defence against a race between two operators.
Index(
    "uq_protocolli_sanitari_mansioni_azienda_mansione_lower",
    ProtocolloSanitarioMansione.azienda_id,
    func.lower(ProtocolloSanitarioMansione.mansione),
    unique=True,
)
