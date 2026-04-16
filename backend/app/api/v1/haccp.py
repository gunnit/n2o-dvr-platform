"""HACCP config CRUD + activity-type catalog (US-4.3).

Endpoints:

  GET  /aziende/{id}/haccp/config              — read (404 if not set up yet)
  PUT  /aziende/{id}/haccp/config              — upsert the config shape
  POST /aziende/{id}/haccp/config/regenerate-ccps
                                               — pre-load or merge CCPs from
                                                 the activity-type default set
  GET  /haccp/_meta/activity-types             — catalog powering the selector

The CCP list is persisted as JSONB on ``haccp_config.ccps``. The upsert
endpoint also auto-preloads defaults the first time a blank config gets
an activity type assigned, so the wizard can be a single PUT + Regenera
for the canonical "I picked an activity type" flow.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.audit import log_audit
from app.core.exceptions import BadRequestError, NotFoundError
from app.data.haccp_activity_types import (
    get_activity_type,
    get_default_ccps,
    list_activity_types,
    merge_ccps,
)
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.azienda import Azienda
from app.models.haccp_form import HaccpConfig
from app.models.user import User
from app.schemas.haccp import (
    HaccpActivityTypeResponse,
    HaccpActivityTypesList,
    HaccpConfigResponse,
    HaccpConfigUpsert,
    HaccpRegenerateCcpsRequest,
    HaccpRegenerateCcpsResponse,
)

router = APIRouter(tags=["haccp"])


# ---------------------------------------------------------------------------
# Activity-type catalog (no azienda context — static data)
# ---------------------------------------------------------------------------


@router.get(
    "/haccp/_meta/activity-types",
    response_model=HaccpActivityTypesList,
)
async def get_activity_types_catalog():
    """Catalog consumed by the HACCP assessment page's activity-type selector."""
    return HaccpActivityTypesList(
        items=[HaccpActivityTypeResponse(**a) for a in list_activity_types()]
    )


# ---------------------------------------------------------------------------
# Azienda-scoped config
# ---------------------------------------------------------------------------


async def _get_azienda_or_404(
    azienda_id: uuid.UUID, user: User, db: AsyncSession
) -> Azienda:
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id,
            Azienda.organization_id == user.organization_id,
        )
    )
    az = result.scalar_one_or_none()
    if not az:
        raise NotFoundError("Azienda non trovata")
    return az


async def _load_config(
    azienda_id: uuid.UUID, db: AsyncSession
) -> HaccpConfig | None:
    result = await db.execute(
        select(HaccpConfig).where(HaccpConfig.azienda_id == azienda_id).limit(1)
    )
    return result.scalar_one_or_none()


@router.get(
    "/aziende/{azienda_id}/haccp/config",
    response_model=HaccpConfigResponse,
)
async def get_haccp_config(
    azienda_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda_or_404(azienda_id, user, db)
    config = await _load_config(azienda_id, db)
    if config is None:
        raise NotFoundError("Configurazione HACCP non ancora creata")
    return config


@router.put(
    "/aziende/{azienda_id}/haccp/config",
    response_model=HaccpConfigResponse,
)
async def upsert_haccp_config(
    azienda_id: uuid.UUID,
    body: HaccpConfigUpsert,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create-or-update the full HACCP config for an azienda.

    Two ergonomic behaviours encoded here:

      1. If this is a first-time save (no existing row) AND ``tipologia_attivita``
         is a known slug AND the caller didn't send any CCPs, we pre-load the
         default CCPs for that activity — matches AC1 without forcing the
         frontend to call the regenerate endpoint on the very first save.
      2. If the activity type changes on a subsequent save and the caller
         didn't send CCPs in the body, we *don't* silently overwrite the
         operator's existing CCPs — they must hit the regenerate endpoint
         explicitly to merge, which is the AC3 "warn before destroy" flow.
    """
    await _get_azienda_or_404(azienda_id, user, db)
    existing = await _load_config(azienda_id, db)

    ccps_payload = [ccp.model_dump() for ccp in body.ccps]

    if existing is None:
        # First save — seed defaults iff caller didn't supply any CCPs and the
        # activity slug is recognised.
        if not ccps_payload and body.tipologia_attivita:
            ccps_payload = get_default_ccps(body.tipologia_attivita)

        existing = HaccpConfig(
            azienda_id=azienda_id,
            tipologia_attivita=body.tipologia_attivita,
            numero_pasti_giorno=body.numero_pasti_giorno,
            tipi_alimenti_trattati=list(body.tipi_alimenti_trattati),
            responsabile_haccp=body.responsabile_haccp,
            note=body.note,
            ccps=ccps_payload,
        )
        db.add(existing)
        audit_action = "haccp_config_created"
    else:
        existing.tipologia_attivita = body.tipologia_attivita
        existing.numero_pasti_giorno = body.numero_pasti_giorno
        existing.tipi_alimenti_trattati = list(body.tipi_alimenti_trattati)
        existing.responsabile_haccp = body.responsabile_haccp
        existing.note = body.note
        # Only overwrite CCPs if the caller explicitly sent a (possibly empty)
        # list, *except* empty list when they just cleared tipologia — we
        # preserve prior CCPs to avoid data loss from accidental saves.
        if ccps_payload:
            existing.ccps = ccps_payload
            flag_modified(existing, "ccps")
        flag_modified(existing, "tipi_alimenti_trattati")
        audit_action = "haccp_config_updated"

    await log_audit(
        db,
        action=audit_action,
        entity_type="haccp_config",
        entity_id=str(existing.id) if existing.id else str(azienda_id),
        user=user,
        changes={"tipologia_attivita": body.tipologia_attivita},
    )

    await db.commit()
    await db.refresh(existing)
    return existing


@router.post(
    "/aziende/{azienda_id}/haccp/config/regenerate-ccps",
    response_model=HaccpRegenerateCcpsResponse,
)
async def regenerate_ccps(
    azienda_id: uuid.UUID,
    body: HaccpRegenerateCcpsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pre-load / merge CCPs from the activity-type defaults (AC1 + AC3).

    Triggered from the frontend when the operator either:

      * picks an activity type for the first time (strategy="replace"),
      * or switches activity after customising CCPs (strategy="merge" with
        a follow-up toast enumerating ``preserved_codici``).
    """
    await _get_azienda_or_404(azienda_id, user, db)
    config = await _load_config(azienda_id, db)
    if config is None:
        raise NotFoundError("Configurazione HACCP non ancora creata")

    if not config.tipologia_attivita:
        raise BadRequestError(
            "Seleziona una tipologia di attivita prima di rigenerare i CCP",
        )

    activity = get_activity_type(config.tipologia_attivita)
    if activity is None:
        raise BadRequestError(
            f"Tipologia di attivita '{config.tipologia_attivita}' non presente nel catalogo",
        )

    defaults = get_default_ccps(config.tipologia_attivita)
    preserved: list[str] = []

    if body.strategy == "replace":
        merged = defaults
    else:
        merged, preserved = merge_ccps(list(config.ccps or []), defaults)

    config.ccps = merged
    flag_modified(config, "ccps")

    await log_audit(
        db,
        action="haccp_ccps_regenerated",
        entity_type="haccp_config",
        entity_id=str(config.id),
        user=user,
        changes={
            "strategy": body.strategy,
            "preserved_count": len(preserved),
            "total_ccps": len(merged),
        },
    )

    await db.commit()

    return HaccpRegenerateCcpsResponse(
        ccps=[ccp for ccp in merged],  # type: ignore[misc]  # pydantic coerces dicts
        preserved_codici=preserved,
        strategy=body.strategy,
        tipologia_attivita=config.tipologia_attivita,
    )
