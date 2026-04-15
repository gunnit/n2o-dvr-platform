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
    """Resolve the token.json location."""
    # Try env override first
    env = os.environ.get("GOOGLE_DRIVE_TOKEN_JSON")
    if env:
        p = Path(env)
        if p.exists():
            return p
    # Common location inside repo
    for candidate in [
        Path("/mnt/c/Dev/dlg/credentials/token.json"),
        Path(__file__).resolve().parents[3] / "credentials" / "token.json",
    ]:
        if candidate.exists():
            return candidate
    return Path("/does-not-exist")


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
    query = (
        f"name = '{folder_name}' and "
        f"mimeType = 'application/vnd.google-apps.folder' and "
        f"'{parent_folder_id}' in parents and trashed = false"
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
        query = f"name = '{filename}' and '{company_folder_id}' in parents and trashed = false"
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
