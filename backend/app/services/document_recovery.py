"""Reclaim document rows abandoned mid-generation.

`document_tasks._run_generation` already rolls a row back to "bozza" when the
generator raises, and gives up with a message after
``MAX_GENERATION_ATTEMPTS``. Both of those need the task to actually reach a
worker. A row whose Celery message died with the worker — a redeploy, an OOM
kill, a broker eviction — is never redelivered, so it sits at "pending" or
"in_progress" forever: an eternal spinner in the Documenti tab with no error
to explain it and no way for the operator to retry.

Production accumulated 25 such rows between 2026-07-28 and 2026-08-04, all
with ``error_message = NULL``. This sweep closes them out on API startup.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import or_, select, update

from app.models.documento_generato import DocumentoGenerato

logger = logging.getLogger(__name__)

# The document task's own ceiling is time_limit=660s (11 min); the Celery app
# ceiling is 20 min. Past 30 minutes nothing can still legitimately be running,
# so anything older than this that is still unfinished has been abandoned.
ABANDONED_AFTER_MINUTES = 30

ABANDONED_GENERATION_ERROR = (
    "Generazione interrotta (servizio riavviato). Riprova a generare il documento."
)

_UNFINISHED = ("pending", "in_progress")


async def reclaim_abandoned_generations(
    db, older_than_minutes: int = ABANDONED_AFTER_MINUTES
) -> int:
    """Mark long-unfinished generations as "bozza" with a retryable message.

    Returns how many rows were reclaimed. Idempotent and safe to run from
    several API instances at once: the UPDATE re-checks the status, so a row
    that a worker finished in the meantime is left alone.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=older_than_minutes)

    # `generation_started_at` is set when a worker picks the row up; rows that
    # never got that far ("pending") are aged off `created_at` instead.
    stale = or_(
        DocumentoGenerato.generation_started_at < cutoff,
        (DocumentoGenerato.generation_started_at.is_(None))
        & (DocumentoGenerato.created_at < cutoff),
    )

    result = await db.execute(
        update(DocumentoGenerato)
        .where(DocumentoGenerato.status.in_(_UNFINISHED), stale)
        .values(
            status="bozza",
            error_message=ABANDONED_GENERATION_ERROR,
            generation_completed_at=datetime.utcnow(),
            file_path=None,
        )
        .execution_options(synchronize_session=False)
    )
    await db.commit()

    reclaimed = result.rowcount or 0
    if reclaimed:
        logger.warning(
            "reclaimed %d document generation(s) abandoned for more than %d minutes",
            reclaimed,
            older_than_minutes,
        )
    return reclaimed


async def count_unfinished(db) -> int:
    """Rows currently mid-generation. Used by tests and by the startup log."""
    rows = await db.execute(
        select(DocumentoGenerato.id).where(DocumentoGenerato.status.in_(_UNFINISHED))
    )
    return len(rows.all())
