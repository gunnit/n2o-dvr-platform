"""add organization branding fields

Revision ID: z7a8b9c0d1e2
Revises: y6z7a8b9c0d1
Create Date: 2026-06-28 00:00:00.000000

Per-organization branding/letterhead (see
docs/superpowers/specs/2026-06-28-org-branding-design.md). Turns the
hardcoded N2O consultancy identity into editable data. All columns nullable
so existing rows and document output are unaffected until an admin sets them.
``organizations.name`` doubles as the firm name on the letterhead.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "z7a8b9c0d1e2"
down_revision: Union[str, None] = "y6z7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COLUMNS = [
    ("logo_path", sa.String()),
    ("indirizzo", sa.String()),
    ("cap", sa.String(length=16)),
    ("citta", sa.String()),
    ("provincia", sa.String(length=8)),
    ("partita_iva", sa.String(length=32)),
    ("codice_fiscale", sa.String(length=32)),
    ("telefono", sa.String(length=64)),
    ("email", sa.String()),
    ("sito_web", sa.String()),
    ("rspp_nome", sa.String()),
]


def upgrade() -> None:
    for name, col_type in _COLUMNS:
        op.add_column("organizations", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        op.drop_column("organizations", name)
