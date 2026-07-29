"""Generate ``docs/qa/feature-map.yaml`` — the executable inventory of the app.

Why this exists
---------------
A hand-written feature list is stale the week after it is written, and nobody
diffs prose. This derives the inventory from the code instead:

* the **route table** comes from the FastAPI app itself, so it is exactly what
  the server will serve — not a grep for ``@router.`` that misses
  ``add_api_route`` and the second router in ``documents.py``;
* the **guards** on each route come from parsing ``app/api/v1/*.py``, matching
  the approach already used by ``tests/test_billing_enforcement.py`` and
  ``tests/test_permissions.py``: a missing guard is silent at runtime, so the
  only way to notice one disappearing is to read the shape of the source;
* the **UI cross-reference** comes from the ``/api/v1/...`` string literals in
  ``frontend/src``, which is how every call is actually spelled (``apiCall``
  takes a path).

The output is deliberately **deterministic and timestamp-free** so that
``tests/test_feature_map.py`` can diff a fresh render against the committed
file. Any new, renamed or removed endpoint fails that test until the manifest
is regenerated and the diff reviewed — which is the whole point. The file is
the reviewable artifact; :func:`build_manifest` is what a test suite consumes.

Usage
-----
    python scripts/build_feature_map.py            # print the manifest
    python scripts/build_feature_map.py --write    # write docs/qa/feature-map.yaml
    python scripts/build_feature_map.py --check    # exit 1 if the file is stale

On this machine the backend deps live in a Linux-layout venv, so::

    wsl -e bash -lc 'cd /mnt/c/Dev/dlg/backend && \
      PYTHONPATH=.venv/lib/python3.12/site-packages:. python3 scripts/build_feature_map.py --write'
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
API_DIR = BACKEND / "app" / "api" / "v1"
FRONTEND_SRC = REPO / "frontend" / "src"
FRONTEND_APP = FRONTEND_SRC / "app"
MANIFEST = REPO / "docs" / "qa" / "feature-map.yaml"

sys.path.insert(0, str(BACKEND))

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

#: Dependencies that mean "this endpoint requires a signed-in user". Any of
#: them anywhere in the endpoint's declaration is enough — ``get_entitlements``
#: and the capability guards all resolve ``get_current_user`` underneath.
AUTH_DEPENDENCIES = frozenset(
    {
        "get_current_user",
        "get_current_org",
        "get_current_capabilities",
        "get_entitlements",
        "require_capability",
        "_require_capability",
        "require_role",
        "require_platform_admin",
    }
)


# --------------------------------------------------------------------------
# Backend: the route table
# --------------------------------------------------------------------------


def _iter_api_routes(routes: Iterable[Any]) -> Iterator[Any]:
    """Yield every ``APIRoute``, descending into nested routers.

    ``include_router()`` used to flatten children onto the parent; on newer
    FastAPI/starlette it keeps the child router as a single entry whose own
    ``.routes`` hold the endpoints. Recursing works on both, which is the same
    hazard ``tests/conftest.py:route_pairs`` documents.
    """
    from fastapi.routing import APIRoute

    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif hasattr(route, "routes"):
            yield from _iter_api_routes(route.routes)


def collect_routes() -> list[dict[str, Any]]:
    """Every (method, path) the API serves, with its endpoint function."""
    from fastapi import FastAPI

    from app.api.v1.router import api_router

    probe = FastAPI()
    probe.include_router(api_router)

    rows: list[dict[str, Any]] = []
    for route in _iter_api_routes(probe.routes):
        for method in sorted(route.methods or set()):
            if method in {"HEAD", "OPTIONS"}:
                continue
            rows.append(
                {
                    "method": method,
                    "path": route.path,
                    "module": route.endpoint.__module__,
                    "function": route.endpoint.__name__,
                    "tags": [str(t) for t in (route.tags or [])],
                    "in_schema": bool(route.include_in_schema),
                }
            )
    return rows


# --------------------------------------------------------------------------
# Backend: the guards, read out of the source
# --------------------------------------------------------------------------


def _capability_values() -> dict[str, str]:
    """``{"DOCUMENTS_GENERATE": "documents:generate", ...}`` plus the reverse."""
    from app.core import permissions as perms

    by_name = {
        name: getattr(perms, name)
        for name in dir(perms)
        if name.isupper() and isinstance(getattr(perms, name), str)
    }
    return {n: v for n, v in by_name.items() if v in perms.ALL_CAPABILITIES}


class _ModuleFacts:
    """Guard facts for every function in one ``app/api/v1/*.py``.

    Endpoints often delegate to a module-private helper — ``documents.py`` has
    ``_ensure_new_version_allowed``, ``aziende.py`` has
    ``_ensure_can_add_azienda`` — so the gates an endpoint *effectively* applies
    are not all spelled in its own body. Local calls are therefore resolved
    transitively, with a cycle guard.
    """

    def __init__(self, path: Path, capability_by_name: dict[str, str]) -> None:
        self.path = path
        self.caps = capability_by_name
        self.cap_values = set(capability_by_name.values())
        self.source = path.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

        self.direct: dict[str, dict[str, set[str]]] = {}
        self.local_calls: dict[str, set[str]] = {}
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.direct[node.name] = self._scan(node)
                self.local_calls[node.name] = self._called_names(node)

    # -- scanning one function ------------------------------------------

    def _resolve_capability(self, node: ast.expr) -> str | None:
        """A capability *value* from a constant name, attribute or literal."""
        if isinstance(node, ast.Name):
            return self.caps.get(node.id)
        if isinstance(node, ast.Attribute):  # e.g. perms.DOCUMENTS_GENERATE
            return self.caps.get(node.attr)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value if node.value in self.cap_values else None
        return None

    def _scan(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, set[str]]:
        """Guards named directly in one function — decorators, signature, body.

        Walking the whole node covers all three call shapes in this codebase:
        a route-level ``dependencies=[Depends(require_capability(X))]``, a
        parameter default ``user: User = Depends(require_capability(X))``, and
        the in-body ``_require_capability(user, X, "...")`` helper.
        """
        found: dict[str, set[str]] = {
            "capabilities": set(),
            "billing_gates": set(),
            "credit_kinds": set(),
            "auth_deps": set(),
        }

        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in AUTH_DEPENDENCIES:
                found["auth_deps"].add(sub.id)
            if not isinstance(sub, ast.Call):
                continue
            name = (
                sub.func.id
                if isinstance(sub.func, ast.Name)
                else sub.func.attr
                if isinstance(sub.func, ast.Attribute)
                else ""
            )

            if name in {"require_capability", "_require_capability"}:
                # Filter by "does this argument resolve to a real capability"
                # rather than by position, so both the bare
                # `require_capability(X, Y)` and the `(user, X, "action")`
                # helper are read correctly.
                for arg in sub.args:
                    value = self._resolve_capability(arg)
                    if value:
                        found["capabilities"].add(value)

            if name.lstrip("_").startswith("ensure_"):
                found["billing_gates"].add(name)

            if name == "metered":
                # metered(org_id, "<kind>", key, db, ent)
                for arg in sub.args[1:3]:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        found["credit_kinds"].add(arg.value)
                        break

        return found

    def _called_names(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
        return {
            sub.func.id
            for sub in ast.walk(node)
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
        }

    # -- transitive resolution -------------------------------------------

    def effective(self, function: str) -> dict[str, set[str]]:
        merged: dict[str, set[str]] = {
            "capabilities": set(),
            "billing_gates": set(),
            "credit_kinds": set(),
            "auth_deps": set(),
        }
        seen: set[str] = set()
        stack = [function]
        while stack:
            name = stack.pop()
            if name in seen or name not in self.direct:
                continue
            seen.add(name)
            for key, values in self.direct[name].items():
                merged[key] |= values
            stack.extend(self.local_calls.get(name, set()) - seen)
        return merged


def load_module_facts(capability_by_name: dict[str, str]) -> dict[str, _ModuleFacts]:
    """Facts keyed by dotted module name, e.g. ``app.api.v1.aziende``."""
    facts: dict[str, _ModuleFacts] = {}
    for path in sorted(API_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        facts[f"app.api.v1.{path.stem}"] = _ModuleFacts(path, capability_by_name)
    return facts


# --------------------------------------------------------------------------
# Frontend
# --------------------------------------------------------------------------

_ROUTE_GROUP = re.compile(r"^\(.*\)$")
_TEMPLATE_HOLE = re.compile(r"\$\{[^}]*\}")
_PATH_LITERAL = re.compile(r"""["'`](/api/v1/[^"'`]*)["'`]""")


def collect_frontend_pages() -> list[dict[str, str]]:
    """Every Next.js App Router page, as the URL a user can actually visit."""
    if not FRONTEND_APP.exists():
        return []
    pages: list[dict[str, str]] = []
    for path in sorted(FRONTEND_APP.rglob("page.tsx")):
        segments = [
            part
            for part in path.relative_to(FRONTEND_APP).parent.parts
            if not _ROUTE_GROUP.match(part)  # (dashboard), (auth) — grouping only
        ]
        pages.append(
            {
                "route": "/" + "/".join(segments) if segments else "/",
                "file": path.relative_to(REPO).as_posix(),
            }
        )
    return pages


def normalize_path(path: str) -> str:
    """Collapse a path to its shape so backend and frontend spellings match.

    ``/api/v1/aziende/{azienda_id}/ambienti`` and
    ``/api/v1/aziende/${aziendaId}/ambienti`` are the same endpoint; the
    parameter *names* never agreed and never needed to.
    """
    path = _TEMPLATE_HOLE.sub("{}", path).split("?", 1)[0]
    path = re.sub(r"\{[^}]*\}", "{}", path)
    return path.rstrip("/") or "/"


def collect_frontend_api_calls() -> dict[str, list[str]]:
    """``{normalized path: [source files]}`` for every ``/api/v1/...`` literal."""
    if not FRONTEND_SRC.exists():
        return {}
    calls: dict[str, set[str]] = defaultdict(set)
    for path in sorted(FRONTEND_SRC.rglob("*.ts*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        for raw in _PATH_LITERAL.findall(path.read_text(encoding="utf-8")):
            calls[normalize_path(raw)].add(path.relative_to(REPO).as_posix())
    return {path: sorted(files) for path, files in sorted(calls.items())}


# --------------------------------------------------------------------------
# The manifest
# --------------------------------------------------------------------------


def build_manifest() -> dict[str, Any]:
    from app.core import permissions as perms

    capability_by_name = _capability_values()
    facts = load_module_facts(capability_by_name)
    ui_calls = collect_frontend_api_calls()
    pages = collect_frontend_pages()

    endpoints: list[dict[str, Any]] = []
    for route in collect_routes():
        module_facts = facts.get(route["module"])
        guards = (
            module_facts.effective(route["function"])
            if module_facts
            else {k: set() for k in ("capabilities", "billing_gates", "credit_kinds", "auth_deps")}
        )
        capabilities = sorted(guards["capabilities"])
        authenticated = bool(guards["auth_deps"])
        # Cross-tenant endpoints are guarded by a deploy-time allowlist, not by
        # any capability — every tenant admin holds `billing:manage`, which is
        # exactly why that gate could not be used here. Tracked separately so
        # the unguarded-write review does not accuse them.
        platform_admin = "require_platform_admin" in guards["auth_deps"]

        # Which personas the server will actually let through. Derived from the
        # matrix rather than restated, so widening a role's grants updates this
        # file instead of contradicting it.
        if not authenticated:
            roles = ["public"]
        elif platform_admin:
            roles = ["platform_admin"]
        elif not capabilities:
            roles = sorted(perms.ALLOWED_ROLES)
        else:
            roles = sorted(
                role
                for role in perms.ALLOWED_ROLES
                if all(perms.has_capability(role, cap) for cap in capabilities)
            )

        normalized = normalize_path(route["path"])
        endpoints.append(
            {
                "id": f"{route['module'].rsplit('.', 1)[-1]}.{route['function']}",
                "method": route["method"],
                "path": route["path"],
                "area": route["tags"][0] if route["tags"] else route["module"].rsplit(".", 1)[-1],
                "source": f"backend/app/api/v1/{route['module'].rsplit('.', 1)[-1]}.py",
                "function": route["function"],
                "auth": "required" if authenticated else "public",
                "capabilities": capabilities,
                "roles_allowed": roles,
                "platform_admin": platform_admin,
                "billing_gates": sorted(guards["billing_gates"]),
                "ai_credits": sorted(guards["credit_kinds"]),
                "called_by_ui": normalized in ui_calls,
                "in_openapi": route["in_schema"],
            }
        )

    endpoints.sort(key=lambda e: (e["path"], e["method"]))

    served = {normalize_path(e["path"]) for e in endpoints}
    by_area: dict[str, int] = defaultdict(int)
    for endpoint in endpoints:
        by_area[endpoint["area"]] += 1

    # --- the review section: what the inventory reveals ------------------
    unguarded_writes = [
        f"{e['method']} {e['path']}"
        for e in endpoints
        if e["method"] in WRITE_METHODS
        and not e["capabilities"]
        and not e["platform_admin"]
        and e["auth"] == "required"
    ]
    # A capability the matrix grants but no endpoint ever asks for is decorative:
    # narrowing a role would change nothing, silently.
    granted = {cap for role in perms.ALLOWED_ROLES for cap in perms.capabilities_for(role)}
    enforced = {cap for e in endpoints for cap in e["capabilities"]}
    unenforced_capabilities = sorted(granted - enforced)
    public_endpoints = [f"{e['method']} {e['path']}" for e in endpoints if e["auth"] == "public"]
    no_ui_caller = [
        f"{e['method']} {e['path']}" for e in endpoints if not e["called_by_ui"]
    ]
    ui_without_route = [path for path in ui_calls if path not in served]

    return {
        "version": 1,
        "totals": {
            "endpoints": len(endpoints),
            "areas": len(by_area),
            "frontend_pages": len(pages),
            "ui_api_call_sites": len(ui_calls),
            "capability_gated": sum(1 for e in endpoints if e["capabilities"]),
            "billing_gated": sum(1 for e in endpoints if e["billing_gates"]),
            "ai_metered": sum(1 for e in endpoints if e["ai_credits"]),
        },
        "endpoints_by_area": [
            {"area": area, "endpoints": count} for area, count in sorted(by_area.items())
        ],
        "review": {
            "unenforced_capabilities": unenforced_capabilities,
            "unguarded_writes": unguarded_writes,
            "public_endpoints": public_endpoints,
            "endpoints_with_no_ui_caller": no_ui_caller,
            "ui_calls_without_a_matching_route": ui_without_route,
        },
        "endpoints": endpoints,
        "frontend_pages": pages,
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

HEADER = """\
# GENERATED FILE - do not edit by hand.
#
# The inventory of every feature this app exposes: each API endpoint with the
# guards that actually apply to it, plus the pages that call them. Derived from
# the code, so it cannot describe an app that does not exist.
#
# Regenerate:
#   python backend/scripts/build_feature_map.py --write
#
# backend/tests/test_feature_map.py diffs a fresh render against this file, so
# adding an endpoint fails the build until the manifest is regenerated. Read
# the diff: a new row with an empty `capabilities` or `billing_gates` is the
# question this file exists to ask.
#
# Fields per endpoint:
#   auth            required | public  (does any auth dependency resolve?)
#   capabilities    app/core/permissions.py -- answers 403
#   roles_allowed   derived from the capability matrix, not restated
#   billing_gates   app/billing/gates.py    -- answers 402
#   ai_credits      credit kinds this endpoint meters via `metered(...)`
#   called_by_ui    a /api/v1 literal in frontend/src matches this path
"""


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render(value: Any, indent: int) -> list[str]:
    pad = " " * indent
    lines: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}{key}:")
                lines.extend(_render(item, indent + 2))
            elif isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}: []" if isinstance(item, list) else f"{pad}{key}: {{}}")
            else:
                lines.append(f"{pad}{key}: {_scalar(item)}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                rendered = _render(item, indent + 2)
                lines.append(f"{pad}- {rendered[0].lstrip()}")
                lines.extend(rendered[1:])
            else:
                lines.append(f"{pad}- {_scalar(item)}")
    return lines


def render(manifest: dict[str, Any]) -> str:
    return HEADER + "\n" + "\n".join(_render(manifest, 0)) + "\n"


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write docs/qa/feature-map.yaml")
    parser.add_argument("--check", action="store_true", help="exit 1 if the manifest is stale")
    args = parser.parse_args()

    text = render(build_manifest())

    if args.check:
        current = MANIFEST.read_text(encoding="utf-8") if MANIFEST.exists() else ""
        if current != text:
            print("feature-map.yaml is stale - rerun with --write", file=sys.stderr)
            return 1
        print("feature-map.yaml is up to date")
        return 0

    if args.write:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(text, encoding="utf-8")
        print(f"wrote {MANIFEST.relative_to(REPO).as_posix()} ({len(text.splitlines())} lines)")
        return 0

    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
