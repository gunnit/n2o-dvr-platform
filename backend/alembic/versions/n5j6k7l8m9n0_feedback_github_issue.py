"""add github_issue_number and github_issue_url to user_feedback

Revision ID: n5j6k7l8m9n0
Revises: k2g3h4i5j6k7
Create Date: 2026-05-12 00:00:00.000000

Every new feedback row gets mirrored as a GitHub issue so the team (and
later @claude) can pick it up from the repo board. Both columns nullable
because GitHub mirroring is best-effort — if the API call fails the
feedback row still exists.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "n5j6k7l8m9n0"
down_revision: Union[str, None] = "k2g3h4i5j6k7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_feedback",
        sa.Column("github_issue_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "user_feedback",
        sa.Column("github_issue_url", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_feedback", "github_issue_url")
    op.drop_column("user_feedback", "github_issue_number")
