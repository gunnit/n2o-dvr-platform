import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.models.persona import Persona
from app.schemas.persona import PersonaCreate, PersonaResponse, PersonaUpdate
from app.services.ai import DpiRischiSuggerito, suggest_dpi_rischi

router = APIRouter(prefix="/aziende/{azienda_id}/persone", tags=["persone"])


async def _get_azienda(azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Azienda:
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


async def _resolve_ambienti(
    azienda_id: uuid.UUID, ambiente_ids: list[uuid.UUID], db: AsyncSession
) -> list[Ambiente]:
    """Return Ambiente rows for the given IDs, validating they all belong to the azienda."""
    if not ambiente_ids:
        return []
    result = await db.execute(
        select(Ambiente).where(
            Ambiente.azienda_id == azienda_id, Ambiente.id.in_(ambiente_ids)
        )
    )
    ambienti = list(result.scalars().all())
    if len(ambienti) != len(set(ambiente_ids)):
        raise BadRequestError("One or more ambiente_ids do not belong to this azienda")
    return ambienti


async def _load_persona(
    azienda_id: uuid.UUID, persona_id: uuid.UUID, db: AsyncSession
) -> Persona | None:
    result = await db.execute(
        select(Persona)
        .where(Persona.id == persona_id, Persona.azienda_id == azienda_id)
        .options(selectinload(Persona.ambienti))
    )
    return result.scalar_one_or_none()


@router.get("", response_model=list[PersonaResponse])
async def list_persone(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    # Feedback #54 (2026-05-25): order by (ordine, created_at) so legacy
    # rows backfilled to the same ordine bucket stay deterministic, and
    # newly created rows land at the end of the list (max+1 on create).
    result = await db.execute(
        select(Persona)
        .where(Persona.azienda_id == azienda_id)
        .order_by(Persona.ordine, Persona.created_at)
        .options(selectinload(Persona.ambienti))
    )
    return list(result.scalars().all())


@router.post("", response_model=PersonaResponse, status_code=201)
async def create_persona(
    azienda_id: uuid.UUID,
    body: PersonaCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    payload = body.model_dump(exclude={"ambiente_ids"})
    # Feedback #54: server-assigned ordine so bulk-add lands rows at the
    # end of the list. Mirrors ambienti's max(ordine)+1 pattern.
    max_ordine = await db.execute(
        select(func.coalesce(func.max(Persona.ordine), -1)).where(
            Persona.azienda_id == azienda_id
        )
    )
    next_ordine = max_ordine.scalar_one() + 1
    persona = Persona(**payload, azienda_id=azienda_id, ordine=next_ordine)
    persona.ambienti = await _resolve_ambienti(azienda_id, body.ambiente_ids, db)
    db.add(persona)
    await db.commit()
    # Reload with the M2M populated so the response carries ambiente_ids.
    reloaded = await _load_persona(azienda_id, persona.id, db)
    assert reloaded is not None
    return reloaded


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    azienda_id: uuid.UUID,
    persona_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    persona = await _load_persona(azienda_id, persona_id, db)
    if not persona:
        raise NotFoundError("Persona not found")
    return persona


@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    azienda_id: uuid.UUID,
    persona_id: uuid.UUID,
    body: PersonaUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    persona = await _load_persona(azienda_id, persona_id, db)
    if not persona:
        raise NotFoundError("Persona not found")

    data = body.model_dump(exclude_unset=True)
    ambiente_ids = data.pop("ambiente_ids", None)
    for field, value in data.items():
        setattr(persona, field, value)
    if ambiente_ids is not None:
        persona.ambienti = await _resolve_ambienti(azienda_id, ambiente_ids, db)

    await db.commit()
    reloaded = await _load_persona(azienda_id, persona.id, db)
    assert reloaded is not None
    return reloaded


@router.delete("/{persona_id}", status_code=204)
async def delete_persona(
    azienda_id: uuid.UUID,
    persona_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Persona).where(Persona.id == persona_id, Persona.azienda_id == azienda_id)
    )
    persona = result.scalar_one_or_none()
    if not persona:
        raise NotFoundError("Persona not found")

    await db.delete(persona)
    await db.commit()


@router.post(
    "/{persona_id}/dpi-rischi/suggerisci",
    response_model=DpiRischiSuggerito,
)
async def suggerisci_dpi_rischi(
    azienda_id: uuid.UUID,
    persona_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """AI-suggest DPI + rischi specifici for a single persona.

    Inputs to the model: the persona's mansione + attrezzature speciali
    flags + the ambienti they're assigned to + the attrezzature in those
    ambienti. PII (nominativo, codice fiscale) is never sent.
    """
    await _get_azienda(azienda_id, org_id, db)
    persona = await _load_persona(azienda_id, persona_id, db)
    if not persona:
        raise NotFoundError("Persona not found")

    # Ambienti: from the M2M loaded by _load_persona. Fall back to the
    # whole azienda when the persona has none assigned, so the model
    # still gets context to reason from.
    if persona.ambienti:
        ambienti = list(persona.ambienti)
    else:
        ambienti = list(
            (
                await db.execute(
                    select(Ambiente).where(Ambiente.azienda_id == azienda_id)
                )
            ).scalars().all()
        )

    ambiente_ids = [a.id for a in ambienti]
    attrezzature = (
        list(
            (
                await db.execute(
                    select(Attrezzatura).where(
                        Attrezzatura.ambiente_id.in_(ambiente_ids)
                    )
                )
            ).scalars().all()
        )
        if ambiente_ids
        else []
    )

    return await suggest_dpi_rischi(
        mansione_nome=(persona.mansione or "").strip() or None,
        attrezzature_speciali_codes=list(persona.attrezzature_speciali or []),
        ambienti=ambienti,
        attrezzature=attrezzature,
    )
