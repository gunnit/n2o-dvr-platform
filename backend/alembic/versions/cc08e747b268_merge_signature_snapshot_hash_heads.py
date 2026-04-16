"""merge signature + snapshot hash heads

Revision ID: cc08e747b268
Revises: c1d2e3f4a5b6, d3e4f5a6b7c8
Create Date: 2026-04-17 00:21:27.395922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc08e747b268'
down_revision: Union[str, None] = ('c1d2e3f4a5b6', 'd3e4f5a6b7c8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
