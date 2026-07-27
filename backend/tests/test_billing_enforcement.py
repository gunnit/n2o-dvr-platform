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
