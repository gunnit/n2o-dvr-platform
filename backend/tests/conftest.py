"""Shared pytest fixtures."""

import os
import sys
from pathlib import Path

import pytest

# Make backend/ importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def tmp_output_dir(tmp_path_factory):
    """Ephemeral directory for generator output across a test session."""
    return tmp_path_factory.mktemp("dlg_gen_output")


def route_pairs(router) -> set[tuple[str, str]]:
    """All ``(method, full_path)`` pairs a router serves, nested routers included.

    Several tests assert that specific endpoints stay registered. They used to
    read ``api_router.routes`` directly and pull ``.path`` / ``.methods`` off
    each entry, which assumed ``include_router()`` copies child routes onto the
    parent in flattened form.

    FastAPI changed that: on 0.135/starlette 1.0 the parent held flattened
    ``APIRoute`` objects, but on 0.140/starlette 1.3 it holds the child routers
    themselves — ``path`` is ``None`` and ``methods`` is absent. The old
    comprehension then yielded an empty set and every such assertion failed,
    even though the app routes correctly (verified: public endpoint 200,
    protected 401, unknown 404 on both versions).

    Walking recursively works on either version, so these tests no longer
    depend on an undocumented internal layout. `requirements.txt` pins nothing,
    so CI and Render resolve whatever is current — tests must not assume a
    version the lockfile doesn't guarantee.

    Implemented via the OpenAPI schema rather than by walking internals: it is
    a public, documented interface that reports exactly the paths and methods
    FastAPI will actually serve, on any version.
    """
    from fastapi import FastAPI

    probe = FastAPI()
    probe.include_router(router)
    spec = probe.openapi()
    return {
        (method.upper(), path)
        for path, operations in spec.get("paths", {}).items()
        for method in operations
        if method.lower() in {"get", "post", "put", "patch", "delete", "head", "options"}
    }
