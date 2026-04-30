"""move DPI + rischi specifici from mansione to persona

Revision ID: m4i5j6k7l8m9
Revises: l3h4i5j6k7l8
Create Date: 2026-04-30 14:00:00.000000

Feedback (Luca Marchetti, 2026-04-29): "non vi siano le mansioni ma i
nominativi dei dipendenti. Per ogni dipendente, andremo a flaggare i vari
DPI e rischi a cui e' esposto." The mansione-level grouping is the wrong
unit — two saldatori in the same azienda may have genuinely different
exposures depending on their attrezzature speciali, ambienti, and tasks.

This migration:
  1. Adds dpi_codes, rischi_specifici_codes, dpi_rischi_note JSONB columns
     to persone.
  2. Fans out existing mansioni_sorveglianza rows into every persona that
     shares the mansione_nome (case-insensitive match on the trimmed name).
  3. Drops the mansioni_sorveglianza table — per-mansione bulk-apply
     becomes a UI-only convenience that copies one persona's flags to all
     persone sharing the mansione, no separate storage needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "m4i5j6k7l8m9"
down_revision: Union[str, Sequence[str], None] = "l3h4i5j6k7l8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "persone",
        sa.Column(
            "dpi_codes",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "persone",
        sa.Column(
            "rischi_specifici_codes",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "persone",
        sa.Column("dpi_rischi_note", sa.Text, nullable=True),
    )

    # Fan-out: copy each mansioni_sorveglianza row into every persona that
    # shares the mansione_nome. We match case-insensitively on the trimmed
    # mansione name, mirroring the wizard's distinctMansioni() behaviour.
    # Skip if mansioni_sorveglianza was already dropped on this DB (idempotent).
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("mansioni_sorveglianza"):
        op.execute(
            """
            UPDATE persone p
            SET
                dpi_codes = COALESCE(ms.dpi_codes, '[]'::jsonb),
                rischi_specifici_codes = COALESCE(ms.rischi_specifici_codes, '[]'::jsonb),
                dpi_rischi_note = ms.note
            FROM mansioni_sorveglianza ms
            WHERE
                ms.azienda_id = p.azienda_id
                AND lower(trim(ms.mansione_nome)) = lower(trim(p.mansione))
            """
        )
        op.drop_table("mansioni_sorveglianza")


def downgrade() -> None:
    # Recreate the mansioni_sorveglianza table and rebuild rows from the
    # per-persona data. Two persone with the same mansione but divergent
    # flags collapse into one row using the union of their codes — same
    # semantics the DVR generator now applies in output.
    op.create_table(
        "mansioni_sorveglianza",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "azienda_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("aziende.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mansione_nome", sa.String, nullable=False),
        sa.Column(
            "dpi_codes",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "rischi_specifici_codes",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "azienda_id",
            "mansione_nome",
            name="uq_mansioni_sorveglianza_azienda_mansione",
        ),
    )
    op.execute(
        """
        INSERT INTO mansioni_sorveglianza
            (azienda_id, mansione_nome, dpi_codes, rischi_specifici_codes, note)
        SELECT
            azienda_id,
            mansione,
            jsonb_agg(DISTINCT dpi)        FILTER (WHERE dpi IS NOT NULL),
            jsonb_agg(DISTINCT rs)         FILTER (WHERE rs  IS NOT NULL),
            MAX(dpi_rischi_note)
        FROM (
            SELECT
                p.azienda_id,
                p.mansione,
                jsonb_array_elements_text(p.dpi_codes) AS dpi,
                NULL::text AS rs,
                p.dpi_rischi_note
            FROM persone p
            WHERE p.mansione IS NOT NULL AND trim(p.mansione) <> ''
            UNION ALL
            SELECT
                p.azienda_id,
                p.mansione,
                NULL::text AS dpi,
                jsonb_array_elements_text(p.rischi_specifici_codes) AS rs,
                p.dpi_rischi_note
            FROM persone p
            WHERE p.mansione IS NOT NULL AND trim(p.mansione) <> ''
        ) sub
        GROUP BY azienda_id, mansione
        """
    )
    op.drop_column("persone", "dpi_rischi_note")
    op.drop_column("persone", "rischi_specifici_codes")
    op.drop_column("persone", "dpi_codes")
