"""Catalog of standard pericoli (hazards) used by the DVR Schede Specifiche.

Source of truth: ``backend/app/data/pericoli_catalog.json`` — extracted from
the N2O standard "Schede Specifiche con l'Individuazione dei pericoli"
(prova.docx.pdf, 2026-04-24). Seeded into this table by the migration that
introduces it. One row per (categoria, condizioni, pericolo) — codes are
stable (e.g. ST-01..22 for Strutture).

Per-azienda surveys reference these rows from ``pericolo_valutazione``
(child of ``valutazione_rischio``); they may also create custom child rows
that don't reference the catalog when something specific needs to be added.

ambiente_tipi and attrezzatura_keywords drive the suggester:
  - empty ambiente_tipi means "applies to all environments";
  - non-empty means the pericolo only surfaces when the ambiente.tipo
    matches one of the listed canonical buckets;
  - attrezzatura_keywords are case-insensitive substrings — when an
    attrezzatura.descrizione contains one, the pericolo is added even
    if the ambiente filter would have hidden it (equipment override).
"""
from __future__ import annotations

import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PericoloLibreria(Base):
    __tablename__ = "pericoli_libreria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Stable human-readable identifier (e.g. "ST-01", "MA-14"). Unique.
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)

    # Canonical long-form categoria (matches reference_data.RISK_CATEGORIES).
    categoria: Mapped[str] = mapped_column(String, nullable=False, index=True)
    macro_categoria: Mapped[str] = mapped_column(String, nullable=False)

    pericolo: Mapped[str] = mapped_column(Text, nullable=False)
    condizioni_esposizione: Mapped[str | None] = mapped_column(Text)
    rischio: Mapped[str | None] = mapped_column(Text)
    misure_prevenzione: Mapped[str | None] = mapped_column(Text)

    # Default scoring from the source PDF — null when scoring lives in a
    # separate allegato (most Incendio/Chimici/Biologici/Cancerogeni rows).
    p_default: Mapped[int | None] = mapped_column(Integer)
    d_default: Mapped[int | None] = mapped_column(Integer)
    # Free-text marker for rows that delegate to allegati or normativa
    # (e.g. "Come da documenti allegati", "Vedi normativa specifica
    # (D.Lgs. 151/2001)"). Surface this in the UI so the operator knows
    # the row is informational here.
    valutazione_riferimento: Mapped[str | None] = mapped_column(Text)

    # Filter controls (Phase 3 tagging — see scripts/tag_pericoli_catalog.py).
    # Empty array = applies to all ambiente tipi (universal).
    ambiente_tipi: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    attrezzatura_keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
