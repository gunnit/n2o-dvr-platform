"""store organization logo as bytes in DB (cross-service)

Revision ID: aa9f8e7d6c5b
Revises: z7a8b9c0d1e2
Create Date: 2026-06-29 00:00:00.000000

Code-review finding #1: the logo was written to the API service's Render disk,
but document generation runs on the Celery worker, which mounts a *separate*
disk (n2o-data vs n2o-data-worker, both at /data). The uploaded file was never
reachable by the generator. Move the logo into Postgres (shared by both
services) as bytes + content-type, and drop the unreachable file-path column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "aa9f8e7d6c5b"
down_revision: Union[str, None] = "z7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("logo_bytes", sa.LargeBinary(), nullable=True))
    op.add_column("organizations", sa.Column("logo_content_type", sa.String(length=64), nullable=True))
    # The old disk-path approach never worked across services; nothing to migrate.
    op.drop_column("organizations", "logo_path")


def downgrade() -> None:
    op.add_column("organizations", sa.Column("logo_path", sa.String(), nullable=True))
    op.drop_column("organizations", "logo_content_type")
    op.drop_column("organizations", "logo_bytes")
