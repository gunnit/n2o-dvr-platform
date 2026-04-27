"""Phase 3 — pericoli_libreria catalog + pericoli_valutazione 1:N rows.

Revision ID: 0a1b2c3d4e5f
Revises: f7b8c9d0e1f2
Create Date: 2026-04-27 12:00:00.000000

Until now ``valutazioni_rischio`` held one summary row per (ambiente,
categoria), squeezing all distinct pericoli into a single text blob.
The DVR template (Schede Specifiche, prova.docx.pdf) actually expects
N pericolo rows per categoria with row-level P/D scoring. This migration:

  1. Creates ``pericoli_libreria`` (catalog of 107 standard pericoli
     extracted from the N2O template) with ambiente_tipi and
     attrezzatura_keywords filter columns.
  2. Creates ``pericoli_valutazione`` — child of valutazione_rischio
     with FK to libreria (nullable for custom rows), per-row P/D, and
     computed indice_i / livello_rischio mirroring the parent table.
  3. Seeds the catalog from ``backend/app/data/pericoli_catalog.json``.
  4. Backfills: every existing ``valutazioni_rischio`` row that has a
     non-empty pericolo gets a single child row preserving the data, so
     legacy DVRs continue to render. Categoria-only rows (no pericolo
     text yet) are left without children.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID


revision: str = "0a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "f7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATALOG_PATH = (
    Path(__file__).resolve().parents[2]
    / "app" / "data" / "pericoli_catalog.json"
)


def upgrade() -> None:
    # --- pericoli_libreria (catalog) ---------------------------------------
    op.create_table(
        "pericoli_libreria",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("categoria", sa.String(), nullable=False, index=True),
        sa.Column("macro_categoria", sa.String(), nullable=False),
        sa.Column("pericolo", sa.Text(), nullable=False),
        sa.Column("condizioni_esposizione", sa.Text(), nullable=True),
        sa.Column("rischio", sa.Text(), nullable=True),
        sa.Column("misure_prevenzione", sa.Text(), nullable=True),
        sa.Column("p_default", sa.Integer(), nullable=True),
        sa.Column("d_default", sa.Integer(), nullable=True),
        sa.Column("valutazione_riferimento", sa.Text(), nullable=True),
        sa.Column(
            "ambiente_tipi",
            ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "attrezzatura_keywords",
            ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )

    # --- pericoli_valutazione (child of valutazione_rischio) ---------------
    op.create_table(
        "pericoli_valutazione",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "valutazione_rischio_id",
            UUID(as_uuid=True),
            sa.ForeignKey("valutazioni_rischio.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "pericolo_libreria_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pericoli_libreria.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source", sa.String(), nullable=False, server_default="catalog"),
        sa.Column("pericolo", sa.Text(), nullable=False),
        sa.Column("condizioni_esposizione", sa.Text(), nullable=True),
        sa.Column("rischio", sa.Text(), nullable=True),
        sa.Column("misure_prevenzione", sa.Text(), nullable=True),
        sa.Column("probabilita_p", sa.Integer(), nullable=True),
        sa.Column("danno_d", sa.Integer(), nullable=True),
        sa.Column("valutazione_riferimento", sa.Text(), nullable=True),
        sa.Column("applicabile", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ordine", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "indice_i",
            sa.Integer(),
            sa.Computed("2 * danno_d + probabilita_p", persisted=True),
        ),
        sa.Column(
            "livello_rischio",
            sa.String(),
            sa.Computed(
                "CASE "
                "WHEN (2 * danno_d + probabilita_p) <= 4 THEN 'ACCETTABILE' "
                "WHEN (2 * danno_d + probabilita_p) <= 6 THEN 'MODESTO' "
                "WHEN (2 * danno_d + probabilita_p) <= 8 THEN 'GRAVE' "
                "ELSE 'GRAVISSIMO' END",
                persisted=True,
            ),
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # --- Seed pericoli_libreria from JSON ---------------------------------
    with CATALOG_PATH.open() as f:
        catalog = json.load(f)
    pericoli_rows = []
    for p in catalog["pericoli"]:
        pericoli_rows.append(
            {
                "id": str(uuid.uuid4()),
                "code": p["code"],
                "categoria": p["categoria"],
                "macro_categoria": p["macro_categoria"],
                "pericolo": p["pericolo"],
                "condizioni_esposizione": p.get("condizioni_esposizione"),
                "rischio": p.get("rischio"),
                "misure_prevenzione": p.get("misure_prevenzione"),
                "p_default": p.get("p_default"),
                "d_default": p.get("d_default"),
                "valutazione_riferimento": p.get("valutazione_riferimento"),
                "ambiente_tipi": p.get("ambiente_tipi") or [],
                "attrezzatura_keywords": p.get("attrezzatura_keywords") or [],
            }
        )
    if pericoli_rows:
        op.bulk_insert(
            sa.table(
                "pericoli_libreria",
                sa.column("id", UUID(as_uuid=True)),
                sa.column("code", sa.String()),
                sa.column("categoria", sa.String()),
                sa.column("macro_categoria", sa.String()),
                sa.column("pericolo", sa.Text()),
                sa.column("condizioni_esposizione", sa.Text()),
                sa.column("rischio", sa.Text()),
                sa.column("misure_prevenzione", sa.Text()),
                sa.column("p_default", sa.Integer()),
                sa.column("d_default", sa.Integer()),
                sa.column("valutazione_riferimento", sa.Text()),
                sa.column("ambiente_tipi", ARRAY(sa.String())),
                sa.column("attrezzatura_keywords", ARRAY(sa.String())),
            ),
            pericoli_rows,
        )

    # --- Backfill: existing valutazioni_rischio → 1 child each -------------
    # Only rows that actually carry a pericolo text get migrated. Empty
    # placeholders stay parent-only and the new UI will populate children
    # from the catalog on next visit.
    op.execute(
        """
        INSERT INTO pericoli_valutazione (
            id, valutazione_rischio_id, pericolo_libreria_id, source,
            pericolo, condizioni_esposizione, rischio, misure_prevenzione,
            probabilita_p, danno_d, applicabile, ordine
        )
        SELECT
            gen_random_uuid(),
            v.id,
            NULL,
            'custom',
            COALESCE(NULLIF(v.pericolo, ''), v.categoria_rischio),
            v.condizioni_esposizione,
            v.rischio,
            v.misure_prevenzione,
            v.probabilita_p,
            v.danno_d,
            COALESCE(v.applicabile, true),
            0
        FROM valutazioni_rischio v
        WHERE v.pericolo IS NOT NULL AND v.pericolo <> ''
        """
    )


def downgrade() -> None:
    op.drop_table("pericoli_valutazione")
    op.drop_table("pericoli_libreria")
