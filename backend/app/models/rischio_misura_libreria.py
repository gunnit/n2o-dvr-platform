"""Per-client library of AI-accepted / user-authored risk improvement measures.

Backs US-2.6 AC2: when the operator accepts, modifies, or manually adds a
measure in the Risk Scoring Interface ("Misure di miglioramento" panel),
the resulting payload is persisted here so it can be surfaced on future
risks of the same categoria for the same azienda and tagged "Libreria"
in the UI.

Scope: one row per (azienda_id, categoria_rischio, titolo+descrizione).
Uniqueness is not enforced at DB level — two slightly different measures
with overlapping text may both live here; the UI is responsible for not
suggesting exact duplicates of what is already saved on the risk.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RischioMisuraLibreria(Base):
    __tablename__ = "rischi_misure_libreria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    azienda_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("aziende.id", ondelete="CASCADE"), nullable=False
    )
    # Categoria del rischio (matches ValutazioneRischio.categoria_rischio
    # one of: Elettrici, Meccanici, Chimici, Biologici, Fisici, Movimentazione,
    # Psicosociali, Incendio, Ergonomici, Cancerogeni, Altro).
    categoria_rischio: Mapped[str] = mapped_column(String, nullable=False)

    titolo: Mapped[str] = mapped_column(String, nullable=False)
    descrizione: Mapped[str] = mapped_column(Text, nullable=False)
    # tipo: tecnica | organizzativa | dpi | formazione | sorveglianza_sanitaria
    tipo: Mapped[str] = mapped_column(String, nullable=False, default="tecnica")
    # priorita: bassa | media | alta | urgente
    priorita: Mapped[str] = mapped_column(String, nullable=False, default="media")
    tempistica: Mapped[str] = mapped_column(String, nullable=False, default="")
    riferimento_normativo: Mapped[str | None] = mapped_column(Text)

    # provenance: how the measure landed in the library
    #   ai-accepted — AI suggestion accepted as-is
    #   ai-modified — AI suggestion accepted then edited
    #   manual      — typed from scratch
    provenance: Mapped[str] = mapped_column(String, nullable=False, default="manual")

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
