"""add error_message column to documenti_generati (US-2.8 AC3)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-15 15:45:00.000000

US-2.8 AC3 says: "the partial file is discarded, the document status is
rolled back to 'Bozza', and the error is logged with a user-friendly
message." The old code path hacked the error string into file_path
(``file_path = "ERROR: ..."``), which leaked the stack-trace-flavored
exception class name to the UI and confused the download endpoint's
``os.path.exists`` check.

A dedicated ``error_message`` TEXT column lets the worker:
  - clear ``file_path`` to NULL on failure (so the download endpoint
    cleanly reports "not ready" instead of probing a bogus path),
  - store a short, Italian, user-friendly line in ``error_message``,
  - let the frontend show a Bozza chip with a tooltip carrying that line.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documenti_generati",
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    # Salvage any error messages that the old code stashed in file_path so
    # historical rows still surface something useful. Anything that starts
    # with "ERROR:" is a marker from the old hack and cannot be a real path.
    op.execute(
        """
        UPDATE documenti_generati
           SET error_message = substring(file_path FROM 8),
               file_path     = NULL,
               status        = 'bozza'
         WHERE file_path LIKE 'ERROR:%'
        """
    )


def downgrade() -> None:
    op.drop_column("documenti_generati", "error_message")
