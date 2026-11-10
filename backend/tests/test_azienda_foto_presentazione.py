"""Company presentation photo: storage, API gates and the generator loader.

The endpoint functions are called directly (as the rest of the suite does) with
a real session, so the DB-backed tests need a reachable Postgres and skip
without one; CI provides it. The route-dependency test is structural and always
runs.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from io import BytesIO
from typing import Any, Callable

import pillow_heif
import pytest
from fastapi import UploadFile
from fastapi.responses import Response
from PIL import Image
from sqlalchemy import text

from app.api.v1 import azienda_foto_presentazione as api
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.permissions import SURVEY_WRITE
from app.db.session import _normalize_async_url
from app.services.document_generator.data_loader import load_foto_presentazione

_URL = (
    _normalize_async_url(os.environ["DATABASE_URL"])
    if os.environ.get("DATABASE_URL")
    else None
)
BAD_FORMAT = "Formato non supportato o file troppo grande (max 10 MB)"


# --- Structural (no DB) -----------------------------------------------------


def _route(method: str):
    for route in api.router.routes:
        if method in getattr(route, "methods", set()):
            return route
    raise AssertionError(f"no {method} route")


def _capability_checks(route):
    """The ``_check`` closures `require_capability(...)` put on the route."""
    return [
        dep.call
        for dep in route.dependant.dependencies
        if getattr(dep.call, "__qualname__", "").startswith("require_capability.")
        and any(
            isinstance(cell.cell_contents, tuple) and SURVEY_WRITE in cell.cell_contents
            for cell in dep.call.__closure__ or ()
        )
    ]


def _declares_survey_write(route) -> bool:
    return bool(_capability_checks(route))


def test_paths_are_under_aziende():
    paths = {r.path for r in api.router.routes}
    assert paths == {"/aziende/{azienda_id}/foto-presentazione"}


@pytest.mark.parametrize("method", ["PUT", "DELETE"])
def test_write_routes_declare_survey_write(method):
    assert _declares_survey_write(_route(method))


@pytest.mark.parametrize("method", ["PUT", "DELETE"])
def test_write_routes_refuse_a_role_without_survey_write(method, monkeypatch):
    """Every real role holds SURVEY_WRITE, so withdraw it to exercise the gate."""
    from types import SimpleNamespace

    from fastapi import HTTPException

    monkeypatch.setattr("app.dependencies.has_capability", lambda role, cap: False)
    check = _capability_checks(_route(method))[0]
    with pytest.raises(HTTPException) as exc:
        asyncio.run(check(user=SimpleNamespace(role="no-such-role")))
    assert exc.value.status_code == 403


def test_get_is_not_capability_gated():
    assert not _declares_survey_write(_route("GET"))


def test_router_is_registered():
    from app.api.v1.router import api_router
    from tests.conftest import route_pairs

    assert ("PUT", "/api/v1/aziende/{azienda_id}/foto-presentazione") in route_pairs(
        api_router
    )


# --- DB-backed --------------------------------------------------------------


def _png(size=(64, 48), color="blue") -> bytes:
    out = BytesIO()
    Image.new("RGB", size, color).save(out, format="PNG")
    return out.getvalue()


def _heic() -> bytes:
    out = BytesIO()
    pillow_heif.from_pillow(Image.new("RGB", (48, 32), "green")).save(out)
    return out.getvalue()


def _upload(content: bytes, filename="logo.png", content_type="image/png"):
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers={"content-type": content_type},
    )


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
                        {"i": org_id, "n": f"pytest-foto-{org_id}"},
                    )
                    await s.execute(
                        text(
                            "INSERT INTO aziende (id, organization_id, ragione_sociale, survey_status)"
                            " VALUES (:a, :o, 'Foto SRL', 'draft')"
                        ),
                        {"a": azienda_id, "o": org_id},
                    )
                    await s.commit()
                return await body(s, org_id, azienda_id)
        finally:
            async with factory() as s:
                # Photo rows go with the azienda (ON DELETE CASCADE).
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


async def _rows(s, azienda_id):
    r = await s.execute(
        text(
            "SELECT document_image_bytes, content_type, size_bytes"
            " FROM azienda_foto_presentazione WHERE azienda_id=:a"
        ),
        {"a": azienda_id},
    )
    return r.all()


@needs_db
def test_put_stores_normalised_bytes():
    async def body(s, org, az):
        out = await api.put_foto_presentazione(az, _upload(_png()), org, s)
        assert out.azienda_id == az
        assert out.content_type == "image/jpeg"
        rows = await _rows(s, az)
        assert len(rows) == 1
        stored, ctype, size = rows[0]
        assert bytes(stored)[:3] == b"\xff\xd8\xff"  # normalised JPEG, not the PNG
        assert ctype == "image/jpeg"
        assert size == len(bytes(stored)) == out.size_bytes

    _in_one_loop(body)


@needs_db
def test_put_replaces_existing():
    async def body(s, org, az):
        await api.put_foto_presentazione(az, _upload(_png(color="red")), org, s)
        first = bytes((await _rows(s, az))[0][0])
        await api.put_foto_presentazione(
            az, _upload(_png(size=(200, 100), color="green")), org, s
        )
        rows = await _rows(s, az)
        assert len(rows) == 1
        assert bytes(rows[0][0]) != first

    _in_one_loop(body)


@needs_db
def test_get_returns_image_or_404():
    async def body(s, org, az):
        with pytest.raises(NotFoundError):
            await api.get_foto_presentazione(az, org, s)
        await api.put_foto_presentazione(az, _upload(_png()), org, s)
        resp = await api.get_foto_presentazione(az, org, s)
        assert isinstance(resp, Response)
        assert resp.media_type == "image/jpeg"
        assert resp.body[:3] == b"\xff\xd8\xff"

    _in_one_loop(body)


@needs_db
def test_delete_removes():
    async def body(s, org, az):
        await api.put_foto_presentazione(az, _upload(_png()), org, s)
        out = await api.delete_foto_presentazione(az, org, s)
        assert out.status_code == 204
        assert await _rows(s, az) == []
        with pytest.raises(NotFoundError):
            await api.get_foto_presentazione(az, org, s)

    _in_one_loop(body)


@needs_db
def test_other_org_gets_404():
    async def body(s, org, az):
        await api.put_foto_presentazione(az, _upload(_png()), org, s)
        stranger = uuid.uuid4()
        with pytest.raises(NotFoundError):
            await api.get_foto_presentazione(az, stranger, s)
        with pytest.raises(NotFoundError):
            await api.put_foto_presentazione(az, _upload(_png()), stranger, s)
        with pytest.raises(NotFoundError):
            await api.delete_foto_presentazione(az, stranger, s)
        assert len(await _rows(s, az)) == 1

    _in_one_loop(body)


@needs_db
def test_rejects_gif_and_over_10mb():
    async def body(s, org, az):
        gif = BytesIO()
        Image.new("RGB", (8, 8)).save(gif, format="GIF")
        with pytest.raises(BadRequestError) as exc:
            await api.put_foto_presentazione(
                az, _upload(gif.getvalue(), "a.gif", "image/gif"), org, s
            )
        assert exc.value.detail == BAD_FORMAT
        big = _png() + b"\0" * (10 * 1024 * 1024 + 1)
        with pytest.raises(BadRequestError) as exc:
            await api.put_foto_presentazione(az, _upload(big), org, s)
        assert exc.value.detail == BAD_FORMAT
        # A whitelisted type that is not really an image is rejected too.
        with pytest.raises(BadRequestError):
            await api.put_foto_presentazione(az, _upload(b"not an image"), org, s)
        assert await _rows(s, az) == []

    _in_one_loop(body)


@needs_db
def test_heic_is_converted_to_jpeg():
    async def body(s, org, az):
        await api.put_foto_presentazione(
            az, _upload(_heic(), "a.heic", "image/heic"), org, s
        )
        stored, ctype, _ = (await _rows(s, az))[0]
        assert ctype == "image/jpeg"
        assert bytes(stored)[:3] == b"\xff\xd8\xff"

    _in_one_loop(body)


@needs_db
def test_loader_returns_bytes_and_type_or_none():
    async def body(s, org, az):
        assert await load_foto_presentazione(s, az) is None
        await api.put_foto_presentazione(az, _upload(_png()), org, s)
        loaded = await load_foto_presentazione(s, az)
        assert loaded is not None
        content, ctype = loaded
        assert ctype == "image/jpeg" and content[:3] == b"\xff\xd8\xff"

    _in_one_loop(body)
