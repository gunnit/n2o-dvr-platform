"""POS CRUD + DPI matrix endpoints (US-4.8).

The DPI matrix lives on the Pos row so each client has their own
customised cells. The global rules engine (services/dpi_rules.py) is only
ever read — operator overrides never bleed back into the global suggestions.

Route order matters: the ``/meta/dpi-catalog`` literal must be declared
before ``/{pos_id}`` so FastAPI doesn't try to parse ``meta`` as a UUID.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.pos import Pos
from app.schemas.pos import (
    DpiCatalogResponse,
    DpiMatrixUpdate,
    PosCreate,
    PosResponse,
    PosUpdate,
)
from app.services.dpi_rules import (
    DPI_CATALOG,
    PHASES_CONSTRUCTION,
    ROLES_CONSTRUCTION,
    build_default_matrix,
)

router = APIRouter(prefix="/aziende/{azienda_id}/pos", tags=["pos"])


# --- Helpers --------------------------------------------------------------


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


async def _get_pos(
    pos_id: uuid.UUID, azienda_id: uuid.UUID, db: AsyncSession
) -> Pos:
    result = await db.execute(
        select(Pos).where(Pos.id == pos_id, Pos.azienda_id == azienda_id)
    )
    pos = result.scalar_one_or_none()
    if not pos:
        raise NotFoundError("POS non trovato")
    return pos


# --- Meta (must come before /{pos_id}) ------------------------------------


@router.get("/meta/dpi-catalog", response_model=DpiCatalogResponse)
async def get_dpi_catalog(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> DpiCatalogResponse:
    """Return the canonical roles / phases / DPI label map.

    Powers the three matrix editor cards on the frontend (role selector,
    phase selector, per-cell DPI chip picker). Static for now but routed
    per-azienda so the frontend uses the same ``/aziende/.../pos`` base URL
    everywhere.
    """
    await _get_azienda(azienda_id, org_id, db)
    return DpiCatalogResponse(
        roles=list(ROLES_CONSTRUCTION),
        phases=list(PHASES_CONSTRUCTION),
        dpi_catalog=dict(DPI_CATALOG),
    )


# --- CRUD -----------------------------------------------------------------


@router.get("", response_model=list[PosResponse])
async def list_pos(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[Pos]:
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Pos).where(Pos.azienda_id == azienda_id).order_by(Pos.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=PosResponse, status_code=status.HTTP_201_CREATED)
async def create_pos(
    azienda_id: uuid.UUID,
    body: PosCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Pos:
    await _get_azienda(azienda_id, org_id, db)
    payload: dict[str, Any] = body.model_dump(exclude_none=True)
    pos = Pos(azienda_id=azienda_id, **payload)
    db.add(pos)
    await db.commit()
    await db.refresh(pos)
    return pos


@router.get("/{pos_id}", response_model=PosResponse)
async def get_pos(
    azienda_id: uuid.UUID,
    pos_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Pos:
    await _get_azienda(azienda_id, org_id, db)
    return await _get_pos(pos_id, azienda_id, db)


@router.put("/{pos_id}", response_model=PosResponse)
async def update_pos(
    azienda_id: uuid.UUID,
    pos_id: uuid.UUID,
    body: PosUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Pos:
    await _get_azienda(azienda_id, org_id, db)
    pos = await _get_pos(pos_id, azienda_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(pos, field, value)
    await db.commit()
    await db.refresh(pos)
    return pos


@router.delete("/{pos_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pos(
    azienda_id: uuid.UUID,
    pos_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_azienda(azienda_id, org_id, db)
    pos = await _get_pos(pos_id, azienda_id, db)
    await db.delete(pos)
    await db.commit()


# --- DPI matrix sub-resource ---------------------------------------------


@router.post("/{pos_id}/dpi-matrix", response_model=PosResponse)
async def update_dpi_matrix(
    azienda_id: uuid.UUID,
    pos_id: uuid.UUID,
    body: DpiMatrixUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Pos:
    """Regenerate or persist the DPI matrix for this POS.

    * ``matrix=None`` → rebuild defaults from the rules engine (the
      "Rigenera dai default" action). Overwrites any operator edits.
    * ``matrix`` provided → persist as-is (cell overrides). Global rules
      are untouched, as required by US-4.8 AC2.
    """
    await _get_azienda(azienda_id, org_id, db)
    pos = await _get_pos(pos_id, azienda_id, db)

    pos.dpi_matrix_roles = list(body.roles)
    pos.dpi_matrix_phases = list(body.phases)
    if body.matrix is None:
        pos.dpi_matrix = build_default_matrix(body.roles, body.phases)
    else:
        pos.dpi_matrix = body.matrix

    # JSONB columns need an explicit dirty flag when we reassign a dict/list
    # that Python might consider the same identity.
    flag_modified(pos, "dpi_matrix")
    flag_modified(pos, "dpi_matrix_roles")
    flag_modified(pos, "dpi_matrix_phases")

    await db.commit()
    await db.refresh(pos)
    return pos
