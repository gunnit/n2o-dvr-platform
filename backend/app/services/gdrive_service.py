"""Google Drive upload service for generated documents.

Reads OAuth token from /mnt/c/Dev/dlg/credentials/token.json (or path
configured in settings). Uploads completed documents to a per-azienda
folder inside GOOGLE_DRIVE_FOLDER_ID.

Best-effort: if credentials missing or API fails, returns None and logs
a warning — the Celery task continues without failing generation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

from app.config import settings
from app.models.documento_generato import DocumentoGenerato

log = logging.getLogger(__name__)


def _token_path() -> Path:
    """Resolve the token.json location.

    Priority: GOOGLE_DRIVE_TOKEN_JSON env var (used on Render to point at a
    mounted Secret File) → `backend/../credentials/token.json` for local dev.
    """
    env = os.environ.get("GOOGLE_DRIVE_TOKEN_JSON")
    if env:
        p = Path(env)
        if p.exists():
            return p
    local = Path(__file__).resolve().parents[3] / "credentials" / "token.json"
    if local.exists():
        return local
    return Path("/does-not-exist")


def _escape_drive_query_literal(value: str) -> str:
    # Drive's v3 `q=` filters wrap string literals in single quotes. An
    # unescaped apostrophe in e.g. "S'AGOSTINO SRL" crashes the request.
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _load_credentials():
    """Load google.oauth2.credentials.Credentials or return None."""
    try:
        from google.oauth2.credentials import Credentials
    except ImportError:
        log.warning("google-auth library not available")
        return None

    path = _token_path()
    if not path.exists():
        log.info("Google Drive token.json not found at %s", path)
        return None

    try:
        with open(path) as f:
            data = json.load(f)
        return Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes"),
        )
    except Exception as e:
        log.warning("Failed to load Google Drive credentials: %s", e)
        return None


def _get_or_create_folder(service, parent_folder_id: str, folder_name: str) -> Optional[str]:
    """Return folder id; create under parent if missing."""
    safe_name = _escape_drive_query_literal(folder_name)
    safe_parent = _escape_drive_query_literal(parent_folder_id)
    query = (
        f"name = '{safe_name}' and "
        f"mimeType = 'application/vnd.google-apps.folder' and "
        f"'{safe_parent}' in parents and trashed = false"
    )
    resp = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = resp.get("files", [])
    if files:
        return files[0]["id"]
    # Create
    meta = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }
    created = service.files().create(body=meta, fields="id").execute()
    return created.get("id")


def _upload_sync(doc_tipo: str, azienda_ragione_sociale: str, local_path: str) -> Optional[str]:
    """Synchronous upload body; runs in a thread via asyncio.to_thread."""
    creds = _load_credentials()
    if creds is None:
        return None
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        log.warning("google-api-python-client not available")
        return None

    try:
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        parent = settings.GOOGLE_DRIVE_FOLDER_ID
        company_folder_id = _get_or_create_folder(service, parent, azienda_ragione_sociale)
        if not company_folder_id:
            return None

        filename = os.path.basename(local_path)
        # Check if file with same name already exists in folder (for versioning)
        safe_filename = _escape_drive_query_literal(filename)
        safe_folder = _escape_drive_query_literal(company_folder_id)
        query = f"name = '{safe_filename}' and '{safe_folder}' in parents and trashed = false"
        existing = service.files().list(q=query, fields="files(id)").execute().get("files", [])
        if existing:
            # Skip re-upload; return existing id
            return existing[0]["id"]

        meta = {"name": filename, "parents": [company_folder_id]}
        mime = "application/zip" if local_path.endswith(".zip") else (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        media = MediaFileUpload(local_path, mimetype=mime, resumable=True)
        result = service.files().create(body=meta, media_body=media, fields="id").execute()
        file_id = result.get("id")
        log.info("Uploaded %s to Google Drive as file %s", filename, file_id)
        return file_id
    except Exception as e:
        log.warning("Google Drive upload failed: %s", e)
        return None


async def upload_generated_document(doc: DocumentoGenerato, local_path: str) -> Optional[str]:
    """Upload a freshly generated document to Google Drive. Returns file id or None."""
    # Derive azienda name via lazy import to avoid circular deps
    from sqlalchemy import select
    from app.db.session import async_session_factory
    from app.models.azienda import Azienda

    async with async_session_factory() as db:
        r = await db.execute(select(Azienda).where(Azienda.id == doc.azienda_id))
        azienda = r.scalar_one_or_none()
    rs = (azienda.ragione_sociale if azienda else str(doc.azienda_id))[:100]

    # Run the blocking sync call in a thread
    file_id = await asyncio.to_thread(_upload_sync, doc.tipo_documento, rs, local_path)
    return file_id


# ---------------------------------------------------------------------------
# Google Doc (editable) conversion, sharing, export
# ---------------------------------------------------------------------------

DOCX_MIMETYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
GDOC_MIMETYPE = "application/vnd.google-apps.document"


def _create_gdoc_sync(
    docx_bytes: bytes,
    filename: str,
    azienda_ragione_sociale: str,
) -> Optional[str]:
    """Upload docx_bytes and trigger Drive's auto-conversion to Google Docs."""
    creds = _load_credentials()
    if creds is None:
        return None
    try:
        import io
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
    except ImportError:
        log.warning("google-api-python-client not available")
        return None

    try:
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        parent = settings.GOOGLE_DRIVE_FOLDER_ID
        company_folder_id = _get_or_create_folder(service, parent, azienda_ragione_sociale)
        if not company_folder_id:
            return None

        # Strip .docx extension so the Google Doc name doesn't show as "foo.docx"
        display_name = filename[:-5] if filename.lower().endswith(".docx") else filename
        # Suffix to distinguish editable copies from archival .docx uploads
        display_name = f"{display_name} (modificabile)"

        meta = {
            "name": display_name,
            "parents": [company_folder_id],
            # Target mimeType triggers Drive's DOCX -> Google Doc conversion
            "mimeType": GDOC_MIMETYPE,
        }
        media = MediaIoBaseUpload(io.BytesIO(docx_bytes), mimetype=DOCX_MIMETYPE, resumable=True)
        result = service.files().create(body=meta, media_body=media, fields="id").execute()
        file_id = result.get("id")
        log.info("Created Google Doc %s from %s", file_id, filename)
        return file_id
    except Exception as e:
        log.warning("Google Doc creation failed: %s", e)
        return None


def _share_anyone_with_link_sync(file_id: str) -> bool:
    creds = _load_credentials()
    if creds is None:
        return False
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError:
        return False

    try:
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        service.permissions().create(
            fileId=file_id,
            body={"role": "writer", "type": "anyone"},
            fields="id",
        ).execute()
        return True
    except HttpError as e:
        # 400 "cannotShareTeamDriveWithNonGoogleAccounts" etc. — log and carry on;
        # for our case duplicate permissions simply no-op on Drive v3.
        log.warning("share_anyone_with_link failed for %s: %s", file_id, e)
        return False
    except Exception as e:
        log.warning("share_anyone_with_link unexpected error: %s", e)
        return False


def _export_gdoc_sync(file_id: str) -> Optional[bytes]:
    creds = _load_credentials()
    if creds is None:
        return None
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return None

    try:
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        data = service.files().export_media(fileId=file_id, mimeType=DOCX_MIMETYPE).execute()
        # export_media returns bytes directly on success
        return data if isinstance(data, (bytes, bytearray)) else None
    except Exception as e:
        log.warning("export_gdoc_as_docx failed for %s: %s", file_id, e)
        return None


async def create_gdoc_from_docx_bytes(
    docx_bytes: bytes,
    filename: str,
    azienda_ragione_sociale: str,
) -> Optional[str]:
    """Create an editable Google Doc from .docx bytes. Returns Doc file ID or None."""
    return await asyncio.to_thread(
        _create_gdoc_sync, docx_bytes, filename, azienda_ragione_sociale
    )


async def share_anyone_with_link(file_id: str) -> bool:
    """Grant 'anyone with link' writer access to a Drive file. True on success."""
    return await asyncio.to_thread(_share_anyone_with_link_sync, file_id)


async def export_gdoc_as_docx(file_id: str) -> Optional[bytes]:
    """Export a Google Doc as .docx bytes. None on error."""
    return await asyncio.to_thread(_export_gdoc_sync, file_id)


def _gdoc_times_sync(file_id: str) -> Optional[tuple[str, str]]:
    """Return (createdTime, modifiedTime) ISO strings, or None on failure."""
    creds = _load_credentials()
    if creds is None:
        return None
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return None
    try:
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        meta = service.files().get(
            fileId=file_id, fields="createdTime,modifiedTime"
        ).execute()
        created = meta.get("createdTime")
        modified = meta.get("modifiedTime")
        if not created or not modified:
            return None
        return (created, modified)
    except Exception as e:
        log.warning("get_gdoc_times failed for %s: %s", file_id, e)
        return None


def _delete_gdoc_sync(file_id: str) -> bool:
    creds = _load_credentials()
    if creds is None:
        return False
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError:
        return False
    try:
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        service.files().delete(fileId=file_id).execute()
        return True
    except HttpError as e:
        # 404 = already gone; treat as success so the caller can still clear state.
        if getattr(e, "status_code", None) == 404 or "404" in str(e):
            return True
        log.warning("delete_gdoc failed for %s: %s", file_id, e)
        return False
    except Exception as e:
        log.warning("delete_gdoc unexpected error: %s", e)
        return False


async def get_gdoc_times(file_id: str) -> Optional[tuple[str, str]]:
    """Fetch (createdTime, modifiedTime) for a Google Doc. Used by the
    dirty-check in sync-from-gdoc — if modifiedTime is within a few seconds
    of createdTime, the user never edited and the sync should be rejected."""
    return await asyncio.to_thread(_gdoc_times_sync, file_id)


async def delete_gdoc(file_id: str) -> bool:
    """Delete a Google Doc from Drive. True on success or if already gone."""
    return await asyncio.to_thread(_delete_gdoc_sync, file_id)
