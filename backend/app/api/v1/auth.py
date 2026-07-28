from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.constants import ACCOUNT_TYPE_CONSULTANT, ACCOUNT_TYPE_DIRECT
from app.core.security import create_access_token, hash_password, verify_password
from app.data.ddl_consent import ACCEPTED_CONSENT_VERSIONS
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RegisterDirectRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_for(user: User, account_type: str) -> str:
    """The session claims. `account_type` decides which price list the customer
    is shown and which channel's plans `/billing/subscribe` will sell them.

    INV-3: plan, limits and credits stay *out* of the token — they resolve from
    the database on every request, so an upgrade or an exhausted credit balance
    takes effect immediately instead of at the next login.
    """
    return create_access_token(
        {
            "sub": str(user.id),
            "org": str(user.organization_id),
            "role": user.role,
            "account_type": account_type,
        }
    )


async def _provision_tenant(
    body: RegisterRequest,
    account_type: str,
    db: AsyncSession,
    *,
    ddl_consent_version: str | None = None,
) -> User:
    """Create an organization and its first admin, atomically.

    Shared by both signup routes so the two channels can never drift on how a
    tenant is born — they differ only in `account_type` and the consent stamp.
    """
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    org_name = (body.organization_name or "").strip() or f"{body.full_name}'s Organization"
    org = Organization(name=org_name, account_type=account_type)
    if ddl_consent_version is not None:
        org.ddl_consent_at = datetime.now(timezone.utc)
        org.ddl_consent_version = ddl_consent_version
    db.add(org)
    await db.flush()

    user = User(
        organization_id=org.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role="admin",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Consultant signup (Model A) — a studio that documents its client companies."""
    user = await _provision_tenant(body, ACCOUNT_TYPE_CONSULTANT, db)
    return TokenResponse(access_token=_token_for(user, ACCOUNT_TYPE_CONSULTANT))


@router.post(
    "/register-direct", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register_direct(body: RegisterDirectRequest, db: AsyncSession = Depends(get_db)):
    """Direct signup (Model B) — a company documenting its own workplace.

    MB-5.4/5.7. Separate from `/register` on purpose: the account type decides
    which price list the tenant may buy from, so it is a property of *which
    endpoint was called*, never a field a caller can flip.

    The consent is validated here rather than trusted from the form (INV-5, the
    same reasoning as the paywall): the browser check is a courtesy, this is the
    one that counts.
    """
    if not body.consenso_datore_lavoro:
        raise HTTPException(
            status_code=422,
            detail=(
                "Per attivare un piano diretto devi dichiarare di essere il datore "
                "di lavoro o il soggetto responsabile della sicurezza."
            ),
        )
    if body.consenso_versione not in ACCEPTED_CONSENT_VERSIONS:
        # The form is showing wording this deploy does not know. Refusing beats
        # recording consent to text we cannot reproduce.
        raise HTTPException(
            status_code=422,
            detail="Versione dell'informativa non riconosciuta. Ricarica la pagina e riprova.",
        )

    user = await _provision_tenant(
        body, ACCOUNT_TYPE_DIRECT, db, ddl_consent_version=body.consenso_versione
    )
    return TokenResponse(access_token=_token_for(user, ACCOUNT_TYPE_DIRECT))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Joined rather than loaded through the relationship: Organization carries
    # the white-label logo as bytes, and there is no reason to drag up to 5 MB
    # of it through every login just to read one string.
    row = (
        await db.execute(
            select(User, Organization.account_type)
            .join(Organization, Organization.id == User.organization_id)
            .where(User.email == body.email)
        )
    ).first()
    if row is None or not verify_password(body.password, row[0].hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user, account_type = row
    return TokenResponse(access_token=_token_for(user, account_type))


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.full_name = body.full_name.strip()
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Password attuale non corretta")
    user.hashed_password = hash_password(body.new_password)
    await db.commit()
