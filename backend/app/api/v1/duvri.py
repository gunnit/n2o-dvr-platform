"""DUVRI CRUD endpoints (US-4.5).

A DUVRI document represents one appalto (contract) between the principal
Azienda (committente) and one contractor (appaltatore). The principal data
is implicit — read from the parent Azienda — so the operator only enters
contractor + contract details. We surface a ``committente_outdated`` flag
when the parent Azienda has been modified after the Duvri was last touched,
so the frontend can show the AC3 sync banner.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.duvri import Duvri
from app.schemas.duvri import DuvriCreate, DuvriResponse, DuvriUpdate

router = APIRouter(prefix="/aziende/{azienda_id}/duvri", tags=["duvri"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_azienda_or_404(
    azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> Azienda:
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id, Azienda.organization_id == org_id
        )
    )
    az = result.scalar_one_or_none()
    if not az:
        raise NotFoundError("Azienda non trovata")
    return az


def _serialize(duvri: Duvri, azienda: Azienda) -> dict[str, Any]:
    """Build the response payload, including derived committente fields."""
    snapshot = {
        "ragione_sociale": azienda.ragione_sociale,
        "partita_iva": azienda.partita_iva,
        "sede_legale_via": azienda.sede_legale_via,
        "sede_legale_citta": azienda.sede_legale_citta,
        "sede_operativa_via": azienda.sede_operativa_via,
        "sede_operativa_citta": azienda.sede_operativa_citta,
    }
    # AC3: flag a stale Duvri when committente data has moved since we last
    # touched the document. We compare timestamps rather than diffing fields
    # because the Duvri doesn't snapshot principal data — it always reads it
    # from the live Azienda at generation time.
    outdated = (
        azienda.updated_at is not None
        and duvri.updated_at is not None
        and azienda.updated_at > duvri.updated_at
    )
    return {
        "id": duvri.id,
        "azienda_id": duvri.azienda_id,
        "appaltatore_ragione_sociale": duvri.appaltatore_ragione_sociale,
        "appaltatore_partita_iva": duvri.appaltatore_partita_iva,
        "appaltatore_referente": duvri.appaltatore_referente,
        "oggetto_appalto": duvri.oggetto_appalto,
        "data_inizio": duvri.data_inizio,
        "data_fine": duvri.data_fine,
        "importo_appalto": float(duvri.importo_appalto)
        if duvri.importo_appalto is not None
        else None,
        "interferenze": duvri.interferenze or [],
        "costi_sicurezza": float(duvri.costi_sicurezza)
        if duvri.costi_sicurezza is not None
        else None,
        "note": duvri.note,
        "created_at": duvri.created_at,
        "updated_at": duvri.updated_at,
        "committente_outdated": outdated,
        "committente_snapshot": snapshot,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[DuvriResponse])
async def list_duvri(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all DUVRI documents for this azienda, newest first."""
    azienda = await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(Duvri)
        .where(Duvri.azienda_id == azienda_id)
        .order_by(Duvri.created_at.desc())
    )
    return [_serialize(d, azienda) for d in result.scalars().all()]


@router.post("", response_model=DuvriResponse, status_code=status.HTTP_201_CREATED)
async def create_duvri(
    azienda_id: uuid.UUID,
    body: DuvriCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    azienda = await _get_azienda_or_404(azienda_id, org_id, db)
    payload = body.model_dump()
    # Pydantic gave us list[InterferenzaItem]; persist as plain dicts in JSONB.
    payload["interferenze"] = [
        item if isinstance(item, dict) else item.model_dump()
        for item in payload.get("interferenze") or []
    ]
    duvri = Duvri(azienda_id=azienda_id, **payload)
    db.add(duvri)
    await db.commit()
    await db.refresh(duvri)
    return _serialize(duvri, azienda)


@router.get("/{duvri_id}", response_model=DuvriResponse)
async def get_duvri(
    azienda_id: uuid.UUID,
    duvri_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    azienda = await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(Duvri).where(Duvri.id == duvri_id, Duvri.azienda_id == azienda_id)
    )
    duvri = result.scalar_one_or_none()
    if not duvri:
        raise NotFoundError("DUVRI non trovato")
    return _serialize(duvri, azienda)


@router.patch("/{duvri_id}", response_model=DuvriResponse)
async def update_duvri(
    azienda_id: uuid.UUID,
    duvri_id: uuid.UUID,
    body: DuvriUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    azienda = await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(Duvri).where(Duvri.id == duvri_id, Duvri.azienda_id == azienda_id)
    )
    duvri = result.scalar_one_or_none()
    if not duvri:
        raise NotFoundError("DUVRI non trovato")

    updates = body.model_dump(exclude_unset=True)
    if "interferenze" in updates and updates["interferenze"] is not None:
        updates["interferenze"] = [
            item if isinstance(item, dict) else item.model_dump()
            for item in updates["interferenze"]
        ]
    for k, v in updates.items():
        setattr(duvri, k, v)
    await db.commit()
    await db.refresh(duvri)
    return _serialize(duvri, azienda)


@router.delete("/{duvri_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_duvri(
    azienda_id: uuid.UUID,
    duvri_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(Duvri).where(Duvri.id == duvri_id, Duvri.azienda_id == azienda_id)
    )
    duvri = result.scalar_one_or_none()
    if not duvri:
        raise NotFoundError("DUVRI non trovato")
    await db.delete(duvri)
    await db.commit()
