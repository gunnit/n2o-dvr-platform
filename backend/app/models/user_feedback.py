"""User-submitted feedback (bug reports, ideas, observations).

Any authenticated user can submit via the Segnala dialog in the sidebar.
Admins triage via /admin/feedback. Deliberately simple: no attachments,
no internal notes, no user-set priority — admins assign priority during
triage since user-reported priority is historically unreliable.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    type: Mapped[str] = mapped_column(String, nullable=False)  # bug | idea | observation
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Auto-captured context from the browser at submission time.
    page_url: Mapped[str | None] = mapped_column(String)
    route: Mapped[str | None] = mapped_column(String)
    user_agent: Mapped[str | None] = mapped_column(String)

    status: Mapped[str] = mapped_column(
        String, nullable=False, default="nuovo"
    )  # nuovo | in_revisione | risolto | non_fara

    # GitHub mirror — populated best-effort by services/github_issues.py
    # after the row is committed. Null if mirroring is disabled or failed.
    github_issue_number: Mapped[int | None] = mapped_column(nullable=True)
    github_issue_url: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
