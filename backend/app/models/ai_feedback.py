"""AI feedback signals (US-2.6 + US-5.3).

Records thumbs-up / thumbs-down reactions that users give to AI-generated
content (improvement measures, company descriptions, SDS extractions, etc.).
These signals feed future model tuning and give admins visibility into how
AI suggestions are performing.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AiFeedback(Base):
    __tablename__ = "ai_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"))
    azienda_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aziende.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    # What the feedback is about.
    entity_type: Mapped[str] = mapped_column(String, nullable=False)  # misura_suggerita | company_description | sds_extraction | ...
    entity_id: Mapped[str | None] = mapped_column(String)  # stable identifier within entity_type

    # The signal itself.
    signal: Mapped[str] = mapped_column(String, nullable=False)  # thumbs_down | thumbs_up
    reason: Mapped[str | None] = mapped_column(Text)

    # Free-form context so we can reproduce / analyse later without joins
    # (e.g., the AI suggestion payload, the risk category, the surrounding state).
    context: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
