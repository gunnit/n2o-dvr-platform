"""The DVR reads the company photo from the database (spec §4.2.4).

``DVRMasterGenerator._load_dvr_extras`` is what the Celery worker runs before
building the document: it must hand ``extras["foto_presentazione"]`` the
stored bytes and content type, and ``None`` when the azienda has no photo.

DB-backed: needs a reachable Postgres and skips without one; CI provides it.
The scratch azienda is built like the other DB tests (raw SQL, the
organization row, ``survey_status='draft'``), as in
``tests/test_azienda_foto_presentazione.py``.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from io import BytesIO
from typing import Any, Callable

import pytest
from PIL import Image
from sqlalchemy import text

from app.db.session import _normalize_async_url
from app.services.document_generator.dvr_master import DVRMasterGenerator

_URL = (
    _normalize_async_url(os.environ["DATABASE_URL"])
    if os.environ.get("DATABASE_URL")
    else None
)


def _jpeg(color: str) -> bytes:
    out = BytesIO()
    Image.new("RGB", (32, 24), color).save(out, format="JPEG")
    return out.getvalue()


def _in_one_loop(body: Callable[..., Any], *, needs_org: bool = True) -> Any:
    """Run ``body(session, org_id, azienda_id)`` with scratch data, in one loop."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    async def _go() -> Any:
        engine = create_async_engine(_URL)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        org_id, azienda_id = uuid.uuid4(), uuid.uuid4()
        try:
            async with factory() as s:
                if needs_org:
                    await s.execute(
                        text("INSERT INTO organizations (id, name) VALUES (:i, :n)"),
                        {"i": org_id, "n": f"pytest-dvr-foto-{org_id}"},
                    )
                    await s.execute(
                        text(
                            "INSERT INTO aziende (id, organization_id, ragione_sociale, survey_status)"
                            " VALUES (:a, :o, 'Foto DVR SRL', 'draft')"
                        ),
                        {"a": azienda_id, "o": org_id},
                    )
                    await s.commit()
                return await body(s, org_id, azienda_id)
        finally:
            async with factory() as s:
                # The photo row goes with the azienda (ON DELETE CASCADE).
                await s.execute(
                    text("DELETE FROM aziende WHERE organization_id=:o"), {"o": org_id}
                )
                await s.execute(text("DELETE FROM organizations WHERE id=:o"), {"o": org_id})
                await s.commit()
            await engine.dispose()

    return asyncio.run(_go())


def _reachable() -> bool:
    if not _URL:
        return False
    try:
        return (
            _in_one_loop(lambda s, *_: s.execute(text("SELECT 1")), needs_org=False)
            is not None
        )
    except Exception:
        return False


needs_db = pytest.mark.skipif(
    not _reachable(), reason="no reachable Postgres in DATABASE_URL"
)


async def _upsert_photo(s, azienda_id, content: bytes, content_type: str) -> None:
    await s.execute(
        text(
            "INSERT INTO azienda_foto_presentazione"
            " (id, azienda_id, document_image_bytes, content_type, size_bytes)"
            " VALUES (:i, :a, :b, :t, :n)"
            " ON CONFLICT (azienda_id) DO UPDATE SET"
            " document_image_bytes = EXCLUDED.document_image_bytes,"
            " content_type = EXCLUDED.content_type,"
            " size_bytes = EXCLUDED.size_bytes,"
            " updated_at = now()"
        ),
        {
            "i": uuid.uuid4(),
            "a": azienda_id,
            "b": content,
            "t": content_type,
            "n": len(content),
        },
    )
    await s.commit()


def _no_people_no_places() -> dict:
    """What ``generate`` hands ``_load_dvr_extras`` for an azienda with no
    environments and no people (nothing to auto-seed)."""
    return {"ambienti": [], "persone": [], "employee_persons": []}


# Tests that run the off-DB harness (``patch_generators`` in
# ``scripts/verify_all_generators.py``) swap ``_load_dvr_extras`` for a fake
# that never returns a photo, and leave it swapped for the rest of the
# session. Bind the real method now, while this module is collected and
# before any test runs, and call that one.
_load_dvr_extras = DVRMasterGenerator._load_dvr_extras


@needs_db
def test_dvr_extras_load_the_company_photo_from_the_database():
    assert _load_dvr_extras.__qualname__ == "DVRMasterGenerator._load_dvr_extras"
    first, second = _jpeg("teal"), _jpeg("orange")

    async def body(s, _org, azienda_id):
        generator = DVRMasterGenerator(azienda_id, s)

        async def photo():
            extras = await _load_dvr_extras(generator, _no_people_no_places())
            return extras["foto_presentazione"]

        assert await photo() is None

        await _upsert_photo(s, azienda_id, first, "image/jpeg")
        assert await photo() == (first, "image/jpeg")

        # A replaced photo is the one the next generation prints.
        await _upsert_photo(s, azienda_id, second, "image/jpeg")
        assert await photo() == (second, "image/jpeg")

    _in_one_loop(body)
