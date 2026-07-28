"""Role capabilities — the matrix, its wiring, and its client-side mirror.

Two kinds of test here, both structural:

* properties of the matrix itself (it nests, it grants nothing unknown);
* properties of the *codebase* — that the endpoints which must be capability-
  gated actually are. Those read the source rather than call it, matching
  `test_billing_enforcement.py`: a future change can quietly drop a
  `require_capability` without failing any behavioural test, and the whole
  point of a permission is that its absence is silent.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from app.core import permissions as perms

BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"
FRONTEND_PERMISSIONS = BACKEND.parent / "frontend" / "src" / "lib" / "permissions.ts"


# --- The matrix ------------------------------------------------------------


def test_matrix_is_self_consistent():
    """Every grant is a real capability, every role has a label, roles nest."""
    perms.validate_matrix()


def test_admin_holds_everything():
    assert perms.capabilities_for(perms.ROLE_ADMIN) == perms.ALL_CAPABILITIES


@pytest.mark.parametrize(
    "role,capability,expected",
    [
        # The persona split that matters: the field operator collects, the
        # office operator finalises.
        (perms.ROLE_OPERATORE_CAMPO, perms.SURVEY_WRITE, True),
        (perms.ROLE_OPERATORE_CAMPO, perms.ASSESSMENTS_WRITE, True),
        (perms.ROLE_OPERATORE_CAMPO, perms.DOCUMENTS_READ, True),
        (perms.ROLE_OPERATORE_CAMPO, perms.DOCUMENTS_GENERATE, False),
        (perms.ROLE_OPERATORE_UFFICIO, perms.DOCUMENTS_GENERATE, True),
        # Money and membership are the admin's alone.
        (perms.ROLE_OPERATORE_UFFICIO, perms.BILLING_MANAGE, False),
        (perms.ROLE_OPERATORE_UFFICIO, perms.USERS_MANAGE, False),
        (perms.ROLE_OPERATORE_UFFICIO, perms.AZIENDE_CREATE, False),
        (perms.ROLE_ADMIN, perms.BILLING_MANAGE, True),
        # Everyone can see the credit balance they are spending (the tracker).
        (perms.ROLE_OPERATORE_CAMPO, perms.BILLING_READ, True),
        (perms.ROLE_OPERATORE_UFFICIO, perms.BILLING_READ, True),
    ],
)
def test_role_grants(role, capability, expected):
    assert perms.has_capability(role, capability) is expected


def test_unknown_role_gets_the_least_privilege():
    """A row carrying something the matrix does not know must not get admin.

    Roles only enter the database through the validated `users` endpoints, but a
    fixture, a migration or a hand-run UPDATE could still write anything, and
    the safe reading of an unrecognised role is "the smallest set".
    """
    unknown = perms.capabilities_for("chief_vibes_officer")
    assert unknown == perms.capabilities_for(perms.ROLE_OPERATORE_CAMPO)
    assert perms.DOCUMENTS_GENERATE not in unknown
    assert perms.BILLING_MANAGE not in unknown
    assert perms.capabilities_for(None) == unknown


def test_every_role_has_an_italian_label_and_description():
    for role in perms.ALLOWED_ROLES:
        assert perms.role_label(role) != role, f"{role} leaks its identifier to the UI"
        assert perms.ROLE_DESCRIPTIONS.get(role), f"{role} has no description"


# --- The wiring ------------------------------------------------------------


def _python_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def _guarded_capabilities(source: str, function_name: str) -> set[str]:
    """Capabilities named in `require_capability(...)` inside one endpoint.

    Covers both call shapes: a parameter default
    (``user: User = Depends(require_capability(X))``) and a route-level
    ``dependencies=[Depends(require_capability(X))]``, which is what endpoints
    that do not otherwise need the ``User`` use.
    """
    tree = ast.parse(source)
    found: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != function_name:
            continue

        # The decorator carries `dependencies=[...]`; the signature carries the
        # parameter defaults. Both are part of the endpoint's declaration.
        for sub in ast.walk(ast.Module(body=[node], type_ignores=[])):
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Name)
                and sub.func.id == "require_capability"
            ):
                for arg in sub.args:
                    if isinstance(arg, ast.Name):
                        found.add(arg.id)
    return found


GATED_ENDPOINTS = [
    # (module, endpoint function, capability constant name)
    ("documents.py", "generate_document", "DOCUMENTS_GENERATE"),
    ("documents.py", "batch_generate_documents", "DOCUMENTS_GENERATE"),
    ("documents.py", "restore_document", "DOCUMENTS_GENERATE"),
    ("documents.py", "sync_document_from_gdoc", "DOCUMENTS_GENERATE"),
    ("documents.py", "save_edited_version", "DOCUMENTS_GENERATE"),
    ("documents.py", "open_document_for_editing", "DOCUMENTS_GENERATE"),
    ("documents.py", "patch_document_overrides", "DOCUMENTS_GENERATE"),
    ("users.py", "create_user", "USERS_MANAGE"),
    ("users.py", "update_user", "USERS_MANAGE"),
    ("billing.py", "subscribe", "BILLING_MANAGE"),
    ("billing.py", "cancel", "BILLING_MANAGE"),
    ("billing.py", "revise", "BILLING_MANAGE"),
    ("billing.py", "checkout_credits", "BILLING_MANAGE"),
    ("billing.py", "capture_credits", "BILLING_MANAGE"),
    ("billing.py", "list_credit_packs", "BILLING_READ"),
    ("billing.py", "list_credit_purchases", "BILLING_READ"),
]


@pytest.mark.parametrize("module,endpoint,capability", GATED_ENDPOINTS)
def test_endpoint_declares_its_capability(module, endpoint, capability):
    """Each write path that a lesser role must not reach names its capability.

    Reading the source rather than issuing requests: this asserts the *shape* of
    the codebase, so removing a guard fails here even when no behavioural test
    happens to cover that endpoint.
    """
    source = (APP / "api" / "v1" / module).read_text(encoding="utf-8")
    guarded = _guarded_capabilities(source, endpoint)
    assert capability in guarded, (
        f"{module}::{endpoint} must be gated on {capability}; "
        f"found {sorted(guarded) or 'no capability guard at all'}"
    )


def test_no_endpoint_still_hardcodes_the_admin_role():
    """`require_role("admin")` has no remaining call sites in the API layer.

    The helper stays for the case where the *role* really is the rule, but every
    current gate is about a named action. A stray `require_role("admin")` means
    a permission that cannot be granted to anyone else without editing an
    endpoint, which is exactly the coupling the matrix removes.
    """
    offenders = [
        str(path.relative_to(BACKEND))
        for path in _python_files(APP / "api")
        if re.search(r'require_role\(\s*["\']admin["\']', path.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"still gating on the role name: {offenders}"


def test_aziende_creation_and_deletion_stay_admin_only():
    """US-5.1's acceptance criterion, pinned.

    Creating or dropping a client is a portfolio decision — and, on Model A, the
    thing that starts the active-company meter billing. The matrix must not
    widen it to operators without that being a deliberate product change.
    """
    for role in (perms.ROLE_OPERATORE_CAMPO, perms.ROLE_OPERATORE_UFFICIO):
        assert not perms.has_capability(role, perms.AZIENDE_CREATE)
        assert not perms.has_capability(role, perms.AZIENDE_DELETE)


def test_read_and_download_are_never_capability_gated_away_from_operators():
    """D.Lgs. 81/2008 retention has a permissions half, not only a billing one.

    The paywall deliberately never gates reads. The same must hold for roles:
    whoever can see a company can see the documents produced for it, or a
    lapsed-plan tenant's field operator loses access to a DVR the law requires
    be available.
    """
    for role in perms.ALLOWED_ROLES:
        assert perms.has_capability(role, perms.DOCUMENTS_READ)
        assert perms.has_capability(role, perms.AZIENDE_READ)


# --- The client-side mirror ------------------------------------------------


def test_frontend_capability_strings_match_the_backend():
    """`frontend/src/lib/permissions.ts` exports exactly our capability strings.

    The frontend reads its capability *set* from `/auth/me`, so the two cannot
    disagree about who holds what. It does still name the individual strings to
    key its `can(...)` calls on, and a typo there fails silently — the check
    would just always be false, hiding a button forever.
    """
    if not FRONTEND_PERMISSIONS.exists():  # pragma: no cover — backend-only checkout
        pytest.skip("frontend not present in this checkout")

    source = FRONTEND_PERMISSIONS.read_text(encoding="utf-8")
    exported = set(re.findall(r'export const [A-Z_]+ = "([^"]+)";', source))
    assert exported == set(perms.ALL_CAPABILITIES), (
        "capability strings drifted between backend and frontend:\n"
        f"  only in backend:  {sorted(set(perms.ALL_CAPABILITIES) - exported)}\n"
        f"  only in frontend: {sorted(exported - set(perms.ALL_CAPABILITIES))}"
    )


def test_frontend_legacy_fallback_matches_the_backend_matrix():
    """The pre-`capabilities` session fallback grants what the server would.

    Sessions minted before `/auth/me` returned capabilities fall back to a
    role-derived set in the frontend. It is the one place a role is interpreted
    client-side, so it is the one place that can silently disagree with the
    server — hence this check rather than trusting the comment above it.
    """
    if not FRONTEND_PERMISSIONS.exists():  # pragma: no cover
        pytest.skip("frontend not present in this checkout")

    source = FRONTEND_PERMISSIONS.read_text(encoding="utf-8")

    def const_list(name: str) -> list[str]:
        block = re.search(rf"const {name}: Capability\[\] = \[(.*?)\];", source, re.S)
        assert block, f"{name} not found in permissions.ts"
        # Entries are either bare identifiers (the exported consts) or a spread
        # of another list; resolve identifiers through the exported strings.
        names = re.findall(r"\b([A-Z][A-Z_]+)\b", block.group(1))
        values = re.findall(r'export const ([A-Z_]+) = "([^"]+)";', source)
        by_name = dict(values)
        out: list[str] = []
        for n in names:
            if n in by_name:
                out.append(by_name[n])
            else:  # a spread of an earlier list, e.g. `...FIELD`
                out.extend(const_list(n))
        return out

    expected = {
        "admin": perms.capabilities_for(perms.ROLE_ADMIN),
        "OFFICE": perms.capabilities_for(perms.ROLE_OPERATORE_UFFICIO),
        "FIELD": perms.capabilities_for(perms.ROLE_OPERATORE_CAMPO),
    }
    assert set(const_list("ALL")) == expected["admin"]
    assert set(const_list("OFFICE")) == expected["OFFICE"]
    assert set(const_list("FIELD")) == expected["FIELD"]
