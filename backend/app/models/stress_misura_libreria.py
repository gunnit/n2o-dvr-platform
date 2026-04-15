"""Per-client library of user-edited or user-authored stress corrective measures.

Backs US-3.8 AC2/AC3: when the operator edits one of the default suggested
measures (or adds a new one from scratch) on the stress assessment page,
the resulting text is persisted here so it can be reused on subsequent
valutazioni for the same azienda, tagged as "Personalizzato" in the UI.

Scope: one row per (azienda_id, livello_rischio, testo). We do NOT dedupe
at DB level — two identical edits would be saved twice; the UI is
responsible for surfacing only distinct entries when it lists them.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StressMisuraLibreria(Base):
    __tablename__ = "stress_misure_libreria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    azienda_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("aziende.id", ondelete="CASCADE"), nullable=False
    )
    # Band the measure applies to — one of Basso / Medio / Alto.
    # (UI Livello values are upper-cased; the domain wording here is
    # title-case per the spec.)
    livello_rischio: Mapped[str] = mapped_column(String, nullable=False)
    testo: Mapped[str] = mapped_column(Text, nullable=False)
    personalizzato: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
