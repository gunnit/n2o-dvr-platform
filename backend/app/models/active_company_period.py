"""Active company period — the Model A meter.

Consultant plans are priced by *how many client companies you actually work on
per period*, not by how many rows sit in the database. A company becomes
"active" the first time a document completes for it in a period.

The composite primary key (org, azienda, period) is what makes the write
retry-safe: every completion path inserts with ON CONFLICT DO NOTHING, so a
Celery retry, a document restore, a Google-Doc sync, and a save-edited-version
all converge on the same single row instead of double-counting (INV-6).

The worker's insert is the *record*; the ``max_companies`` gate is enforced
synchronously at the API so the user gets a 402 instead of a silently failed
background job.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActiveCompanyPeriod(Base):
    __tablename__ = "active_company_periods"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    azienda_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("aziende.id", ondelete="CASCADE"), primary_key=True
    )
    period_start: Mapped[date] = mapped_column(Date, primary_key=True)

    first_activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
