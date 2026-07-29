"""Structural guarantees about where the paywall is wired (Phase 2).

These tests read the source rather than call it. That is the point: they assert
properties of the *codebase* that a future change could quietly break without
failing any behavioral test — a new endpoint that dispatches a generation task
directly, or an AI call that slipped in ahead of its credit check.

INV-5: the paywall is server-side. Frontend gating is cosmetic; if a path can
reach the worker or OpenAI without passing a gate, the paywall has a hole.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"
DOCUMENTS = APP / "api" / "v1" / "documents.py"


def _python_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


# --- MB-2.2: one guarded dispatch site ------------------------------------


def _delay_call_sites() -> list[tuple[str, int, str]]:
    """Every real `<something>.delay(...)` call in the app, as (file, line, enclosing func).

    Parsed rather than grepped so that prose mentioning ``.delay(`` — including
    this module's own docstrings — is not mistaken for a dispatch.
    """
    sites: list[tuple[str, int, str]] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self, rel: str) -> None:
            self.rel = rel
            self.stack: list[str] = ["<module>"]

        def _visit_func(self, node):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        visit_FunctionDef = _visit_func
        visit_AsyncFunctionDef = _visit_func

        def visit_Call(self, node: ast.Call) -> None:
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "delay"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "generate_document_task"
            ):
                sites.append((self.rel, node.lineno, self.stack[-1]))
            self.generic_visit(node)

    for path in _python_files(APP):
        Visitor(str(path.relative_to(BACKEND)).replace("\\", "/")).visit(
            ast.parse(path.read_text(encoding="utf-8"))
        )
    return sorted(sites)


def test_generation_is_dispatched_from_exactly_one_place():
    """`generate_document_task.delay(...)` may be called only inside
    `_enqueue_generation`, which checks the doc-type gate first.

    A second call site would be a paywall bypass — the whole reason the plan
    asks for this helper.
    """
    sites = _delay_call_sites()
    assert len(sites) == 1, f"expected exactly one dispatch site, found: {sites}"
    path, _lineno, enclosing = sites[0]
    assert path == "app/api/v1/documents.py"
    assert enclosing == "_enqueue_generation", (
        f"generation is dispatched from {enclosing!r}; it must go through "
        "_enqueue_generation so the doc-type gate cannot be bypassed"
    )


def test_enqueue_helper_checks_the_doc_type_gate():
    tree = ast.parse(DOCUMENTS.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_enqueue_generation":
            calls = {
                n.func.id
                for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            }
            assert "ensure_doc_type_allowed" in calls
            return
    pytest.fail("_enqueue_generation not found")


# --- MB-2.1: both chokepoints resolve entitlements -------------------------


@pytest.mark.parametrize("endpoint", ["generate_document", "batch_generate_documents"])
def test_generation_endpoints_depend_on_entitlements(endpoint):
    """Both must take `ent: Entitlements = Depends(get_entitlements)`.

    Resolving per request is INV-3 — entitlements are never read from the JWT,
    so an upgrade or a credit exhaustion takes effect immediately.
    """
    tree = ast.parse(DOCUMENTS.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == endpoint:
            args = [a.arg for a in node.args.args + node.args.kwonlyargs]
            assert "ent" in args, f"{endpoint} does not resolve entitlements"
            src = ast.get_source_segment(
                DOCUMENTS.read_text(encoding="utf-8"), node
            )
            assert "get_entitlements" in src
            return
    pytest.fail(f"{endpoint} not found")


# --- MB-2.3: every completed-row path records the activation ---------------


def test_all_completion_paths_record_the_activation():
    """Four paths mint a `status="completed"` row. Each must record the
    company as active, or a consultant could generate unlimited companies by
    routing through restore / gdoc-sync / save-edited-version."""
    source = DOCUMENTS.read_text(encoding="utf-8")
    completed = [
        lineno
        for lineno, line in enumerate(source.splitlines(), 1)
        if re.search(r'status\s*=\s*"completed"', line)
    ]
    recorded = [
        lineno
        for lineno, line in enumerate(source.splitlines(), 1)
        if "record_activation_for_azienda(" in line and "import" not in line
    ]
    assert len(completed) == 3, (
        f"expected 3 direct-completion paths in documents.py, found {len(completed)} "
        f"at lines {completed} — a new one must also record the activation"
    )
    assert len(recorded) == 3, (
        f"expected 3 activation records, found {len(recorded)} at {recorded}"
    )
    # The worker's own completion path is the fourth.
    worker = (APP / "tasks" / "document_tasks.py").read_text(encoding="utf-8")
    assert "record_activation_for_azienda(" in worker


def test_direct_completion_paths_are_gated_not_just_metered():
    """Recording an activation is accounting; it is not a gate (MB-6.2).

    The three endpoints that mint a completed row without going through the
    worker used to record the activation and never ask whether the tenant was
    allowed to produce it — a canceled subscription could still emit versions,
    and an activation could silently exceed the active-company ceiling. Each
    must now take an `ent` dependency and funnel through
    `_ensure_new_version_allowed`, which applies the same three gates
    `/generate` does.
    """
    source = DOCUMENTS.read_text(encoding="utf-8")
    tree = ast.parse(source)
    bypass_endpoints = {
        "restore_document",
        "sync_document_from_gdoc",
        "save_edited_version",
    }
    seen: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef) or node.name not in bypass_endpoints:
            continue
        seen.add(node.name)
        args = {a.arg for a in node.args.args + node.args.kwonlyargs}
        assert "ent" in args, (
            f"{node.name} mints a completed version but takes no entitlements "
            "dependency — it would bypass the paywall (INV-5)"
        )
        calls = {
            n.func.id
            for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        assert "_ensure_new_version_allowed" in calls, (
            f"{node.name} must call _ensure_new_version_allowed before writing a "
            "new version"
        )
    assert seen == bypass_endpoints, f"endpoint(s) renamed or removed: {bypass_endpoints - seen}"


def test_creating_an_azienda_is_gated():
    """`create_azienda` is where a direct tenant's `max_sites` is sold and, until
    MB-6.2, never enforced — `ensure_site_slot` had zero call sites."""
    aziende = (APP / "api" / "v1" / "aziende.py").read_text(encoding="utf-8")
    tree = ast.parse(aziende)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "create_azienda":
            args = {a.arg for a in node.args.args + node.args.kwonlyargs}
            assert "ent" in args, "create_azienda takes no entitlements dependency"
            calls = {
                n.func.id
                for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            }
            assert "_ensure_can_add_azienda" in calls
            break
    else:  # pragma: no cover - the endpoint disappearing is itself the failure
        raise AssertionError("create_azienda not found in aziende.py")
    assert "ensure_site_slot(" in aziende, "the site limit is sold but unenforced"


# --- cross-tenant endpoints ------------------------------------------------


def test_every_cross_tenant_endpoint_is_platform_gated():
    """An endpoint that names an ``organization_id`` needs platform authority.

    Every other endpoint acts on `get_current_org()` — the caller's own tenant —
    so the capability system is the whole answer. One that takes the id as a
    path parameter is different in kind, and guarding it on `billing:manage`
    made the admin plan endpoint a free-plan dispenser: signing up makes you the
    admin of your own organization, so every customer held the capability, and
    the id being a parameter meant they could also name someone else's.

    Reads the decorators rather than calling them so a *new* cross-tenant
    endpoint fails here on the day it is written.
    """
    offenders: list[str] = []
    for path in _python_files(APP / "api"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = str(path.relative_to(BACKEND)).replace("\\", "/")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            routes = [
                d.args[0].value
                for d in node.decorator_list
                if isinstance(d, ast.Call)
                and d.args
                and isinstance(d.args[0], ast.Constant)
                and isinstance(d.args[0].value, str)
            ]
            if not any("{organization_id}" in r for r in routes):
                continue
            guards = {
                n.func.id
                for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            } | {
                n.id for n in ast.walk(node) if isinstance(n, ast.Name)
            }
            if "require_platform_admin" not in guards:
                offenders.append(f"{rel}:{node.lineno} {node.name}")

    assert not offenders, (
        "endpoint(s) take an organization_id without require_platform_admin — "
        f"any tenant admin could act on any tenant: {offenders}"
    )


# --- INV-8: the seam holds -------------------------------------------------


def test_generators_and_calculators_never_import_billing():
    """Belt and braces alongside .importlinter — this one runs in the default
    test suite even where lint-imports isn't installed."""
    offenders = []
    for sub in ("services/document_generator", "services/ai"):
        for path in _python_files(APP / sub):
            text = path.read_text(encoding="utf-8")
            if re.search(r"^\s*(from|import)\s+app\.billing", text, re.M):
                offenders.append(str(path.relative_to(BACKEND)))
    assert not offenders, f"regulatory/AI code must not import billing: {offenders}"


def test_ai_client_has_no_billing_concepts():
    """services/ai/client.py stays the OpenAI + privacy boundary. Metering
    happens one layer up, at the endpoint, where org and db are in scope."""
    client = (APP / "services" / "ai" / "client.py").read_text(encoding="utf-8")
    for term in ("credit", "entitle", "billing", "spend_credits"):
        assert term not in client.lower(), f"{term!r} leaked into the AI client"
