"""API for per-mansione DPI + rischi specifici (sorveglianza sanitaria).

Key design choice: keyed by ``(azienda_id, mansione_nome)`` rather than
``persona_id`` because the Medico del Lavoro defines the visite-mediche
protocol per mansione. Two saldatori collapse into one row; the UI picks
up the shared flags when rendering either persona.

The upsert endpoint makes the wizard's in-field flow simple — no need to
know whether a row already exists, just PUT the snapshot of ticks.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.mansione_sorveglianza import MansioneSorveglianza
from app.schemas.mansione_sorveglianza import (
    MansioneSorveglianzaResponse,
    MansioneSorveglianzaUpsert,
)

router = APIRouter(
    prefix="/aziende/{azienda_id}/mansioni-sorveglianza",
    tags=["mansioni-sorveglianza"],
)


async def _verify_azienda(
    azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> None:
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id, Azienda.organization_id == org_id
        )
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Azienda not found")


@router.get("", response_model=list[MansioneSorveglianzaResponse])
async def list_mansioni_sorveglianza(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Return all mansione rows for the azienda, including empty ones."""
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(MansioneSorveglianza)
        .where(MansioneSorveglianza.azienda_id == azienda_id)
        .order_by(MansioneSorveglianza.mansione_nome)
    )
    return result.scalars().all()


@router.put("", response_model=MansioneSorveglianzaResponse)
async def upsert_mansione_sorveglianza(
    azienda_id: uuid.UUID,
    body: MansioneSorveglianzaUpsert,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Create or update the sorveglianza row for a given mansione_nome.

    Matches on ``(azienda_id, mansione_nome)``. The mansione_nome is
    trimmed but preserved case-sensitively — the frontend is expected to
    pass the same string that appears in the persone list.
    """
    await _verify_azienda(azienda_id, org_id, db)

    mansione_nome = body.mansione_nome.strip()

    result = await db.execute(
        select(MansioneSorveglianza).where(
            MansioneSorveglianza.azienda_id == azienda_id,
            MansioneSorveglianza.mansione_nome == mansione_nome,
        )
    )
    row = result.scalar_one_or_none()

    if row is None:
        row = MansioneSorveglianza(
            azienda_id=azienda_id,
            mansione_nome=mansione_nome,
            dpi_codes=body.dpi_codes,
            rischi_specifici_codes=body.rischi_specifici_codes,
            note=body.note,
        )
        db.add(row)
    else:
        row.dpi_codes = body.dpi_codes
        row.rischi_specifici_codes = body.rischi_specifici_codes
        row.note = body.note

    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/{mansione_id}", status_code=204)
async def delete_mansione_sorveglianza(
    azienda_id: uuid.UUID,
    mansione_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Remove a mansione row. Used when a mansione disappears from persone."""
    await _verify_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(MansioneSorveglianza).where(
            MansioneSorveglianza.id == mansione_id,
            MansioneSorveglianza.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Mansione sorveglianza not found")
    await db.delete(row)
    await db.commit()
