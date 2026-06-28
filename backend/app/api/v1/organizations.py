"""Per-organization branding / letterhead.

Reads are open to any authenticated user (the app chrome and document
generation need them); writes are admin-only. Everything is scoped to the
caller's organization, so orgs can never see or edit each other's branding.

See docs/superpowers/specs/2026-06-28-org-branding-design.md.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
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
ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg"}
EXT_TO_CONTENT_TYPE = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
CONTENT_TYPE_TO_EXT = {"image/png": ".png", "image/jpeg": ".jpg"}
MAX_LOGO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB — logos are small
_LOGO_ERROR = "Formato logo non supportato (PNG o JPG) o file troppo grande (max 5 MB)"


async def _get_org(org_id: uuid.UUID, db: AsyncSession) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise NotFoundError("Organization not found")
    return org


def _to_response(org: Organization) -> OrganizationBrandingResponse:
    has_logo = bool(org.logo_path) and Path(org.logo_path).exists()
    return OrganizationBrandingResponse(
        id=org.id,
        name=org.name,
        has_logo=has_logo,
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
            # Firm name is NOT NULL and doubles as the letterhead name — never
            # let it be blanked out.
            if cleaned:
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

    filename = file.filename or "logo"
    ext = Path(filename).suffix.lower()
    content_type = file.content_type or ""
    is_allowed_type = content_type in ALLOWED_LOGO_CONTENT_TYPES
    is_allowed_ext = ext in ALLOWED_LOGO_EXTENSIONS
    if not (is_allowed_type or is_allowed_ext):
        raise BadRequestError(_LOGO_ERROR)
    if not is_allowed_type and is_allowed_ext:
        content_type = EXT_TO_CONTENT_TYPE[ext]

    content = await file.read()
    if len(content) == 0 or len(content) > MAX_LOGO_SIZE_BYTES:
        raise BadRequestError(_LOGO_ERROR)

    logo_dir = Path(settings.FILE_STORAGE_PATH) / "org_logos" / str(org.id)
    logo_dir.mkdir(parents=True, exist_ok=True)
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        ext = CONTENT_TYPE_TO_EXT.get(content_type, ".png")
    new_path = logo_dir / f"{uuid.uuid4()}{ext}"
    new_path.write_bytes(content)

    # Drop the previous logo file so the disk doesn't accumulate orphans.
    old_path = org.logo_path
    org.logo_path = str(new_path)
    await db.commit()
    await db.refresh(org)
    if old_path and old_path != str(new_path):
        Path(old_path).unlink(missing_ok=True)

    return _to_response(org)


@router.get("/me/branding/logo")
async def get_logo(
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Serve the org's custom logo bytes for the app chrome. 404 when none is
    set — the frontend then falls back to the bundled default mark."""
    org = await _get_org(org_id, db)
    if not org.logo_path:
        raise NotFoundError("No custom logo set")
    path = Path(org.logo_path)
    if not path.exists():
        raise NotFoundError("Logo file missing on storage")
    media_type = EXT_TO_CONTENT_TYPE.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(path=str(path), media_type=media_type, filename=path.name)


@router.delete("/me/branding/logo", response_model=OrganizationBrandingResponse)
async def delete_logo(
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    org = await _get_org(admin.organization_id, db)
    old_path = org.logo_path
    org.logo_path = None
    await db.commit()
    await db.refresh(org)
    if old_path:
        Path(old_path).unlink(missing_ok=True)
    return _to_response(org)
