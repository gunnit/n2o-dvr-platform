"""Programma di Miglioramento — measure rows for the DVR Master Table 109.

The audit (2026-04-28) flagged the §4.1 Programma di Miglioramento as
placeholder-only: 118 pericoli with I>=5 in the database produced zero
real rows in the generated DVR. This model persists the operator-editable
misura grid so future generations stay stable, and so the same data flows
into rigenerazioni without losing the operator's adjustments.

Each row maps to one cell row in T109:
  | misura | procedura | risorse | responsabile | scadenza |

The optional ``pericolo_valutazione_id`` link captures provenance when the
row was auto-seeded from a high-index pericolo (I >= 7). The link is
SET NULL on pericolo deletion so rigenerazioni do not silently drop the
misura — the operator can re-target it manually if the underlying pericolo
moved.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MisuraMiglioramento(Base):
    __tablename__ = "misure_miglioramento"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    azienda_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("aziende.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Optional provenance link to the high-index pericolo that triggered
    # auto-seeding. SET NULL on pericolo deletion so the operator never
    # silently loses a misura row.
    pericolo_valutazione_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pericoli_valutazione.id", ondelete="SET NULL")
    )

    # T109 columns — six free-text fields (operator-editable).
    misura: Mapped[str] = mapped_column(Text, nullable=False)
    # The concrete improvement measure (prevenzione/protezione action).
    # Added in feedback round #7; populated by AI via suggest_measures().
    misura_miglioramento: Mapped[str | None] = mapped_column(Text)
    procedura: Mapped[str | None] = mapped_column(Text)
    risorse: Mapped[str | None] = mapped_column(Text)
    responsabile: Mapped[str | None] = mapped_column(String)
    # Free-form so operators can write "Entro 6 mesi", "31/12/2026",
    # "Immediatamente", etc. The auto-seeder uses the first two.
    scadenza: Mapped[str | None] = mapped_column(String)

    # Mirrors PericoloValutazione.livello_rischio when seeded; helps the
    # renderer emit color-banded ordering. Free string so operator can
    # override (e.g., bump priority on a non-pericolo row).
    priorita: Mapped[str | None] = mapped_column(String)

    # Display order — lower first. Defaults to insertion order.
    ordine: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    azienda: Mapped["Azienda"] = relationship()  # noqa: F821
    pericolo: Mapped["PericoloValutazione | None"] = relationship()  # noqa: F821
