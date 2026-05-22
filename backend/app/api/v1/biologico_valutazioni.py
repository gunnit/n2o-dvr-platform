"""Rischio Biologico CRUD — D.Lgs. 81/2008 Titolo X.

One row per (azienda, settore) where settore ∈ {alimentare, asilo, dentisti}.
POST upserts: if a row already exists for the (azienda, settore) pair it is
overwritten; otherwise a new row is created. This matches the operator's
mental model — there's one biological assessment per sector, edited over time.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.ambiente import Ambiente
from app.models.azienda import Azienda
from app.models.biologico_valutazione import BiologicoValutazione
from app.schemas.biologico import (
    BiologicoCreate,
    BiologicoResponse,
    BiologicoUpdate,
)

router = APIRouter(
    prefix="/aziende/{azienda_id}/biologico-valutazioni", tags=["biologico"]
)


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


async def _validate_ambiente(
    azienda_id: uuid.UUID,
    ambiente_id: uuid.UUID | None,
    db: AsyncSession,
) -> None:
    if ambiente_id is None:
        return
    result = await db.execute(
        select(Ambiente).where(
            Ambiente.id == ambiente_id, Ambiente.azienda_id == azienda_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise BadRequestError("ambiente_id non appartiene a questa azienda")


def _serialize_risposte(items: list) -> list:
    """Pydantic models or dicts -> list of plain dicts for JSONB storage."""
    out = []
    for r in items:
        if hasattr(r, "model_dump"):
            out.append(r.model_dump())
        else:
            out.append(dict(r))
    return out


@router.get("", response_model=list[BiologicoResponse])
async def list_biologico(
    azienda_id: uuid.UUID,
    settore: str | None = Query(None),
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[BiologicoValutazione]:
    await _get_azienda_or_404(azienda_id, org_id, db)
    stmt = (
        select(BiologicoValutazione)
        .where(BiologicoValutazione.azienda_id == azienda_id)
        .order_by(BiologicoValutazione.created_at.desc())
    )
    if settore:
        stmt = stmt.where(BiologicoValutazione.settore == settore)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "", response_model=BiologicoResponse, status_code=status.HTTP_201_CREATED
)
async def upsert_biologico(
    azienda_id: uuid.UUID,
    body: BiologicoCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> BiologicoValutazione:
    """Create or overwrite the biologico valutazione for (azienda, settore)."""
    await _get_azienda_or_404(azienda_id, org_id, db)
    payload = body.model_dump()
    await _validate_ambiente(azienda_id, payload.get("ambiente_id"), db)

    risposte = _serialize_risposte(payload.get("risposte_checklist") or [])
    payload["risposte_checklist"] = risposte

    existing = await db.execute(
        select(BiologicoValutazione).where(
            BiologicoValutazione.azienda_id == azienda_id,
            BiologicoValutazione.settore == payload["settore"],
        )
    )
    row = existing.scalar_one_or_none()
    if row:
        # Overwrite in place — same id, updated fields.
        for k, v in payload.items():
            if k == "settore":
                continue  # never re-key
            setattr(row, k, v)
    else:
        row = BiologicoValutazione(azienda_id=azienda_id, **payload)
        db.add(row)

    await db.commit()
    await db.refresh(row)
    return row


@router.get("/{valutazione_id}", response_model=BiologicoResponse)
async def get_biologico(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> BiologicoValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(BiologicoValutazione).where(
            BiologicoValutazione.id == valutazione_id,
            BiologicoValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione biologico non trovata")
    return row


@router.patch("/{valutazione_id}", response_model=BiologicoResponse)
async def update_biologico(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    body: BiologicoUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> BiologicoValutazione:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(BiologicoValutazione).where(
            BiologicoValutazione.id == valutazione_id,
            BiologicoValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione biologico non trovata")

    updates = body.model_dump(exclude_unset=True)
    if "ambiente_id" in updates:
        await _validate_ambiente(azienda_id, updates.get("ambiente_id"), db)
    if "risposte_checklist" in updates and updates["risposte_checklist"] is not None:
        updates["risposte_checklist"] = _serialize_risposte(updates["risposte_checklist"])

    for k, v in updates.items():
        setattr(row, k, v)

    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/{valutazione_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_biologico(
    azienda_id: uuid.UUID,
    valutazione_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_azienda_or_404(azienda_id, org_id, db)
    result = await db.execute(
        select(BiologicoValutazione).where(
            BiologicoValutazione.id == valutazione_id,
            BiologicoValutazione.azienda_id == azienda_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError("Valutazione biologico non trovata")
    await db.delete(row)
    await db.commit()
