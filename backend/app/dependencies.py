import logging
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.permissions import capabilities_for, has_capability
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        # A validly-signed token can still carry a non-UUID `sub`; treat as auth failure, not 500.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_org(user: User = Depends(get_current_user)) -> uuid.UUID:
    return user.organization_id


def require_role(*roles: str):
    """Gate on the role name itself.

    Kept for the handful of screens that really are "admin only" as a category
    rather than because of one named action (the oversight tools). Anything that
    guards a *specific* capability should use :func:`require_capability`, which
    survives the role list changing.
    """

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return _check


def require_capability(*capabilities: str):
    """Gate on what the person may *do*, from ``app.core.permissions``.

    403, never 402: this is "your role does not allow it", which no amount of
    money fixes. The paywall is a separate decision made by ``app.billing.gates``
    and both may apply to the same endpoint — generating a document needs the
    capability *and* an active plan that covers the document type.

    All listed capabilities are required (AND), because every real call site
    guards one action. The Italian detail surfaces directly in the operator's
    UI.
    """

    async def _check(user: User = Depends(get_current_user)) -> User:
        missing = [c for c in capabilities if not has_capability(user.role, c)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Il tuo ruolo non consente questa operazione. "
                    "Chiedi a un amministratore dell'organizzazione."
                ),
            )
        return user

    return _check


async def require_platform_admin(user: User = Depends(get_current_user)) -> User:
    """Gate an operation that reaches **across** tenants.

    Distinct from every capability in ``app.core.permissions``, which answer
    "what may this person do *inside their own organization*". ``billing:manage``
    means "may commit **this** organization to a charge" and every self-serve
    signup's first user holds it — so using it to guard an endpoint that takes
    an arbitrary ``organization_id`` let any customer put themselves on any plan
    for free, and rewrite other tenants' subscriptions besides.

    Membership is a deploy-time allowlist rather than a role because there is no
    such thing as a platform operator *inside* a tenant: the N2O staff who close
    invoices are ordinary admins of the N2O organization. An empty allowlist
    therefore denies everyone — the failure mode of missing configuration has to
    be "nobody can", never "anybody can".
    """
    if user.email.strip().lower() not in settings.platform_admin_emails:
        # Worth a line in the log: a request reaching here is either a
        # misconfigured deploy or someone probing a cross-tenant endpoint.
        logging.getLogger(__name__).warning(
            "platform admin denied for %s (org %s)", user.email, user.organization_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operazione riservata allo staff della piattaforma.",
        )
    return user


async def get_current_capabilities(
    user: User = Depends(get_current_user),
) -> frozenset[str]:
    """The signed-in user's capability set."""
    return capabilities_for(user.role)
