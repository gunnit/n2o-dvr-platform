"""Health-surveillance alerts (US-3.5).

Feeds the "Visite in scadenza" and "Visite scadute" dashboard widgets.
Scoped to the authenticated user's organization — cross-azienda so the
consultant can see every worker nearing a due date across their entire
client portfolio in one glance.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.persona import Persona
from app.models.vdt_valutazione import VdtValutazione
from app.services.vdt_surveillance import IN_SCADENZA_WINDOW_DAYS, SurveillanceBucket, bucket_for

router = APIRouter(prefix="/sorveglianza", tags=["sorveglianza"])


class SurveillanceWorkerRow(BaseModel):
    """One worker surfaced in a widget."""

    valutazione_id: uuid.UUID
    azienda_id: uuid.UUID
    azienda_ragione_sociale: str
    persona_id: uuid.UUID | None
    nominativo: str | None
    postazione: str
    data_ultima_visita: date | None
    data_prossima_visita: date
    periodicita_sorveglianza: str | None
    eta_50_plus: bool
    days_until_due: int  # negative when already scadute

    model_config = {"from_attributes": True}


class SurveillanceAlertsResponse(BaseModel):
    in_scadenza: list[SurveillanceWorkerRow]
    scadute: list[SurveillanceWorkerRow]
    as_of: date
    window_days: int


@router.get("/alerts", response_model=SurveillanceAlertsResponse)
async def surveillance_alerts(
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> SurveillanceAlertsResponse:
    """List workers needing a VDT eye exam soon or already overdue.

    Returned buckets:
      - ``in_scadenza``: next visit due within the next 60 days (inclusive).
      - ``scadute``: next visit date is in the past.

    Both lists are sorted by ``data_prossima_visita`` ascending — the
    most urgent row first in each widget. A row with
    ``data_prossima_visita IS NULL`` is skipped entirely (not esposto or
    never scheduled); the VDT module is responsible for populating the
    column on classification.
    """
    today = datetime.now(timezone.utc).date()
    horizon = today.replace(day=today.day)  # simple copy for clarity
    # Date arithmetic done in Python to sidestep dialect quirks.
    from datetime import timedelta

    window_end = today + timedelta(days=IN_SCADENZA_WINDOW_DAYS)

    # Fetch only rows that would land in one of the two buckets. Eager
    # load persona + azienda so the response can include the operator-
    # facing labels without an N+1.
    stmt = (
        select(VdtValutazione)
        .join(Azienda, Azienda.id == VdtValutazione.azienda_id)
        .where(
            Azienda.organization_id == org_id,
            VdtValutazione.esposto.is_(True),
            VdtValutazione.data_prossima_visita.is_not(None),
            or_(
                VdtValutazione.data_prossima_visita < today,
                and_(
                    VdtValutazione.data_prossima_visita >= today,
                    VdtValutazione.data_prossima_visita <= window_end,
                ),
            ),
        )
        .options(
            selectinload(VdtValutazione.azienda),  # type: ignore[arg-type]
        )
        .order_by(VdtValutazione.data_prossima_visita.asc())
    )
    rows: list[VdtValutazione] = list((await db.execute(stmt)).scalars().all())

    # Resolve persona names in one round-trip. We don't eager-load Persona
    # because VdtValutazione.persona_id is a SET NULL FK with no back-ref
    # configured, and for this read-only response a side lookup is cleaner
    # than adding a relationship just for this endpoint.
    persona_ids = {r.persona_id for r in rows if r.persona_id is not None}
    persone_by_id: dict[uuid.UUID, Persona] = {}
    if persona_ids:
        persone_stmt = select(Persona).where(Persona.id.in_(persona_ids))
        persone_by_id = {p.id: p for p in (await db.execute(persone_stmt)).scalars().all()}

    in_scadenza: list[SurveillanceWorkerRow] = []
    scadute: list[SurveillanceWorkerRow] = []

    for r in rows:
        bucket = bucket_for(r.data_prossima_visita, today)
        if bucket not in (SurveillanceBucket.SCADUTE, SurveillanceBucket.IN_SCADENZA):
            continue  # defensive: the SQL filter already excludes these
        assert r.data_prossima_visita is not None  # narrowed by SQL + bucket_for

        persona = persone_by_id.get(r.persona_id) if r.persona_id else None
        days_delta = (r.data_prossima_visita - today).days

        row = SurveillanceWorkerRow(
            valutazione_id=r.id,
            azienda_id=r.azienda_id,
            azienda_ragione_sociale=r.azienda.ragione_sociale if r.azienda else "",
            persona_id=r.persona_id,
            nominativo=persona.nominativo if persona else None,
            postazione=r.postazione,
            data_ultima_visita=r.data_ultima_visita,
            data_prossima_visita=r.data_prossima_visita,
            periodicita_sorveglianza=r.periodicita_sorveglianza,
            eta_50_plus=r.eta_50_plus,
            days_until_due=days_delta,
        )
        if bucket == SurveillanceBucket.SCADUTE:
            scadute.append(row)
        else:
            in_scadenza.append(row)

    return SurveillanceAlertsResponse(
        in_scadenza=in_scadenza,
        scadute=scadute,
        as_of=today,
        window_days=IN_SCADENZA_WINDOW_DAYS,
    )
