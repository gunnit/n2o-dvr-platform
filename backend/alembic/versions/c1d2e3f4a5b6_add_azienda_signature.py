"""add signature columns to aziende (US-1.6 AC3/AC4)

Revision ID: c1d2e3f4a5b6
Revises: b9c0d1e2f3a4
Create Date: 2026-04-15 18:00:00.000000

US-1.6 AC3: "the signature is stored as a PNG against the survey with a
server-side timestamp and the survey lifecycle moves to status 'Firmato'."

Adds three nullable columns to ``aziende``:

  * firma_png            BYTEA — raw PNG bytes of the client signature
  * firma_signed_at      TIMESTAMPTZ — server-assigned wall-clock at the
    moment the operator confirmed the signature
  * firma_signed_by_name TEXT — optional free-text representative name
    (defaults to the persona DdL when not supplied)

The ``survey_status`` column is reused to track the post-sign lifecycle
("firmato" / "in_revisione") — no enum constraint exists today so nothing
to migrate there.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "aziende",
        sa.Column("firma_png", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "aziende",
        sa.Column("firma_signed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "aziende",
        sa.Column("firma_signed_by_name", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("aziende", "firma_signed_by_name")
    op.drop_column("aziende", "firma_signed_at")
    op.drop_column("aziende", "firma_png")
