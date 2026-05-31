"""Chemical-risk exposure (MoVaRisCh) — one row per (worker x substance).

Mirrors the MMC pattern: stores both the exposure *inputs* (AI-suggested,
operator-reviewed) and the derived *results* (P, Einal, Rinal, Ecute, Rcute,
Rcum, livelli) denormalized so the document generator and dashboards don't
recompute on every read. The maths lives in
``app.services.movarisch_calculator``; see
``docs/context/RISCHIO_CHIMICO_MAPPING.md``.

Decision (2026-05-30): exposure is modelled per worker per substance, the
inputs are AI-suggested then human-reviewed, and the inhalation route is
computed with the model-correct rule (Einal = I*d > 0), not the source tool's
D=0 artifact.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RischioChimicoEsposizione(Base):
    __tablename__ = "rischio_chimico_esposizioni"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    persona_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("persone.id", ondelete="SET NULL"))
    sostanza_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sostanze_chimiche.id", ondelete="SET NULL")
    )
    ambiente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ambienti.id", ondelete="SET NULL"))

    # --- Exposure inputs (AI-suggested, human-reviewed) ---
    # Free-text option strings matching the documented MoVaRisCh option sets
    # (see movarisch_calculator Literals / movarisch_reference.json).
    proprieta_fisiche: Mapped[str | None] = mapped_column(String)      # volatility tier
    quantita_classe: Mapped[str | None] = mapped_column(String)
    tipologia_uso: Mapped[str | None] = mapped_column(String)
    tipologia_controllo: Mapped[str | None] = mapped_column(String)
    tempo_esposizione: Mapped[str | None] = mapped_column(String)
    distanza_classe: Mapped[str | None] = mapped_column(String)
    via_cutanea_applicabile: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    contatto_cutaneo: Mapped[str | None] = mapped_column(String)

    # --- Derived results (denormalized; recomputed server-side on save) ---
    p_score: Mapped[float | None] = mapped_column(Numeric)
    governing_code: Mapped[str | None] = mapped_column(String)      # the H/R code that set P
    is_cancerogeno: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    d_ind: Mapped[int | None] = mapped_column(Integer)              # disponibilità
    u_ind: Mapped[int | None] = mapped_column(Integer)              # uso
    c_ind: Mapped[int | None] = mapped_column(Integer)              # compensazione
    i_ind: Mapped[int | None] = mapped_column(Integer)             # intensità

    einal: Mapped[float | None] = mapped_column(Numeric)
    rinal: Mapped[float | None] = mapped_column(Numeric)
    ecute: Mapped[int | None] = mapped_column(Integer)
    rcute: Mapped[float | None] = mapped_column(Numeric)
    rcum: Mapped[float | None] = mapped_column(Numeric)
    r_governing: Mapped[float | None] = mapped_column(Numeric)

    zona: Mapped[str | None] = mapped_column(String)               # VERDE/ARANCIO/GIALLO/ROSSA/NERA
    livello_salute: Mapped[str | None] = mapped_column(String)     # Irrilevante / Superiore
    livello_sicurezza: Mapped[str | None] = mapped_column(String)  # Basso / Non Basso

    # --- Lifecycle ---
    ai_suggested: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    note: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
