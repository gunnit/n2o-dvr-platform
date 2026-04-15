"""Per-client library of risk improvement measures (US-2.6 AC2).

Endpoints under /aziende/{azienda_id}/rischi/misure-libreria:
  * GET  ""                — list (optionally filtered by categoria_rischio)
  * POST ""                — create a library entry
  * PATCH "/{misura_id}"   — update fields in place
  * DELETE "/{misura_id}"  — remove

Org scope is enforced via the same _get_azienda pattern used in
stress_misure.py: any request against an azienda the caller's org does
not own returns 404.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.rischio_misura_libreria import RischioMisuraLibreria
from app.schemas.rischio_misura import (
    RischioMisuraLibreriaCreate,
    RischioMisuraLibreriaResponse,
    RischioMisuraLibreriaUpdate,
)

router = APIRouter(
    prefix="/aziende/{azienda_id}/rischi/misure-libreria",
    tags=["rischi-misure-libreria"],
)


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


@router.get("", response_model=list[RischioMisuraLibreriaResponse])
async def list_misure(
    azienda_id: uuid.UUID,
    categoria_rischio: str | None = Query(default=None),
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    stmt = select(RischioMisuraLibreria).where(
        RischioMisuraLibreria.azienda_id == azienda_id
    )
    if categoria_rischio is not None:
        stmt = stmt.where(
            RischioMisuraLibreria.categoria_rischio == categoria_rischio
        )
    stmt = stmt.order_by(RischioMisuraLibreria.created_at.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post(
    "", response_model=RischioMisuraLibreriaResponse, status_code=201
)
async def create_misura(
    azienda_id: uuid.UUID,
    body: RischioMisuraLibreriaCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    misura = RischioMisuraLibreria(
        azienda_id=azienda_id,
        categoria_rischio=body.categoria_rischio,
        titolo=body.titolo,
        descrizione=body.descrizione,
        tipo=body.tipo,
        priorita=body.priorita,
        tempistica=body.tempistica,
        riferimento_normativo=body.riferimento_normativo,
        provenance=body.provenance,
    )
    db.add(misura)
    await db.commit()
    await db.refresh(misura)
    return misura


@router.patch(
    "/{misura_id}", response_model=RischioMisuraLibreriaResponse
)
async def update_misura(
    azienda_id: uuid.UUID,
    misura_id: uuid.UUID,
    body: RischioMisuraLibreriaUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(RischioMisuraLibreria).where(
            RischioMisuraLibreria.id == misura_id,
            RischioMisuraLibreria.azienda_id == azienda_id,
        )
    )
    misura = result.scalar_one_or_none()
    if not misura:
        raise NotFoundError("Misura not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(misura, field, value)

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
        select(RischioMisuraLibreria).where(
            RischioMisuraLibreria.id == misura_id,
            RischioMisuraLibreria.azienda_id == azienda_id,
        )
    )
    misura = result.scalar_one_or_none()
    if not misura:
        raise NotFoundError("Misura not found")
    await db.delete(misura)
    await db.commit()
