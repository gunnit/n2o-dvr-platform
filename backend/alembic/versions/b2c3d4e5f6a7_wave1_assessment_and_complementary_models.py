"""wave1 assessment and complementary models

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MMC valutazioni
    op.create_table(
        "mmc_valutazioni",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("persona_id", sa.UUID(), nullable=True),
        sa.Column("ambiente_id", sa.UUID(), nullable=True),
        sa.Column("compito", sa.String(), nullable=False),
        sa.Column("peso_kg", sa.Numeric(), nullable=False),
        sa.Column("sesso", sa.String(), nullable=False),
        sa.Column("fascia_eta", sa.String(), nullable=False),
        sa.Column("cp", sa.Numeric(), nullable=False),
        sa.Column("fattore_a", sa.Numeric(), nullable=False),
        sa.Column("fattore_b", sa.Numeric(), nullable=False),
        sa.Column("fattore_c", sa.Numeric(), nullable=False),
        sa.Column("fattore_d", sa.Numeric(), nullable=False),
        sa.Column("fattore_e", sa.Numeric(), nullable=False),
        sa.Column("fattore_f", sa.Numeric(), nullable=False),
        sa.Column("plr", sa.Numeric(), nullable=True),
        sa.Column("indice_ir", sa.Numeric(), nullable=True),
        sa.Column("livello_rischio", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["persone.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ambiente_id"], ["ambienti.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    # VDT valutazioni
    op.create_table(
        "vdt_valutazioni",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("persona_id", sa.UUID(), nullable=True),
        sa.Column("ambiente_id", sa.UUID(), nullable=True),
        sa.Column("postazione", sa.String(), nullable=False),
        sa.Column("ore_settimanali", sa.Numeric(), nullable=False),
        sa.Column("esposto", sa.Boolean(), nullable=False),
        sa.Column("schermo_conforme", sa.Boolean(), nullable=False),
        sa.Column("tastiera_separata", sa.Boolean(), nullable=False),
        sa.Column("sedile_regolabile", sa.Boolean(), nullable=False),
        sa.Column("poggiapiedi_disponibile", sa.Boolean(), nullable=False),
        sa.Column("illuminazione_adeguata", sa.Boolean(), nullable=False),
        sa.Column("riflessi_assenti", sa.Boolean(), nullable=False),
        sa.Column("spazio_adeguato", sa.Boolean(), nullable=False),
        sa.Column("pause_previste", sa.Boolean(), nullable=False),
        sa.Column("idoneita_visiva", sa.String(), nullable=True),
        sa.Column("periodicita_sorveglianza", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["persone.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ambiente_id"], ["ambienti.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Stress
    op.create_table(
        "stress_valutazioni",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("gruppo_omogeneo", sa.String(), nullable=False),
        sa.Column("area_a_eventi_sentinella", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("area_b_contenuto_lavoro", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("area_c_contesto_lavoro", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("punteggio_a", sa.Integer(), nullable=True),
        sa.Column("punteggio_b", sa.Integer(), nullable=True),
        sa.Column("punteggio_c", sa.Integer(), nullable=True),
        sa.Column("punteggio_totale", sa.Integer(), nullable=True),
        sa.Column("livello_rischio", sa.String(), nullable=True),
        sa.Column("misure_correttive", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Incendio
    op.create_table(
        "incendio_valutazioni",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("ambiente_id", sa.UUID(), nullable=True),
        sa.Column("inf", sa.Integer(), nullable=False),
        sa.Column("si", sa.Integer(), nullable=False),
        sa.Column("pi", sa.Integer(), nullable=False),
        sa.Column("punteggio_totale", sa.Integer(), sa.Computed("inf + si + pi", persisted=True), nullable=True),
        sa.Column(
            "livello_rischio",
            sa.String(),
            sa.Computed(
                "CASE WHEN (inf + si + pi) <= 4 THEN 'BASSO' "
                "WHEN (inf + si + pi) <= 7 THEN 'MEDIO' ELSE 'ALTO' END",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("misure_prevenzione", sa.Text(), nullable=True),
        sa.Column("estintori_presenti", sa.Integer(), nullable=False),
        sa.Column("idranti_presenti", sa.Integer(), nullable=False),
        sa.Column("uscite_emergenza", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ambiente_id"], ["ambienti.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Microclima
    op.create_table(
        "microclima_valutazioni",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("ambiente_id", sa.UUID(), nullable=True),
        sa.Column("tipo_ambiente", sa.String(), nullable=False),
        sa.Column("temperatura_aria", sa.Numeric(), nullable=False),
        sa.Column("temperatura_radiante", sa.Numeric(), nullable=False),
        sa.Column("velocita_aria", sa.Numeric(), nullable=False),
        sa.Column("umidita_relativa", sa.Numeric(), nullable=False),
        sa.Column("metabolismo", sa.Numeric(), nullable=False),
        sa.Column("isolamento_vestiario", sa.Numeric(), nullable=False),
        sa.Column("pmv", sa.Numeric(), nullable=True),
        sa.Column("ppd", sa.Numeric(), nullable=True),
        sa.Column("categoria_comfort", sa.String(), nullable=True),
        sa.Column("phs_sw_tot", sa.Numeric(), nullable=True),
        sa.Column("phs_t_re", sa.Numeric(), nullable=True),
        sa.Column("dlim_loss50", sa.Numeric(), nullable=True),
        sa.Column("livello_rischio", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ambiente_id"], ["ambienti.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Gestanti
    op.create_table(
        "gestanti_valutazioni",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("persona_id", sa.UUID(), nullable=False),
        sa.Column("stato", sa.String(), nullable=False),
        sa.Column("data_notifica", sa.Date(), nullable=True),
        sa.Column("data_presunto_parto", sa.Date(), nullable=True),
        sa.Column("rischi_vietati", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("misure_adeguamento", sa.Text(), nullable=True),
        sa.Column("mansione_alternativa", sa.Text(), nullable=True),
        sa.Column("richiesta_astensione_anticipata", sa.Boolean(), nullable=False),
        sa.Column("firma_lavoratrice", sa.String(), nullable=True),
        sa.Column("firma_datore_lavoro", sa.String(), nullable=True),
        sa.Column("firma_rspp", sa.String(), nullable=True),
        sa.Column("firma_medico_competente", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["persone.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Biologico
    op.create_table(
        "biologico_valutazioni",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("settore", sa.String(), nullable=False),
        sa.Column("ambiente_id", sa.UUID(), nullable=True),
        sa.Column("agenti_identificati", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("misure_protettive", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("dpi_richiesti", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("protocollo_sanitario", sa.Text(), nullable=True),
        sa.Column("formazione_specifica", sa.Text(), nullable=True),
        sa.Column("livello_rischio", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ambiente_id"], ["ambienti.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    # HACCP Config
    op.create_table(
        "haccp_config",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("tipologia_attivita", sa.String(), nullable=True),
        sa.Column("numero_pasti_giorno", sa.Integer(), nullable=True),
        sa.Column("tipi_alimenti_trattati", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("ccps", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("responsabile_haccp", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # HACCP form states
    op.create_table(
        "haccp_form_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("form_code", sa.String(), nullable=False),
        sa.Column("form_title", sa.String(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # PEE
    op.create_table(
        "pee_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("squadra_emergenza", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("addetti_primo_soccorso", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("addetti_antincendio", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("coordinatore_emergenza", sa.String(), nullable=True),
        sa.Column("telefoni_emergenza", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("scenari", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("punto_raccolta", sa.String(), nullable=True),
        sa.Column("vie_fuga", sa.Text(), nullable=True),
        sa.Column("tempo_evacuazione_stimato_min", sa.Integer(), nullable=True),
        sa.Column("frequenza_prove", sa.String(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # DUVRI
    op.create_table(
        "duvri",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("appaltatore_ragione_sociale", sa.String(), nullable=False),
        sa.Column("appaltatore_partita_iva", sa.String(), nullable=True),
        sa.Column("appaltatore_referente", sa.String(), nullable=True),
        sa.Column("oggetto_appalto", sa.Text(), nullable=False),
        sa.Column("data_inizio", sa.Date(), nullable=True),
        sa.Column("data_fine", sa.Date(), nullable=True),
        sa.Column("importo_appalto", sa.Numeric(), nullable=True),
        sa.Column("interferenze", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("costi_sicurezza", sa.Numeric(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # POS
    op.create_table(
        "pos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("azienda_id", sa.UUID(), nullable=False),
        sa.Column("cantiere_indirizzo", sa.String(), nullable=False),
        sa.Column("cantiere_descrizione", sa.Text(), nullable=True),
        sa.Column("committente", sa.String(), nullable=True),
        sa.Column("direttore_lavori", sa.String(), nullable=True),
        sa.Column("coordinatore_sicurezza", sa.String(), nullable=True),
        sa.Column("data_inizio", sa.Date(), nullable=True),
        sa.Column("data_fine", sa.Date(), nullable=True),
        sa.Column("importo_lavori", sa.Numeric(), nullable=True),
        sa.Column("numero_massimo_lavoratori", sa.Integer(), nullable=True),
        sa.Column("fasi_lavorative", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("valutazione_rumore", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("valutazione_vibrazioni", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("mezzi_attrezzature", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("sostanze_pericolose", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["azienda_id"], ["aziende.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Audit log
    op.create_table(
        "audit_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column("changes", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("pos")
    op.drop_table("duvri")
    op.drop_table("pee_plans")
    op.drop_table("haccp_form_states")
    op.drop_table("haccp_config")
    op.drop_table("biologico_valutazioni")
    op.drop_table("gestanti_valutazioni")
    op.drop_table("microclima_valutazioni")
    op.drop_table("incendio_valutazioni")
    op.drop_table("stress_valutazioni")
    op.drop_table("vdt_valutazioni")
    op.drop_table("mmc_valutazioni")
