"""Per-azienda revision history for the DVR Part I company description.

US-2.1 AC2: every AI generation and every operator save snapshots one row,
``source`` tagged ``ai`` or ``manual``. The frontend list+restore lives in
``frontend/src/components/ai/description-history.tsx``.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Allowed string values for ``DescriptionRevision.source``. Kept as a plain
# tuple (not an Enum) so we can append values without a migration — the
# column is just text.
SOURCE_AI = "ai"
SOURCE_MANUAL = "manual"
ALLOWED_SOURCES: tuple[str, ...] = (SOURCE_AI, SOURCE_MANUAL)


class DescriptionRevision(Base):
    __tablename__ = "description_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    azienda_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("aziende.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
