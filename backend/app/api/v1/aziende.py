import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org, get_current_user
from app.models.azienda import Azienda
from app.models.user import User
from app.schemas.azienda import AziendaCreate, AziendaResponse, AziendaUpdate
from app.services.ai import generate_company_description


class DescriptionResponse(BaseModel):
    description: str


class DashboardKpis(BaseModel):
    clienti_attivi: int
    sopralluoghi_in_corso: int
    sopralluoghi_completati: int
    bozze: int
    scadenze_imminenti: int


router = APIRouter(prefix="/aziende", tags=["aziende"])


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Solo gli amministratori possono creare clienti",
        )


@router.get("", response_model=list[AziendaResponse])
async def list_aziende(
    search: str | None = Query(None),
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Azienda).where(Azienda.organization_id == org_id)

    if search:
        q = f"%{search}%"
        stmt = stmt.where(
            or_(
                Azienda.ragione_sociale.ilike(q),
                Azienda.partita_iva.ilike(q),
                Azienda.sede_legale_citta.ilike(q),
                Azienda.sede_operativa_citta.ilike(q),
            )
        )

    stmt = stmt.order_by(Azienda.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


# Literal `/dashboard/kpis` must be declared BEFORE any `/{azienda_id}` route
# so FastAPI doesn't try to parse "dashboard" as a UUID (mirrors the
# batch-upload pattern in sostanze_chimiche.py).
@router.get("/dashboard/kpis", response_model=DashboardKpis)
async def dashboard_kpis(
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Return dashboard KPIs for the current org.

    Aggregates azienda survey_status counts and the "scadenze imminenti"
    figure — aziende whose DVR expires within the next 30 days (inclusive)
    and hasn't already expired. US-5.1 acceptance criteria.
    """
    total_stmt = select(func.count(Azienda.id)).where(Azienda.organization_id == org_id)
    total = (await db.execute(total_stmt)).scalar() or 0

    def _count_by_status(status: str):
        return select(func.count(Azienda.id)).where(
            Azienda.organization_id == org_id,
            Azienda.survey_status == status,
        )

    in_progress = (await db.execute(_count_by_status("in_progress"))).scalar() or 0
    completed = (await db.execute(_count_by_status("completed"))).scalar() or 0
    drafts = (await db.execute(_count_by_status("draft"))).scalar() or 0

    today = date.today()
    horizon = today + timedelta(days=30)
    scadenze_stmt = select(func.count(Azienda.id)).where(
        Azienda.organization_id == org_id,
        Azienda.data_scadenza_dvr.is_not(None),
        Azienda.data_scadenza_dvr >= today,
        Azienda.data_scadenza_dvr <= horizon,
    )
    scadenze_imminenti = (await db.execute(scadenze_stmt)).scalar() or 0

    return DashboardKpis(
        clienti_attivi=total,
        sopralluoghi_in_corso=in_progress,
        sopralluoghi_completati=completed,
        bozze=drafts,
        scadenze_imminenti=scadenze_imminenti,
    )


@router.post("", response_model=AziendaResponse, status_code=201)
async def create_azienda(
    body: AziendaCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    azienda = Azienda(**body.model_dump(), organization_id=user.organization_id)
    db.add(azienda)
    await db.commit()
    await db.refresh(azienda)
    return azienda


@router.get("/{azienda_id}", response_model=AziendaResponse)
async def get_azienda(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


@router.put("/{azienda_id}", response_model=AziendaResponse)
async def update_azienda(
    azienda_id: uuid.UUID,
    body: AziendaUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(azienda, field, value)

    await db.commit()
    await db.refresh(azienda)
    return azienda


@router.delete("/{azienda_id}", status_code=204)
async def delete_azienda(
    azienda_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id, Azienda.organization_id == user.organization_id
        )
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")

    await db.delete(azienda)
    await db.commit()


@router.post("/{azienda_id}/genera-descrizione", response_model=DescriptionResponse)
async def genera_descrizione(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI company description for DVR Part I (US-2.1).

    Returns the generated text. The caller (frontend editor) is responsible
    for persisting it via PUT /aziende/{id} with descrizione_attivita set.
    This lets the user review/edit before committing.
    """
    result = await db.execute(
        select(Azienda)
        .where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
        .options(
            selectinload(Azienda.ambienti),
            selectinload(Azienda.persone),
        )
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")

    description = await generate_company_description(azienda)
    return DescriptionResponse(description=description)
