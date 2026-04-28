"""add azienda autofill fields

Revision ID: h9d0e1f2g3h4
Revises: g8c9d0e1f2g3
Create Date: 2026-04-28 12:00:00.000000

Adds the columns the AI autofill (POST /aziende/autofill) populates from
VIES + Serper + Firecrawl. All nullable so existing rows keep working and
the operator can always override.

Postal codes (CAP) and provincia stay separate from the existing free-form
``sede_legale_via`` / ``sede_operativa_via`` because VIES returns them as
distinct fields and downstream documents (DVR cover, PEE) reference them
individually.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h9d0e1f2g3h4"
down_revision: Union[str, Sequence[str], None] = "g8c9d0e1f2g3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_COLUMNS = (
    sa.Column("codice_fiscale", sa.String, nullable=True),
    sa.Column("forma_giuridica", sa.String, nullable=True),
    sa.Column("pec", sa.String, nullable=True),
    sa.Column("email", sa.String, nullable=True),
    sa.Column("telefono", sa.String, nullable=True),
    sa.Column("sito_web", sa.String, nullable=True),
    sa.Column("numero_dipendenti_dichiarati", sa.Integer, nullable=True),
    sa.Column("data_costituzione", sa.Date, nullable=True),
    sa.Column("capitale_sociale", sa.Numeric, nullable=True),
    sa.Column("rea", sa.String, nullable=True),
    sa.Column("provincia_legale", sa.String(2), nullable=True),
    sa.Column("cap_legale", sa.String(5), nullable=True),
    sa.Column("provincia_operativa", sa.String(2), nullable=True),
    sa.Column("cap_operativa", sa.String(5), nullable=True),
)


def upgrade() -> None:
    for col in _NEW_COLUMNS:
        op.add_column("aziende", col.copy())


def downgrade() -> None:
    for col in reversed(_NEW_COLUMNS):
        op.drop_column("aziende", col.name)
