from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

persone_ambienti = Table(
    "persone_ambienti",
    Base.metadata,
    Column("persona_id", UUID(as_uuid=True), ForeignKey("persone.id", ondelete="CASCADE"), primary_key=True),
    Column("ambiente_id", UUID(as_uuid=True), ForeignKey("ambienti.id", ondelete="CASCADE"), primary_key=True),
)
