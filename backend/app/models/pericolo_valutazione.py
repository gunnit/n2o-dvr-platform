"""Per-azienda pericolo row — child of ``valutazione_rischio``.

The DVR Schede Specifiche assign multiple distinct pericolo rows to each
risk category (e.g. Macchine has 14 standard rows). Until Phase 3 the
codebase modelled one summary block per (ambiente, categoria), losing the
row-by-row P/D detail required by the template's table layout.

This model restores the 1:N: each ValutazioneRischio (categoria header for
an ambiente) has a list of PericoloValutazione children, one per surveyed
hazard. Children may reference a PericoloLibreria catalog entry (typical)
or stand alone (custom row added by the operator).

The ``probabilita_p`` / ``danno_d`` pair lives on the child so each row
can be scored independently. ``indice_i`` and ``livello_rischio`` are
computed columns mirroring ValutazioneRischio's formulas (I = 2*D + P).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import Computed

from app.db.base import Base


class PericoloValutazione(Base):
    __tablename__ = "pericoli_valutazione"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    valutazione_rischio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("valutazioni_rischio.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Optional FK to the catalog. Null when the operator typed a custom row.
    pericolo_libreria_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pericoli_libreria.id", ondelete="SET NULL")
    )
    # Provenance: 'catalog' (originated from PericoloLibreria, may be edited),
    # 'custom' (typed from scratch). Helps the UI badge rows and helps the
    # generator know when to fall back to the catalog text.
    source: Mapped[str] = mapped_column(String, nullable=False, default="catalog")

    # Denormalized text — copied from the catalog at insert time so future
    # edits to the catalog don't silently rewrite finalized DVRs. The operator
    # can also override these strings inline without losing the catalog link.
    pericolo: Mapped[str] = mapped_column(Text, nullable=False)
    condizioni_esposizione: Mapped[str | None] = mapped_column(Text)
    rischio: Mapped[str | None] = mapped_column(Text)
    misure_prevenzione: Mapped[str | None] = mapped_column(Text)

    # Per-row scoring. Null while pending (e.g. catalog rows whose default
    # P/D is null because scoring belongs to an allegato).
    probabilita_p: Mapped[int | None] = mapped_column(Integer)
    danno_d: Mapped[int | None] = mapped_column(Integer)
    valutazione_riferimento: Mapped[str | None] = mapped_column(Text)

    # Operator can untick a suggested row to keep it visible-but-not-applied.
    applicabile: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Display order within the categoria (defaults to insertion order).
    ordine: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    indice_i: Mapped[int | None] = mapped_column(
        Integer, Computed("2 * danno_d + probabilita_p", persisted=True)
    )
    livello_rischio: Mapped[str | None] = mapped_column(
        String,
        Computed(
            "CASE "
            "WHEN (2 * danno_d + probabilita_p) <= 4 THEN 'ACCETTABILE' "
            "WHEN (2 * danno_d + probabilita_p) <= 6 THEN 'MODESTO' "
            "WHEN (2 * danno_d + probabilita_p) <= 8 THEN 'GRAVE' "
            "ELSE 'GRAVISSIMO' END",
            persisted=True,
        ),
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    valutazione_rischio: Mapped["ValutazioneRischio"] = relationship(  # noqa: F821
        back_populates="pericoli"
    )
    libreria: Mapped["PericoloLibreria | None"] = relationship()  # noqa: F821
