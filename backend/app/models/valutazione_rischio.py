import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import Computed

from app.db.base import Base


class ValutazioneRischio(Base):
    __tablename__ = "valutazioni_rischio"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ambiente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ambienti.id", ondelete="CASCADE"))
    categoria_rischio: Mapped[str] = mapped_column(String, nullable=False)
    applicabile: Mapped[bool] = mapped_column(Boolean, default=False)
    pericolo: Mapped[str | None] = mapped_column(Text)
    condizioni_esposizione: Mapped[str | None] = mapped_column(Text)
    rischio: Mapped[str | None] = mapped_column(Text)
    misure_prevenzione: Mapped[str | None] = mapped_column(Text)
    probabilita_p: Mapped[int | None] = mapped_column(Integer)
    danno_d: Mapped[int | None] = mapped_column(Integer)
    indice_i: Mapped[int | None] = mapped_column(Integer, Computed("2 * danno_d + probabilita_p", persisted=True))
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

    ambiente: Mapped["Ambiente"] = relationship(back_populates="valutazioni_rischio")
    # Phase 3 (1:N) — child rows from the Schede Specifiche pericoli catalog.
    # The legacy single-block pericolo/condizioni/rischio/misure fields above
    # remain for back-compat (auto-derived from the first child by the
    # generator) but new code should iterate `pericoli`.
    pericoli: Mapped[list["PericoloValutazione"]] = relationship(  # noqa: F821
        back_populates="valutazione_rischio",
        cascade="all, delete-orphan",
        order_by="PericoloValutazione.ordine",
    )
