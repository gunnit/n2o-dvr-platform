"""Per-client library of stress corrective measures (US-3.8).

Endpoints under /aziende/{azienda_id}/stress/misure:
  * GET  ""              — list (optionally filtered by livello_rischio)
  * POST ""              — create a library entry
  * PUT  "/{misura_id}"  — update text
  * DELETE "/{misura_id}" — remove

Org scope is enforced via the same _get_azienda pattern used in
sostanze_chimiche.py: any request against an azienda the caller's org
does not own returns 404.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.stress_misura_libreria import StressMisuraLibreria
from app.schemas.stress_misura import (
    StressMisuraLibreriaCreate,
    StressMisuraLibreriaResponse,
    StressMisuraLibreriaUpdate,
)

router = APIRouter(
    prefix="/aziende/{azienda_id}/stress/misure", tags=["stress-misure"]
)

_ALLOWED_LIVELLI = {"Basso", "Medio", "Alto"}


async def _get_azienda(
    azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> Azienda:
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id, Azienda.organization_id == org_id
        )
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


@router.get("", response_model=list[StressMisuraLibreriaResponse])
async def list_misure(
    azienda_id: uuid.UUID,
    livello_rischio: str | None = Query(default=None),
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    stmt = select(StressMisuraLibreria).where(
        StressMisuraLibreria.azienda_id == azienda_id
    )
    if livello_rischio is not None:
        if livello_rischio not in _ALLOWED_LIVELLI:
            raise BadRequestError(
                "livello_rischio deve essere Basso, Medio o Alto"
            )
        stmt = stmt.where(StressMisuraLibreria.livello_rischio == livello_rischio)
    stmt = stmt.order_by(StressMisuraLibreria.created_at.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=StressMisuraLibreriaResponse, status_code=201)
async def create_misura(
    azienda_id: uuid.UUID,
    body: StressMisuraLibreriaCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    misura = StressMisuraLibreria(
        azienda_id=azienda_id,
        livello_rischio=body.livello_rischio,
        testo=body.testo,
        personalizzato=True,
    )
    db.add(misura)
    await db.commit()
    await db.refresh(misura)
    return misura


@router.put("/{misura_id}", response_model=StressMisuraLibreriaResponse)
async def update_misura(
    azienda_id: uuid.UUID,
    misura_id: uuid.UUID,
    body: StressMisuraLibreriaUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(StressMisuraLibreria).where(
            StressMisuraLibreria.id == misura_id,
            StressMisuraLibreria.azienda_id == azienda_id,
        )
    )
    misura = result.scalar_one_or_none()
    if not misura:
        raise NotFoundError("Misura not found")
    misura.testo = body.testo
    misura.personalizzato = True
    await db.commit()
    await db.refresh(misura)
    return misura


@router.delete("/{misura_id}", status_code=204)
async def delete_misura(
    azienda_id: uuid.UUID,
    misura_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(StressMisuraLibreria).where(
            StressMisuraLibreria.id == misura_id,
            StressMisuraLibreria.azienda_id == azienda_id,
        )
    )
    misura = result.scalar_one_or_none()
    if not misura:
        raise NotFoundError("Misura not found")
    await db.delete(misura)
    await db.commit()
