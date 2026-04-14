"""add partita_iva to aziende

Revision ID: 96e1f6c7aaf0
Revises: 16ede39998d6
Create Date: 2026-04-13 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '96e1f6c7aaf0'
down_revision: Union[str, None] = '16ede39998d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('aziende', sa.Column('partita_iva', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('aziende', 'partita_iva')
