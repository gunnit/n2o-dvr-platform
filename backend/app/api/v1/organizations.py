"""Per-organization branding / letterhead.

Reads are open to any authenticated user (the app chrome and document
generation need them); writes are admin-only. Everything is scoped to the
caller's organization, so orgs can never see or edit each other's branding.

The logo is stored as bytes on the Organization row (not on disk): document
generation runs on the Celery worker, which mounts a different Render disk from
this API, so a file path would be unreachable there.

See docs/superpowers/specs/2026-06-28-org-branding-design.md.
"""

import uuid

from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org, require_role
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import (
    OrganizationBrandingResponse,
    OrganizationBrandingUpdate,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])

# Logos are embedded into .docx documents, so restrict to raster formats
# python-docx can actually place (no SVG).
ALLOWED_LOGO_CONTENT_TYPES = {"image/png", "image/jpeg"}
MAX_LOGO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB — logos are small
_LOGO_ERROR = "Formato logo non supportato (PNG o JPG) o file troppo grande (max 5 MB)"

# Magic-byte signatures — we validate the actual bytes, not just the declared
# content-type/extension, so a mislabelled or non-image file can't be stored.
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"


def _detect_image_type(content: bytes) -> str | None:
    """Return the real image content-type from the leading bytes, or None."""
    if content.startswith(_PNG_MAGIC):
        return "image/png"
    if content.startswith(_JPEG_MAGIC):
        return "image/jpeg"
    return None


async def _get_org(org_id: uuid.UUID, db: AsyncSession) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise NotFoundError("Organization not found")
    return org


def _to_response(org: Organization) -> OrganizationBrandingResponse:
    return OrganizationBrandingResponse(
        id=org.id,
        name=org.name,
        has_logo=bool(org.logo_bytes),
        indirizzo=org.indirizzo,
        cap=org.cap,
        citta=org.citta,
        provincia=org.provincia,
        partita_iva=org.partita_iva,
        codice_fiscale=org.codice_fiscale,
        telefono=org.telefono,
        email=org.email,
        sito_web=org.sito_web,
        rspp_nome=org.rspp_nome,
    )


@router.get("/me/branding", response_model=OrganizationBrandingResponse)
async def get_branding(
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    org = await _get_org(org_id, db)
    return _to_response(org)


@router.put("/me/branding", response_model=OrganizationBrandingResponse)
async def update_branding(
    body: OrganizationBrandingUpdate,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    org = await _get_org(admin.organization_id, db)

    provided = body.model_dump(exclude_unset=True)
    for key, value in provided.items():
        cleaned = value.strip() if isinstance(value, str) else value
        if key == "name":
            # Firm name is NOT NULL and doubles as the letterhead name — reject
            # a blank value instead of silently keeping the old one.
            if not cleaned:
                raise BadRequestError("La ragione sociale non può essere vuota")
            org.name = cleaned
            continue
        # Empty string means "clear this optional field".
        setattr(org, key, cleaned or None)

    await db.commit()
    await db.refresh(org)
    return _to_response(org)


@router.post("/me/branding/logo", response_model=OrganizationBrandingResponse)
async def upload_logo(
    file: UploadFile = File(...),
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    org = await _get_org(admin.organization_id, db)

    content = await file.read()
    if len(content) == 0 or len(content) > MAX_LOGO_SIZE_BYTES:
        raise BadRequestError(_LOGO_ERROR)

    # Validate the real bytes, not just the declared type/extension — a file
    # must actually be a PNG or JPEG to be stored as a logo.
    detected = _detect_image_type(content)
    if detected is None or detected not in ALLOWED_LOGO_CONTENT_TYPES:
        raise BadRequestError(_LOGO_ERROR)

    org.logo_bytes = content
    org.logo_content_type = detected
    await db.commit()
    await db.refresh(org)
    return _to_response(org)


@router.get("/me/branding/logo")
async def get_logo(
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Serve the org's custom logo bytes for the app chrome. 404 when none is
    set — the frontend then falls back to the bundled default mark."""
    org = await _get_org(org_id, db)
    if not org.logo_bytes:
        raise NotFoundError("No custom logo set")
    return Response(
        content=org.logo_bytes,
        media_type=org.logo_content_type or "application/octet-stream",
    )


@router.delete("/me/branding/logo", response_model=OrganizationBrandingResponse)
async def delete_logo(
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    org = await _get_org(admin.organization_id, db)
    org.logo_bytes = None
    org.logo_content_type = None
    await db.commit()
    await db.refresh(org)
    return _to_response(org)
