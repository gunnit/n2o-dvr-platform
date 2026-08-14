"""luca feedback batch aug 2026

Revision ID: c2d3e4f5a6b7
Revises: b0c1d2e3f4a5
Create Date: 2026-08-14 00:00:00.000000

Schema changes for the Aug 3-5 operator feedback batch, consolidated across
four modules so the revision graph stays linear:

- VDT: per-postazione ``attivita`` label and ``data_nascita`` (drives the
  age-based sorveglianza periodicita, art. 176 c.3). Both nullable; legacy
  rows fall back to the ambiente name / ``eta_50_plus`` flag at read time.
- PEE: ``pee_plans.tipologia_allarme``; NULL means "not configured" and all
  readers fall back to the "Sirena" default, so no backfill.
- POS: cantiere fields (subappalti, dipendenti in cantiere, figure di
  sicurezza, sostanze pericolose flag). JSONB ids are Persona UUIDs stored
  as strings on purpose - no FK, generator tolerates stale ids.
- Microclima: cached IREQ outputs for the new freddo severo path (UNI EN
  ISO 11079); advisory cache only, the generator recomputes from inputs.
- Gestanti: new ``gestanti_mansioni_valutazioni`` table for the preventive
  per-mansione assessment (art. 11 D.Lgs. 151/2001) that exists with no
  pregnant worker registered.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- VDT ---
    op.add_column("vdt_valutazioni", sa.Column("attivita", sa.String(), nullable=True))
    op.add_column("vdt_valutazioni", sa.Column("data_nascita", sa.Date(), nullable=True))

    # --- PEE ---
    op.add_column("pee_plans", sa.Column("tipologia_allarme", sa.String(), nullable=True))

    # --- POS ---
    op.add_column(
        "pos",
        sa.Column(
            "sostanze_pericolose_presenti",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "pos",
        sa.Column(
            "subappalti_presenti",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    for name in ("subappaltatori", "dipendenti_cantiere", "figure_sicurezza"):
        op.add_column(
            "pos",
            sa.Column(
                name,
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
    # Rows with a populated legacy sostanze list were implicitly "presenti".
    op.execute(
        "UPDATE pos SET sostanze_pericolose_presenti = true "
        "WHERE jsonb_array_length(coalesce(sostanze_pericolose, '[]'::jsonb)) > 0"
    )

    # --- Microclima (IREQ cache) ---
    for name in ("ireq_neutral", "ireq_minimal", "t_wind_chill", "dle_freddo"):
        op.add_column("microclima_valutazioni", sa.Column(name, sa.Numeric(), nullable=True))

    # --- Gestanti preventive per-mansione assessment ---
    op.create_table(
        "gestanti_mansioni_valutazioni",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "azienda_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("aziende.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mansione", sa.String(), nullable=False),
        sa.Column("esito", sa.String(), nullable=False),
        sa.Column("rischi", postgresql.JSONB(), nullable=True),
        sa.Column("misure", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "azienda_id", "mansione", name="uq_gestanti_mansioni_azienda_mansione"
        ),
    )

    # VDT exposure is now the person-level sum of hours across postazioni.
    # The API re-syncs on every write; this backfill only spares existing
    # multi-device workers a stale flag until then.
    op.execute(
        """
        WITH person_totals AS (
          SELECT azienda_id, persona_id, SUM(ore_settimanali) AS tot
          FROM vdt_valutazioni
          WHERE persona_id IS NOT NULL
          GROUP BY azienda_id, persona_id
        )
        UPDATE vdt_valutazioni v
        SET esposto = (pt.tot >= 20)
        FROM person_totals pt
        WHERE v.azienda_id = pt.azienda_id AND v.persona_id = pt.persona_id
        """
    )


def downgrade() -> None:
    op.drop_table("gestanti_mansioni_valutazioni")
    for name in ("dle_freddo", "t_wind_chill", "ireq_minimal", "ireq_neutral"):
        op.drop_column("microclima_valutazioni", name)
    for name in (
        "figure_sicurezza",
        "dipendenti_cantiere",
        "subappaltatori",
        "subappalti_presenti",
        "sostanze_pericolose_presenti",
    ):
        op.drop_column("pos", name)
    op.drop_column("pee_plans", "tipologia_allarme")
    op.drop_column("vdt_valutazioni", "data_nascita")
    op.drop_column("vdt_valutazioni", "attivita")
