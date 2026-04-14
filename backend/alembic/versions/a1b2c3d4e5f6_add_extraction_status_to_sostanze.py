"""add extraction_status and extraction_error to sostanze_chimiche

Revision ID: a1b2c3d4e5f6
Revises: 96e1f6c7aaf0
Create Date: 2026-04-14 10:00:00.000000

Tracks async SDS extraction lifecycle:
  - pending    : queued, extractor not yet started
  - processing : extractor running
  - completed  : extractor returned successfully (ai_confidence populated)
  - failed     : extractor raised AIError (reason stored in extraction_error)

Manual entries (ai_extracted=False) have extraction_status=NULL and are
exempt from polling.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '96e1f6c7aaf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sostanze_chimiche',
        sa.Column('extraction_status', sa.String(), nullable=True),
    )
    op.add_column(
        'sostanze_chimiche',
        sa.Column('extraction_error', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('sostanze_chimiche', 'extraction_error')
    op.drop_column('sostanze_chimiche', 'extraction_status')
