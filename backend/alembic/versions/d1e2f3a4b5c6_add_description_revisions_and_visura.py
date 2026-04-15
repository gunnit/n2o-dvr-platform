"""add description_revisions table + visura columns (US-2.1)

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-04-15 19:00:00.000000

US-2.1 AC1: visura PDF upload path. We persist the uploaded PDF on the
local disk + a locally-extracted text snippet on the row so the AI prompt
can use it without re-parsing the file. **PII never leaves the box** —
only short anonymised snippets are forwarded to the model (privacy
contract in CLAUDE.md).

US-2.1 AC2: per-azienda revision history of the descrizione_attivita.
Every AI generation and every operator save creates one row, source
tagged with ``ai`` or ``manual``. The frontend uses this to show the
"Modificato dall'utente" badge flow and the historical list with restore.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d1e2f3a4b5c6"
# Parented on the committed head ``b9c0d1e2f3a4`` (documento_generato
# options) so the chain stays valid even if the in-flight US-1.6 firma
# migration ``c1d2e3f4a5b6`` is still untracked when this lands. When that
# migration eventually lands it can re-target itself off this revision.
down_revision: Union[str, None] = "b9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "aziende",
        sa.Column("visura_pdf_path", sa.Text(), nullable=True),
    )
    op.add_column(
        "aziende",
        sa.Column("visura_extracted_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "aziende",
        sa.Column("visura_uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "description_revisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "azienda_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("aziende.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 'ai' or 'manual'. Application-level enum (kept as text so we can
        # add 'restored' / 'imported' later without a migration).
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "generated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Every list query is `WHERE azienda_id = :id ORDER BY created_at DESC`.
    op.create_index(
        "ix_description_revisions_azienda_created",
        "description_revisions",
        ["azienda_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_description_revisions_azienda_created",
        table_name="description_revisions",
    )
    op.drop_table("description_revisions")
    op.drop_column("aziende", "visura_uploaded_at")
    op.drop_column("aziende", "visura_extracted_text")
    op.drop_column("aziende", "visura_pdf_path")
