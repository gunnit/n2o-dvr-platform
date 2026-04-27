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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.models.mansione_sorveglianza import MansioneSorveglianza
from app.models.persona import Persona
from app.models.persone_ambienti import persone_ambienti
from app.schemas.mansione_sorveglianza import (
    MansioneSorveglianzaResponse,
    MansioneSorveglianzaUpsert,
)
from app.services.ai import (
    MansioneProtocolSuggerito,
    suggest_mansione_protocol,
)


class SuggestProtocolRequest(BaseModel):
    mansione_nome: str

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


@router.post("/suggerisci", response_model=MansioneProtocolSuggerito)
async def suggerisci_mansione_protocol(
    azienda_id: uuid.UUID,
    body: SuggestProtocolRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Phase 5.1 + 5.2 — AI-suggest DPI + rischi specifici for a mansione.

    Loads the relevant persone (matching mansione_nome), the ambienti they
    operate in, and the equipment in those ambienti, then asks the model
    to propose codes from the DPI / Rischi Specifici catalogs. Returns
    only catalog-valid codes.
    """
    await _verify_azienda(azienda_id, org_id, db)

    mansione_nome = body.mansione_nome.strip()
    if not mansione_nome:
        raise HTTPException(
            status_code=422,
            detail="mansione_nome must not be empty",
        )

    # Find personas with this mansione → their ambienti → attrezzature.
    personas = (
        await db.execute(
            select(Persona).where(
                Persona.azienda_id == azienda_id,
                Persona.mansione == mansione_nome,
            )
        )
    ).scalars().all()
    persona_ids = [p.id for p in personas]

    if persona_ids:
        ambiente_rows = (
            await db.execute(
                select(Ambiente)
                .join(persone_ambienti, persone_ambienti.c.ambiente_id == Ambiente.id)
                .where(persone_ambienti.c.persona_id.in_(persona_ids))
                .distinct()
            )
        ).scalars().all()
    else:
        # No persona matched (mansione typed but not yet linked to anyone) —
        # fall back to all azienda ambienti so the model still gets context.
        ambiente_rows = (
            await db.execute(
                select(Ambiente).where(Ambiente.azienda_id == azienda_id)
            )
        ).scalars().all()

    ambiente_ids = [a.id for a in ambiente_rows]
    attrezzature_rows = (
        (
            await db.execute(
                select(Attrezzatura).where(
                    Attrezzatura.ambiente_id.in_(ambiente_ids)
                )
            )
        ).scalars().all()
        if ambiente_ids
        else []
    )

    return await suggest_mansione_protocol(
        mansione_nome=mansione_nome,
        ambienti=list(ambiente_rows),
        attrezzature=list(attrezzature_rows),
    )


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
