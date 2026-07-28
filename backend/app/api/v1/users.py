import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.entitlements import Entitlements, get_entitlements
from app.billing.gates import ensure_seat_available
from app.core.security import hash_password
from app.db.session import get_db
from app.core.permissions import (
    ALLOWED_ROLES,
    ROLE_DESCRIPTIONS,
    USERS_MANAGE,
    capabilities_for,
    role_label,
)
from app.dependencies import require_capability
from app.models.azienda import Azienda
from app.models.documento_generato import DocumentoGenerato
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])



class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)
    role: str


class UserUpdate(BaseModel):
    role: str | None = None
    password: str | None = Field(default=None, min_length=8)
    full_name: str | None = Field(default=None, min_length=1)


class RoleOut(BaseModel):
    """One assignable role, as the user-management screen renders it."""

    role: str
    label: str
    description: str
    capabilities: list[str]


class UserStatsRow(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    role: str
    aziende_count: int
    documenti_count: int


def _validate_role(role: str) -> None:
    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Ruolo non valido. Ammessi: {', '.join(sorted(ALLOWED_ROLES))}",
        )


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(_admin: User = Depends(require_capability(USERS_MANAGE))):
    """The assignable roles, in ascending order of privilege.

    Served rather than hardcoded in the frontend so the "chi può fare cosa"
    table on the user-management screen is generated from the same matrix the
    server enforces — the alternative is a marketing description of permissions
    that quietly stops being true.
    """
    return [
        RoleOut(
            role=role,
            label=role_label(role),
            description=ROLE_DESCRIPTIONS.get(role, ""),
            capabilities=sorted(capabilities_for(role)),
        )
        # Ascending privilege: the matrix guarantees the three nest, so sorting
        # by capability count is a faithful ordering rather than a guess.
        for role in sorted(ALLOWED_ROLES, key=lambda r: len(capabilities_for(r)))
    ]


@router.get("", response_model=list[UserOut])
async def list_users(
    admin: User = Depends(require_capability(USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .where(User.organization_id == admin.organization_id)
        .order_by(User.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    admin: User = Depends(require_capability(USERS_MANAGE)),
    ent: Entitlements = Depends(get_entitlements),
    db: AsyncSession = Depends(get_db),
):
    _validate_role(body.role)

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email già registrata")

    # MB-2.5 — seats are a plan limit. Counted here rather than tracked on the
    # subscription so the number can never drift from reality: it *is* the
    # number of users in the org.
    seats_used = (
        await db.execute(
            select(func.count(User.id)).where(
                User.organization_id == admin.organization_id
            )
        )
    ).scalar_one()
    ensure_seat_available(ent, seats_used, admin.organization_id)

    user = User(
        organization_id=admin.organization_id,
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/stats", response_model=list[UserStatsRow])
async def user_stats(
    admin: User = Depends(require_capability(USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    aziende_counts = (
        select(
            Azienda.created_by_user_id.label("user_id"),
            func.count(Azienda.id).label("n"),
        )
        .where(Azienda.organization_id == admin.organization_id)
        .group_by(Azienda.created_by_user_id)
        .subquery()
    )
    documenti_counts = (
        select(
            DocumentoGenerato.generated_by.label("user_id"),
            func.count(DocumentoGenerato.id).label("n"),
        )
        .join(Azienda, Azienda.id == DocumentoGenerato.azienda_id)
        .where(Azienda.organization_id == admin.organization_id)
        .group_by(DocumentoGenerato.generated_by)
        .subquery()
    )

    stmt = (
        select(
            User.id,
            User.full_name,
            User.email,
            User.role,
            func.coalesce(aziende_counts.c.n, 0),
            func.coalesce(documenti_counts.c.n, 0),
        )
        .outerjoin(aziende_counts, aziende_counts.c.user_id == User.id)
        .outerjoin(documenti_counts, documenti_counts.c.user_id == User.id)
        .where(User.organization_id == admin.organization_id)
        .order_by(User.full_name)
    )
    rows = (await db.execute(stmt)).all()
    return [
        UserStatsRow(
            user_id=r[0],
            full_name=r[1],
            email=r[2],
            role=r[3],
            aziende_count=int(r[4]),
            documenti_count=int(r[5]),
        )
        for r in rows
    ]


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    admin: User = Depends(require_capability(USERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.id == user_id, User.organization_id == admin.organization_id
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    # Prevent an admin from demoting themselves and stranding the org without one.
    if user.id == admin.id and body.role is not None and body.role != "admin":
        raise HTTPException(
            status_code=400,
            detail="Non puoi rimuovere il ruolo admin da te stesso",
        )

    if body.role is not None:
        _validate_role(body.role)
        user.role = body.role
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.password is not None:
        user.hashed_password = hash_password(body.password)

    await db.commit()
    await db.refresh(user)
    return user
